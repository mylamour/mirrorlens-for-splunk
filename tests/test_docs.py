from pathlib import Path
import tomllib

def test_docs_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "docs" / "video-script.md").exists()
    assert (root / "docs" / "submission-copy.md").exists()


def test_cli_ingest_docs_include_events_path():
    root = Path(__file__).resolve().parents[1]
    docs = "\n".join(
        [
            (root / "README.md").read_text(),
            (root / "README.zh.md").read_text(),
            (root / "QUICKSTART.md").read_text(),
        ]
    )

    assert "uv run mirrorlens ingest examples/incident_events.jsonl" in docs
    bare_ingest_lines = [
        line for line in docs.splitlines()
        if line.split("#", 1)[0].strip() == "uv run mirrorlens ingest"
    ]
    assert bare_ingest_lines == []


def test_pytest_defaults_skip_live_integration_tests():
    root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text())

    addopts = pyproject["tool"]["pytest"]["ini_options"].get("addopts", [])
    assert "-m" in addopts
    assert "not integration" in addopts
