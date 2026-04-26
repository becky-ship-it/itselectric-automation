"""Log streaming endpoints."""

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from server import log_store

router = APIRouter()


@router.get("/logs")
def get_logs(n: int = 200):
    return {"lines": log_store.get_recent(n)}


@router.get("/logs/stream")
async def stream_logs():
    async def _gen():
        q = log_store.subscribe()
        try:
            while True:
                entry = await q.get()
                yield f"data: {json.dumps(entry)}\n\n"
        except asyncio.CancelledError:
            log_store.unsubscribe(q)

    return StreamingResponse(_gen(), media_type="text/event-stream")
