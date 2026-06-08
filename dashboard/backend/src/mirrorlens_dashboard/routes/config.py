"""Configuration status endpoint for the dashboard."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter

router = APIRouter()

def _load_dashboard_env() -> None:
    override = os.environ.get("MIRRORLENS_DOTENV_PATH")
    candidates = (
        [Path(override)]
        if override
        else [
            Path(__file__).resolve().parents[5] / ".env",
            Path("/app/.env"),
            Path(".env"),
        ]
    )
    dotenv_path = next((p for p in candidates if p.is_file()), None)
    if dotenv_path:
        load_dotenv(dotenv_path, override=False)


@router.get("/config")
async def config_status() -> dict[str, Any]:
    _load_dashboard_env()
    splunk_url = os.environ.get("SPLUNK_MCP_URL", "").strip()
    splunk_token = os.environ.get("SPLUNK_MCP_TOKEN", "").strip()

    return {
        "configured": bool(splunk_url and splunk_token),
        "splunk_url_configured": bool(splunk_url),
        "splunk_token_configured": bool(splunk_token),
        "splunk_url_preview": None,
    }
