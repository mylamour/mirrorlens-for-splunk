# MirrorLens — Quick Start

> [中文快速开始](#中文快速开始)

Get MirrorLens running in under 5 minutes.

---

## Prerequisites

- Docker + Docker Compose  **or** Python 3.11+ with `uv` + Node.js 18+ with `pnpm`
- Splunk Enterprise with MCP Server enabled (`/services/mcp`)
- Anthropic API key

---

## Option A — Docker (Recommended)

```bash
git clone https://github.com/mylamour/mirrorlens-for-splunk.git
cd mirrorlens-for-splunk

cp .env.example .env
# Open .env and fill in the three required values:
#   SPLUNK_MCP_URL=https://your-splunk:8089/services/mcp
#   SPLUNK_MCP_TOKEN=your-bearer-token
#   ANTHROPIC_API_KEY=your-api-key
# That's it — MirrorLens auto-discovers all indexes.

docker compose up --build
```

Open **http://localhost:8091** — the dashboard is ready.

---

## Option B — Manual Dev Setup

```bash
git clone https://github.com/mylamour/mirrorlens-for-splunk.git
cd mirrorlens-for-splunk

cp .env.example .env
# Fill in credentials (see above)

# Install dependencies
uv sync
cd dashboard/backend && uv sync && cd ../..
cd dashboard/frontend && pnpm install && cd ../..

# Terminal 1: backend
cd dashboard/backend
uv run uvicorn mirrorlens_dashboard.server:app --reload --port 8091

# Terminal 2: frontend (in a new terminal)
cd dashboard/frontend
pnpm dev
```

Open **http://localhost:5174**

---

## Running Your First Investigation

1. The dashboard opens to a connection form.
2. Enter your **Splunk MCP URL** (e.g. `https://splunk.example.com:8089/services/mcp`) and **Bearer Token**.
3. Click **Connect & Investigate**.
4. Watch the AI autonomously:
   - Discover all indexes, hosts, and sourcetypes
   - Run targeted SPL queries
   - Build a MITRE ATT&CK timeline
   - Identify detection gaps
   - Generate and validate SPL detection rules
   - **Full-screen alert fires when a rule matches live data**
5. After investigation, Watch Mode starts automatically (5-min polling).

---

## View Sample Investigation (No Splunk needed)

The dashboard ships with a real desensitized investigation result. To view it without any Splunk credentials:

1. Start the dashboard (Docker or dev mode — see above)
2. On the connection screen, click **⚡ Load Sample Investigation**
3. The full investigation result loads instantly — 12-step MITRE ATT&CK timeline, 8 detection gaps, 5 validated rules all with live matches

Or via API directly:
```bash
curl -X POST http://localhost:8091/api/demo/load
```

---

## Load Your Own Demo Data (Optional)

If you want to use the included synthetic attack data:

```bash
# Requires SPLUNK_HEC_URL and SPLUNK_HEC_TOKEN in .env
uv run mirrorlens ingest

# Or run the full demo (ingest + investigate via CLI)
uv run mirrorlens demo
```

---

## Model Selection

By default MirrorLens uses `claude-sonnet-4-20250514`. To use Opus:

```bash
# In .env:
ANTHROPIC_MODEL=claude-opus-4-6
```

Or override at runtime:
```bash
docker compose run -e ANTHROPIC_MODEL=claude-opus-4-6 mirrorlens
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `SPLUNK_MCP_URL not set` | Check `.env` is filled in and `docker compose` picks it up |
| SSL certificate errors | Set `SPLUNK_VERIFY_SSL=false` in `.env` |
| `Connection refused` on MCP | Verify Splunk MCP Server is enabled and the port is reachable |
| Dashboard blank after connect | Check browser console for WebSocket errors; ensure backend is running on 8091 |
| Frontend shows "Connecting..." indefinitely | Check backend logs (`docker compose logs mirrorlens`) |

---

---

## 中文快速开始

5 分钟内启动 MirrorLens。

### 前置要求

- Docker + Docker Compose **或** Python 3.11+（`uv`）+ Node.js 18+（`pnpm`）
- 已启用 MCP Server 的 Splunk Enterprise（`/services/mcp`）
- Anthropic API 密钥

### 方式 A — Docker（推荐）

```bash
git clone https://github.com/mylamour/mirrorlens-for-splunk.git
cd mirrorlens-for-splunk

cp .env.example .env
# 编辑 .env，填入三个必填项：
#   SPLUNK_MCP_URL=https://your-splunk:8089/services/mcp
#   SPLUNK_MCP_TOKEN=your-bearer-token
#   ANTHROPIC_API_KEY=your-api-key
# 仅此即可 — MirrorLens 会自动发现所有索引

docker compose up --build
```

打开 **http://localhost:8091**，仪表盘即可使用。

### 方式 B — 手动开发环境

```bash
git clone https://github.com/mylamour/mirrorlens-for-splunk.git
cd mirrorlens-for-splunk

cp .env.example .env
# 填入凭证（见上方）

uv sync
cd dashboard/backend && uv sync && cd ../..
cd dashboard/frontend && pnpm install && cd ../..

# 终端 1：后端
cd dashboard/backend
uv run uvicorn mirrorlens_dashboard.server:app --reload --port 8091

# 终端 2：前端
cd dashboard/frontend
pnpm dev
```

打开 **http://localhost:5174**

### 第一次调查

1. 仪表盘显示连接表单。
2. 输入 **Splunk MCP URL** 和 **Bearer Token**。
3. 点击 **Connect & Investigate**。
4. 观察 AI 自主完成：发现索引→执行 SPL→构建攻击时间线→识别检测盲区→验证检测规则→**规则命中实时数据时触发全屏警报**。
5. 调查结束后，Watch 模式自动启动（每 5 分钟轮询）。

### 导入演示数据（可选）

```bash
# 需要在 .env 中配置 SPLUNK_HEC_URL 和 SPLUNK_HEC_TOKEN
uv run mirrorlens ingest

# 完整演示（导入 + CLI 调查）
uv run mirrorlens demo
```
