"""Tests for the investigation workflow logic."""

from __future__ import annotations

from mirrorlens.utils import build_status_summary
from mirrorlens.workflow import build_investigation_steps, _dedup_events


def test_build_investigation_steps_has_five_phases():
    steps = build_investigation_steps()
    names = [s["name"] for s in steps]
    assert names == ["Discover", "Explore", "Investigate", "Analyze", "Recommend"]


def test_build_status_summary_groups_by_technique():
    events = [
        {"technique_id": "T1190", "technique_name": "SQLi", "detection_status": "detected"},
        {"technique_id": "T1190", "technique_name": "SQLi", "detection_status": "detected"},
        {"technique_id": "T1021.002", "technique_name": "SMB", "detection_status": "missed"},
    ]
    summary = build_status_summary(events)
    assert len(summary) == 2

    by_id = {s["group_key"]: s for s in summary}
    assert by_id["T1190"]["event_count"] == 2
    assert by_id["T1190"]["detection_statuses"] == ["detected"]
    assert by_id["T1021.002"]["detection_statuses"] == ["missed"]


def test_build_status_summary_falls_back_to_sourcetype():
    events = [
        {"sourcetype": "syslog", "severity": "high"},
        {"sourcetype": "syslog", "severity": "medium"},
    ]
    summary = build_status_summary(events)
    assert len(summary) == 1
    assert summary[0]["group_key"] == "syslog"
    assert summary[0]["event_count"] == 2


def test_dedup_events_removes_exact_duplicates():
    events = [
        {"_raw": "same event", "host": "a"},
        {"_raw": "same event", "host": "a"},
        {"_raw": "different", "host": "b"},
    ]
    result = _dedup_events(events)
    assert len(result) == 2


def test_dedup_events_without_raw_uses_full_dict():
    events = [
        {"host": "a", "value": 1},
        {"host": "a", "value": 1},
        {"host": "b", "value": 2},
    ]
    result = _dedup_events(events)
    assert len(result) == 2
