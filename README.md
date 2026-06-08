# MirrorLens for Splunk

**AI-Powered Autonomous Security Investigation via Splunk MCP Server**

> [中文文档](README.zh.md)

MirrorLens is an autonomous AI security investigator that connects to Splunk via the official [Splunk MCP Server](https://dev.splunk.com/). It uses a Claude-powered ReAct loop to discover data, run SPL queries, build MITRE ATT&CK timelines, identify detection gaps, validate detection rules against live data, and enter continuous watch mode — all streamed to a real-time cyberpunk dashboard.

---

## Hackathon

- **Track:** Security
- **Bonus Prize Target:** Best Use of Splunk MCP Server
- **Deadline:** 2026-06-15 09:00 PDT

---

## Key Features

| Feature | Description |
|---------|-------------|
| **ReAct Loop** | Claude-native `tool_use` autonomous investigation loop (REASON → ACT → OBSERVE), up to 30 iterations |
| **MCP-First** | All Splunk interaction through the official MCP Server — no direct REST API |
| **Real-Time Dashboard** | WebSocket-streamed cyberpunk UI showing investigation progress live |
| **Rule Validation** | Generated detection rules tested against live Splunk data with match count |
| **Rule Match Alert** | Full-screen red alert overlay when a validated rule fires (match_count > 0) |
| **Continuous Watch Mode** | After investigation completes, auto-enters lightweight MCP polling every 5 min; triggers new ReAct loop when new data sources appear |
| **CLI + Dashboard** | Both a Rich terminal CLI and a full-featured web dashboard |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Real-Time Dashboard (React 19 + MUI + Framer Motion)               │
│  ┌──────────┐ ┌───────────────────────────────────────┐             │
│  │  Header  │ │ Result-first Dashboard                 │             │
│  │  Phase   │ │ Attack Timeline · Detection Rules      │             │
│  │  Watch   │ │ Response Playbook                       │             │
│  │  Trace   │ │ Discovery/Evidence as secondary context │             │
│  │  Status  │ │ Agent Trace / MCP Proof drawer          │             │
│  └──────────┘ └───────────────────────────────────────┘             │
│        ↑ WebSocket /api/stream                                       │
├─────────────────────────────────────────────────────────────────────┤
│  Dashboard Backend (FastAPI + EventBus)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐         │
│  │ /api/snapshot │  │ /api/stream  │  │ /api/investigate   │         │
│  │ /api/status   │  │  (WebSocket) │  │ /api/watch/stop    │         │
│  └──────────────┘  └──────────────┘  └────────────────────┘         │
│        ↑ EventBus (9 channels: phase, mcp_call, ai_call,            │
│          discovery, evidence, analysis, recommendation,              │
│          status, watch)                                              │
├─────────────────────────────────────────────────────────────────────┤
│  Core Engine (ReAct Loop + ToolExecutor)                             │
│  ┌──────────────────────────────────────────────────┐                │
│  │  Claude API (tool_use)                           │                │
│  │  SYSTEM_PROMPT → Messages → Tool Calls → Results │                │
│  │  6 Tools:                                        │                │
│  │  ├── discover_splunk_data (indexes, hosts, ST)   │                │
│  │  ├── explore_index_fields (schema discovery)     │                │
│  │  ├── run_spl_query (SPL via MCP)                 │                │
│  │  ├── analyze_security_events (timeline + gaps)   │                │
│  │  ├── validate_detection_rule (test against live) │                │
│  │  └── submit_findings (executive summary)         │                │
│  └──────────────────────────────────────────────────┘                │
│        ↑ MCP Protocol (Streamable HTTP)                              │
├─────────────────────────────────────────────────────────────────────┤
│  Splunk Enterprise                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐         │
│  │  MCP Server  │  │   Indexes    │  │  Saved Searches     │         │
│  │  /services/  │  │  (security   │  │  Alerts             │         │
│  │  mcp         │  │   data)      │  │  Knowledge Objects  │         │
│  └─────────────┘  └──────────────┘  └─────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

### Investigation Flow

```
1. DISCOVER (via MCP)
   get_indexes → get_metadata → explore_index_fields
   ↓
2. INVESTIGATE (via MCP)
   run_spl_query (targeted SPL across multiple indexes, auto-adapting)
   ↓
3. ANALYZE (Claude AI)
   analyze_security_events → ATT&CK timeline + detection gaps + use cases
   ↓
4. VALIDATE (MCP + AI)
   validate_detection_rule → test generated SPL against live data
   ↓
5. SUBMIT
   submit_findings → executive summary + risk level + key findings
   ↓
6. WATCH (Continuous)
   Poll indexes + sourcetypes every 5 min → trigger new ReAct on changes
```

---

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for the fastest path to a running demo.

### Prerequisites

- Python 3.11+, [uv](https://docs.astral.sh/uv/)
- Node.js 18+ with pnpm
- Splunk Enterprise with [Splunk MCP Server](https://dev.splunk.com/) enabled
- Splunk HEC token (for demo data ingest)
- Anthropic API key (or compatible proxy)

### Installation

```bash
git clone <repo-url>
cd mirrorlens-for-splunk

uv sync
cd dashboard/backend && uv sync && cd ../..
cd dashboard/frontend && pnpm install && cd ../..
```

### Configuration

```bash
cp .env.example .env
# Edit .env — fill in your Splunk and Anthropic credentials
```

| Variable | Description |
|----------|-------------|
| `SPLUNK_MCP_URL` | Splunk MCP Server endpoint |
| `SPLUNK_MCP_TOKEN` | Bearer token for MCP auth |
| `SPLUNK_HEC_URL` | Splunk HEC endpoint (for demo data) |
| `SPLUNK_HEC_TOKEN` | HEC token |
| `SPLUNK_INDEX` | Target index (default: `mirrorlens_demo`) |
| `SPLUNK_VERIFY_SSL` | SSL verification (`false` for self-signed) |
| `ANTHROPIC_API_KEY` | Claude API key |
| `ANTHROPIC_BASE_URL` | API proxy URL (leave empty for direct) |
| `ANTHROPIC_MODEL` | Model name (default: `claude-sonnet-4-20250514`) |

### Usage

#### One-command Docker

```bash
cp .env.example .env  # fill in credentials
docker compose up --build
# Open http://localhost:8091
```

#### CLI Mode

```bash
uv run mirrorlens ingest examples/incident_events.jsonl  # send demo data to Splunk
uv run mirrorlens demo                                  # run AI investigation
uv run mirrorlens investigate                           # run AI investigation
```

#### Dashboard Dev Mode

```bash
# Terminal 1: backend
cd dashboard/backend
uv run uvicorn mirrorlens_dashboard.server:app --reload --port 8091

# Terminal 2: frontend
cd dashboard/frontend
pnpm dev
```

Open `http://localhost:5174`. If `.env` contains `SPLUNK_MCP_URL` and
`SPLUNK_MCP_TOKEN`, click "Start Investigation". To test a different Splunk
instance, expand "Use different connection", enter the MCP URL and token, then
click "Connect & Investigate".

---

## Dashboard Panels

| Panel | Description |
|-------|-------------|
| **Header** | Phase progress (ReAct LOOP badge + iteration counter), WATCHING indicator, metric cards, LIVE status |
| **Attack Timeline** | MITRE ATT&CK technique timeline with tactic mapping |
| **Detection Rules** | AI-generated SPL rules merged with live validation status and match count |
| **Response Playbook** | Executive summary + numbered remediation actions with risk levels |
| **Discovery & Evidence** | Collapsed supporting context with Splunk server info, indexes, fields, hosts, sourcetypes, and evidence queries |
| **Detection Gaps** | Collapsed supporting context for attack steps that lack detection coverage |
| **Agent Trace / MCP Proof** | Drawer with real-time ReAct reasoning stages and Splunk MCP tool calls, SPL, status, and row counts |

### Rule Match Alert

When a validated detection rule has `match_count > 0`, a **full-screen red alert overlay** fires with the rule name, match count, SPL, and sample matches. Dismiss with ACKNOWLEDGE button, Esc, click outside, or auto-dismiss after 10s.

### Continuous Watch Mode

After the ReAct investigation completes:

1. Captures baseline: current indexes + sourcetypes via MCP
2. Polls every 5 minutes (configurable via `watch_interval`)
3. If new indexes or sourcetypes appear → triggers a new ReAct investigation
4. Dashboard shows WATCHING / CHECKING / CHANGES DETECTED indicators
5. Stop via `POST /api/watch/stop`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/investigate` | Start investigation with optional `index`, `splunk_url`, `splunk_token`, `watch_interval` |
| `GET` | `/api/status` | Returns `running`, `phase`, `elapsed_seconds`, `watch_running` |
| `POST` | `/api/watch/stop` | Stop continuous watch mode |
| `GET` | `/api/snapshot` | Full replay state for all 9 EventBus channels |
| `POST` | `/api/demo/reset` | Clear sample replay/dashboard state |
| `WS` | `/api/stream` | Real-time WebSocket event stream |

---

## MCP Tools Used

| Tool | Purpose | Phase |
|------|---------|-------|
| `get_info` | Verify Splunk connection | Discovery |
| `get_indexes` | List available data indexes | Discovery |
| `get_metadata` | Enumerate hosts, sourcetypes, sources | Discovery |
| `get_index_info` | Get index schema and field summary | Discovery |
| `run_query` | Execute read-only SPL queries | Investigation |
| `get_knowledge_objects` | List saved searches and alerts | Investigation |

---

## Project Structure

```
mirrorlens-for-splunk/
├── .env.example
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── QUICKSTART.md
│
├── src/mirrorlens/
│   ├── cli.py
│   ├── config.py
│   ├── mcp_client.py           # MCP SDK client (Streamable HTTP)
│   ├── react_loop.py           # ReAct investigation loop (Claude tool_use)
│   ├── tools.py                # 6 tool definitions + ToolExecutor
│   ├── workflow.py
│   ├── prompts.py
│   ├── ingest.py
│   └── report.py
│
├── dashboard/
│   ├── backend/
│   │   └── src/mirrorlens_dashboard/
│   │       ├── server.py
│   │       ├── runner.py       # InvestigationRunner + WatchLoop
│   │       ├── bus.py          # EventBus (9 channels, 200-event replay)
│   │       └── routes/
│   │
│   └── frontend/
│       └── src/
│           ├── App.tsx
│           ├── data/           # types, api, context
│           ├── components/     # Header, CenterPanel, AiActivityPanel
│           └── theme.ts
│
├── examples/
│   ├── incident_events.jsonl   # 5-step attack chain
│   └── incident_summary.csv
│
└── tests/
```

---

## Demo Data

The `examples/` directory contains a synthetic 5-step attack chain:

| Step | Technique | Host | Detection |
|------|-----------|------|-----------|
| 1 | T1190 SQL Injection | webapp-01 | Detected (Suricata, 130s) |
| 2 | T1059.004 Reverse Shell | linux-01 | Detected (auditd, 30s) |
| 3 | T1558.003 Kerberoasting | dc-01 | Detected (Win Security, 720s) |
| 4 | T1021.002 SMB Lateral Movement | ws-01 | **Missed** |
| 5 | T1003.001 LSASS Memory Dump | ws-01 | **Evidence Insufficient** |

All data is fully synthetic — no real hosts, IPs, or customer data.

---

## How AI Is Used

MirrorLens uses Claude AI via Anthropic's native `tool_use` API in a ReAct loop:

1. **Autonomous Investigation** — Claude decides which tools to call, what SPL to run, and when to move to the next phase. No hardcoded workflow.
2. **Evidence Analysis** — Builds MITRE ATT&CK timeline from raw Splunk events with technique IDs, tactics, confidence scores.
3. **Detection Gap Analysis** — Compares attack timeline against existing Splunk saved searches and alerts to find blind spots.
4. **Rule Generation + Live Validation** — Generates SPL detection rules and tests them against live data to verify they fire.
5. **Response Recommendations** — Categorized (containment/eradication/recovery) actions with risk levels.

All AI analysis is **read-only and advisory** — no automated responses are executed.

---

## Tests

```bash
uv run python -m pytest -q                    # unit tests; skips live Splunk integration by default
uv run python -m pytest -q -m integration     # live Splunk integration only
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Engine | Claude API (Anthropic `tool_use`), ReAct loop |
| Splunk Integration | MCP SDK (`mcp>=1.20`, Streamable HTTP) |
| Core Backend | Python 3.11+, `uv` |
| Dashboard Backend | FastAPI, uvicorn, WebSocket, asyncio EventBus |
| Dashboard Frontend | React 19, TypeScript, Vite, MUI 9, Framer Motion |
| CLI | Click, Rich |
| Testing | pytest, pytest-asyncio |

---

## Security & Open Source Boundary

- All credentials isolated in `.env` (gitignored)
- No real Splunk instance addresses in code
- This repository contains only the public hackathon demo
- Does **not** include commercial product source code, production logic, customer data, or secrets

---

## License

MIT — see [LICENSE](LICENSE).
