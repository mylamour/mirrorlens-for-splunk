# MirrorLens for Splunk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public, self-contained Splunk hackathon demo that uses MCP and AI agents to investigate a sanitized security incident, explain the evidence, and propose safe next steps without exposing any commercial X2 source code.

**Architecture:** The repo will stay intentionally small. A local demo app will load sanitized attack data into Splunk, call Splunk MCP Server for discovery and search, and present an investigation report with timeline, evidence, and recommendations. Commercial X2 products remain out of tree; only the demo harness, sample data, and documentation are open source.

**Tech Stack:** Python, Splunk Enterprise trial, Splunk MCP Server, lightweight CLI or web UI, sample JSON/CSV data, Markdown docs, optional hosted-model integration.

---

### Task 1: Create the public hackathon repo skeleton

**Files:**
- Create: `LICENSE`
- Create: `README.md`
- Create: `architecture_diagram.md`
- Create: `.env.example`
- Create: `tests/test_repo_skeleton.py`
- Create: `examples/.gitkeep`
- Create: `src/.gitkeep`
- Create: `tests/.gitkeep`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_repo_skeleton_exists():
    root = Path(__file__).resolve().parents[1]
    assert (root / "README.md").exists()
    assert (root / "LICENSE").exists()
    assert (root / "architecture_diagram.md").exists()
    assert (root / ".env.example").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_repo_skeleton.py -v`
Expected: FAIL because the files are not created yet.

- [ ] **Step 3: Write minimal implementation**

Create the listed files with short, factual content describing the demo, its open-source boundary, and how to run it locally.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_repo_skeleton.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add LICENSE README.md architecture_diagram.md .env.example examples/.gitkeep src/.gitkeep tests/.gitkeep tests/test_repo_skeleton.py
git commit -m "feat: add hackathon repo skeleton"
```

### Task 2: Add sanitized demo data and Splunk ingest inputs

**Files:**
- Create: `examples/incident_events.jsonl`
- Create: `examples/incident_summary.csv`
- Create: `tests/test_demo_data.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import json

def test_demo_data_has_expected_fields():
    root = Path(__file__).resolve().parents[1]
    lines = (root / "examples" / "incident_events.jsonl").read_text().splitlines()
    event = json.loads(lines[0])
    assert "timestamp" in event
    assert "host" in event
    assert "event_type" in event
    assert event["tenant_id"] == "demo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_demo_data.py -v`
Expected: FAIL because the sample data does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create a small, realistic attack chain using only synthetic or sanitized values. Keep the data consistent with one incident narrative.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_demo_data.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples/incident_events.jsonl examples/incident_summary.csv tests/test_demo_data.py
git commit -m "feat: add sanitized demo incident data"
```

### Task 3: Build the Splunk MCP investigation workflow

**Files:**
- Create: `src/mirrorlens/__init__.py`
- Create: `src/mirrorlens/workflow.py`
- Create: `src/mirrorlens/report.py`
- Create: `tests/test_workflow.py`

- [ ] **Step 1: Write the failing test**

```python
from mirrorlens.workflow import build_investigation_steps

def test_workflow_builds_three_core_actions():
    steps = build_investigation_steps("incident-001")
    assert [step["name"] for step in steps] == ["Investigate", "Explain", "Recommend"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_workflow.py -v`
Expected: FAIL because the workflow module is not implemented yet.

- [ ] **Step 3: Write minimal implementation**

Implement a small pure-Python workflow that returns the three agent actions, then extend it to consume Splunk search results and build a report object.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_workflow.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mirrorlens/__init__.py src/mirrorlens/workflow.py src/mirrorlens/report.py tests/test_workflow.py
git commit -m "feat: add investigation workflow"
```

### Task 4: Add a thin CLI or UI runner

**Files:**
- Create: `src/mirrorlens/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
from click.testing import CliRunner
from mirrorlens.cli import main

def test_cli_help_renders():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "MirrorLens" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL because the CLI does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add a very small Click CLI that can ingest demo data, print a generated report, and optionally point to Splunk connection settings.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mirrorlens/cli.py tests/test_cli.py
git commit -m "feat: add demo CLI"
```

### Task 5: Document runbook, video script, and submission copy

**Files:**
- Update: `README.md`
- Create: `docs/video-script.md`
- Create: `docs/submission-copy.md`
- Create: `tests/test_docs.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_docs_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "docs" / "video-script.md").exists()
    assert (root / "docs" / "submission-copy.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_docs.py -v`
Expected: FAIL because the docs do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add English-only submission copy tailored to Splunk hackathon judging and a short demo video script under three minutes.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_docs.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/video-script.md docs/submission-copy.md tests/test_docs.py
git commit -m "docs: add hackathon submission assets"
```

### Task 6: Validate the repo is clean and ready for submission work

**Files:**
- Modify: none

- [ ] **Step 1: Run the repo checks**

Run: `pytest -q`
Expected: all tests pass.

- [ ] **Step 2: Confirm the worktree state**

Run: `git status --short --branch`
Expected: clean on `main`.

- [ ] **Step 3: Prepare the next implementation pass**

Capture the exact Splunk integration choice, demo data shape, and whether hosted models will be optional or required.
