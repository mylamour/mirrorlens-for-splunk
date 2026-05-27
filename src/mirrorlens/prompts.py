"""Claude prompt templates and AI analysis helper."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic

from mirrorlens.config import Settings

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase 0: Auto-discovery — pick the most interesting security data
# ---------------------------------------------------------------------------

DATA_DISCOVERY_PROMPT = """\
You are a senior SOC analyst examining a Splunk instance for the first time. \
Based on the metadata below, decide which data is most relevant for a security \
investigation.

## Available Indexes (name, totalEventCount, currentDBSizeMB)
{indexes_json}

## Hosts across all indexes
{hosts_json}

## Sourcetypes across all indexes
{sourcetypes_json}

## Task
1. Pick 1-3 indexes that are most likely to contain security-relevant events \
   (e.g. firewall, IDS, endpoint, authentication, SIEM alerts). Exclude \
   internal/system indexes (those starting with _ ).
2. Pick up to 10 sourcetypes that look security-relevant.
3. Suggest 3-5 SPL queries that would surface interesting security events from \
   the selected data. Each query MUST start with "search" and use only safe \
   read-only SPL commands. Keep each query under 300 characters.

Return ONLY valid JSON (no markdown fences):
{{
  "selected_indexes": ["idx1", "idx2"],
  "selected_sourcetypes": ["st1", "st2"],
  "reasoning": "1-2 sentences explaining your choice",
  "exploration_queries": [
    {{
      "name": "short description",
      "spl": "search index=... ..."
    }}
  ]
}}"""

# ---------------------------------------------------------------------------
# Phase 1: Evidence analysis — build timeline from whatever data was found
# ---------------------------------------------------------------------------

EVIDENCE_ANALYSIS_PROMPT = """\
You are a senior SOC analyst. Analyze the following Splunk search results \
and build a security assessment.

## Raw Events (from Splunk)
{events_json}

## Context
These events were auto-discovered from a Splunk instance. The data may include \
alerts, authentication logs, network events, endpoint telemetry, or other \
security-relevant records. Not all events may represent attacks — use your \
judgment to identify what is notable.

## Task
1. Build a chronological timeline of security-relevant findings. For each, provide:
   - timestamp (earliest event for that finding)
   - technique_id (MITRE ATT&CK if applicable, or "N/A")
   - technique_name
   - tactic (MITRE tactic or general category)
   - target host
   - what happened (1-2 sentences, analyst-friendly)
   - key evidence (which log source, what was observed)
   - confidence: HIGH / MEDIUM / LOW
2. Summarize the overall security posture or attack chain in 2-3 sentences.
3. Estimate observation time window (first event to last event).

Return ONLY valid JSON (no markdown fences):
{{
  "timeline": [
    {{
      "timestamp": "ISO-8601 or original timestamp",
      "technique_id": "T#### or N/A",
      "technique_name": "...",
      "tactic": "...",
      "host": "...",
      "description": "...",
      "evidence": "...",
      "confidence": "HIGH|MEDIUM|LOW"
    }}
  ],
  "attack_chain_summary": "...",
  "dwell_time": "..."
}}"""

# ---------------------------------------------------------------------------
# Phase 2: Detection gap analysis
# ---------------------------------------------------------------------------

DETECTION_GAP_PROMPT = """\
You are a detection engineer reviewing a security investigation. Compare the \
findings against existing Splunk saved searches and alerts to identify \
detection gaps and improvement opportunities.

## Security Findings Timeline
{timeline_json}

## Existing Saved Searches / Alerts from Splunk
{detections_json}

## Event-level Detection Status (if available)
{status_json}

## Task
1. For each finding, determine whether existing saved searches or alerts \
   would detect it. If no saved searches exist, note that as a gap.
2. Identify missing detection use cases — what SHOULD be monitored but isn't.
3. For each gap, propose a specific SPL query that would improve detection.
4. Rate each gap severity: CRITICAL / HIGH / MEDIUM / LOW.

Return ONLY valid JSON:
{{
  "gaps": [
    {{
      "technique_id": "T#### or N/A",
      "technique_name": "...",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "gap_description": "...",
      "recommended_spl": "index=... | where ...",
      "recommended_alert_name": "..."
    }}
  ],
  "coverage_summary": "X of Y findings have matching detections",
  "priority_actions": ["..."]
}}"""

# ---------------------------------------------------------------------------
# Phase 3: Use case generation
# ---------------------------------------------------------------------------

USECASE_GENERATION_PROMPT = """\
You are a security architect. Based on the data available in this Splunk \
instance and the investigation findings, generate actionable detection use \
cases that the SOC team should implement.

## Available Data Summary
- Indexes: {indexes}
- Sourcetypes: {sourcetypes}
- Hosts: {hosts}

## Investigation Findings
{findings_json}

## Detection Gaps
{gaps_json}

## Task
Generate 3-5 concrete detection use cases. Each must include:
- A descriptive name
- MITRE ATT&CK mapping (technique + tactic)
- A ready-to-use SPL query for a Splunk saved search / correlation rule
- Expected alert conditions and threshold
- Priority: P1 (critical) / P2 (high) / P3 (medium)

Return ONLY valid JSON:
{{
  "use_cases": [
    {{
      "name": "...",
      "description": "...",
      "mitre_technique": "T####",
      "mitre_tactic": "...",
      "spl_query": "index=... | ...",
      "alert_condition": "when count > N in M minutes",
      "priority": "P1|P2|P3",
      "data_sources_required": ["sourcetype1", "sourcetype2"]
    }}
  ],
  "maturity_assessment": "1-2 sentences on the SOC's current detection maturity"
}}"""

# ---------------------------------------------------------------------------
# Phase 4: Response recommendations
# ---------------------------------------------------------------------------

RESPONSE_RECOMMENDATION_PROMPT = """\
You are an incident responder. Based on the investigation, propose safe \
DRY-RUN response actions. These MUST NOT modify production systems — they \
are recommendations for human review.

## Attack Summary
{summary_json}

## Detection Gaps
{gaps_json}

## Task
Propose 3-5 response actions covering containment, eradication, and recovery. \
Each action must include:
- description (what to do)
- spl_validation (SPL query to check if the action's preconditions are met)
- risk_level: LOW / MEDIUM / HIGH
- dry_run: always true

Return ONLY valid JSON:
{{
  "recommendations": [
    {{
      "action": "...",
      "category": "containment|eradication|recovery|detection",
      "spl_validation": "...",
      "risk_level": "LOW|MEDIUM|HIGH",
      "dry_run": true
    }}
  ],
  "executive_summary": "2-3 sentence summary for management"
}}"""


# ---------------------------------------------------------------------------
# Claude call helper
# ---------------------------------------------------------------------------

async def analyze_with_claude(prompt: str, settings: Settings) -> Any:
    """Call Claude API and parse the JSON response."""
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY required for AI analysis")

    client_kwargs: dict = {
        "api_key": settings.anthropic_api_key,
        "timeout": 300.0,
    }
    if settings.anthropic_base_url:
        client_kwargs["base_url"] = settings.anthropic_base_url
    client = anthropic.AsyncAnthropic(**client_kwargs)
    log.info("Calling Claude (%s) ...", settings.anthropic_model)

    response = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    text_blocks = [b for b in response.content if hasattr(b, "text")]
    if not text_blocks:
        raise RuntimeError("Claude returned no text content")
    text = text_blocks[0].text
    text = _strip_code_fences(text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.warning("Claude response was not valid JSON, returning raw text")
        return {"raw": text}


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences that Claude sometimes wraps JSON in."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()
