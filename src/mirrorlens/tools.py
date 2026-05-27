"""ReAct tool definitions and executor for Claude tool_use."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from mirrorlens.config import Settings
from mirrorlens.mcp_client import SplunkMCPSession
from mirrorlens.prompts import (
    DETECTION_GAP_PROMPT,
    EVIDENCE_ANALYSIS_PROMPT,
    RESPONSE_RECOMMENDATION_PROMPT,
    USECASE_GENERATION_PROMPT,
    analyze_with_claude,
)
from mirrorlens.utils import build_status_summary, extract_names

log = logging.getLogger(__name__)

EventCallback = Callable[[str, dict[str, Any]], Awaitable[None]]

TOOLS: list[dict[str, Any]] = [
    {
        "name": "discover_splunk_data",
        "description": (
            "Discover what data exists in the Splunk instance. Returns server info, "
            "all indexes (with event counts), hosts, sourcetypes, saved searches, and alerts. "
            "Call this first to understand the environment."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "explore_index_fields",
        "description": (
            "Explore the schema of a specific Splunk index. Returns top fields with types, "
            "sample values, and event counts. Use this to understand what data an index "
            "contains before writing SPL queries against it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "index_name": {
                    "type": "string",
                    "description": "Name of the Splunk index to explore.",
                },
                "sample_count": {
                    "type": "integer",
                    "description": "Number of sample events to retrieve (default 5, max 20).",
                    "default": 5,
                },
            },
            "required": ["index_name"],
        },
    },
    {
        "name": "run_spl_query",
        "description": (
            "Execute an SPL query against Splunk via MCP. Use for evidence collection, "
            "correlation, or validation. The query MUST start with 'search' and use only "
            "safe read-only SPL commands. If a query returns 0 rows, try a different approach."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SPL query to execute. Must start with 'search'.",
                },
                "purpose": {
                    "type": "string",
                    "description": "Brief description of what this query is investigating.",
                },
            },
            "required": ["query", "purpose"],
        },
    },
    {
        "name": "analyze_security_events",
        "description": (
            "Run AI analysis on collected security events. Produces a timeline of findings, "
            "detection gap analysis, use case recommendations, and response playbooks. "
            "Call this after you have gathered enough evidence from SPL queries. Pass all "
            "relevant events, saved searches, and any context about the environment."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "events": {
                    "type": "array",
                    "description": "Raw security events collected from SPL queries.",
                    "items": {"type": "object"},
                },
                "saved_searches": {
                    "type": "array",
                    "description": "Existing saved searches/alerts from Splunk.",
                    "items": {"type": "object"},
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about the environment or investigation focus.",
                },
            },
            "required": ["events"],
        },
    },
    {
        "name": "validate_detection_rule",
        "description": (
            "Validate a generated detection rule by running it against live Splunk data. "
            "Returns match count and sample matches. Use this after generating detection "
            "use cases to verify they would actually fire on real data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_name": {
                    "type": "string",
                    "description": "Human-readable name for this detection rule.",
                },
                "spl_query": {
                    "type": "string",
                    "description": "The SPL detection query to validate.",
                },
                "expected_behavior": {
                    "type": "string",
                    "description": "What matches would indicate — true positives vs noise.",
                },
            },
            "required": ["rule_name", "spl_query"],
        },
    },
    {
        "name": "submit_findings",
        "description": (
            "Submit the final investigation findings. Call this when you have gathered "
            "enough evidence and completed your analysis. This signals the end of the "
            "investigation loop."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "executive_summary": {
                    "type": "string",
                    "description": "2-3 sentence executive summary for management.",
                },
                "key_findings": {
                    "type": "array",
                    "description": "Top findings from the investigation.",
                    "items": {"type": "string"},
                },
                "risk_level": {
                    "type": "string",
                    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
                    "description": "Overall risk assessment.",
                },
            },
            "required": ["executive_summary", "key_findings", "risk_level"],
        },
    },
]


class ToolExecutor:
    """Executes ReAct tools, wrapping MCP session + Claude analysis calls."""

    def __init__(
        self,
        session: SplunkMCPSession,
        settings: Settings,
        emit: EventCallback,
    ) -> None:
        self._session = session
        self._settings = settings
        self._emit = emit
        self._collected_events: list[dict] = []
        self._saved_searches: list[Any] = []
        self._alerts: list[Any] = []
        self._indexes: list[Any] = []
        self._hosts: list[str] = []
        self._sourcetypes: list[str] = []
        self._validated_rules: list[dict] = []
        self._iteration = 0

    @property
    def collected_events(self) -> list[dict]:
        return self._collected_events

    def set_iteration(self, n: int) -> None:
        self._iteration = n

    async def execute(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        handler = {
            "discover_splunk_data": self._discover,
            "explore_index_fields": self._explore_fields,
            "run_spl_query": self._run_spl,
            "analyze_security_events": self._analyze,
            "validate_detection_rule": self._validate_rule,
            "submit_findings": self._submit,
        }.get(tool_name)

        if not handler:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        try:
            result = await handler(tool_input)
            return json.dumps(result, default=str)
        except Exception as exc:
            log.exception("Tool %s failed", tool_name)
            return json.dumps({"error": str(exc)})

    async def _discover(self, _input: dict[str, Any]) -> dict[str, Any]:
        await self._emit("mcp_call", {"tool": "get_info", "status": "running"})
        server_info = await self._session.get_info()
        await self._emit("mcp_call", {"tool": "get_info", "status": "done"})
        await self._emit("discovery", {"type": "server_info", "data": server_info})

        await self._emit("mcp_call", {"tool": "get_indexes", "status": "running"})
        indexes = await self._session.get_indexes()
        self._indexes = indexes if isinstance(indexes, list) else []
        await self._emit("mcp_call", {"tool": "get_indexes", "status": "done", "row_count": len(self._indexes)})
        await self._emit("discovery", {"type": "indexes", "count": len(self._indexes), "data": self._indexes[:20]})

        await self._emit("mcp_call", {"tool": "get_metadata", "status": "running"})
        hosts_data = await self._session.get_metadata("hosts", "*")
        self._hosts = extract_names(hosts_data)
        await self._emit("mcp_call", {"tool": "get_metadata", "status": "done", "row_count": len(self._hosts)})
        await self._emit("discovery", {"type": "hosts", "count": len(self._hosts), "data": self._hosts})

        await self._emit("mcp_call", {"tool": "get_metadata", "status": "running"})
        st_data = await self._session.get_metadata("sourcetypes", "*")
        self._sourcetypes = extract_names(st_data)
        await self._emit("mcp_call", {"tool": "get_metadata", "status": "done", "row_count": len(self._sourcetypes)})
        await self._emit("discovery", {"type": "sourcetypes", "count": len(self._sourcetypes), "data": self._sourcetypes})

        await self._emit("mcp_call", {"tool": "get_knowledge_objects", "status": "running"})
        saved = await self._session.get_knowledge_objects("saved_searches")
        self._saved_searches = saved if isinstance(saved, list) else []
        await self._emit("mcp_call", {"tool": "get_knowledge_objects", "status": "done", "row_count": len(self._saved_searches)})
        await self._emit("discovery", {"type": "saved_searches", "count": len(self._saved_searches)})

        await self._emit("mcp_call", {"tool": "get_knowledge_objects", "status": "running"})
        alerts = await self._session.get_knowledge_objects("alerts")
        self._alerts = alerts if isinstance(alerts, list) else []
        await self._emit("mcp_call", {"tool": "get_knowledge_objects", "status": "done", "row_count": len(self._alerts)})
        await self._emit("discovery", {"type": "alerts", "count": len(self._alerts)})

        idx_summary = []
        for idx in self._indexes[:30]:
            if isinstance(idx, dict):
                name = idx.get("title") or idx.get("name", "unknown")
                events = idx.get("totalEventCount", 0)
                size_mb = idx.get("currentDBSizeMB", 0)
                idx_summary.append({"name": name, "totalEventCount": events, "currentDBSizeMB": size_mb})

        return {
            "server_info": server_info,
            "indexes": idx_summary,
            "hosts": self._hosts[:50],
            "sourcetypes": self._sourcetypes[:50],
            "saved_searches_count": len(self._saved_searches),
            "alerts_count": len(self._alerts),
            "saved_search_names": [
                s.get("title") or s.get("name", "") for s in self._saved_searches[:20] if isinstance(s, dict)
            ],
            "alert_names": [
                a.get("title") or a.get("name", "") for a in self._alerts[:20] if isinstance(a, dict)
            ],
        }

    async def _explore_fields(self, inp: dict[str, Any]) -> dict[str, Any]:
        index_name = inp["index_name"]
        sample_count = min(inp.get("sample_count", 5), 20)

        field_spl = f"search index={index_name} | head 200 | fieldsummary"
        await self._emit("mcp_call", {"tool": "run_query", "spl": field_spl, "status": "running"})
        field_data = await self._session.run_query(field_spl)
        fields = field_data if isinstance(field_data, list) else []
        await self._emit("mcp_call", {"tool": "run_query", "spl": field_spl, "status": "done", "row_count": len(fields)})

        sample_spl = f"search index={index_name} | head {sample_count}"
        await self._emit("mcp_call", {"tool": "run_query", "spl": sample_spl, "status": "running"})
        sample_data = await self._session.run_query(sample_spl)
        samples = sample_data if isinstance(sample_data, list) else []
        await self._emit("mcp_call", {"tool": "run_query", "spl": sample_spl, "status": "done", "row_count": len(samples)})

        field_summary = []
        for f in fields[:30]:
            if isinstance(f, dict):
                field_summary.append({
                    "field": f.get("field", ""),
                    "count": f.get("count", 0),
                    "distinct_count": f.get("distinct_count", 0),
                    "numeric_count": f.get("numeric_count", 0),
                    "values": f.get("values", ""),
                })

        await self._emit("discovery", {
            "type": "field_discovery",
            "index": index_name,
            "fields": field_summary,
            "sample_count": len(samples),
        })

        return {
            "index": index_name,
            "fields": field_summary,
            "sample_events": samples[:sample_count],
            "total_fields": len(fields),
        }

    async def _run_spl(self, inp: dict[str, Any]) -> dict[str, Any]:
        query = inp["query"]
        purpose = inp.get("purpose", "")

        await self._emit("mcp_call", {"tool": "run_query", "spl": query, "status": "running"})
        try:
            data = await self._session.run_query(query)
            rows = data if isinstance(data, list) else []
            await self._emit("mcp_call", {"tool": "run_query", "spl": query, "status": "done", "row_count": len(rows)})

            self._collected_events.extend(rows)
            await self._emit("evidence", {
                "type": "query_result",
                "name": purpose,
                "spl": query,
                "row_count": len(rows),
            })

            return {
                "row_count": len(rows),
                "results": rows[:50],
                "truncated": len(rows) > 50,
                "total_collected_events": len(self._collected_events),
            }
        except Exception as exc:
            await self._emit("mcp_call", {"tool": "run_query", "spl": query, "status": "error", "error": str(exc)})
            await self._emit("evidence", {"type": "query_error", "name": purpose, "spl": query, "error": str(exc)})
            return {"error": str(exc), "row_count": 0}

    async def _analyze(self, inp: dict[str, Any]) -> dict[str, Any]:
        events = inp.get("events", self._collected_events)
        saved = inp.get("saved_searches", self._saved_searches)
        context = inp.get("context", "")

        if not events:
            return {"error": "No events to analyze. Run SPL queries first."}

        def _j(obj: Any, limit: int = 6000) -> str:
            return json.dumps(obj, default=str)[:limit]

        result: dict[str, Any] = {}

        await self._emit("ai_call", {"type": "evidence_analysis", "status": "running"})
        evidence_prompt = EVIDENCE_ANALYSIS_PROMPT.format(events_json=_j(events[:100], 8000))
        if context:
            evidence_prompt += f"\n\n## Additional Context\n{context}"
        evidence = await analyze_with_claude(evidence_prompt, self._settings)
        timeline = evidence.get("timeline", [])
        result["timeline"] = timeline
        result["attack_chain_summary"] = evidence.get("attack_chain_summary", "")
        result["dwell_time"] = evidence.get("dwell_time", "")
        await self._emit("ai_call", {"type": "evidence_analysis", "status": "done", "timeline_count": len(timeline)})
        await self._emit("analysis", {"type": "timeline", "data": timeline, "summary": result["attack_chain_summary"]})

        await self._emit("ai_call", {"type": "gap_analysis", "status": "running"})
        gap_prompt = DETECTION_GAP_PROMPT.format(
            timeline_json=_j(timeline, 4000),
            detections_json=_j(saved[:10], 3000),
            status_json=_j(build_status_summary(events), 3000),
        )
        gaps = await analyze_with_claude(gap_prompt, self._settings)
        result["gaps"] = gaps.get("gaps", [])
        result["coverage_summary"] = gaps.get("coverage_summary", "")
        result["priority_actions"] = gaps.get("priority_actions", [])
        await self._emit("ai_call", {"type": "gap_analysis", "status": "done", "gap_count": len(result["gaps"])})
        await self._emit("analysis", {"type": "gaps", "data": result["gaps"], "coverage": result["coverage_summary"]})

        await self._emit("ai_call", {"type": "usecase_generation", "status": "running"})
        uc_prompt = USECASE_GENERATION_PROMPT.format(
            indexes=", ".join(s.get("title", s.get("name", "")) for s in self._indexes[:5] if isinstance(s, dict)),
            sourcetypes=", ".join(self._sourcetypes[:10]),
            hosts=", ".join(self._hosts[:10]),
            findings_json=_j(timeline, 4000),
            gaps_json=_j(result["gaps"], 3000),
        )
        uc = await analyze_with_claude(uc_prompt, self._settings)
        result["use_cases"] = uc.get("use_cases", [])
        result["maturity_assessment"] = uc.get("maturity_assessment", "")
        await self._emit("ai_call", {"type": "usecase_generation", "status": "done", "usecase_count": len(result["use_cases"])})
        await self._emit("analysis", {"type": "use_cases", "data": result["use_cases"], "maturity": result["maturity_assessment"]})

        return result

    async def _validate_rule(self, inp: dict[str, Any]) -> dict[str, Any]:
        rule_name = inp["rule_name"]
        spl = inp["spl_query"]
        expected = inp.get("expected_behavior", "")

        await self._emit("mcp_call", {"tool": "run_query", "spl": spl, "status": "running"})
        try:
            data = await self._session.run_query(spl)
            rows = data if isinstance(data, list) else []
            await self._emit("mcp_call", {"tool": "run_query", "spl": spl, "status": "done", "row_count": len(rows)})

            validation = {
                "rule_name": rule_name,
                "spl": spl,
                "match_count": len(rows),
                "sample_matches": rows[:5],
                "would_fire": len(rows) > 0,
                "expected_behavior": expected,
            }
            self._validated_rules.append(validation)

            await self._emit("analysis", {
                "type": "rule_validation",
                "rule_name": rule_name,
                "spl": spl,
                "match_count": len(rows),
                "sample_matches": rows[:3],
            })

            return validation
        except Exception as exc:
            await self._emit("mcp_call", {"tool": "run_query", "spl": spl, "status": "error", "error": str(exc)})
            return {"rule_name": rule_name, "error": str(exc), "match_count": 0, "would_fire": False}

    async def _submit(self, inp: dict[str, Any]) -> dict[str, Any]:
        summary = inp["executive_summary"]
        findings = inp.get("key_findings", [])
        risk = inp.get("risk_level", "MEDIUM")

        await self._emit("ai_call", {"type": "response_recommendation", "status": "running"})
        rec_prompt = RESPONSE_RECOMMENDATION_PROMPT.format(
            summary_json=json.dumps({
                "executive_summary": summary,
                "key_findings": findings,
                "risk_level": risk,
            }, default=str)[:5000],
            gaps_json="[]",
        )
        rec = await analyze_with_claude(rec_prompt, self._settings)
        recommendations = rec.get("recommendations", [])
        await self._emit("ai_call", {"type": "response_recommendation", "status": "done", "rec_count": len(recommendations)})
        await self._emit("recommendation", {
            "data": recommendations,
            "executive_summary": summary,
            "key_findings": findings,
            "risk_level": risk,
            "validated_rules": self._validated_rules,
        })

        return {
            "status": "complete",
            "recommendations_count": len(recommendations),
            "validated_rules_count": len(self._validated_rules),
        }
