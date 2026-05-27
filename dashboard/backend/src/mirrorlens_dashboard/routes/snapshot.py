"""REST endpoints for initial state and health."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from mirrorlens_dashboard.bus import ALL_CHANNELS, bus

router = APIRouter()

_DEMO_CANDIDATES = [
    Path(__file__).resolve().parents[5] / "examples" / "sample_investigation.json",
    Path("/app/examples/sample_investigation.json"),
    Path("examples/sample_investigation.json"),
]


@router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "subscribers": bus.subscriber_count}


@router.get("/snapshot")
async def snapshot() -> dict[str, Any]:
    data: dict[str, list[dict[str, Any]]] = {}
    for ch in ALL_CHANNELS:
        data[ch] = [e.payload for e in bus.replay(ch, limit=40)]
    return {"ok": True, "channels": list(data.keys()), "data": data}


@router.post("/demo/load")
async def load_demo(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Replay sample_investigation.json into the EventBus with realistic timing."""
    demo_path = next((p for p in _DEMO_CANDIDATES if p.is_file()), None)
    if not demo_path:
        raise HTTPException(status_code=404, detail="Sample investigation file not found")

    try:
        payload = json.loads(demo_path.read_text())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse demo file: {exc}") from exc

    summary = payload.get("summary", {})
    sequence = _build_replay_sequence(payload.get("data", {}))
    background_tasks.add_task(_replay, sequence)
    return {"ok": True, "mode": "replay", "events_queued": len(sequence), "summary": summary}


# ── Replay helpers ────────────────────────────────────────────────────────────

async def _replay(sequence: list[tuple[float, str, dict]]) -> None:
    """Publish events with the given delays."""
    for delay, channel, event_payload in sequence:
        if delay > 0:
            await asyncio.sleep(delay)
        await bus.publish(channel, event_payload)


def _build_replay_sequence(data: dict[str, list]) -> list[tuple[float, str, dict]]:
    """
    Reconstruct a realistic replay order from grouped channel data.

    Returns list of (delay_seconds, channel, payload) tuples.
    Delays are relative to the previous event.
    """
    seq: list[tuple[float, str, dict]] = []

    phases       = data.get("phase", [])
    ai_calls     = data.get("ai_call", [])
    mcp_calls    = data.get("mcp_call", [])
    discoveries  = data.get("discovery", [])
    evidences    = data.get("evidence", [])
    analyses     = data.get("analysis", [])
    recs         = data.get("recommendation", [])
    statuses     = data.get("status", [])

    # Split ai_calls into reasoning steps and tool calls
    reasoning = [e for e in ai_calls if e.get("type") == "react_reasoning" and e.get("status") == "done"]
    tool_calls = [e for e in ai_calls if e.get("type") == "react_tool_call"]

    # Split mcp_calls into batches by tool type
    discovery_mcps = [e for e in mcp_calls
                      if e.get("tool", "").replace("splunk_", "") in
                      ("get_info", "get_indexes", "get_metadata", "get_knowledge_objects")]
    query_mcps = [e for e in mcp_calls
                  if e.get("tool", "").replace("splunk_", "") == "run_query"]

    # Split evidence into query results and completion
    query_results = [e for e in evidences if e.get("type") in ("query_result", "query_error")]
    completion    = [e for e in evidences if e.get("type") == "collection_complete"]

    # Split analysis
    timeline_ev   = [e for e in analyses if e.get("type") == "timeline"]
    gaps_ev       = [e for e in analyses if e.get("type") == "gaps"]
    usecases_ev   = [e for e in analyses if e.get("type") == "use_cases"]
    validations   = [e for e in analyses if e.get("type") == "rule_validation"]

    def add(delay: float, ch: str, ev: dict) -> None:
        seq.append((delay, ch, ev))

    def add_all(delay_first: float, delay_rest: float, ch: str, events: list) -> None:
        for i, ev in enumerate(events):
            add(delay_first if i == 0 else delay_rest, ch, ev)

    # ── Status: started ──────────────────────────────────────────────
    started = [e for e in statuses if e.get("event") == "started"]
    for ev in started:
        add(0.0, "status", ev)

    # ── Phase: running ───────────────────────────────────────────────
    running_phases = [e for e in phases if e.get("status") == "running"]
    add_all(0.2, 0.1, "phase", running_phases)

    # ── Iteration 1: AI reasons about the environment ────────────────
    if reasoning:
        add(0.5, "ai_call", reasoning[0])

    # ── Discovery MCP calls fire ─────────────────────────────────────
    for i, ev in enumerate(discovery_mcps):
        add(0.4 if i == 0 else 0.35, "mcp_call", ev)

    # ── Discovery data arrives ───────────────────────────────────────
    # server_info first, then indexes, then hosts/sourcetypes, then field discovery
    ordered_disc = sorted(
        discoveries,
        key=lambda e: ["server_info", "indexes", "hosts", "sourcetypes",
                        "saved_searches", "alerts", "field_discovery"].index(
            e.get("type", "field_discovery")
            if e.get("type") in ["server_info", "indexes", "hosts", "sourcetypes",
                                  "saved_searches", "alerts", "field_discovery"]
            else "field_discovery"
        )
    )
    add_all(0.3, 0.4, "discovery", ordered_disc)

    # ── Subsequent reasoning iterations with query batches ───────────
    remaining_reasoning = reasoning[1:]
    # Split query_mcps and query_results into batches per reasoning step
    n_steps = max(len(remaining_reasoning), 1)
    qm_batches = _split_into(query_mcps, n_steps)
    qr_batches = _split_into(query_results, n_steps)

    for i, reason_ev in enumerate(remaining_reasoning):
        # AI thinks before each batch
        add(1.5, "ai_call", reason_ev)
        # MCP queries fire
        for ev in qm_batches[i]:
            add(0.35, "mcp_call", ev)
        # Query results arrive
        for ev in qr_batches[i]:
            add(0.25, "evidence", ev)

    # Evidence collection complete
    for ev in completion:
        add(0.5, "evidence", ev)

    # ── Analysis: big reveals ─────────────────────────────────────────
    for ev in timeline_ev:
        add(2.0, "analysis", ev)
    for ev in gaps_ev:
        add(1.5, "analysis", ev)
    for ev in usecases_ev:
        add(1.5, "analysis", ev)

    # ── Rule validations: one by one, dramatic ────────────────────────
    for ev in validations:
        add(1.2, "analysis", ev)

    # ── Recommendations ───────────────────────────────────────────────
    for ev in recs:
        add(2.0, "recommendation", ev)

    # ── Phase done + status completed ────────────────────────────────
    done_phases = [e for e in phases if e.get("status") == "done"]
    add_all(0.5, 0.1, "phase", done_phases)

    completed = [e for e in statuses if e.get("event") == "completed"]
    for ev in completed:
        add(0.3, "status", ev)

    return seq


def _split_into(items: list, n: int) -> list[list]:
    """Split a list as evenly as possible into n sub-lists."""
    if n <= 0:
        return [items]
    size = max(1, len(items) // n)
    result = []
    for i in range(n):
        start = i * size
        end = start + size if i < n - 1 else len(items)
        result.append(items[start:end])
    return result
