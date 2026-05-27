"""Ingest JSONL demo data into Splunk via HEC (HTTP Event Collector)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from mirrorlens.config import Settings

log = logging.getLogger(__name__)


@dataclass
class IngestResult:
    total: int = 0
    succeeded: int = 0
    failed: int = 0


def _iso_to_epoch(iso_str: str) -> float:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.timestamp()


def _build_hec_payload(
    event: dict, index: str, sourcetype: str = "mirrorlens:attack"
) -> dict:
    return {
        "time": _iso_to_epoch(event["timestamp"]),
        "index": index,
        "sourcetype": sourcetype,
        "host": event.get("host", "unknown"),
        "event": event,
    }


async def ingest_events(
    settings: Settings,
    events_path: str | Path,
    *,
    dry_run: bool = False,
) -> IngestResult:
    """Read JSONL and send events to Splunk HEC."""
    path = Path(events_path)
    lines = [
        line for line in path.read_text().splitlines() if line.strip()
    ]
    events = [json.loads(line) for line in lines]
    result = IngestResult(total=len(events))

    if dry_run:
        log.info("Dry-run: validated %d events, skipping HEC send", len(events))
        result.succeeded = len(events)
        return result

    if not settings.splunk_hec_url or not settings.splunk_hec_token:
        raise RuntimeError(
            "SPLUNK_HEC_URL and SPLUNK_HEC_TOKEN required for ingest"
        )

    async with httpx.AsyncClient(
        verify=settings.splunk_verify_ssl,
        timeout=httpx.Timeout(30.0),
    ) as client:
        for event in events:
            payload = _build_hec_payload(event, settings.splunk_index)
            try:
                resp = await client.post(
                    f"{settings.splunk_hec_url}/services/collector/event",
                    headers={
                        "Authorization": f"Splunk {settings.splunk_hec_token}",
                    },
                    json=payload,
                )
                if resp.status_code == 200:
                    result.succeeded += 1
                else:
                    log.warning(
                        "HEC returned %d: %s", resp.status_code, resp.text
                    )
                    result.failed += 1
            except httpx.HTTPError as exc:
                log.error("HEC request failed: %s", exc)
                result.failed += 1

    return result
