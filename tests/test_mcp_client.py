"""Tests for the MCP client parse logic and structure."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import pytest

from mirrorlens.config import Settings
from mirrorlens.mcp_client import SplunkMCPClient, _parse_content


@dataclass
class FakeTextContent:
    text: str
    type: str = "text"


@dataclass
class FakeCallToolResult:
    content: list[Any]
    isError: bool = False


def test_parse_json_content():
    data = [{"index": "main", "count": 42}]
    result = FakeCallToolResult(content=[FakeTextContent(text=json.dumps(data))])
    assert _parse_content(result) == data


def test_parse_plain_text():
    result = FakeCallToolResult(content=[FakeTextContent(text="OK")])
    assert _parse_content(result) == "OK"


def test_parse_empty_content():
    result = FakeCallToolResult(content=[])
    assert _parse_content(result) is None


def test_parse_multiple_text_blocks():
    result = FakeCallToolResult(
        content=[
            FakeTextContent(text='{"a": 1'),
            FakeTextContent(text=', "b": 2}'),
        ]
    )
    parsed = _parse_content(result)
    assert parsed == {"a": 1, "b": 2}


async def test_splunk_mcp_client_ignores_local_http_proxy_environment(monkeypatch):
    class CapturedTransport(Exception):
        pass

    captured: dict[str, Any] = {}

    @asynccontextmanager
    async def fake_streamable_http_client(*, url: str, http_client: Any):
        captured["url"] = url
        captured["trust_env"] = http_client.trust_env
        raise CapturedTransport
        yield

    monkeypatch.setattr(
        "mirrorlens.mcp_client.streamable_http_client",
        fake_streamable_http_client,
    )
    settings = Settings(
        splunk_mcp_url="https://splunk.example.com:8089/services/mcp",
        splunk_mcp_token="token",
    )

    with pytest.raises(CapturedTransport):
        async with SplunkMCPClient(settings).connect():
            pass

    assert captured == {
        "url": "https://splunk.example.com:8089/services/mcp",
        "trust_env": False,
    }


@pytest.mark.integration
async def test_live_connection():
    """Requires .env with valid SPLUNK_MCP_URL and SPLUNK_MCP_TOKEN."""

    settings = Settings.from_env()
    client = SplunkMCPClient(settings)
    async with client.connect() as session:
        tools = await session.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
