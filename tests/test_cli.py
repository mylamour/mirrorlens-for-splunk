"""Tests for CLI help and command structure."""

from __future__ import annotations

from click.testing import CliRunner

from mirrorlens.cli import main


def test_cli_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "MirrorLens" in result.output


def test_cli_version():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_ingest_help():
    result = CliRunner().invoke(main, ["ingest", "--help"])
    assert result.exit_code == 0
    assert "EVENTS" in result.output or "events" in result.output.lower()
    assert "--dry-run" in result.output


def test_investigate_help():
    result = CliRunner().invoke(main, ["investigate", "--help"])
    assert result.exit_code == 0
    assert "--index" in result.output
    assert "auto-discover" in result.output.lower()


def test_demo_help():
    result = CliRunner().invoke(main, ["demo", "--help"])
    assert result.exit_code == 0
    assert "AI investigation" in result.output
    assert "--skip-ingest" not in result.output
