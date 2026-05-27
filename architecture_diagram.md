# Architecture Diagram

> [中文版](architecture_diagram.zh.md)

## System Overview

```mermaid
flowchart TB
    subgraph FRONTEND["Dashboard Frontend — React 19 + TypeScript + MUI + Framer Motion"]
        header["Header — Phase Progress · Watch Status · Metrics"]
        center["Center Panels — Discovery · Timeline · Rules · Gaps · Playbook"]
        sidebar["AI Activity Sidebar — AI Reasoning · Splunk MCP Calls"]
        alert["Rule Match Alert — Full-screen overlay on rule fire"]
    end

    subgraph BACKEND["Dashboard Backend — FastAPI + uvicorn"]
        api_inv["POST /api/investigate"]
        api_status["GET /api/status"]
        api_watch["POST /api/watch/stop"]
        api_snap["GET /api/snapshot"]
        api_ws["WS /api/stream"]
        bus["EventBus — 9 channels · 200-event replay"]
        runner["InvestigationRunner"]
        watch["WatchLoop — 5-min polling"]
    end

    subgraph ENGINE["Core Engine — Python 3.11+"]
        react["ReAct Loop — Claude tool_use · max 30 iterations"]
        tools["ToolExecutor — 6 MCP tools"]
        prompts["Prompt Templates"]
    end

    subgraph AI["AI Layer"]
        claude["Claude API — Anthropic tool_use"]
    end

    subgraph SPLUNK["Splunk Enterprise"]
        mcp_srv["Splunk MCP Server — /services/mcp"]
        indexes["Indexes · Events"]
        knowledge["Saved Searches · Alerts"]
        hec["HEC Endpoint"]
    end

    subgraph DATA["Demo Data"]
        events["examples/incident_events.jsonl — 5-step attack chain"]
    end

    header & center & sidebar ---|WebSocket| api_ws
    alert -.- center

    api_inv --> runner
    runner --> react
    runner --> watch
    watch -->|"new sources → re-investigate"| react
    react --> tools
    react --> claude
    tools -->|"MCP Protocol — Streamable HTTP"| mcp_srv
    prompts --> claude

    bus -.-> api_ws
    bus -.-> api_snap
    runner -.->|"emit events"| bus
    tools -.->|"emit events"| bus

    mcp_srv --> indexes
    mcp_srv --> knowledge
    events -->|"HEC POST"| hec
    hec --> indexes

    style FRONTEND fill:#0a1628,stroke:#00e5ff,color:#e0e0e0
    style BACKEND fill:#0d1a2d,stroke:#4fc3f7,color:#e0e0e0
    style ENGINE fill:#0d2a0d,stroke:#66bb6a,color:#e0e0e0
    style AI fill:#2a0d0d,stroke:#ef5350,color:#e0e0e0
    style SPLUNK fill:#0d2137,stroke:#1a5276,color:#e0e0e0
    style DATA fill:#1a1a2e,stroke:#7c4dff,color:#e0e0e0
```

---

## ReAct Loop Detail

```mermaid
flowchart LR
    subgraph REACT["ReAct Loop (max 30 iterations)"]
        direction TB
        reason["REASON — Claude reads context, decides next action"]
        act["ACT — Claude calls tool(s)"]
        observe["OBSERVE — Tool results returned to conversation"]
        reason --> act --> observe --> reason
    end

    subgraph TOOLS["6 Tools"]
        t1["discover_splunk_data"]
        t2["explore_index_fields"]
        t3["run_spl_query"]
        t4["analyze_security_events"]
        t5["validate_detection_rule"]
        t6["submit_findings"]
    end

    act --> t1 & t2 & t3 & t4 & t5 & t6

    subgraph EXIT["Exit Conditions"]
        e1["submit_findings called"]
        e2["end_turn (Claude stops)"]
        e3["max iterations reached"]
    end

    t6 --> e1

    style REACT fill:#1a0d2e,stroke:#7c4dff,color:#e0e0e0
    style TOOLS fill:#0d2a0d,stroke:#66bb6a,color:#e0e0e0
    style EXIT fill:#2a0d0d,stroke:#ef5350,color:#e0e0e0
```

---

## Continuous Watch Mode

```mermaid
flowchart TB
    done["ReAct Investigation Complete"]
    capture["Capture Baseline — indexes + sourcetypes"]
    sleep["Sleep 5 min"]
    check["Poll MCP — get_indexes + get_metadata"]
    diff{"New sources?"}
    reinvestigate["Trigger New ReAct Loop"]
    update["Update Baseline"]
    noop["No Changes"]
    stop["POST /api/watch/stop"]

    done --> capture --> sleep --> check --> diff
    diff -->|Yes| reinvestigate --> update --> sleep
    diff -->|No| noop --> sleep
    stop -.->|"cancel"| sleep

    style done fill:#0d2a0d,stroke:#66bb6a,color:#e0e0e0
    style reinvestigate fill:#2a0d0d,stroke:#ef5350,color:#e0e0e0
    style diff fill:#2a2a0d,stroke:#ffa726,color:#e0e0e0
```

---

## EventBus Channels

| Channel | Payload Description |
|---------|---------------------|
| `phase` | Phase name + status (pending/running/done) |
| `mcp_call` | MCP tool name, SPL query, status, row count, error |
| `ai_call` | ReAct reasoning type, iteration, reasoning text, stage results |
| `discovery` | Server info, indexes, hosts, sourcetypes, field discovery |
| `evidence` | Query results, collection status |
| `analysis` | Timeline, gaps, use cases, rule validations |
| `recommendation` | Response actions, executive summary, risk level |
| `status` | Started/completed/error with elapsed time |
| `watch` | Watch lifecycle events (started, checking, changes_detected, stopped) |

---

## MCP Tools Mapping

| MirrorLens Tool | MCP Server Calls | Phase |
|-----------------|-----------------|-------|
| `discover_splunk_data` | `get_info` + `get_indexes` + `get_metadata(hosts)` + `get_metadata(sourcetypes)` + `get_knowledge_objects(saved_searches)` + `get_knowledge_objects(alerts)` | Discover |
| `explore_index_fields` | `run_query("search index={name} \| fieldsummary")` + `run_query("search index={name} \| head 3")` | Discover |
| `run_spl_query` | `run_query(spl)` | Investigate |
| `analyze_security_events` | Claude API (no MCP) | Analyze |
| `validate_detection_rule` | `run_query(spl)` | Validate |
| `submit_findings` | None (local aggregation) | Submit |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **MCP-first** | All Splunk interaction through official MCP Server — no direct REST API. Ensures protocol compliance and bonus prize eligibility. |
| **ReAct over pipeline** | Claude autonomously decides investigation path instead of hardcoded phases. More adaptive to unknown data shapes. |
| **AI-advisory** | All analysis is read-only. No automated responses executed. Human review required. |
| **Live rule validation** | Generated rules tested against real Splunk data, not just syntax checked. Proves detection viability. |
| **Continuous watch** | Lightweight MCP polling detects new data sources without constant full investigation. Cost-effective 24/7 monitoring. |
| **EventBus architecture** | Decouples investigation engine from dashboard delivery. Supports WebSocket streaming + snapshot replay. |
| **Secrets isolated** | All credentials in `.env` (gitignored). Code references only environment variables. |
