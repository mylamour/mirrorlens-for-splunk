from fastapi.testclient import TestClient

from mirrorlens_dashboard.server import build_app


def test_config_reports_configured_splunk_without_exposing_token(monkeypatch):
    monkeypatch.setenv("MIRRORLENS_DOTENV_PATH", "/tmp/mirrorlens-test-missing.env")
    monkeypatch.setenv("SPLUNK_MCP_URL", "https://splunk.example.com:8089/services/mcp")
    monkeypatch.setenv("SPLUNK_MCP_TOKEN", "super-secret-token")

    client = TestClient(build_app())

    response = client.get("/api/config")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["splunk_url_configured"] is True
    assert body["splunk_token_configured"] is True
    assert body["splunk_url_preview"] is None
    assert "splunk.example.com" not in response.text
    assert "super-secret-token" not in response.text


def test_config_reports_unconfigured_splunk(monkeypatch):
    monkeypatch.setenv("MIRRORLENS_DOTENV_PATH", "/tmp/mirrorlens-test-missing.env")
    monkeypatch.delenv("SPLUNK_MCP_URL", raising=False)
    monkeypatch.delenv("SPLUNK_MCP_TOKEN", raising=False)

    client = TestClient(build_app())

    response = client.get("/api/config")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["splunk_url_configured"] is False
    assert body["splunk_token_configured"] is False
    assert body["splunk_url_preview"] is None
