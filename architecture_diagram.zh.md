# 架构图

> [English](architecture_diagram.md)

## 系统总览

```mermaid
flowchart TB
    subgraph FRONTEND["仪表盘前端 — React 19 + TypeScript + MUI + Framer Motion"]
        header["顶部栏 — 阶段进度 · 监控状态 · 指标卡"]
        center["中央面板 — 发现 · 时间线 · 规则 · 盲区 · 响应手册"]
        sidebar["AI 活动侧边栏 — AI 推理 · Splunk MCP 调用"]
        alert["规则匹配警报 — 规则触发时全屏覆盖层"]
    end

    subgraph BACKEND["仪表盘后端 — FastAPI + uvicorn"]
        api_inv["POST /api/investigate"]
        api_status["GET /api/status"]
        api_watch["POST /api/watch/stop"]
        api_snap["GET /api/snapshot"]
        api_ws["WS /api/stream"]
        bus["EventBus — 9 个频道 · 200 事件重放缓冲"]
        runner["InvestigationRunner（调查运行器）"]
        watch["WatchLoop — 5 分钟轮询"]
    end

    subgraph ENGINE["核心引擎 — Python 3.11+"]
        react["ReAct 循环 — Claude tool_use · 最多 30 轮迭代"]
        tools["ToolExecutor — 6 个 MCP 工具"]
        prompts["提示模板"]
    end

    subgraph AI["AI 层"]
        claude["Claude API — Anthropic tool_use"]
    end

    subgraph SPLUNK["Splunk Enterprise"]
        mcp_srv["Splunk MCP Server — /services/mcp"]
        indexes["索引 · 事件"]
        knowledge["保存的搜索 · 告警"]
        hec["HEC 端点"]
    end

    subgraph DATA["演示数据"]
        events["examples/incident_events.jsonl — 5 步攻击链"]
    end

    header & center & sidebar ---|WebSocket| api_ws
    alert -.- center

    api_inv --> runner
    runner --> react
    runner --> watch
    watch -->|"新数据源 → 重新调查"| react
    react --> tools
    react --> claude
    tools -->|"MCP 协议 — Streamable HTTP"| mcp_srv
    prompts --> claude

    bus -.-> api_ws
    bus -.-> api_snap
    runner -.->|"推送事件"| bus
    tools -.->|"推送事件"| bus

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

## ReAct 循环详情

```mermaid
flowchart LR
    subgraph REACT["ReAct 循环（最多 30 轮迭代）"]
        direction TB
        reason["推理 — Claude 阅读上下文，决定下一步行动"]
        act["行动 — Claude 调用工具"]
        observe["观察 — 工具结果返回对话"]
        reason --> act --> observe --> reason
    end

    subgraph TOOLS["6 个工具"]
        t1["discover_splunk_data — 发现 Splunk 数据"]
        t2["explore_index_fields — 探索索引字段"]
        t3["run_spl_query — 执行 SPL 查询"]
        t4["analyze_security_events — 分析安全事件"]
        t5["validate_detection_rule — 验证检测规则"]
        t6["submit_findings — 提交调查结果"]
    end

    act --> t1 & t2 & t3 & t4 & t5 & t6

    subgraph EXIT["退出条件"]
        e1["submit_findings 被调用"]
        e2["end_turn（Claude 结束）"]
        e3["达到最大迭代数"]
    end

    t6 --> e1

    style REACT fill:#1a0d2e,stroke:#7c4dff,color:#e0e0e0
    style TOOLS fill:#0d2a0d,stroke:#66bb6a,color:#e0e0e0
    style EXIT fill:#2a0d0d,stroke:#ef5350,color:#e0e0e0
```

---

## 持续监控模式

```mermaid
flowchart TB
    done["ReAct 调查完成"]
    capture["捕获基线 — 索引 + 源类型"]
    sleep["等待 5 分钟"]
    check["轮询 MCP — get_indexes + get_metadata"]
    diff{"有新数据源？"}
    reinvestigate["触发新 ReAct 调查"]
    update["更新基线"]
    noop["无变化"]
    stop["POST /api/watch/stop"]

    done --> capture --> sleep --> check --> diff
    diff -->|是| reinvestigate --> update --> sleep
    diff -->|否| noop --> sleep
    stop -.->|"取消"| sleep

    style done fill:#0d2a0d,stroke:#66bb6a,color:#e0e0e0
    style reinvestigate fill:#2a0d0d,stroke:#ef5350,color:#e0e0e0
    style diff fill:#2a2a0d,stroke:#ffa726,color:#e0e0e0
```

---

## EventBus 频道

| 频道 | 负载描述 |
|------|----------|
| `phase` | 阶段名称 + 状态（pending/running/done） |
| `mcp_call` | MCP 工具名、SPL 查询、状态、行数、错误 |
| `ai_call` | ReAct 推理类型、迭代数、推理文本、阶段结果 |
| `discovery` | 服务器信息、索引、主机、源类型、字段发现 |
| `evidence` | 查询结果、采集状态 |
| `analysis` | 时间线、检测盲区、用例、规则验证 |
| `recommendation` | 响应操作、执行摘要、风险等级 |
| `status` | 开始/完成/错误及耗时 |
| `watch` | 监控生命周期事件（started, checking, changes_detected, stopped） |

---

## MCP 工具映射

| MirrorLens 工具 | MCP 服务调用 | 阶段 |
|----------------|------------|------|
| `discover_splunk_data` | `get_info` + `get_indexes` + `get_metadata(hosts)` + `get_metadata(sourcetypes)` + `get_knowledge_objects(saved_searches)` + `get_knowledge_objects(alerts)` | 发现 |
| `explore_index_fields` | `run_query("search index={name} \| fieldsummary")` + `run_query("search index={name} \| head 3")` | 发现 |
| `run_spl_query` | `run_query(spl)` | 调查 |
| `analyze_security_events` | Claude API（无 MCP） | 分析 |
| `validate_detection_rule` | `run_query(spl)` | 验证 |
| `submit_findings` | 无（本地聚合） | 提交 |

---

## 关键设计决策

| 决策 | 原因 |
|------|------|
| **MCP 优先** | 所有 Splunk 交互通过官方 MCP Server，确保协议合规和奖项资格 |
| **ReAct 而非管道** | Claude 自主决定调查路径，对未知数据结构更具适应性 |
| **AI 建议性** | 所有分析均为只读，不执行自动响应，需人工审核 |
| **实时规则验证** | 生成的规则在真实 Splunk 数据上验证，不仅检查语法，证明检测可行性 |
| **持续监控** | 轻量 MCP 轮询发现新数据源，无需持续完整调查，高性价比 7×24 监控 |
| **EventBus 架构** | 将调查引擎与仪表盘解耦，支持 WebSocket 流式推送和快照重放 |
| **密钥隔离** | 所有凭证在 `.env` 中（已 gitignore），代码仅引用环境变量 |
