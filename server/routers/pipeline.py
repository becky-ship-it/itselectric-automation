"""Pipeline API endpoints."""

import asyncio
import uuid
from datetime import datetime, timezone
from threading import Thread
from typing import Annotated

import yaml  # type: ignore
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from server.pipeline_service import run_pipeline
from server.sse import create_run, event_stream, remove_run

router = APIRouter()

_status: dict = {"status": "idle", "last_run_at": None, "run_id": None}

DECISION_TREE_PATH = "decision_tree.yaml"
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
def pipeline_run(db: DbDep, fixture: bool = Query(default=False)):
    run_id = str(uuid.uuid4())
    _status["status"] = "running"
    _status["run_id"] = run_id
    queue = create_run(run_id)

    decision_tree = None
    try:
        with open(DECISION_TREE_PATH) as f:
            decision_tree = yaml.safe_load(f)
    except FileNotFoundError:
        pass

    fixture_messages = None
    if fixture:
        from src.itselectric.fixture import load_fixture_messages

        try:
            fixture_messages = load_fixture_messages(FIXTURE_DIR)
        except FileNotFoundError:
            fixture_messages = []

    loop = asyncio.new_event_loop()

    def _log(msg: str) -> None:
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
