"""Wraps mirrorlens investigation with EventBus emission."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mirrorlens.config import Settings
from mirrorlens.mcp_client import SplunkMCPClient
from mirrorlens.react_loop import react_investigate
from mirrorlens.utils import extract_names

_DOTENV_CANDIDATES = [
    Path(__file__).resolve().parents[4] / ".env",
    Path("/app/.env"),
    Path(".env"),
]
DOTENV_PATH = next((p for p in _DOTENV_CANDIDATES if p.is_file()), None)

from mirrorlens_dashboard.bus import EventBus

log = logging.getLogger(__name__)

DEFAULT_WATCH_INTERVAL = 300


class InvestigationRunner:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._phase = "idle"
        self._started_at: float = 0
        self._watch_task: asyncio.Task[None] | None = None
        self._watch_running = False
        self._settings: Settings | None = None
        self._target_index: str | None = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def elapsed(self) -> float:
        if not self._started_at:
            return 0
        return time.time() - self._started_at

    @property
    def watch_running(self) -> bool:
        return self._watch_running

    async def start(
        self,
        target_index: str | None = None,
        splunk_url: str | None = None,
        splunk_token: str | None = None,
        watch_interval: int = DEFAULT_WATCH_INTERVAL,
    ) -> None:
        if self._running:
            raise RuntimeError("Investigation already running")
        self._running = True
        self._started_at = time.time()
        self._phase = "starting"
        self._target_index = target_index
        self._task = asyncio.create_task(
            self._run(target_index, splunk_url, splunk_token, watch_interval)
        )

    async def stop_watch(self) -> None:
        self._watch_running = False
        if self._watch_task and not self._watch_task.done():
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
        self._watch_task = None
        await self._emit("watch", {"event": "stopped"})

    async def _emit(self, channel: str, payload: dict[str, Any]) -> None:
        await self.bus.publish(channel, payload)

    def _build_settings(
        self,
        splunk_url: str | None = None,
        splunk_token: str | None = None,
    ) -> Settings:
        base = Settings.from_env(DOTENV_PATH)
        overrides: dict[str, Any] = {}
        if splunk_url:
            overrides["splunk_mcp_url"] = splunk_url
        if splunk_token:
            overrides["splunk_mcp_token"] = splunk_token
        if overrides:
            d = asdict(base)
            d.update(overrides)
            return Settings(**d)
        return base

    async def _run(
        self,
        target_index: str | None,
        splunk_url: str | None = None,
        splunk_token: str | None = None,
        watch_interval: int = DEFAULT_WATCH_INTERVAL,
    ) -> None:
        try:
            self._settings = self._build_settings(splunk_url, splunk_token)
            await react_investigate(
                self._settings,
                target_index=target_index,
                on_event=self._emit,
            )
            if watch_interval > 0:
                self._watch_running = True
                self._watch_task = asyncio.create_task(
                    self._watch_loop(watch_interval)
                )
        except Exception as exc:
            log.exception("Investigation failed")
            await self._emit("status", {
                "event": "error",
                "error": str(exc),
                "elapsed_seconds": round(self.elapsed, 1),
            })
        finally:
            self._running = False
            self._phase = "idle"

    async def _watch_loop(self, interval: int) -> None:
        settings = self._settings
        if not settings:
            return

        try:
            baseline_indexes, baseline_sourcetypes = await self._capture_baseline(settings)
            await self._emit("watch", {
                "event": "baseline_captured",
                "interval": interval,
                "index_count": len(baseline_indexes),
                "sourcetype_count": len(baseline_sourcetypes),
            })
        except Exception as exc:
            log.error("Watch baseline capture failed: %s", exc)
            await self._emit("watch", {"event": "error", "error": str(exc)})
            self._watch_running = False
            return

        await self._emit("watch", {"event": "started", "interval": interval})

        while self._watch_running:
            await asyncio.sleep(interval)
            if not self._watch_running:
                break

            try:
                await self._emit("watch", {"event": "checking"})
                current_indexes, current_sourcetypes = await self._capture_baseline(settings)

                new_indexes = current_indexes - baseline_indexes
                new_sourcetypes = current_sourcetypes - baseline_sourcetypes

                if new_indexes or new_sourcetypes:
                    log.info("Watch detected changes: +%d indexes, +%d sourcetypes",
                             len(new_indexes), len(new_sourcetypes))
                    await self._emit("watch", {
                        "event": "changes_detected",
                        "new_indexes": sorted(new_indexes),
                        "new_sourcetypes": sorted(new_sourcetypes),
                    })

                    self._running = True
                    self._started_at = time.time()
                    self._phase = "re-investigating"
                    try:
                        await react_investigate(
                            settings,
                            target_index=self._target_index,
                            on_event=self._emit,
                        )
                    finally:
                        self._running = False
                        self._phase = "watching"

                    baseline_indexes = current_indexes
                    baseline_sourcetypes = current_sourcetypes
                    await self._emit("watch", {
                        "event": "baseline_updated",
                        "index_count": len(baseline_indexes),
                        "sourcetype_count": len(baseline_sourcetypes),
                    })
                else:
                    await self._emit("watch", {
                        "event": "no_changes",
                        "index_count": len(current_indexes),
                        "sourcetype_count": len(current_sourcetypes),
                    })
            except Exception as exc:
                log.error("Watch check error: %s", exc)
                await self._emit("watch", {"event": "check_error", "error": str(exc)})

        self._watch_running = False

    async def _capture_baseline(self, settings: Settings) -> tuple[set[str], set[str]]:
        mcp = SplunkMCPClient(settings)
        async with mcp.connect() as session:
            idx_data = await session.get_indexes()
            st_data = await session.get_metadata("sourcetypes")
        indexes = set(extract_names(idx_data))
        sourcetypes = set(extract_names(st_data))
        return indexes, sourcetypes

    def set_phase(self, phase: str) -> None:
        self._phase = phase
