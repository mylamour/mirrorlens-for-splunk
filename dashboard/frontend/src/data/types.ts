export type PhaseStatus = "pending" | "running" | "done";

export interface PhaseEvent {
  name: string;
  step: number;
  status: PhaseStatus;
}

export interface McpCallEvent {
  tool: string;
  name?: string;
  spl?: string;
  status: "running" | "done" | "error";
  count?: number;
  row_count?: number;
  error?: string;
  result?: unknown;
}

export interface AiCallEvent {
  type: string;
  model?: string;
  status: "running" | "done" | "error";
  selected_indexes?: string[];
  reasoning?: string;
  query_count?: number;
  timeline_count?: number;
  gap_count?: number;
  usecase_count?: number;
  rec_count?: number;
  iteration?: number;
  tool?: string;
}

export interface FieldInfo {
  field: string;
  count: number;
  distinct_count: number;
  numeric_count?: number;
  values?: string;
}

export interface DiscoveryEvent {
  type: string;
  data?: unknown;
  count?: number;
  index?: string;
  fields?: FieldInfo[];
  sample_count?: number;
}

export interface EvidenceEvent {
  type: string;
  index?: number;
  name?: string;
  spl?: string;
  row_count?: number;
  error?: string;
  total_raw?: number;
  deduplicated?: number;
  saved_searches?: number;
  alerts?: number;
}

export interface AnalysisEvent {
  type: "timeline" | "gaps" | "use_cases" | "rule_validation";
  data?: unknown[];
  summary?: string;
  dwell_time?: string;
  coverage?: string;
  priority_actions?: string[];
  maturity?: string;
  rule_name?: string;
  spl?: string;
  match_count?: number;
  sample_matches?: unknown[];
}

export interface RuleValidation {
  rule_name: string;
  spl: string;
  match_count: number;
  would_fire: boolean;
  sample_matches?: unknown[];
}

export interface RecommendationEvent {
  data?: unknown[];
  executive_summary?: string;
  key_findings?: string[];
  risk_level?: string;
  validated_rules?: RuleValidation[];
}

export interface StatusEvent {
  event: "started" | "completed" | "error";
  error?: string;
  elapsed_seconds?: number;
  target_index?: string | null;
  mode?: string;
  iterations?: number;
  total_events_collected?: number;
}

export interface WatchEvent {
  event: "started" | "baseline_captured" | "checking" | "no_changes"
    | "changes_detected" | "baseline_updated" | "check_error" | "stopped" | "error";
  interval?: number;
  index_count?: number;
  sourcetype_count?: number;
  new_indexes?: string[];
  new_sourcetypes?: string[];
  error?: string;
}

export interface StreamEvent {
  channel: string;
  payload: Record<string, unknown>;
  timestamp: number;
}

export interface DashboardData {
  status: "idle" | "connecting" | "live" | "mock";
  investigationRunning: boolean;
  phases: PhaseEvent[];
  mcpCalls: McpCallEvent[];
  aiCalls: AiCallEvent[];
  discovery: DiscoveryEvent[];
  evidence: EvidenceEvent[];
  analysis: AnalysisEvent[];
  recommendations: RecommendationEvent[];
  statusEvents: StatusEvent[];
  watchEvents: WatchEvent[];
}
