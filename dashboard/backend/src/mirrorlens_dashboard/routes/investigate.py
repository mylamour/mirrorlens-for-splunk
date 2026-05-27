"""Investigation trigger and status endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from mirrorlens_dashboard.bus import bus
from mirrorlens_dashboard.runner import InvestigationRunner

router = APIRouter()
runner = InvestigationRunner(bus)


class InvestigateRequest(BaseModel):
    index: str | None = None
    splunk_url: str | None = None
    splunk_token: str | None = None
    watch_interval: int = 300


@router.post("/investigate")
async def start_investigation(req: InvestigateRequest | None = None) -> dict[str, Any]:
    if runner.running:
        return {"ok": False, "error": "Investigation already running"}
    target = req.index if req else None
    await runner.start(
        target_index=target,
        splunk_url=req.splunk_url if req else None,
        splunk_token=req.splunk_token if req else None,
        watch_interval=req.watch_interval if req else 300,
    )
    return {"ok": True, "target_index": target}


@router.post("/watch/stop")
async def stop_watch() -> dict[str, Any]:
    if not runner.watch_running:
        return {"ok": False, "error": "Watch mode not running"}
    await runner.stop_watch()
    return {"ok": True}


@router.get("/status")
async def status() -> dict[str, Any]:
    return {
        "running": runner.running,
        "phase": runner.phase,
        "elapsed_seconds": round(runner.elapsed, 1),
        "watch_running": runner.watch_running,
    }
