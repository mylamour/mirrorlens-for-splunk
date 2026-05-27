# MirrorLens for Splunk

**基于 Splunk MCP Server 的 AI 自主安全调查平台**

> [English Documentation](README.md)

MirrorLens 是一个 AI 自主安全调查系统，通过官方 [Splunk MCP Server](https://dev.splunk.com/) 连接 Splunk。它使用 Claude 驱动的 ReAct 循环发现数据、执行 SPL 查询、构建 MITRE ATT&CK 攻击时间线、识别检测盲区、对检测规则进行实时验证，并进入持续监控模式 —— 全部通过实时赛博朋克风格仪表盘呈现。

---

## 比赛信息

- **赛道：** Security
- **奖项目标：** Best Use of Splunk MCP Server
- **截止日期：** 2026-06-15 09:00 PDT

---

## 核心功能

| 功能 | 描述 |
|------|------|
| **ReAct 循环** | Claude 原生 `tool_use` 自主调查循环（推理→行动→观察），最多 30 轮迭代 |
| **MCP 优先** | 所有 Splunk 交互均通过官方 MCP Server，不使用直接 REST API |
| **实时仪表盘** | WebSocket 实时推送的赛博朋克 UI，实时展示调查进度 |
| **规则验证** | 生成的检测规则在 Splunk 实时数据上验证并显示匹配数 |
| **规则触发警报** | 当验证规则触发（匹配数 > 0）时，弹出全屏红色警报覆盖层 |
| **持续监控模式** | 调查完成后自动进入轻量 MCP 轮询（每 5 分钟）；发现新数据源时触发新一轮 ReAct 调查 |
| **CLI + 仪表盘** | 同时支持 Rich 终端 CLI 和全功能 Web 仪表盘 |

---

## 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│  实时仪表盘（React 19 + MUI + Framer Motion）                        │
│  ┌──────────┐ ┌───────────────────┐ ┌─────────────────┐             │
│  │  顶部栏   │ │   中央面板        │ │  AI 活动侧边栏  │             │
│  │  阶段进度 │ │   发现            │ │  AI 推理        │             │
│  │  监控状态 │ │   时间线          │ │  Splunk MCP     │             │
│  │          │ │   规则 + 盲区     │ │  调用记录       │             │
│  │          │ │   响应手册        │ │                 │             │
│  └──────────┘ └───────────────────┘ └─────────────────┘             │
│        ↑ WebSocket /api/stream                                       │
├─────────────────────────────────────────────────────────────────────┤
│  仪表盘后端（FastAPI + EventBus）                                     │
│  EventBus 9 个频道：phase, mcp_call, ai_call, discovery, evidence,  │
│  analysis, recommendation, status, watch                             │
├─────────────────────────────────────────────────────────────────────┤
│  核心引擎（ReAct 循环 + ToolExecutor）                                │
│  Claude API tool_use — 6 个工具：                                    │
│  discover_splunk_data / explore_index_fields / run_spl_query         │
│  analyze_security_events / validate_detection_rule / submit_findings │
│        ↑ MCP 协议（Streamable HTTP）                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Splunk Enterprise                                                   │
│  MCP Server / 索引 / 保存的搜索 / 告警 / 知识对象                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 调查流程

```
1. 发现阶段（通过 MCP）
   get_indexes → get_metadata → explore_index_fields
   ↓
2. 调查阶段（通过 MCP）
   run_spl_query（跨多个索引的针对性 SPL 查询，自动适应）
   ↓
3. 分析阶段（Claude AI）
   analyze_security_events → ATT&CK 时间线 + 检测盲区 + 用例
   ↓
4. 验证阶段（MCP + AI）
   validate_detection_rule → 在实时数据上验证生成的 SPL
   ↓
5. 提交阶段
   submit_findings → 执行摘要 + 风险等级 + 关键发现
   ↓
6. 持续监控
   每 5 分钟轮询索引和源类型 → 发现变化时触发新一轮 ReAct 调查
```

---

## 快速开始

请参阅 [QUICKSTART.md](QUICKSTART.md) 获取最快速的运行指南。

### 前置要求

- Python 3.11+，[uv](https://docs.astral.sh/uv/)
- Node.js 18+ 及 pnpm
- 已启用 [Splunk MCP Server](https://dev.splunk.com/) 的 Splunk Enterprise
- Splunk HEC Token（用于演示数据导入）
- Anthropic API 密钥（或兼容代理）

### 安装

```bash
git clone <repo-url>
cd mirrorlens-for-splunk

uv sync
cd dashboard/backend && uv sync && cd ../..
cd dashboard/frontend && pnpm install && cd ../..
```

### 配置

```bash
cp .env.example .env
# 编辑 .env，填入 Splunk 和 Anthropic 凭证
```

| 变量 | 描述 |
|------|------|
| `SPLUNK_MCP_URL` | Splunk MCP 服务端点 |
| `SPLUNK_MCP_TOKEN` | MCP 认证 Bearer Token |
| `SPLUNK_HEC_URL` | Splunk HEC 端点（用于演示数据） |
| `SPLUNK_HEC_TOKEN` | HEC 令牌 |
| `SPLUNK_INDEX` | 目标索引（默认：`mirrorlens_demo`） |
| `SPLUNK_VERIFY_SSL` | SSL 验证（自签名证书设为 `false`） |
| `ANTHROPIC_API_KEY` | Claude API 密钥 |
| `ANTHROPIC_BASE_URL` | API 代理地址（直连留空） |
| `ANTHROPIC_MODEL` | 模型名称（默认：`claude-sonnet-4-20250514`） |

### 使用方式

#### 一键 Docker 部署

```bash
cp .env.example .env  # 填入凭证
docker compose up --build
# 打开 http://localhost:8091
```

#### 命令行模式

```bash
uv run mirrorlens demo          # 导入演示数据 + 运行调查
uv run mirrorlens ingest        # 向 Splunk 导入演示数据
uv run mirrorlens investigate   # 运行 AI 调查
```

#### 仪表盘开发模式

```bash
# 终端 1：启动后端
cd dashboard/backend
uv run uvicorn mirrorlens_dashboard.server:app --reload --port 8091

# 终端 2：启动前端
cd dashboard/frontend
pnpm dev
```

打开 `http://localhost:5174` → 输入 Splunk MCP URL 和 Token → 点击 "Connect & Investigate"

---

## 仪表盘面板

| 面板 | 描述 |
|------|------|
| **顶部栏** | 阶段进度（ReAct LOOP 徽章 + 迭代计数器）、WATCHING 指示器、指标卡、实时状态 |
| **Discovery & Evidence** | Splunk 服务器信息、索引及事件数、字段发现、主机、源类型、证据查询 |
| **Attack Timeline** | MITRE ATT&CK 技术时间线与战术映射 |
| **Generated Detection Rules** | AI 生成的 SPL 检测规则，含优先级和 MITRE 映射 |
| **Detection Gaps** | 按严重程度评级的检测盲区（攻击步骤缺乏检测覆盖） |
| **Validated Detection Rules** | 在 Splunk 实时数据上验证的规则及匹配数 |
| **Response Playbook** | 执行摘要 + 编号的修复操作及风险等级 |
| **AI Reasoning**（侧边栏） | 实时 ReAct 推理阶段 |
| **Splunk MCP**（侧边栏） | 实时 MCP 工具调用，含 SPL、状态、行数 |

### 规则匹配警报

当验证的检测规则 `match_count > 0` 时，触发**全屏红色警报覆盖层**，显示规则名称、匹配数、SPL 查询和样本匹配。关闭方式：ACKNOWLEDGE 按钮、Esc 键、点击外部、10 秒自动关闭。

### 持续监控模式

ReAct 调查完成后：

1. 捕获基线：通过 MCP 获取当前索引和源类型
2. 每 5 分钟轮询（可通过 `watch_interval` 配置）
3. 发现新索引或源类型时 → 触发新一轮 ReAct 调查
4. 仪表盘显示 WATCHING / CHECKING / CHANGES DETECTED 指示器
5. 通过 `POST /api/watch/stop` 停止

---

## API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| `POST` | `/api/investigate` | 启动调查（可选 `index`, `splunk_url`, `splunk_token`, `watch_interval`） |
| `GET` | `/api/status` | 返回 `running`, `phase`, `elapsed_seconds`, `watch_running` |
| `POST` | `/api/watch/stop` | 停止持续监控 |
| `GET` | `/api/snapshot` | 所有 9 个 EventBus 频道的完整重播状态 |
| `WS` | `/api/stream` | 实时 WebSocket 事件流 |

---

## 使用的 MCP 工具

| 工具 | 用途 | 阶段 |
|------|------|------|
| `get_info` | 验证 Splunk 连接 | 发现 |
| `get_indexes` | 列出可用索引 | 发现 |
| `get_metadata` | 枚举主机、源类型、数据源 | 发现 |
| `get_index_info` | 获取索引结构和字段摘要 | 发现 |
| `run_query` | 执行只读 SPL 查询 | 调查 |
| `get_knowledge_objects` | 列出保存的搜索和告警 | 调查 |

---

## 演示数据

`examples/` 目录包含合成的 5 步攻击链：

| 步骤 | 技术 | 主机 | 检测状态 |
|------|------|------|----------|
| 1 | T1190 SQL 注入 | webapp-01 | 已检测（Suricata，130秒） |
| 2 | T1059.004 反向 Shell | linux-01 | 已检测（auditd，30秒） |
| 3 | T1558.003 Kerberoasting | dc-01 | 已检测（Windows 安全日志，720秒） |
| 4 | T1021.002 SMB 横向移动 | ws-01 | **未检测** |
| 5 | T1003.001 LSASS 内存转储 | ws-01 | **证据不足** |

所有数据均为合成数据 —— 不包含真实主机、IP 或客户数据。

---

## AI 使用方式

MirrorLens 通过 Anthropic 原生 `tool_use` API 在 ReAct 循环中使用 Claude AI：

1. **自主调查** — Claude 自主决定调用哪些工具、执行什么 SPL、何时进入下一阶段。无硬编码流程，AI 根据发现自适应调整。
2. **证据分析** — 从原始 Splunk 事件构建 MITRE ATT&CK 时间线，含技术 ID、战术、置信度。
3. **检测盲区分析** — 将攻击时间线与现有 Splunk 保存的搜索和告警比对，发现检测盲区。
4. **规则生成 + 实时验证** — 生成 SPL 检测规则并在 Splunk 实时数据上验证其是否会触发。
5. **响应建议** — 生成分类的（遏制/根除/恢复）响应操作及风险等级。

所有 AI 分析均为**只读和建议性质** — 不执行任何自动响应操作。

---

## 测试

```bash
uv run pytest tests/ -v                          # 所有单元测试
uv run pytest tests/ -v -m "not integration"     # 跳过实时 Splunk 测试
uv run pytest tests/ -v -m integration           # 仅实时集成测试
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| AI 引擎 | Claude API（Anthropic `tool_use`），ReAct 循环 |
| Splunk 集成 | MCP SDK（`mcp>=1.20`，Streamable HTTP） |
| 核心后端 | Python 3.11+，`uv` |
| 仪表盘后端 | FastAPI，uvicorn，WebSocket，asyncio EventBus |
| 仪表盘前端 | React 19，TypeScript，Vite，MUI 9，Framer Motion |
| CLI | Click，Rich |
| 测试 | pytest，pytest-asyncio |

---

## 安全与开源边界

- 所有凭证隔离在 `.env` 中（已 gitignore）
- 代码中不包含真实 Splunk 实例地址
- 本仓库仅包含公开的黑客松演示
- **不**包含商业产品源代码、生产逻辑、客户数据或密钥

---

## 许可证

MIT — 参见 [LICENSE](LICENSE)。
