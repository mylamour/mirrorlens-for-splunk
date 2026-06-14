"""PDF report download endpoint."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from mirrorlens_dashboard.bus import bus
from pydantic import BaseModel

from mirrorlens_dashboard.report_generator import generate_finding_pdf

router = APIRouter()
log = logging.getLogger(__name__)


class FindingRequest(BaseModel):
    finding: dict[str, Any]
    # Optional: frontend passes its current analysis/recommendation snapshot so
    # exported rules always match the investigation run the user is looking at,
    # even in Watch Mode where the EventBus may contain events from multiple runs.
    analysis: list[dict[str, Any]] | None = None
    recommendation: list[dict[str, Any]] | None = None


def _related_context(
    finding: dict[str, Any],
    analysis: list[dict[str, Any]] | None = None,
    recommendation: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Pull detection rules and response actions that relate to this finding.

    Uses caller-supplied snapshots when provided (Watch Mode safety); falls back
    to a fresh EventBus replay otherwise.
    """
    if analysis is None:
        analysis = [e.payload for e in bus.replay("analysis", limit=200)]
    if recommendation is None:
        recommendation = [e.payload for e in bus.replay("recommendation", limit=200)]

    tech_id = str(finding.get("technique_id", "")).upper()
    tactic  = str(finding.get("tactic", "")).lower()

    # Detection rules: exact technique match first, fall back to tactic match only
    # when no exact matches exist (avoids showing loosely-related rules)
    uc_ev   = next((e for e in reversed(analysis) if e.get("type") == "use_cases"), {})
    all_ucs = uc_ev.get("data", [])
    exact_rules = [
        {**uc, "_match": "exact"}
        for uc in all_ucs
        if tech_id and str(uc.get("mitre_technique", "")).upper() == tech_id
    ]
    tactic_rules = [
        {**uc, "_match": "tactic"}
        for uc in all_ucs
        if tactic and str(uc.get("mitre_tactic", "")).lower() == tactic
        and str(uc.get("mitre_technique", "")).upper() != tech_id
    ]
    candidate_rules = exact_rules or tactic_rules

    # Within the candidate set, sort by keyword overlap with the finding context
    finding_keywords = {
        w.lower() for w in (
            str(finding.get("technique_name", "")).split()
            + str(finding.get("description", "")).split()
            + str(finding.get("evidence", "")).split()
        )
        if len(w) > 4
    }

    def _rule_score(rule: dict[str, Any]) -> int:
        corpus = " ".join([
            str(rule.get("name", "")),
            str(rule.get("description", "")),
            str(rule.get("spl_query", "")),
        ]).lower()
        return sum(1 for kw in finding_keywords if kw in corpus)

    matched_rules: list[dict[str, Any]] = sorted(candidate_rules, key=_rule_score, reverse=True)[:3]

    # Response actions: score by keyword overlap with technique_id, tactic, description
    rec_ev  = next((e for e in reversed(recommendation) if e.get("data")), {})
    all_recs = rec_ev.get("data", [])
    keywords = {
        w.lower() for w in (
            tech_id.split() + tactic.split()
            + str(finding.get("technique_name", "")).lower().split()
            + str(finding.get("description", "")).lower().split()
        )
        if len(w) > 4
    }

    def _score(rec: dict[str, Any]) -> int:
        text = str(rec.get("action", "")).lower()
        return sum(1 for kw in keywords if kw in text)

    matched_recs: list[dict[str, Any]] = sorted(all_recs, key=_score, reverse=True)[:2]

    return {"rules": matched_rules, "actions": matched_recs}


@router.post("/report/finding")
async def download_finding_pdf(req: FindingRequest) -> StreamingResponse:
    if not req.finding:
        return JSONResponse(status_code=400, content={"error": "missing finding data"})

    related = _related_context(req.finding, analysis=req.analysis, recommendation=req.recommendation)

    try:
        pdf_bytes = generate_finding_pdf(req.finding, related=related)
    except Exception as exc:
        log.exception("Finding PDF generation failed")
        return JSONResponse(status_code=500, content={"error": f"PDF generation failed: {exc}"})

    tech_id = str(req.finding.get("technique_id", "finding"))
    # Whitelist: keep only lowercase alphanumerics and hyphens to prevent header injection
    safe_id = re.sub(r"[^a-z0-9-]", "", tech_id.lower().replace(".", "-").replace("/", "-"))
    if not safe_id:
        safe_id = "finding"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"mirrorlens-finding-{safe_id}-{ts}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
