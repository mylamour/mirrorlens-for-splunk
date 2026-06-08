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
