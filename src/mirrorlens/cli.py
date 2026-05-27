"""CLI entry point for MirrorLens."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler

import mirrorlens
from mirrorlens.config import Settings

console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False, rich_tracebacks=True)],
    )


@click.group()
@click.version_option(version=mirrorlens.__version__, prog_name="MirrorLens")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def main(verbose: bool) -> None:
    """MirrorLens for Splunk -- AI-powered security investigation."""
    _setup_logging(verbose)


@main.command()
@click.argument("events", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Validate events without sending to Splunk")
def ingest(events: str, dry_run: bool) -> None:
    """Ingest attack events from a JSONL file into Splunk via HEC."""
    from mirrorlens.ingest import ingest_events

    settings = Settings.from_env()
    result = asyncio.run(ingest_events(settings, events, dry_run=dry_run))
    console.print(
        f"[bold]Ingest complete:[/bold] {result.succeeded}/{result.total} events"
        f" ({'dry-run' if dry_run else 'sent'})"
    )
    if result.failed:
        console.print(f"[red]{result.failed} events failed[/red]")
        sys.exit(1)


@main.command("investigate")
@click.option(
    "--index",
    default=None,
    help="Target a specific index (skip auto-discovery)",
)
def investigate_cmd(index: str | None) -> None:
    """Run AI-powered investigation via Splunk MCP Server.

    By default, auto-discovers all indexes and lets AI pick the most
    security-relevant data. Use --index to target a specific index.
    """
    from mirrorlens.report import render_report
    from mirrorlens.workflow import investigate

    settings = Settings.from_env()
    if index:
        console.print(
            f"[bold]Investigating index [cyan]{index}[/cyan] via Splunk MCP...[/bold]\n"
        )
    else:
        console.print(
            "[bold]Auto-discovering Splunk data via MCP Server...[/bold]\n"
        )
    result = asyncio.run(investigate(settings, target_index=index))
    render_report(result, console)


@main.command()
@click.option("--skip-ingest", is_flag=True, help="Skip data ingest step")
def demo(skip_ingest: bool) -> None:
    """Run the full demo: ingest sample data + auto-discover + investigate."""
    from mirrorlens.ingest import ingest_events
    from mirrorlens.report import render_report
    from mirrorlens.workflow import investigate

    settings = Settings.from_env()

    if not skip_ingest:
        console.print("[bold]Step 1: Skipping ingest (use --skip-ingest or provide events via 'ingest' command)[/bold]")

    console.print("[bold]Step 2: Auto-discovering and investigating via Splunk MCP...[/bold]\n")
    result = asyncio.run(investigate(settings))
    render_report(result, console)
