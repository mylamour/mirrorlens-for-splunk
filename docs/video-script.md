# Video Script / 演示视频脚本

> Target: 3-minute demo video with English narration.
> 目标：3 分钟演示视频，英文旁白。

---

## Scene 1: Problem (0:00–0:25) / 场景1：问题

**Narration:**
"Security teams have more data in Splunk than ever — but turning that data into an investigation is still painfully manual. You search, you pivot, you correlate across indexes, and you try to figure out what your detections are missing. What if an AI agent could do that entire workflow through Splunk's MCP Server?"

**画面：**
Show a Splunk search interface with multiple tabs open, conveying complexity.
展示打开多个标签的 Splunk 搜索界面，传达复杂性。

---

## Scene 2: Connect (0:25–0:45) / 场景2：连接

**Narration:**
"MirrorLens connects to your Splunk instance through the official MCP Server. Just enter your MCP endpoint and token, and click Connect & Investigate. That's it — the AI takes over."

**画面：**
Show the MirrorLens dashboard idle state → type in MCP URL → click "Connect & Investigate" → status changes to LIVE, ReAct LOOP badge appears with REASON / ACT / OBSERVE indicators.

展示 MirrorLens 仪表盘空闲状态 → 输入 MCP URL → 点击"Connect & Investigate" → 状态变为 LIVE，ReAct LOOP 徽章出现。

---

## Scene 3: Discovery (0:45–1:15) / 场景3：发现

**Narration:**
"The AI agent starts by discovering what data exists. Through MCP, it finds all indexes, hosts, sourcetypes, and saved searches. It then drills into each security-relevant index to understand the field schema. The default dashboard stays result-focused, while the Agent Trace drawer preserves the full reasoning and MCP proof."

**画面：**
Discovery & Evidence appears as secondary context below the result panels. Open Agent Trace / MCP Proof to show "Reasoning — Deciding next investigation step" plus `get_indexes`, `get_metadata`, and `run_query` calls with OK status and row counts.

Discovery & Evidence 作为辅助上下文展示服务器信息、索引及事件数、字段发现标签、主机、源类型。打开 Agent Trace / MCP Proof 抽屉展示推理过程和 MCP 调用状态。

---

## Scene 4: Investigation + Analysis (1:15–1:55) / 场景4：调查+分析

**Narration:**
"Now the agent runs targeted SPL queries across multiple indexes, adapting when queries return zero results. It's not following a script — it's reasoning about what to look for next based on what it's already found."

**画面 (1:15–1:35):**
Evidence queries appear in secondary context. Agent Trace / MCP Proof shows multiple `run_query` calls. Iteration counter incrementing.

证据查询显示在辅助上下文中。Agent Trace / MCP Proof 显示多个 `run_query` 调用。迭代计数器递增。

**Narration (cont'd):**
"Once it has enough evidence, it builds a MITRE ATT&CK timeline showing each attack technique, and identifies detection gaps — attack steps where your Splunk instance has no corresponding alert."

**画面 (1:35–1:55):**
Attack Timeline becomes a primary result panel with technique IDs (T1190, T1059, etc.) and tactic labels. Detection Gaps remain visible as secondary context.

Attack Timeline 成为主结果面板，含技术 ID 和战术标签。Detection Gaps 作为辅助上下文保留。

---

## Scene 5: Rule Validation + Alert (1:55–2:30) / 场景5：规则验证+警报

**Narration:**
"Here's where it gets powerful. The agent doesn't just generate detection rules — it validates them against your live Splunk data. Watch — when a rule actually matches real events..."

**画面 (1:55–2:10):**
Detection Rules panel appears with generated SPL rules, priority badges, validation status, and match counts in one place.

Detection Rules 面板合并展示生成的 SPL 规则、优先级、验证状态和匹配数。

**Narration (cont'd):**
"...you get a full-screen alert. This rule would have caught 47 events. That's not a theoretical detection — that's proven coverage."

**画面 (2:10–2:30):**
**FULL-SCREEN RED ALERT** fires: "DETECTION RULE FIRED" with pulsing header, rule name, "47 MATCHES" badge, SPL query, sample matches. User clicks ACKNOWLEDGE to dismiss.

**全屏红色警报**触发："DETECTION RULE FIRED"脉冲标题、规则名称、"47 MATCHES" 徽章、SPL 查询、样本匹配。用户点击 ACKNOWLEDGE 关闭。

---

## Scene 6: Playbook + Watch (2:30–2:50) / 场景6：Playbook + 监控

**Narration:**
"The investigation wraps up with a Response Playbook — containment, eradication, and recovery actions, each with a risk level. And then MirrorLens enters continuous watch mode — polling Splunk every five minutes for new data sources. If a new index or sourcetype appears, it automatically starts a new investigation."

**画面:**
Response Playbook panel fills in with executive summary and numbered actions. "WATCHING" badge appears (pulsing amber) next to the green ReAct LOOP checkmark in the header. Show WATCHING indicator in the header bar too.

Response Playbook 面板填入执行摘要和编号操作。"WATCHING" 徽章（脉冲琥珀色）出现在标题栏。

---

## Scene 7: Value Prop (2:50–3:00) / 场景7：价值主张

**Narration:**
"In under three minutes, MirrorLens autonomously completed what typically takes a security analyst two to four hours — discovering data across multiple indexes, running dozens of targeted queries, building a MITRE ATT&CK timeline, identifying detection gaps, generating and validating SPL detection rules against live data, and producing a response playbook. All through the Splunk MCP Server — zero manual queries, zero hardcoded logic, fully autonomous."

**画面:**
Pull back to show the result-first dashboard: Attack Timeline, Detection Rules, and Response Playbook, with WATCHING badge pulsing. Open Agent Trace / MCP Proof briefly to show MCP evidence. Overlay key metrics: "X indexes scanned · Y queries executed · Z rules validated · N minutes". Fade to MirrorLens logo + "Built with Splunk MCP Server."

全景展示结果优先的仪表盘：Attack Timeline、Detection Rules、Response Playbook，WATCHING 标签脉冲。短暂打开 Agent Trace / MCP Proof 展示 MCP 证据。叠加关键指标："X 个索引扫描 · Y 个查询执行 · Z 条规则验证 · N 分钟"。淡入 MirrorLens logo + "Built with Splunk MCP Server."
