"""PDF report download endpoint."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from mirrorlens_dashboard.bus import ALL_CHANNELS, bus
from pydantic import BaseModel

from mirrorlens_dashboard.report_generator import generate_finding_pdf, generate_pdf

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/report/pdf")
async def download_pdf_report() -> StreamingResponse:
    data: dict[str, list[dict[str, Any]]] = {
        ch: [e.payload for e in bus.replay(ch, limit=200)]
        for ch in ALL_CHANNELS
    }

    has_content = any(
        len(data.get(ch, [])) > 0
        for ch in ("analysis", "recommendation")
    )
    if not has_content:
        return JSONResponse(status_code=404, content={"error": "No investigation data available"})

    try:
        pdf_bytes = generate_pdf(data)
    except Exception as exc:
        log.exception("PDF generation failed")
        return JSONResponse(status_code=500, content={"error": f"PDF generation failed: {exc}"})

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"mirrorlens-report-{ts}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class FindingRequest(BaseModel):
    finding: dict[str, Any]


@router.post("/report/finding")
async def download_finding_pdf(req: FindingRequest) -> StreamingResponse:
    if not req.finding:
        return JSONResponse(status_code=400, content={"error": "missing finding data"})

    try:
        pdf_bytes = generate_finding_pdf(req.finding)
    except Exception as exc:
        log.exception("Finding PDF generation failed")
        return JSONResponse(status_code=500, content={"error": f"PDF generation failed: {exc}"})

    tech_id = str(req.finding.get("technique_id", "finding"))
    safe_id = tech_id.lower().replace(".", "-").replace("/", "-")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"mirrorlens-finding-{safe_id}-{ts}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
