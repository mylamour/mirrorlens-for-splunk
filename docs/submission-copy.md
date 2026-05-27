# Submission Copy / 提交文案

> For Devpost submission. / 用于 Devpost 提交。

---

## Inspiration / 灵感来源

Security teams already have the data in Splunk, but the path from alert to understanding is still too manual. An analyst must context-switch between dozens of searches, mentally correlate events across indexes, and figure out what's missing from detection coverage — all under time pressure.

安全团队已经在 Splunk 中拥有数据，但从告警到理解的路径仍然过于手动。分析师必须在数十个搜索间切换上下文，在脑中关联不同索引的事件，并在时间压力下找出检测覆盖中的盲区。

MirrorLens explores how an AI agent can use Splunk MCP Server to do that investigation autonomously — discovering data, running targeted queries, building attack timelines, and even validating the detection rules it generates.

MirrorLens 探索了 AI 代理如何利用 Splunk MCP Server 自主完成调查 —— 发现数据、执行针对性查询、构建攻击时间线，甚至验证其生成的检测规则。

---

## What It Does / 功能

MirrorLens is an autonomous AI security investigator powered by Claude and connected to Splunk via the official MCP Server. When you click "Connect & Investigate," it:

MirrorLens 是一个由 Claude 驱动、通过官方 MCP Server 连接 Splunk 的 AI 自主安全调查系统。当你点击"Connect & Investigate"时，它会：

1. **Discovers** all available indexes, hosts, sourcetypes, and saved searches via MCP
   **发现**所有可用的索引、主机、源类型和保存的搜索

2. **Explores** each security-relevant index — field schemas, sample events, event distributions
   **探索**每个安全相关索引 —— 字段结构、样本事件、事件分布

3. **Investigates** by running targeted SPL queries, adapting when queries return zero results
   **调查** —— 执行针对性 SPL 查询，当查询无结果时自动调整策略

4. **Analyzes** evidence to build a MITRE ATT&CK timeline, identify detection gaps, and generate SPL detection rules
   **分析**证据以构建 MITRE ATT&CK 时间线、识别检测盲区、生成 SPL 检测规则

5. **Validates** every generated rule against live Splunk data — proving whether it would actually fire
   **验证**每条生成的规则在实时 Splunk 数据上是否会触发

6. **Watches** continuously after investigation, polling for new data sources every 5 minutes and triggering new investigations when changes appear
   **持续监控** —— 调查后每 5 分钟轮询新数据源，发现变化时触发新一轮调查

Everything streams live to a cyberpunk-themed dashboard where you can watch the AI think, see MCP calls fire, and get alerted when a detection rule matches real events.

所有过程实时推送到赛博朋克风格仪表盘，你可以观看 AI 的思考过程、查看 MCP 调用、并在检测规则匹配真实事件时收到警报。

---

## How We Built It / 如何构建

**Core AI Engine:**
- Claude API with native `tool_use` in a ReAct (Reasoning + Acting) loop — up to 30 autonomous iterations
- 6 custom tools wrapping Splunk MCP Server calls: `discover_splunk_data`, `explore_index_fields`, `run_spl_query`, `analyze_security_events`, `validate_detection_rule`, `submit_findings`
- No hardcoded investigation workflow — Claude decides the investigation path based on what it discovers

**核心 AI 引擎：**
- Claude API 原生 `tool_use` 的 ReAct 循环 —— 最多 30 轮自主迭代
- 6 个自定义工具封装 Splunk MCP Server 调用
- 无硬编码调查流程 —— Claude 根据发现自主决定调查路径

**Splunk Integration:**
- Official Splunk MCP Server via `mcp` SDK (Streamable HTTP transport)
- All data access is read-only through MCP — no direct Splunk REST API calls
- Continuous watch mode uses MCP polling to detect new indexes and sourcetypes

**Splunk 集成：**
- 通过 `mcp` SDK 使用官方 Splunk MCP Server（Streamable HTTP 传输）
- 所有数据访问均通过 MCP 只读 —— 不直接调用 Splunk REST API
- 持续监控模式通过 MCP 轮询检测新索引和源类型

**Real-Time Dashboard:**
- React 19 + TypeScript + MUI + Framer Motion for a cyberpunk-themed investigation UI
- FastAPI backend with async EventBus (9 channels, 200-event replay buffer)
- WebSocket streaming for live progress + full-screen alert overlays when rules fire

**实时仪表盘：**
- React 19 + TypeScript + MUI + Framer Motion 构建赛博朋克风格调查 UI
- FastAPI 后端配异步 EventBus（9 个频道，200 事件重放缓冲）
- WebSocket 实时推送 + 规则触发时全屏警报覆盖层

---

## Challenges / 挑战

- Getting Claude to adapt its SPL queries when Splunk field names or data shapes differed from expectations — solved by including field exploration results in the conversation context
  让 Claude 在字段名或数据结构与预期不同时调整 SPL —— 通过将字段探索结果加入对话上下文解决

- Balancing autonomy vs. cost — Claude can iterate extensively, so we cap at 30 iterations and truncate tool results to 30K characters
  平衡自主性与成本 —— 限制最多 30 轮迭代，工具结果截断至 30K 字符

- Streaming live investigation progress without overwhelming the dashboard — solved by EventBus with bounded replay buffers
  在不淹没仪表盘的情况下实时推送调查进度 —— 通过有界重放缓冲的 EventBus 解决

---

## What We Learned / 收获

- MCP provides a clean, standardized way for AI agents to interact with Splunk — no brittle REST API wrappers needed
  MCP 为 AI 代理与 Splunk 的交互提供了标准化接口 —— 无需脆弱的 REST API 封装

- ReAct loops with native tool_use are significantly more adaptive than hardcoded multi-phase pipelines for security investigation
  原生 tool_use 的 ReAct 循环在安全调查中比硬编码多阶段管道更具适应性

- Validating detection rules against live data is a game-changer — it's the difference between "here's a rule" and "here's a rule that would have caught 47 events"
  在实时数据上验证检测规则是革命性的 —— "这是一条规则" 与 "这条规则会捕获 47 个事件" 的区别

---

## Impact / 影响

- **Speed**: What takes a security analyst 2-4 hours of manual SPL queries and context-switching, MirrorLens completes autonomously in under 5 minutes
- **Coverage**: Explores all available indexes and sourcetypes — no blind spots from analyst fatigue or unfamiliarity
- **Validated detections**: Every generated rule is tested against live data, eliminating the gap between "rule exists" and "rule works"
- **Continuous monitoring**: Watch mode provides 24/7 detection of new data sources without ongoing analyst effort
- **MCP ecosystem**: Demonstrates how the Splunk MCP Server enables a new category of autonomous AI security tools that interact with Splunk through a standardized protocol

**速度**：安全分析师需要 2-4 小时的手动 SPL 查询，MirrorLens 在 5 分钟内自主完成。
**覆盖率**：探索所有可用索引和源类型 —— 不会因分析师疲劳而遗漏。
**经过验证的检测**：每条规则在实时数据上测试，消除"规则存在"与"规则有效"之间的差距。
**持续监控**：Watch 模式 7×24 检测新数据源，无需持续人力。
**MCP 生态**：展示 Splunk MCP Server 如何赋能新一代自主 AI 安全工具。

---

## What's Next / 下一步

- Multi-tenant support — investigate multiple Splunk instances in parallel
  多租户支持 —— 并行调查多个 Splunk 实例

- Automated response playbook execution (with human approval gate)
  自动化响应 Playbook 执行（带人工审批）

- Integration with SOAR platforms for closed-loop detection → investigation → response
  与 SOAR 平台集成，实现检测→调查→响应的闭环
