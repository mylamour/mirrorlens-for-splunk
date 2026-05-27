"""Configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    splunk_mcp_url: str
    splunk_mcp_token: str
    splunk_hec_url: str = ""
    splunk_hec_token: str = ""
    splunk_index: str = "mirrorlens_demo"
    splunk_verify_ssl: bool = False
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    @classmethod
    def from_env(cls, dotenv_path: str | Path | None = None) -> Settings:
        load_dotenv(dotenv_path or ".env", override=True)
        return cls(
            splunk_mcp_url=os.environ["SPLUNK_MCP_URL"],
            splunk_mcp_token=os.environ["SPLUNK_MCP_TOKEN"],
            splunk_hec_url=os.environ.get("SPLUNK_HEC_URL", ""),
            splunk_hec_token=os.environ.get("SPLUNK_HEC_TOKEN", ""),
            splunk_index=os.environ.get("SPLUNK_INDEX", "mirrorlens_demo"),
            splunk_verify_ssl=os.environ.get("SPLUNK_VERIFY_SSL", "false").lower()
            == "true",
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            anthropic_base_url=os.environ.get("ANTHROPIC_BASE_URL", ""),
            anthropic_model=os.environ.get(
                "ANTHROPIC_MODEL", "claude-sonnet-4-20250514"
            ),
        )
