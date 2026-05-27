"""Shared utility functions."""

from __future__ import annotations

import json
from typing import Any


def extract_names(data: Any) -> list[str]:
    """Extract human-readable names from MCP metadata results."""
    if isinstance(data, list):
        names = []
        for item in data:
            if isinstance(item, dict):
                for key in ("host", "sourcetype", "source", "name", "title"):
                    if key in item:
                        names.append(str(item[key]))
                        break
            elif isinstance(item, str):
                names.append(item)
        return names
    return []


def build_status_summary(events: list[dict]) -> list[dict]:
    """Group events by technique/sourcetype and detection status."""
    groups: dict[str, dict] = {}
    for e in events:
        tid = e.get("technique_id") or e.get("sourcetype") or e.get("source", "unknown")
        if tid not in groups:
            groups[tid] = {
                "group_key": tid,
                "technique_name": e.get("technique_name", ""),
                "sourcetype": e.get("sourcetype", ""),
                "detection_statuses": set(),
                "event_count": 0,
            }
        status = e.get("detection_status") or e.get("severity") or "info"
        groups[tid]["detection_statuses"].add(status)
        groups[tid]["event_count"] += 1
    return [
        {**v, "detection_statuses": sorted(v["detection_statuses"])}
        for v in groups.values()
    ]


def as_list(data: Any) -> list:
    """Coerce data to a list."""
    if isinstance(data, list):
        return data
    return []


def count(data: Any) -> int:
    """Count items if data is a list, else 0."""
    if isinstance(data, list):
        return len(data)
    return 0
