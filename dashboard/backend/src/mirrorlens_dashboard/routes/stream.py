"""WebSocket event stream."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mirrorlens_dashboard.bus import bus

log = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    await ws.accept()
    queue = await bus.subscribe()
    log.info("WebSocket client connected (total: %d)", bus.subscriber_count)
    try:
        for evt in bus.replay(limit=60):
            await ws.send_json(evt.to_dict())

        while True:
            try:
                evt = await asyncio.wait_for(queue.get(), timeout=30.0)
                await ws.send_json(evt.to_dict())
            except asyncio.TimeoutError:
                await ws.send_json(
                    {"channel": "heartbeat", "payload": {}, "timestamp": 0}
                )
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("WebSocket error")
    finally:
        await bus.unsubscribe(queue)
        log.info("WebSocket client disconnected")
