import type {
  AiCallEvent,
  AnalysisEvent,
  DashboardData,
  DiscoveryEvent,
  EvidenceEvent,
  McpCallEvent,
  PhaseEvent,
  RecommendationEvent,
  StatusEvent,
  StreamEvent,
  WatchEvent,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const WS_BASE = API_BASE
  ? API_BASE.replace(/^http/, "ws")
  : `ws://${window.location.host}`;

const MAX_BUF = 60;

function append<T>(arr: T[], item: T): T[] {
  const next = [...arr, item];
  return next.length > MAX_BUF ? next.slice(-MAX_BUF) : next;
}

export function createInitialData(): DashboardData {
  return {
    status: "idle",
    investigationRunning: false,
    phases: [],
    mcpCalls: [],
    aiCalls: [],
    discovery: [],
    evidence: [],
    analysis: [],
    recommendations: [],
    statusEvents: [],
    watchEvents: [],
  };
}

export async function fetchSnapshot(): Promise<DashboardData> {
  try {
    const res = await fetch(`${API_BASE}/api/snapshot`, { signal: AbortSignal.timeout(3000) });
    const json = await res.json();
    const d = createInitialData();
    d.status = "live";
    const data = json.data ?? {};
    d.phases = (data.phase ?? []) as PhaseEvent[];
    d.mcpCalls = (data.mcp_call ?? []) as McpCallEvent[];
    d.aiCalls = (data.ai_call ?? []) as AiCallEvent[];
    d.discovery = (data.discovery ?? []) as DiscoveryEvent[];
    d.evidence = (data.evidence ?? []) as EvidenceEvent[];
    d.analysis = (data.analysis ?? []) as AnalysisEvent[];
    d.recommendations = (data.recommendation ?? []) as RecommendationEvent[];
    d.statusEvents = (data.status ?? []) as StatusEvent[];
    d.watchEvents = (data.watch ?? []) as WatchEvent[];
    return d;
  } catch {
    return { ...createInitialData(), status: "mock" };
  }
}

export function connectStream(
  onUpdate: (updater: (prev: DashboardData) => DashboardData) => void,
): () => void {
  let ws: WebSocket | null = null;
  let stopped = false;

  function connect() {
    if (stopped) return;
    ws = new WebSocket(`${WS_BASE}/api/stream`);

    ws.onopen = () => {
      onUpdate((prev) => ({ ...prev, status: "live" }));
    };

    ws.onmessage = (msg) => {
      try {
        const evt: StreamEvent = JSON.parse(msg.data);
        if (evt.channel === "heartbeat") return;
        onUpdate((prev) => applyEvent(prev, evt));
      } catch { /* ignore parse errors */ }
    };

    ws.onclose = () => {
      if (!stopped) setTimeout(connect, 2000);
    };
  }

  connect();
  return () => { stopped = true; ws?.close(); };
}

function applyEvent(prev: DashboardData, evt: StreamEvent): DashboardData {
  const p = evt.payload;
  switch (evt.channel) {
    case "phase":
      return { ...prev, phases: append(prev.phases, p as unknown as PhaseEvent) };
    case "mcp_call":
      return { ...prev, mcpCalls: append(prev.mcpCalls, p as unknown as McpCallEvent) };
    case "ai_call":
      return { ...prev, aiCalls: append(prev.aiCalls, p as unknown as AiCallEvent) };
    case "discovery":
      return { ...prev, discovery: append(prev.discovery, p as unknown as DiscoveryEvent) };
    case "evidence":
      return { ...prev, evidence: append(prev.evidence, p as unknown as EvidenceEvent) };
    case "analysis":
      return { ...prev, analysis: append(prev.analysis, p as unknown as AnalysisEvent) };
    case "recommendation":
      return { ...prev, recommendations: append(prev.recommendations, p as unknown as RecommendationEvent) };
    case "status": {
      const se = p as unknown as StatusEvent;
      return {
        ...prev,
        statusEvents: append(prev.statusEvents, se),
        investigationRunning: se.event === "started",
      };
    }
    case "watch":
      return { ...prev, watchEvents: append(prev.watchEvents, p as unknown as WatchEvent) };
    default:
      return prev;
  }
}

export async function loadDemoData(): Promise<{ summary?: Record<string, number> }> {
  const res = await fetch(`${API_BASE}/api/demo/load`, { method: "POST" });
  if (!res.ok) throw new Error(`Demo load failed: ${res.status}`);
  return res.json();
}

export async function triggerInvestigation(opts?: {
  index?: string;
  splunk_url?: string;
  splunk_token?: string;
  watch_interval?: number;
}): Promise<void> {
  await fetch(`${API_BASE}/api/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      index: opts?.index ?? null,
      splunk_url: opts?.splunk_url ?? null,
      splunk_token: opts?.splunk_token ?? null,
      watch_interval: opts?.watch_interval ?? 300,
    }),
  });
}
