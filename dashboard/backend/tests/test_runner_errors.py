import httpx

from mirrorlens.config import Settings
from mirrorlens_dashboard.runner import _format_investigation_error


def test_formats_taskgroup_connect_error_as_splunk_mcp_connection_failure():
    settings = Settings(
        splunk_mcp_url="https://192.168.202.220:8089/services/mcp?token=secret",
        splunk_mcp_token="super-secret-token",
        splunk_verify_ssl=False,
        anthropic_api_key="anthropic-key",
        anthropic_model="claude-test",
    )
    error = ExceptionGroup(
        "unhandled errors in a TaskGroup",
        [httpx.ConnectError("")],
    )

    message = _format_investigation_error(error, settings)

    assert "Unable to connect to Splunk MCP endpoint" in message
    assert "192.168.202.220:8089" in message
    assert "/services/mcp" in message
    assert "TaskGroup" not in message
    assert "super-secret-token" not in message
    assert "secret" not in message
