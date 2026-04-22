"""Pipeline API endpoints."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from threading import Thread
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from server import log_store
from server.models import AppConfig
from server.pipeline_service import run_pipeline
from server.sse import create_run, event_stream, remove_run

router = APIRouter()

_status: dict = {"status": "idle", "last_run_at": None, "run_id": None}

_DECISION_TREE_KEY = "__decision_tree_json__"
FIXTURE_DIR = "tests/fixtures/emails"


def get_db():
    from server.db import get_engine
    from server.main import DB_URL

    engine = get_engine(DB_URL)
    s = sessionmaker(bind=engine)()
    try:
        yield s
    finally:
        s.close()


DbDep = Annotated[Session, Depends(get_db)]


@router.get("/status")
def pipeline_status():
    return _status


@router.post("/run")
async def pipeline_run(db: DbDep, fixture: bool = Query(default=False)):
    run_id = str(uuid.uuid4())
    _status["status"] = "running"
    _status["run_id"] = run_id
    queue = create_run(run_id)

    _tree_row = db.query(AppConfig).filter_by(key=_DECISION_TREE_KEY).first()
    decision_tree = json.loads(_tree_row.value) if _tree_row else None
    if decision_tree is None:
        log_store.append("Warning: no decision tree in DB — emails will not be routed")

    fixture_messages = None
    if fixture:
        from src.itselectric.fixture import load_fixture_messages

        try:
            fixture_messages = load_fixture_messages(FIXTURE_DIR)
        except FileNotFoundError:
            fixture_messages = []

    loop = asyncio.get_running_loop()

    def _log(msg: str) -> None:
        from server import log_store
        log_store.append(msg)
        loop.call_soon_threadsafe(queue.put_nowait, msg)

    def _run() -> None:
        try:
            run_pipeline(
                db,
                decision_tree=decision_tree,
                log=_log,
                fixture_messages=fixture_messages,
            )
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)
            _status["status"] = "idle"
            _status["last_run_at"] = datetime.now(timezone.utc).isoformat()
            _status["run_id"] = None
            remove_run(run_id)

    Thread(target=_run, daemon=True).start()
    return {"run_id": run_id}


@router.get("/stream/{run_id}")
async def pipeline_stream(run_id: str):
    return StreamingResponse(event_stream(run_id), media_type="text/event-stream")
