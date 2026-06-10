from pathlib import Path


def test_dashboard_trace_is_secondary_drawer():
    root = Path(__file__).resolve().parents[1]
    app = (root / "dashboard/frontend/src/App.tsx").read_text()
    header = (root / "dashboard/frontend/src/components/Header.tsx").read_text()

    assert "AgentTraceDrawer" in app
    assert "gridTemplateColumns: \"1fr\"" in app
    assert "AGENT TRACE" in header
    assert "MCP PROOF" in header
    assert "1fr 280px" not in app


def test_dashboard_uses_combined_detection_rules_panel():
    root = Path(__file__).resolve().parents[1]
    center = (root / "dashboard/frontend/src/components/CenterPanel.tsx").read_text()

    assert "DetectionRulesSection" in center
    assert 'GlassCard title="Detection Rules"' in center
    assert 'GlassCard title="Generated Detection Rules"' not in center
    assert 'GlassCard title="Validated Detection Rules"' not in center
    assert "dedupeRuleValidations" in center


def test_dashboard_header_uses_rule_matches_metric():
    root = Path(__file__).resolve().parents[1]
    header = (root / "dashboard/frontend/src/components/Header.tsx").read_text()

    assert 'label="Matches"' in header
    assert 'label="Events"' not in header
    assert 'type === "rule_validation"' in header


def test_dashboard_result_panels_stay_summary_first():
    root = Path(__file__).resolve().parents[1]
    center = (root / "dashboard/frontend/src/components/CenterPanel.tsx").read_text()

    assert "SUMMARY_LINE_CLAMP" in center
    assert "sortDetectionRuleRows(rows)" in center
    assert "visibleRecommendations = recs.slice(0, 3)" in center
    assert "generated?.alert_condition" not in center


def test_supporting_context_is_collapsed_by_default():
    root = Path(__file__).resolve().parents[1]
    center = (root / "dashboard/frontend/src/components/CenterPanel.tsx").read_text()

    assert "showSupportingContext" in center
    assert "SHOW EVIDENCE & GAPS" in center
    assert "HIDE EVIDENCE & GAPS" in center
    assert "primaryPanels.length > 0 && secondaryPanels.length > 0 && showSupportingContext" in center


def test_dashboard_labels_timeline_panel_as_attack_findings():
    root = Path(__file__).resolve().parents[1]
    center = (root / "dashboard/frontend/src/components/CenterPanel.tsx").read_text()

    assert 'GlassCard title="Attack Findings"' in center
    assert 'GlassCard title="Attack Timeline"' not in center
    assert 'timeline: "Attack Finding Detail"' in center
