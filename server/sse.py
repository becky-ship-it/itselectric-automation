"""Server-Sent Events queue for streaming pipeline progress."""

import asyncio
from typing import AsyncGenerator

_queues: dict[str, asyncio.Queue] = {}


def create_run(run_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _queues[run_id] = q
    return q


def get_queue(run_id: str) -> asyncio.Queue | None:
    return _queues.get(run_id)


def remove_run(run_id: str) -> None:
    _queues.pop(run_id, None)


async def event_stream(run_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted lines until the queue sends a sentinel None."""
    q = get_queue(run_id)
    if q is None:
        yield "data: run not found\n\n"
        return
    while True:
        msg = await q.get()
        if msg is None:
            yield "data: [done]\n\n"
            break
        yield f"data: {msg}\n\n"
