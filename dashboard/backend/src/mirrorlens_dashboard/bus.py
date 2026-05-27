"""In-memory async event bus with bounded replay buffer."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

log = logging.getLogger(__name__)

EventChannel = Literal[
    "phase",
    "mcp_call",
    "ai_call",
    "discovery",
    "evidence",
    "analysis",
    "recommendation",
    "status",
    "watch",
]

ALL_CHANNELS: list[EventChannel] = list(EventChannel.__args__)  # type: ignore[attr-defined]

MAX_REPLAY = 200
MAX_QUEUE = 1024


@dataclass(slots=True)
class Event:
    channel: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[Event]] = set()
        self._replay: dict[str, deque[Event]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        evt = Event(channel=channel, payload=payload)
        buf = self._replay.setdefault(channel, deque(maxlen=MAX_REPLAY))
        buf.append(evt)

        dead: list[asyncio.Queue[Event]] = []
        for q in self._subscribers:
            try:
                q.put_nowait(evt)
            except asyncio.QueueFull:
                dead.append(q)

        if dead:
            async with self._lock:
                for q in dead:
                    self._subscribers.discard(q)
                    log.warning("Dropped slow subscriber")

    async def subscribe(self) -> asyncio.Queue[Event]:
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=MAX_QUEUE)
        async with self._lock:
            self._subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue[Event]) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    def replay(
        self, channel: str | None = None, limit: int = 50
    ) -> list[Event]:
        if channel:
            buf = self._replay.get(channel, deque())
            return list(buf)[-limit:]
        merged: list[Event] = []
        for buf in self._replay.values():
            merged.extend(buf)
        merged.sort(key=lambda e: e.timestamp)
        return merged[-limit:]

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


bus = EventBus()
