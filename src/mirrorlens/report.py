"""Rich terminal report renderer for investigation results."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mirrorlens.utils import count
from mirrorlens.workflow import InvestigationResult

SEVERITY_STYLES = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "dim",
    "CRITICAL": "bold red",
    "HIGH": "red",
    "MEDIUM": "yellow",
    "LOW": "dim",
    "P1": "bold red",
    "P2": "red",
    "P3": "yellow",
}


def render_report(
    result: InvestigationResult, console: Console | None = None
) -> None:
    console = console or Console()
    console.print()

    # ── Header ──────────────────────────────────────────────────────
    console.print(
        Panel.fit(
            "[bold cyan]MirrorLens Investigation Report[/bold cyan]",
            subtitle=f"Observation window: {result.dwell_time or 'N/A'}",
        )
    )

    # ── Discovery ───────────────────────────────────────────────────
    console.print("\n[bold underline]Phase 1: Discovery[/bold underline]")
    console.print(
        f"  Scanned [cyan]{count(result.indexes)}[/cyan] indexes, "
        f"[cyan]{len(result.all_hosts)}[/cyan] hosts, "
        f"[cyan]{len(result.all_sourcetypes)}[/cyan] sourcetypes"
    )
    if result.selected_indexes:
        console.print(
            f"  Selected indexes: [green]{', '.join(result.selected_indexes)}[/green]"
        )
    if result.discovery_reasoning:
        console.print(f"  Reasoning: {result.discovery_reasoning}")

    # ── Exploration queries ─────────────────────────────────────────
    if result.exploration_queries_run:
        console.print("\n[bold underline]Phase 2: Exploration Queries[/bold underline]")
        for q in result.exploration_queries_run:
            status = (
                f"[green]{q['rowcount']} rows[/green]"
                if "rowcount" in q
                else f"[red]error: {q.get('error', 'unknown')}[/red]"
            )
            console.print(f"  {q.get('name', 'query')}: {status}")
            console.print(f"    [dim]{q.get('spl', '')}[/dim]")

    console.print(
        f"\n  Total events collected: [cyan]{len(result.raw_events)}[/cyan]"
        f"  |  Saved searches: [cyan]{len(result.saved_searches)}[/cyan]"
        f"  |  Alerts: [cyan]{len(result.alerts)}[/cyan]"
    )

    # ── Attack chain summary ────────────────────────────────────────
    if result.attack_chain_summary:
        console.print(
            Panel(
                result.attack_chain_summary,
                title="Security Assessment",
                border_style="blue",
            )
        )

    # ── Timeline ────────────────────────────────────────────────────
    if result.timeline:
        _render_timeline(result.timeline, console)

    # ── Detection gaps ──────────────────────────────────────────────
    if result.detection_gaps:
        _render_gaps(result.detection_gaps, console)

    if result.coverage_summary:
        console.print(f"\n[bold]Coverage:[/bold] {result.coverage_summary}")

    if result.priority_actions:
        console.print("\n[bold]Priority Actions:[/bold]")
        for i, action in enumerate(result.priority_actions, 1):
            console.print(f"  {i}. {action}")

    # ── Use cases ───────────────────────────────────────────────────
    if result.use_cases:
        _render_use_cases(result.use_cases, console)

    if result.maturity_assessment:
        console.print(
            f"\n[bold]Maturity Assessment:[/bold] {result.maturity_assessment}"
        )

    # ── Response recommendations ────────────────────────────────────
    if result.recommendations:
        _render_recommendations(result.recommendations, console)

    # ── Executive summary ───────────────────────────────────────────
    if result.executive_summary:
        console.print(
            Panel(
                result.executive_summary,
                title="Executive Summary",
                border_style="green",
            )
        )
    console.print()


# ------------------------------------------------------------------
# Section renderers
# ------------------------------------------------------------------


def _render_timeline(timeline: list[dict], console: Console) -> None:
    table = Table(title="\nAttack Timeline", show_lines=True)
    table.add_column("Time", style="cyan", width=22)
    table.add_column("Technique", style="red", width=16)
    table.add_column("Tactic", width=18)
    table.add_column("Host", style="green", width=12)
    table.add_column("Description", width=50)
    table.add_column("Confidence", width=10)

    for step in timeline:
        table.add_row(
            str(step.get("timestamp", "")),
            f"{step.get('technique_id', '')} {step.get('technique_name', '')}",
            step.get("tactic", ""),
            step.get("host", ""),
            step.get("description", ""),
            step.get("confidence", ""),
        )

    console.print(table)


def _render_gaps(gaps: list[dict], console: Console) -> None:
    table = Table(title="\nDetection Gaps", show_lines=True)
    table.add_column("Severity", width=10)
    table.add_column("Technique", width=20)
    table.add_column("Gap", width=40)
    table.add_column("Recommended SPL", width=50)

    for gap in gaps:
        severity = gap.get("severity", "MEDIUM")
        style = SEVERITY_STYLES.get(severity, "")
        table.add_row(
            Text(severity, style=style),
            f"{gap.get('technique_id', '')} {gap.get('technique_name', '')}",
            gap.get("gap_description", ""),
            gap.get("recommended_spl", ""),
        )

    console.print(table)


def _render_use_cases(use_cases: list[dict], console: Console) -> None:
    table = Table(title="\nGenerated Detection Use Cases", show_lines=True)
    table.add_column("Priority", width=4)
    table.add_column("Name", width=28)
    table.add_column("MITRE", width=14)
    table.add_column("SPL Query", width=55)
    table.add_column("Alert Condition", width=25)

    for uc in use_cases:
        prio = uc.get("priority", "P3")
        style = SEVERITY_STYLES.get(prio, "")
        table.add_row(
            Text(prio, style=style),
            uc.get("name", ""),
            f"{uc.get('mitre_technique', '')} {uc.get('mitre_tactic', '')}",
            uc.get("spl_query", ""),
            uc.get("alert_condition", ""),
        )

    console.print(table)


def _render_recommendations(recs: list[dict], console: Console) -> None:
    table = Table(title="\nResponse Recommendations (Dry-Run)", show_lines=True)
    table.add_column("#", width=3)
    table.add_column("Category", width=14)
    table.add_column("Action", width=45)
    table.add_column("Risk", width=8)
    table.add_column("Validation SPL", width=45)

    for i, rec in enumerate(recs, 1):
        risk = rec.get("risk_level", "LOW")
        style = SEVERITY_STYLES.get(risk, "")
        table.add_row(
            str(i),
            rec.get("category", ""),
            rec.get("action", ""),
            Text(risk, style=style),
            rec.get("spl_validation", ""),
        )

    console.print(table)
