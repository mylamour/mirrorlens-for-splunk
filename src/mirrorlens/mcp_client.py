"""MCP client for the official Splunk MCP Server."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Any

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult

from mirrorlens.config import Settings

log = logging.getLogger(__name__)

TOOL_PREFIX_CANDIDATES = ("splunk_", "")


class SplunkMCPSession:
    """Typed wrapper over a live MCP session connected to Splunk."""

    def __init__(self, session: ClientSession, tool_prefix: str = "") -> None:
        self._session = session
        self._prefix = tool_prefix

    async def list_tools(self) -> list[str]:
        result = await self._session.list_tools()
        return [t.name for t in result.tools]

    async def get_info(self) -> Any:
        return await self._call("get_info")

    async def get_indexes(self) -> Any:
        return await self._call("get_indexes")

    async def get_index_info(self, index_name: str) -> Any:
        return await self._call("get_index_info", {"index_name": index_name})

    async def get_metadata(
        self, metadata_type: str, index: str = "*"
    ) -> Any:
        return await self._call(
            "get_metadata", {"type": metadata_type, "index": index}
        )

    async def run_query(self, query: str) -> Any:
        return await self._call(
            "run_query",
            {"query": query},
            read_timeout=timedelta(seconds=120),
        )

    async def get_knowledge_objects(self, obj_type: str) -> Any:
        return await self._call("get_knowledge_objects", {"type": obj_type})

    async def run_saved_search(
        self, name: str, *, earliest_time: str = "", latest_time: str = ""
    ) -> Any:
        args: dict[str, Any] = {"saved_search_name": name}
        if earliest_time:
            args["earliest_time"] = earliest_time
        if latest_time:
            args["latest_time"] = latest_time
        return await self._call("run_saved_search", args)

    # ------------------------------------------------------------------

    async def _call(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        *,
        read_timeout: timedelta | None = None,
    ) -> Any:
        full_name = f"{self._prefix}{tool_name}"
        log.info("MCP call: %s(%s)", full_name, arguments or {})
        result: CallToolResult = await self._session.call_tool(
            full_name, arguments, read_timeout_seconds=read_timeout
        )
        return _parse_content(result)


class SplunkMCPClient:
    """Factory that opens an authenticated MCP session to Splunk."""

    def __init__(self, settings: Settings) -> None:
        self._url = settings.splunk_mcp_url
        self._token = settings.splunk_mcp_token
        self._verify_ssl = settings.splunk_verify_ssl

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[SplunkMCPSession, None]:
        headers = {"Authorization": f"Bearer {self._token}"}
        http_client = httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(30, read=300),
            verify=self._verify_ssl,
        )
        async with streamable_http_client(
            url=self._url,
            http_client=http_client,
        ) as (read_stream, write_stream, _get_session_id):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                log.info("MCP session initialised at %s", self._url)
                prefix = await _detect_tool_prefix(session)
                log.info("Detected tool prefix: %r", prefix)
                yield SplunkMCPSession(session, tool_prefix=prefix)


async def _detect_tool_prefix(session: ClientSession) -> str:
    """Auto-detect whether tools use a 'splunk_' prefix or not."""
    result = await session.list_tools()
    names = {t.name for t in result.tools}
    for prefix in TOOL_PREFIX_CANDIDATES:
        if f"{prefix}get_indexes" in names:
            return prefix
    return ""


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _parse_content(result: CallToolResult) -> Any:
    """Extract usable data from an MCP tool result.

    The official Splunk MCP Server wraps results in
    ``{"results": [...], "truncated": bool}``.  We unwrap automatically.
    """
    texts = [c.text for c in result.content if hasattr(c, "text")]
    if not texts:
        return None
    combined = "\n".join(texts)
    try:
        data = json.loads(combined)
    except json.JSONDecodeError:
        return combined
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data
