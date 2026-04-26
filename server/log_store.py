"""In-memory log buffer with SSE fan-out."""

import asyncio
from collections import deque
from datetime import datetime, timezone

_MAX_LINES = 500

_lines: deque[dict] = deque(maxlen=_MAX_LINES)
_subscribers: list[asyncio.Queue] = []


def append(message: str) -> None:
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "msg": message}
    _lines.append(entry)
    for q in list(_subscribers):
        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            pass


def get_recent(n: int = 200) -> list[dict]:
    return list(_lines)[-n:]


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    try:
        _subscribers.remove(q)
    except ValueError:
        pass
