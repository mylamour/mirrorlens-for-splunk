"""Investigation workflow: auto-discover → explore → analyze → recommend."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from mirrorlens.config import Settings
from mirrorlens.mcp_client import SplunkMCPClient, SplunkMCPSession
from mirrorlens.prompts import (
    DATA_DISCOVERY_PROMPT,
    DETECTION_GAP_PROMPT,
    EVIDENCE_ANALYSIS_PROMPT,
    RESPONSE_RECOMMENDATION_PROMPT,
    USECASE_GENERATION_PROMPT,
    analyze_with_claude,
)
from mirrorlens.utils import as_list, build_status_summary, count, extract_names

log = logging.getLogger(__name__)


@dataclass
class InvestigationResult:
    # Discovery
    server_info: Any = None
    indexes: list[Any] = field(default_factory=list)
    all_hosts: list[str] = field(default_factory=list)
    all_sourcetypes: list[str] = field(default_factory=list)
    selected_indexes: list[str] = field(default_factory=list)
    selected_sourcetypes: list[str] = field(default_factory=list)
    discovery_reasoning: str = ""
    # Evidence
    raw_events: list[dict] = field(default_factory=list)
    exploration_queries_run: list[dict] = field(default_factory=list)
    saved_searches: list[Any] = field(default_factory=list)
    alerts: list[Any] = field(default_factory=list)
    # Analysis
    timeline: list[dict] = field(default_factory=list)
    attack_chain_summary: str = ""
    dwell_time: str = ""
    detection_gaps: list[dict] = field(default_factory=list)
    coverage_summary: str = ""
    priority_actions: list[str] = field(default_factory=list)
    # Use cases
    use_cases: list[dict] = field(default_factory=list)
    maturity_assessment: str = ""
    # Response
    recommendations: list[dict] = field(default_factory=list)
    executive_summary: str = ""


def build_investigation_steps(incident_id: str = "") -> list[dict]:
    """Return the investigation phases (useful for display and testing)."""
    return [
        {
            "name": "Discover",
            "description": "Connect to Splunk MCP, auto-discover indexes, hosts, sourcetypes",
        },
        {
            "name": "Explore",
            "description": "AI picks interesting data and runs exploration SPL queries",
        },
        {
            "name": "Investigate",
            "description": "Query events and existing detections via MCP",
        },
        {
            "name": "Analyze",
            "description": "AI builds timeline, finds detection gaps, generates use cases",
        },
        {
            "name": "Recommend",
            "description": "AI proposes dry-run response actions and new detection rules",
        },
    ]


EventCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


async def _noop(_c: str, _p: dict[str, Any]) -> None:
    pass


async def investigate(
    settings: Settings,
    *,
    target_index: str | None = None,
    on_event: EventCallback | None = None,
) -> InvestigationResult:
    """Run the full investigation workflow.

    If target_index is given, skip auto-discovery and investigate that index.
    Otherwise, scan the entire Splunk instance and let AI pick the best data.

    If on_event is provided, it is called at each key step for real-time
    dashboard streaming.  The callback receives (channel, payload).
    """
    emit = on_event or _noop
    result = InvestigationResult()
    client = SplunkMCPClient(settings)

    async with client.connect() as session:
        # ── Phase 1: Discovery ──────────────────────────────────────
        log.info("Phase 1: Discovery — scanning Splunk instance")
        await emit("phase", {"name": "Discover", "step": 1, "status": "running"})

        await emit("mcp_call", {"tool": "get_info", "status": "running"})
        result.server_info = await session.get_info()
        await emit("mcp_call", {"tool": "get_info", "status": "done", "result": result.server_info})
        await emit("discovery", {"type": "server_info", "data": result.server_info})

        await emit("mcp_call", {"tool": "get_indexes", "status": "running"})
        result.indexes = await session.get_indexes()
        log.info("Found %d indexes", count(result.indexes))
        await emit("mcp_call", {"tool": "get_indexes", "status": "done", "count": count(result.indexes)})
        await emit("discovery", {"type": "indexes", "count": count(result.indexes), "data": result.indexes[:20]})

        hosts_data, st_data = await asyncio.gather(
            session.get_metadata("hosts", "*"),
            session.get_metadata("sourcetypes", "*"),
        )
        result.all_hosts = extract_names(hosts_data)
        result.all_sourcetypes = extract_names(st_data)
        log.info(
            "Global: %d hosts, %d sourcetypes",
            len(result.all_hosts),
            len(result.all_sourcetypes),
        )
        await emit("discovery", {"type": "hosts", "count": len(result.all_hosts), "data": result.all_hosts})
        await emit("discovery", {"type": "sourcetypes", "count": len(result.all_sourcetypes), "data": result.all_sourcetypes})

        saved_data, alerts_data = await asyncio.gather(
            session.get_knowledge_objects("saved_searches"),
            session.get_knowledge_objects("alerts"),
        )
        result.saved_searches = as_list(saved_data)
        result.alerts = as_list(alerts_data)
        await emit("discovery", {"type": "saved_searches", "count": len(result.saved_searches)})
        await emit("discovery", {"type": "alerts", "count": len(result.alerts)})
        await emit("phase", {"name": "Discover", "step": 1, "status": "done"})

        if target_index:
            result.selected_indexes = [target_index]
            result.selected_sourcetypes = result.all_sourcetypes[:10]
            result.discovery_reasoning = f"User specified index: {target_index}"
            exploration_queries = [
                {
                    "name": "all events",
                    "spl": f"search index={target_index} | sort _time | head 500",
                }
            ]
        else:
            # ── Phase 2: AI-driven data selection ───────────────────
            log.info("Phase 2: AI-driven data selection")
            await emit("phase", {"name": "Explore", "step": 2, "status": "running"})
            await emit("ai_call", {"type": "data_discovery", "model": settings.anthropic_model, "status": "running"})
            discovery_prompt = DATA_DISCOVERY_PROMPT.format(
                indexes_json=json.dumps(
                    result.indexes[:50], indent=2, default=str
                )[:6000],
                hosts_json=json.dumps(result.all_hosts[:100], default=str),
                sourcetypes_json=json.dumps(
                    result.all_sourcetypes[:100], default=str
                ),
            )
            discovery = await analyze_with_claude(discovery_prompt, settings)
            result.selected_indexes = discovery.get("selected_indexes", [])
            result.selected_sourcetypes = discovery.get(
                "selected_sourcetypes", []
            )
            result.discovery_reasoning = discovery.get("reasoning", "")
            exploration_queries = discovery.get("exploration_queries", [])
            log.info(
                "AI selected indexes=%s, sourcetypes=%d, queries=%d",
                result.selected_indexes,
                len(result.selected_sourcetypes),
                len(exploration_queries),
            )
            await emit("ai_call", {
                "type": "data_discovery", "status": "done",
                "selected_indexes": result.selected_indexes,
                "reasoning": result.discovery_reasoning,
                "query_count": len(exploration_queries),
            })
            await emit("phase", {"name": "Explore", "step": 2, "status": "done"})

        # ── Phase 3: Evidence collection via MCP ────────────────────
        log.info("Phase 3: Evidence collection")
        await emit("phase", {"name": "Investigate", "step": 3, "status": "running"})
        all_events: list[dict] = []

        for qi, q in enumerate(exploration_queries[:5]):
            spl = q.get("spl", "")
            if not spl:
                continue
            qname = q.get("name", spl[:60])
            log.info("Running: %s", qname)
            await emit("mcp_call", {"tool": "run_query", "name": qname, "spl": spl, "status": "running"})
            try:
                data = await session.run_query(spl)
                rows = as_list(data)
                entry = {"name": qname, "spl": spl, "row_count": len(rows)}
                result.exploration_queries_run.append(entry)
                all_events.extend(rows)
                await emit("mcp_call", {"tool": "run_query", "name": qname, "status": "done", "row_count": len(rows)})
                await emit("evidence", {"type": "query_result", "index": qi, **entry})
            except Exception as exc:
                log.warning("Query failed (%s): %s", qname, exc)
                entry = {"name": qname, "spl": spl, "error": str(exc)}
                result.exploration_queries_run.append(entry)
                await emit("mcp_call", {"tool": "run_query", "name": qname, "status": "error", "error": str(exc)})
                await emit("evidence", {"type": "query_error", "index": qi, **entry})

        result.raw_events = _dedup_events(all_events)
        log.info(
            "Collected %d events (%d after dedup), %d saved searches, %d alerts",
            len(all_events),
            len(result.raw_events),
            len(result.saved_searches),
            len(result.alerts),
        )
        await emit("evidence", {
            "type": "collection_complete",
            "total_raw": len(all_events),
            "deduplicated": len(result.raw_events),
            "saved_searches": len(result.saved_searches),
            "alerts": len(result.alerts),
        })
        await emit("phase", {"name": "Investigate", "step": 3, "status": "done"})

    # ── Phase 4: AI analysis (outside MCP session) ──────────────────
    if not result.raw_events:
        log.warning("No events found — skipping AI analysis")
        result.attack_chain_summary = "No security events were found in the selected indexes."
        return result

    log.info("Phase 4: AI analysis")
    await emit("phase", {"name": "Analyze", "step": 4, "status": "running"})

    def _j(obj: Any, limit: int = 6000) -> str:
        return json.dumps(obj, default=str)[:limit]

    # 4a: Evidence analysis -> timeline
    await emit("ai_call", {"type": "evidence_analysis", "model": settings.anthropic_model, "status": "running"})
    evidence_prompt = EVIDENCE_ANALYSIS_PROMPT.format(
        events_json=_j(result.raw_events[:100], 8000)
    )
    evidence_analysis = await analyze_with_claude(evidence_prompt, settings)
    result.timeline = evidence_analysis.get("timeline", [])
    result.attack_chain_summary = evidence_analysis.get(
        "attack_chain_summary", ""
    )
    result.dwell_time = evidence_analysis.get("dwell_time", "")
    await emit("ai_call", {"type": "evidence_analysis", "status": "done", "timeline_count": len(result.timeline)})
    await emit("analysis", {"type": "timeline", "data": result.timeline, "summary": result.attack_chain_summary, "dwell_time": result.dwell_time})

    # 4b: Detection gap analysis
    await emit("ai_call", {"type": "gap_analysis", "model": settings.anthropic_model, "status": "running"})
    status_summary = build_status_summary(result.raw_events)
    gap_prompt = DETECTION_GAP_PROMPT.format(
        timeline_json=_j(result.timeline, 4000),
        detections_json=_j(result.saved_searches[:10], 3000),
        status_json=_j(status_summary, 3000),
    )
    gap_analysis = await analyze_with_claude(gap_prompt, settings)
    result.detection_gaps = gap_analysis.get("gaps", [])
    result.coverage_summary = gap_analysis.get("coverage_summary", "")
    result.priority_actions = gap_analysis.get("priority_actions", [])
    await emit("ai_call", {"type": "gap_analysis", "status": "done", "gap_count": len(result.detection_gaps)})
    await emit("analysis", {"type": "gaps", "data": result.detection_gaps, "coverage": result.coverage_summary, "priority_actions": result.priority_actions})

    # 4c: Use case generation
    await emit("ai_call", {"type": "usecase_generation", "model": settings.anthropic_model, "status": "running"})
    uc_prompt = USECASE_GENERATION_PROMPT.format(
        indexes=", ".join(result.selected_indexes),
        sourcetypes=", ".join(result.selected_sourcetypes[:10]),
        hosts=", ".join(result.all_hosts[:10]),
        findings_json=_j(result.timeline, 4000),
        gaps_json=_j(result.detection_gaps, 3000),
    )
    uc_analysis = await analyze_with_claude(uc_prompt, settings)
    result.use_cases = uc_analysis.get("use_cases", [])
    result.maturity_assessment = uc_analysis.get("maturity_assessment", "")
    await emit("ai_call", {"type": "usecase_generation", "status": "done", "usecase_count": len(result.use_cases)})
    await emit("analysis", {"type": "use_cases", "data": result.use_cases, "maturity": result.maturity_assessment})
    await emit("phase", {"name": "Analyze", "step": 4, "status": "done"})

    # ── Phase 5: Response recommendations ───────────────────────────
    log.info("Phase 5: Response recommendations")
    await emit("phase", {"name": "Recommend", "step": 5, "status": "running"})
    await emit("ai_call", {"type": "response_recommendation", "model": settings.anthropic_model, "status": "running"})
    rec_prompt = RESPONSE_RECOMMENDATION_PROMPT.format(
        summary_json=_j(
            {
                "attack_chain": result.attack_chain_summary,
                "dwell_time": result.dwell_time,
                "timeline": result.timeline[:10],
            },
            5000,
        ),
        gaps_json=_j(result.detection_gaps, 3000),
    )
    rec_analysis = await analyze_with_claude(rec_prompt, settings)
    result.recommendations = rec_analysis.get("recommendations", [])
    result.executive_summary = rec_analysis.get("executive_summary", "")
    await emit("ai_call", {"type": "response_recommendation", "status": "done", "rec_count": len(result.recommendations)})
    await emit("recommendation", {"data": result.recommendations, "executive_summary": result.executive_summary})
    await emit("phase", {"name": "Recommend", "step": 5, "status": "done"})

    log.info("Investigation complete")
    return result


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _dedup_events(events: list[dict]) -> list[dict]:
    """Remove exact duplicate events based on _raw or full content."""
    seen: set[str] = set()
    unique: list[dict] = []
    for e in events:
        key = e.get("_raw", "") or json.dumps(e, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique
