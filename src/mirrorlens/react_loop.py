"""ReAct investigation loop using Claude's native tool_use."""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from mirrorlens.config import Settings
from mirrorlens.mcp_client import SplunkMCPClient
from mirrorlens.tools import TOOLS, EventCallback, ToolExecutor

log = logging.getLogger(__name__)

MAX_ITERATIONS = 30

SYSTEM_PROMPT = """\
You are MirrorLens, an autonomous AI security investigator connected to a Splunk \
SIEM via MCP (Model Context Protocol). Your mission is to conduct a thorough \
security investigation of the connected Splunk instance.

## Investigation Methodology

Follow the OODA loop: Observe → Orient → Decide → Act.

1. **DISCOVER** — Call discover_splunk_data first to understand what data exists \
   (indexes, fields, sourcetypes, saved searches, alerts).
2. **EXPLORE** — Pick the most interesting security-relevant indexes and call \
   explore_index_fields to understand their schema and sample events. Focus on \
   indexes that likely contain security data (firewall, IDS, endpoint, auth, SIEM alerts). \
   Skip internal indexes starting with _.
3. **INVESTIGATE** — Run targeted SPL queries to find security-relevant events. \
   Start broad, then drill down. If a query returns 0 results, adapt — try different \
   time ranges, fields, or sourcetypes. Correlate across multiple indexes.
4. **ANALYZE** — Once you have enough evidence (at least 10-20 events from multiple \
   sources), call analyze_security_events to build a timeline, find detection gaps, \
   and generate use cases.
5. **VALIDATE** — For each generated detection rule or use case, call \
   validate_detection_rule to test it against live data. Refine rules that don't match.
6. **SUBMIT** — When you have a comprehensive picture, call submit_findings with \
   your executive summary.

## Key Principles

- **Be thorough**: Don't stop after one index. Explore at least 2-3 indexes.
- **Adapt**: If queries return 0 rows, reason about why and try differently. \
  Maybe the field name is different, the time range is wrong, or the data structure \
  is unexpected.
- **Correlate**: Look for connections between events in different indexes.
- **Validate**: Test your detection rules — a rule that never fires is useless.
- **Be efficient**: Don't run the same query twice. Build on what you learn.

## SPL Query Guidelines

- Always start queries with "search"
- Use only read-only SPL commands (search, stats, where, eval, table, head, sort, etc.)
- Keep queries under 300 characters
- Use "| head 100" or "| head 500" to limit results
- Use "| stats count by field" for aggregation
- Use "| fieldsummary" to understand index schema
"""


async def _noop(_c: str, _p: dict[str, Any]) -> None:
    pass


async def react_investigate(
    settings: Settings,
    *,
    target_index: str | None = None,
    on_event: EventCallback | None = None,
    max_iterations: int = MAX_ITERATIONS,
) -> dict[str, Any]:
    """Run an autonomous ReAct investigation loop using Claude tool_use."""
    emit = on_event or _noop

    await emit("status", {"event": "started", "mode": "react"})
    await emit("phase", {"name": "ReAct Loop", "step": 1, "status": "running"})

    client_kwargs: dict[str, Any] = {
        "api_key": settings.anthropic_api_key,
        "timeout": 300.0,
    }
    if settings.anthropic_base_url:
        client_kwargs["base_url"] = settings.anthropic_base_url
    claude = anthropic.AsyncAnthropic(**client_kwargs)

    mcp_client = SplunkMCPClient(settings)

    async with mcp_client.connect() as session:
        executor = ToolExecutor(session, settings, emit)

        messages: list[dict[str, Any]] = []
        if target_index:
            messages.append({
                "role": "user",
                "content": (
                    f"Investigate the Splunk instance. Focus on index '{target_index}' "
                    "but also explore related indexes for correlation. Start by discovering "
                    "what data exists, then drill into the target index."
                ),
            })
        else:
            messages.append({
                "role": "user",
                "content": (
                    "Investigate this Splunk instance for security issues. Start by "
                    "discovering what data exists, then systematically explore, query, "
                    "analyze, and validate. Be thorough and autonomous."
                ),
            })

        iteration = 0
        for iteration in range(1, max_iterations + 1):
            executor.set_iteration(iteration)
            log.info("ReAct iteration %d/%d", iteration, max_iterations)
            await emit("ai_call", {
                "type": "react_reasoning",
                "status": "running",
                "iteration": iteration,
            })

            try:
                response = await claude.messages.create(
                    model=settings.anthropic_model,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages,
                )
            except Exception as exc:
                log.error("Claude API error at iteration %d: %s", iteration, exc)
                await emit("ai_call", {
                    "type": "react_reasoning",
                    "status": "error",
                    "iteration": iteration,
                    "reasoning": str(exc),
                })
                break

            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            reasoning_parts = []
            tool_uses = []
            for block in assistant_content:
                if hasattr(block, "text"):
                    reasoning_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)

            if reasoning_parts:
                reasoning_text = "\n".join(reasoning_parts)
                log.info("ReAct reasoning: %s", reasoning_text[:200])
                await emit("ai_call", {
                    "type": "react_reasoning",
                    "status": "done",
                    "iteration": iteration,
                    "reasoning": reasoning_text[:500],
                })

            if not tool_uses:
                log.info("ReAct loop ended — Claude stopped calling tools at iteration %d", iteration)
                break

            tool_results = []
            for tool_use in tool_uses:
                tool_name = tool_use.name
                tool_input = tool_use.input
                log.info("ReAct tool call: %s(%s)", tool_name, json.dumps(tool_input, default=str)[:200])

                await emit("ai_call", {
                    "type": "react_tool_call",
                    "status": "running",
                    "iteration": iteration,
                    "tool": tool_name,
                })

                result_str = await executor.execute(tool_name, tool_input)

                await emit("ai_call", {
                    "type": "react_tool_call",
                    "status": "done",
                    "iteration": iteration,
                    "tool": tool_name,
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": _truncate(result_str, 30000),
                })

                if tool_name == "submit_findings":
                    log.info("ReAct loop: submit_findings called — investigation complete")
                    messages.append({"role": "user", "content": tool_results})
                    await emit("phase", {"name": "ReAct Loop", "step": 1, "status": "done"})
                    await emit("status", {
                        "event": "completed",
                        "mode": "react",
                        "iterations": iteration,
                        "total_events_collected": len(executor.collected_events),
                    })
                    return {
                        "mode": "react",
                        "iterations": iteration,
                        "events_collected": len(executor.collected_events),
                    }

            messages.append({"role": "user", "content": tool_results})

            if response.stop_reason == "end_turn":
                log.info("ReAct: end_turn at iteration %d", iteration)
                break

    await emit("phase", {"name": "ReAct Loop", "step": 1, "status": "done"})
    await emit("status", {
        "event": "completed",
        "mode": "react",
        "iterations": iteration,
        "total_events_collected": len(executor.collected_events),
    })

    return {
        "mode": "react",
        "iterations": max_iterations,
        "events_collected": len(executor.collected_events),
    }


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "... [truncated]"
