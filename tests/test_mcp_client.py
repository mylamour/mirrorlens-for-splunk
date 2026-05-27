"""Tests for the MCP client parse logic and structure."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

from mirrorlens.mcp_client import _parse_content


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


@pytest.mark.integration
async def test_live_connection():
    """Requires .env with valid SPLUNK_MCP_URL and SPLUNK_MCP_TOKEN."""
    from mirrorlens.config import Settings
    from mirrorlens.mcp_client import SplunkMCPClient

    settings = Settings.from_env()
    client = SplunkMCPClient(settings)
    async with client.connect() as session:
        tools = await session.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
