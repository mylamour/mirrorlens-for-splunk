import { useState, useRef, useEffect } from "react";
import { Box, Typography, Button, TextField, InputAdornment, IconButton } from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";
import GlassCard from "./shared/GlassCard";
import DetailDrawer, { DetailField } from "./shared/DetailDrawer";
import { useData } from "../data/context";
import { triggerInvestigation, loadDemoData, fetchDashboardConfig, REPORT_FINDING_URL } from "../data/api";
import { COLORS } from "../theme";
import type { AccentColor } from "../theme";
import type { DashboardConfig } from "../data/types";

const SEVERITY_COLOR: Record<string, AccentColor> = {
  CRITICAL: "red", HIGH: "red", MEDIUM: "amber", LOW: "green",
  P1: "red", P2: "amber", P3: "green",
};

type DetailItem = {
  type: "timeline" | "gap" | "usecase" | "validation" | "evidence" | "recommendation";
  data: Record<string, unknown>;
};

export default function CenterPanel() {
  const { phases, discovery, evidence, analysis, recommendations, investigationRunning, statusEvents } = useData();
  const [detail, setDetail] = useState<DetailItem | null>(null);
  const [showSupportingContext, setShowSupportingContext] = useState(false);
  const [exportingFinding, setExportingFinding] = useState(false);

  const handleExportFinding = async (finding: Record<string, unknown>) => {
    setExportingFinding(true);
    try {
      const res = await fetch(REPORT_FINDING_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ finding, analysis, recommendation: recommendations }),
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const techId = String(finding.technique_id ?? "finding")
        .toLowerCase().replace(/[./]/g, "-");
      a.download = `mirrorlens-finding-${techId}-${new Date().toISOString().slice(0,10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setExportingFinding(false);
    }
  };

  const latestPhase = new Map<string, string>();
  for (const p of phases) latestPhase.set(p.name, p.status);

  const currentStep = getCurrentStep(latestPhase);
  const isComplete = statusEvents.some((s) => s.event === "completed");
  const errorEvent = statusEvents.find((s) => s.event === "error");
  const isIdle = !investigationRunning && !isComplete && !errorEvent && phases.length === 0;

  if (isIdle) {
    return (
      <Box sx={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <ConnectionSetup />
      </Box>
    );
  }

  if (errorEvent && !isComplete && discovery.length === 0) {
    return (
      <Box sx={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Box sx={{ textAlign: "center", maxWidth: 480 }}>
          <Typography sx={{ fontFamily: "'Orbitron'", fontWeight: 700, fontSize: 18, letterSpacing: 2, color: COLORS.red, textShadow: `0 0 12px ${COLORS.red}66`, mb: 1 }}>
            CONNECTION FAILED
          </Typography>
          <Typography sx={{ color: "grey.400", fontSize: 14, mb: 2, wordBreak: "break-word" }}>
            {errorEvent.error ?? "Unable to connect to Splunk MCP Server"}
          </Typography>
          <Button variant="outlined" onClick={() => window.location.reload()} sx={{ fontFamily: "'Orbitron'", fontWeight: 600, letterSpacing: 1, fontSize: 13, borderColor: COLORS.cyan, color: COLORS.cyan, "&:hover": { background: `${COLORS.cyan}15` } }}>
            TRY AGAIN
          </Button>
        </Box>
      </Box>
    );
  }

  const hasAnyData = discovery.length > 0 || evidence.length > 0;
  if (investigationRunning && !hasAnyData) {
    return (
      <Box sx={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Box sx={{ textAlign: "center" }}>
          <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 2, repeat: Infinity }}>
            <Typography sx={{ fontFamily: "'Orbitron'", fontWeight: 700, fontSize: 18, letterSpacing: 2, color: COLORS.cyan, textShadow: `0 0 12px ${COLORS.cyan}66`, mb: 1 }}>
              INITIALIZING
            </Typography>
          </motion.div>
          <Typography sx={{ color: "grey.500", fontSize: 14 }}>
            Connecting to Splunk MCP Server...
          </Typography>
        </Box>
      </Box>
    );
  }

  const tlData = analysis.find((a) => a.type === "timeline");
  const gapData = analysis.find((a) => a.type === "gaps");
  const ucData = analysis.find((a) => a.type === "use_cases");
  const validations = analysis.filter((a) => a.type === "rule_validation");

  const hasResultPanels =
    (tlData && (tlData.data?.length ?? 0) > 0) ||
    (gapData && (gapData.data?.length ?? 0) > 0) ||
    (ucData && (ucData.data?.length ?? 0) > 0) ||
    validations.length > 0 ||
    recommendations.some((r) => (r.data?.length ?? 0) > 0 || r.executive_summary);

  const primaryPanels: Array<{ key: string; node: React.ReactNode }> = [];
  const secondaryPanels: Array<{ key: string; node: React.ReactNode }> = [];

  if (tlData && (tlData.data?.length ?? 0) > 0) primaryPanels.push({ key: "timeline", node: <TimelineSection analysis={analysis} onSelect={(d) => setDetail({ type: "timeline", data: d })} /> });
  if ((ucData && (ucData.data?.length ?? 0) > 0) || validations.length > 0) {
    primaryPanels.push({
      key: "rules",
      node: <DetectionRulesSection analysis={analysis} validations={validations} onSelect={(type, d) => setDetail({ type, data: d })} />,
    });
  }
  if (recommendations.length > 0) {
    const latestRec = recommendations[recommendations.length - 1];
    if ((latestRec?.data?.length ?? 0) > 0 || latestRec?.executive_summary) {
      primaryPanels.push({ key: "recs", node: <RecommendSection recommendations={recommendations} onSelect={(d) => setDetail({ type: "recommendation", data: d })} /> });
    }
  }

  secondaryPanels.push({
    key: "discovery",
    node: <DiscoveryEvidencePanel discovery={discovery} evidence={evidence} currentStep={currentStep} investigating={investigationRunning} expanded={!hasResultPanels} onSelectEvidence={(d) => setDetail({ type: "evidence", data: d })} />,
  });
  if (gapData && (gapData.data?.length ?? 0) > 0) secondaryPanels.push({ key: "gaps", node: <GapsSection analysis={analysis} onSelect={(d) => setDetail({ type: "gap", data: d })} /> });

  const resultPanels = primaryPanels.length > 0 ? primaryPanels : secondaryPanels;
  const resultCols = resultPanels.length <= 1 ? 1 : Math.min(3, resultPanels.length);
  const secondaryCols = Math.min(2, secondaryPanels.length);
  const gapCount = (gapData?.data?.length ?? 0);
  const supportingSummary = `${discovery.length} discovery · ${evidence.length} evidence${gapCount > 0 ? ` · ${gapCount} gaps` : ""}`;

  return (
    <>
      <RuleMatchAlert analysis={analysis} />
      <Box
        sx={{
          height: "100%",
          overflow: { xs: "auto", md: "hidden" },
          display: "flex",
          flexDirection: "column",
          gap: 0.75,
        }}
      >
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: `repeat(${resultCols}, minmax(0, 1fr))` },
            gridAutoRows: { xs: "minmax(260px, 1fr)", md: "minmax(0, 1fr)" },
            gap: 0.75,
          }}
        >
          <AnimatePresence>
            {resultPanels.map(({ key, node }) => (
              <motion.div
                key={key}
                initial={{ opacity: 0, scale: 0.95, y: 12 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                style={{ minHeight: 0, overflow: "hidden" }}
              >
                {node}
              </motion.div>
            ))}
          </AnimatePresence>
        </Box>

        {primaryPanels.length > 0 && secondaryPanels.length > 0 && (
          <Box
            sx={{
              flexShrink: 0,
              minHeight: 34,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 1.25,
              borderTop: "1px solid rgba(255,255,255,0.06)",
              pt: 0.25,
            }}
          >
            <Button
              variant="outlined"
              size="small"
              onClick={() => setShowSupportingContext((value) => !value)}
              sx={{
                borderColor: `${COLORS.cyan}55`,
                color: COLORS.cyan,
                fontFamily: "'Orbitron'",
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: 1,
                minWidth: 180,
                py: 0.25,
                "&:hover": { background: `${COLORS.cyan}12`, borderColor: COLORS.cyan },
              }}
            >
              {showSupportingContext ? "HIDE EVIDENCE & GAPS" : "SHOW EVIDENCE & GAPS"}
            </Button>
            <Typography variant="caption" sx={{ color: "grey.600", fontSize: 11, fontFamily: "'JetBrains Mono'" }}>
              {supportingSummary}
            </Typography>
          </Box>
        )}

        {primaryPanels.length > 0 && secondaryPanels.length > 0 && showSupportingContext && (
          <Box
            sx={{
              height: { xs: "auto", md: 150 },
              minHeight: { xs: 150, md: 150 },
              flexShrink: 0,
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: `repeat(${secondaryCols}, minmax(0, 1fr))` },
              gridAutoRows: { xs: 150, md: "minmax(0, 1fr)" },
              gap: 0.75,
              opacity: 0.92,
            }}
          >
            {secondaryPanels.map(({ key, node }) => (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
                style={{ minHeight: 0, overflow: "hidden" }}
              >
                {node}
              </motion.div>
            ))}
          </Box>
        )}
      </Box>

      <DetailDrawer
        open={detail !== null}
        onClose={() => setDetail(null)}
        title={detail ? DETAIL_TITLES[detail.type] : ""}
        accent={detail ? DETAIL_ACCENTS[detail.type] : "cyan"}
        footer={detail?.type === "timeline" ? (
          <Button
            variant="outlined"
            size="small"
            disabled={exportingFinding}
            onClick={() => handleExportFinding(detail.data)}
            sx={{
              borderColor: `${COLORS.cyan}55`,
              color: COLORS.cyan,
              fontFamily: "'Orbitron'",
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: 1,
              "&:hover": { background: `${COLORS.cyan}12`, borderColor: COLORS.cyan },
            }}
          >
            {exportingFinding ? "EXPORTING..." : "EXPORT FINDING CARD"}
          </Button>
        ) : undefined}
      >
        {detail && <DetailContent item={detail} />}
      </DetailDrawer>

    </>
  );
}

const DETAIL_TITLES: Record<DetailItem["type"], string> = {
  timeline: "Attack Finding Detail",
  gap: "Detection Gap Detail",
  usecase: "Detection Rule Detail",
  validation: "Rule Validation Detail",
  evidence: "Evidence Query Detail",
  recommendation: "Response Action Detail",
};

const DETAIL_ACCENTS: Record<DetailItem["type"], AccentColor> = {
  timeline: "red",
  gap: "red",
  usecase: "green",
  validation: "green",
  evidence: "cyan",
  recommendation: "amber",
};

function DetailContent({ item }: { item: DetailItem }) {
  const d = item.data;
  switch (item.type) {
    case "timeline":
      return (
        <>
          <DetailField label="Technique" value={`${d.technique_id ?? ""} ${d.technique_name ?? ""}`} color={COLORS.red} />
          <DetailField label="Tactic" value={d.tactic as string} color={COLORS.amber} />
          <DetailField label="Timestamp" value={d.timestamp as string} mono />
          <DetailField label="Host" value={d.host as string} color={COLORS.green} />
          <DetailField label="Description" value={d.description as string} />
          <DetailField label="Evidence" value={d.evidence as string} />
          <DetailField label="Confidence" value={d.confidence as string} />
        </>
      );
    case "gap":
      return (
        <>
          <DetailField label="Severity" value={d.severity as string} color={COLORS[SEVERITY_COLOR[d.severity as string] ?? "amber"]} />
          <DetailField label="Technique" value={`${d.technique_id ?? ""} ${d.technique_name ?? ""}`} color={COLORS.red} />
          <DetailField label="Gap Description" value={d.gap_description as string} />
          <DetailField label="Recommended SPL" value={d.recommended_spl as string} mono color={COLORS.cyan} />
          <DetailField label="Recommended Alert Name" value={d.recommended_alert_name as string} />
        </>
      );
    case "usecase":
      return (
        <>
          <DetailField label="Name" value={d.name as string} color={COLORS.green} />
          <DetailField label="Priority" value={d.priority as string} color={COLORS[SEVERITY_COLOR[d.priority as string] ?? "green"]} />
          <DetailField label="Description" value={d.description as string} />
          <DetailField label="MITRE Technique" value={d.mitre_technique as string} color={COLORS.red} />
          <DetailField label="MITRE Tactic" value={d.mitre_tactic as string} />
          <DetailField label="SPL Query" value={d.spl_query as string} mono color={COLORS.cyan} />
          <DetailField label="Alert Condition" value={d.alert_condition as string} color={COLORS.amber} />
          <DetailField label="Data Sources" value={Array.isArray(d.data_sources_required) ? (d.data_sources_required as string[]).join(", ") : d.data_sources_required as string} />
        </>
      );
    case "validation":
      return (
        <>
          <DetailField label="Rule Name" value={d.rule_name as string} />
          <DetailField label="Match Count" value={d.match_count as number} color={(d.match_count as number) > 0 ? COLORS.green : COLORS.amber} />
          <DetailField label="SPL Query" value={d.spl as string} mono color={COLORS.cyan} />
          {Array.isArray(d.sample_matches) && (d.sample_matches as unknown[]).length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" sx={{ color: "grey.500", fontSize: 11, fontFamily: "'Orbitron'", letterSpacing: 1, textTransform: "uppercase", display: "block", mb: 0.5 }}>
                Sample Matches
              </Typography>
              {(d.sample_matches as Array<Record<string, unknown>>).slice(0, 5).map((m, i) => (
                <Box key={i} sx={{ px: 1.5, py: 0.75, mb: 0.5, borderRadius: 0.5, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
                  <Typography sx={{ color: "grey.400", fontSize: 12, fontFamily: "'JetBrains Mono'", wordBreak: "break-all", lineHeight: 1.5 }}>
                    {JSON.stringify(m, null, 2)}
                  </Typography>
                </Box>
              ))}
            </Box>
          )}
        </>
      );
    case "evidence":
      return (
        <>
          <DetailField label="Query Name" value={d.name as string} />
          <DetailField label="SPL Query" value={d.spl as string} mono color={COLORS.cyan} />
          <DetailField label="Row Count" value={d.row_count as number} color={(d.row_count as number) > 0 ? COLORS.green : "grey.500"} />
          {d.error && <DetailField label="Error" value={d.error as string} color={COLORS.red} />}
        </>
      );
    case "recommendation":
      return (
        <>
          <DetailField label="Category" value={(d.category as string)?.toUpperCase()} color={COLORS.cyan} />
          <DetailField label="Action" value={d.action as string} />
          <DetailField label="Risk Level" value={d.risk_level as string} color={COLORS[d.risk_level === "HIGH" ? "red" : d.risk_level === "MEDIUM" ? "amber" : "green"]} />
          <DetailField label="Validation SPL" value={d.spl_validation as string} mono color={COLORS.cyan} />
        </>
      );
    default:
      return null;
  }
}

/* ---------- helpers ---------- */

function getCurrentStep(latestPhase: Map<string, string>): number {
  if (latestPhase.has("ReAct Loop")) {
    const s = latestPhase.get("ReAct Loop");
    return s === "done" ? 5 : 3;
  }
  const order = ["Discover", "Explore", "Investigate", "Analyze", "Recommend"];
  let maxDone = 0;
  for (let i = 0; i < order.length; i++) {
    const s = latestPhase.get(order[i]);
    if (s === "done" || s === "running") maxDone = i + 1;
  }
  return maxDone;
}

/* ---------- Clickable row style ---------- */

const clickableRow = {
  cursor: "pointer",
  transition: "background 0.15s",
  "&:hover": { background: "rgba(255,255,255,0.04)" },
};

const SUMMARY_LINE_CLAMP = {
  display: "-webkit-box",
  WebkitLineClamp: 4,
  WebkitBoxOrient: "vertical",
  overflow: "hidden",
};

/* ---------- Connection Setup ---------- */

const neonInput = {
  "& .MuiOutlinedInput-root": {
    fontFamily: "'JetBrains Mono'", fontSize: 14, color: "#E0E0E0",
    "& fieldset": { borderColor: `${COLORS.cyan}44` },
    "&:hover fieldset": { borderColor: `${COLORS.cyan}88` },
    "&.Mui-focused fieldset": { borderColor: COLORS.cyan, boxShadow: `0 0 8px ${COLORS.cyan}33` },
  },
  "& .MuiInputLabel-root": { color: "grey.500", fontFamily: "'Rajdhani'", fontSize: 15 },
  "& .MuiInputLabel-root.Mui-focused": { color: COLORS.cyan },
};

function ConnectionSetup() {
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [showToken, setShowToken] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [loadingDemo, setLoadingDemo] = useState(false);
  const [config, setConfig] = useState<DashboardConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [useOverride, setUseOverride] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchDashboardConfig()
      .then((next) => {
        if (!cancelled) setConfig(next);
      })
      .catch(() => {
        if (!cancelled) setConfig(null);
      })
      .finally(() => {
        if (!cancelled) setConfigLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const configured = config?.configured === true;
  const showManualFields = !configLoading && (!configured || useOverride);
  const manualReady = url.trim().length > 0 && token.trim().length > 0;
  const canSubmit = !configLoading && (showManualFields ? manualReady : configured) && !connecting && !loadingDemo;

  const handleConnect = async () => {
    if (!canSubmit) return;
    setConnecting(true);
    try {
      window.localStorage.removeItem("mirrorlens_sample_replay");
      if (showManualFields) {
        await triggerInvestigation({ splunk_url: url.trim(), splunk_token: token.trim() });
      } else {
        await triggerInvestigation();
      }
    } catch {
      setConnecting(false);
    }
  };

  const handleDemo = async () => {
    if (loadingDemo || connecting) return;
    setLoadingDemo(true);
    try {
      window.localStorage.setItem("mirrorlens_sample_replay", "1");
      await loadDemoData();
    } catch {
      window.localStorage.removeItem("mirrorlens_sample_replay");
      setLoadingDemo(false);
    }
  };

  return (
    <Box sx={{ width: "100%", maxWidth: 560 }}>
      <GlassCard title="Connect to Splunk" accent="cyan">
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5, py: 3, px: 2 }}>
          <Typography variant="body1" sx={{ color: "grey.400", textAlign: "center", mb: 1, fontSize: 16 }}>
            {configured && !useOverride ? "Using configured Splunk MCP Server." : "Enter your Splunk MCP Server connection details."}<br />
            MirrorLens AI will autonomously investigate your security posture.
          </Typography>

          {configLoading && (
            <Typography variant="caption" sx={{ color: "grey.500", textAlign: "center", fontSize: 12 }}>
              Checking configured Splunk connection...
            </Typography>
          )}

          {configured && !useOverride && (
            <Box sx={{ border: `1px solid ${COLORS.green}55`, background: `${COLORS.green}08`, px: 2, py: 1.5 }}>
              <Typography sx={{ fontFamily: "'Orbitron'", fontWeight: 700, letterSpacing: 1, color: COLORS.green, fontSize: 12 }}>
                SPLUNK MCP CONFIGURED
              </Typography>
              <Typography sx={{ color: "grey.500", fontSize: 12, mt: 0.5 }}>
                URL and token are loaded from environment variables.
              </Typography>
            </Box>
          )}

          {showManualFields && (
            <>
              <TextField label="Splunk MCP URL" placeholder="https://your-splunk:8089/services/mcp" value={url} onChange={(e) => setUrl(e.target.value)} fullWidth size="small" sx={neonInput} />

              <TextField
                label="Bearer Token" placeholder="Splunk authentication token" type={showToken ? "text" : "password"}
                value={token} onChange={(e) => setToken(e.target.value)} fullWidth size="small" sx={neonInput}
                slotProps={{ input: { endAdornment: (
                  <InputAdornment position="end">
                    <IconButton size="small" onClick={() => setShowToken(!showToken)} sx={{ color: "grey.500", fontSize: 14 }}>
                      {showToken ? "◉" : "◎"}
                    </IconButton>
                  </InputAdornment>
                )}}}
              />
            </>
          )}

          <Button
            variant="outlined" size="large" disabled={!canSubmit} onClick={handleConnect}
            sx={{
              mt: 1, fontFamily: "'Orbitron'", fontWeight: 600, letterSpacing: 1.5, fontSize: 14,
              borderColor: canSubmit ? COLORS.cyan : "grey.700", color: canSubmit ? COLORS.cyan : "grey.600",
              "&:hover": { background: `${COLORS.cyan}15`, borderColor: COLORS.cyan },
              "&.Mui-disabled": { borderColor: "grey.800", color: "grey.600" },
            }}
          >
            {connecting ? "Connecting..." : configured && !useOverride ? "Start Investigation" : "Connect & Investigate"}
          </Button>

          {configured && (
            <Button
              variant="text" size="small" disabled={connecting || loadingDemo}
              onClick={() => setUseOverride((value) => !value)}
              sx={{ color: "grey.500", fontSize: 12, fontFamily: "'Rajdhani'", textTransform: "none", mt: -1 }}
            >
              {useOverride ? "Use configured Splunk connection" : "Use different connection"}
            </Button>
          )}

          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <Box sx={{ flex: 1, height: "1px", background: "rgba(255,255,255,0.08)" }} />
            <Typography variant="caption" sx={{ color: "grey.600", fontSize: 11, fontFamily: "'Orbitron'", letterSpacing: 1 }}>OR</Typography>
            <Box sx={{ flex: 1, height: "1px", background: "rgba(255,255,255,0.08)" }} />
          </Box>

          <Button
            variant="outlined" size="medium" disabled={loadingDemo || connecting} onClick={handleDemo}
            sx={{
              fontFamily: "'Orbitron'", fontWeight: 600, letterSpacing: 1.5, fontSize: 13,
              borderColor: `${COLORS.purple}88`, color: COLORS.purple,
              "&:hover": { background: `${COLORS.purple}15`, borderColor: COLORS.purple },
              "&.Mui-disabled": { borderColor: "grey.800", color: "grey.600" },
            }}
          >
            {loadingDemo ? "Loading..." : "⚡ Load Sample Investigation"}
          </Button>
          <Typography variant="caption" sx={{ color: "grey.600", fontSize: 11, textAlign: "center", mt: -1.5 }}>
            View a real investigation result without Splunk credentials
          </Typography>
        </Box>
      </GlassCard>
    </Box>
  );
}

/* ---------- Discovery & Evidence ---------- */

type DataHook = typeof useData extends () => infer D ? D : never;

function DiscoveryEvidencePanel({ discovery, evidence, currentStep, investigating, expanded, onSelectEvidence }: { discovery: DataHook["discovery"]; evidence: DataHook["evidence"]; currentStep: number; investigating: boolean; expanded?: boolean; onSelectEvidence: (d: Record<string, unknown>) => void }) {
  const serverInfo = discovery.find((d) => d.type === "server_info");
  const server = (serverInfo?.data as Array<Record<string, string>> | undefined)?.[0];
  const indexes = discovery.find((d) => d.type === "indexes");
  const hosts = discovery.find((d) => d.type === "hosts");
  const sourcetypes = discovery.find((d) => d.type === "sourcetypes");
  const savedSearches = discovery.find((d) => d.type === "saved_searches");
  const alerts = discovery.find((d) => d.type === "alerts");
  const fieldDiscoveries = discovery.filter((d) => d.type === "field_discovery");
  const idxData = (indexes?.data ?? []) as Array<Record<string, string | number>>;
  const hostList = (hosts?.data ?? []) as string[];
  const stList = (sourcetypes?.data ?? []) as string[];

  const queries = evidence.filter((e) => e.type === "query_result" || e.type === "query_error");
  const complete = evidence.find((e) => e.type === "collection_complete");

  const subtitle = investigating && !complete
    ? "AI autonomously investigating..."
    : complete
      ? `${complete.deduplicated} events collected`
      : `${idxData.length} indexes · ${hostList.length} hosts · ${stList.length} sourcetypes`;

  return (
    <GlassCard title="Discovery & Evidence" subtitle={subtitle} accent="cyan">
      {server && (
        <Box sx={{ mb: 1, pb: 0.75, borderBottom: "1px solid rgba(0,229,255,0.15)" }}>
          <Typography variant="caption" sx={{ color: COLORS.cyan, fontFamily: "'Orbitron'", fontSize: 12, mb: 0.5, display: "block" }}>
            SPLUNK SERVER
          </Typography>
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <InfoChip label="Server" value={server.serverName} />
            <InfoChip label="Version" value={server.version} />
            <InfoChip label="OS" value={server.os_name} />
            <InfoChip label="Cores" value={server.numberOfCores} />
            <InfoChip label="Memory" value={`${server.physicalMemoryMB}MB`} />
            <InfoChip label="License" value={server.licenseState} color={server.licenseState === "OK" ? "green" : "red"} />
            <InfoChip label="Health" value={server.health_info} color={server.health_info === "green" ? "green" : "red"} />
          </Box>
        </Box>
      )}

      <Typography variant="caption" sx={{ color: COLORS.cyan, fontFamily: "'Orbitron'", fontSize: 12, mb: 0.5, display: "block" }}>
        INDEXES ({idxData.length})
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 1 }}>
        {idxData.slice(0, 40).map((idx, i) => {
          const name = (idx.title ?? idx.name ?? `idx-${i}`) as string;
          const count = Number(idx.totalEventCount ?? 0);
          const hasData = count > 0;
          return (
            <Typography
              key={name} variant="caption"
              sx={{
                px: 0.6, py: 0.2, borderRadius: 0.5,
                border: `1px solid ${hasData ? COLORS.cyan : "rgba(255,255,255,0.15)"}44`,
                background: hasData ? `${COLORS.cyan}11` : "transparent",
                color: hasData ? COLORS.cyan : "grey.600",
                fontFamily: "'JetBrains Mono'", fontSize: 12,
              }}
            >
              {name}
              {count > 0 && ` ${count > 1000000 ? `${(count / 1000000).toFixed(1)}M` : count > 1000 ? `${(count / 1000).toFixed(0)}K` : count}`}
            </Typography>
          );
        })}
        {idxData.length > 40 && <Typography variant="caption" sx={{ color: "grey.600", fontSize: 11 }}>+{idxData.length - 40}</Typography>}
      </Box>

      {fieldDiscoveries.length > 0 && (
        <Box sx={{ mb: 1, pl: 0.5 }}>
          {fieldDiscoveries.map((fd, i) => (
            <Box key={fd.index ?? i} sx={{ mb: 0.75 }}>
              <Typography variant="caption" sx={{ color: COLORS.purple, fontFamily: "'JetBrains Mono'", fontSize: 12, fontWeight: 600 }}>
                {fd.index} — {fd.fields?.length ?? 0} fields · {fd.sample_count ?? 0} samples
              </Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.4, mt: 0.25 }}>
                {fd.fields?.slice(0, 15).map((f) => (
                  <Typography key={f.field} variant="caption" sx={{
                    px: 0.5, py: 0.1, borderRadius: 0.5,
                    border: `1px solid ${COLORS.purple}33`, color: COLORS.purple,
                    fontSize: 11, fontFamily: "'JetBrains Mono'",
                  }}>
                    {f.field} <span style={{ color: "#888" }}>({f.distinct_count})</span>
                  </Typography>
                ))}
                {(fd.fields?.length ?? 0) > 15 && <Typography variant="caption" sx={{ color: "grey.600", fontSize: 11 }}>+{(fd.fields?.length ?? 0) - 15}</Typography>}
              </Box>
            </Box>
          ))}
        </Box>
      )}

      <Box sx={{ display: "flex", gap: 3, mb: 1 }}>
        {hostList.length > 0 && (
          <Box>
            <Typography variant="caption" sx={{ color: COLORS.green, fontFamily: "'Orbitron'", fontSize: 12, mb: 0.25, display: "block" }}>
              HOSTS ({hostList.length})
            </Typography>
            <Typography variant="caption" sx={{ color: "grey.300", fontSize: 13 }}>
              {hostList.join(", ")}
            </Typography>
          </Box>
        )}
        {stList.length > 0 && (
          <Box>
            <Typography variant="caption" sx={{ color: COLORS.amber, fontFamily: "'Orbitron'", fontSize: 12, mb: 0.25, display: "block" }}>
              SOURCETYPES ({stList.length})
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {stList.map((st) => (
                <Typography key={st} variant="caption" sx={{ px: 0.5, py: 0.1, borderRadius: 0.5, border: `1px solid ${COLORS.amber}33`, color: COLORS.amber, fontSize: 12 }}>
                  {st}
                </Typography>
              ))}
            </Box>
          </Box>
        )}
      </Box>

      {(savedSearches || alerts) && (
        <Box sx={{ display: "flex", gap: 2, mb: 1 }}>
          {savedSearches && <Typography variant="caption" sx={{ color: "grey.400", fontSize: 13 }}>Saved Searches: {savedSearches.count}</Typography>}
          {alerts && <Typography variant="caption" sx={{ color: "grey.400", fontSize: 13 }}>Alerts: {alerts.count}</Typography>}
        </Box>
      )}

      {currentStep >= 3 && queries.length > 0 && (
        <Box sx={{ borderTop: "1px solid rgba(255,255,255,0.08)", pt: 0.75, display: "flex", flexDirection: "column", minHeight: 0, flex: expanded ? 1 : "none" }}>
          <Typography variant="caption" sx={{ color: COLORS.amber, fontFamily: "'Orbitron'", fontSize: 12, mb: 0.5, display: "block", flexShrink: 0 }}>
            EVIDENCE QUERIES ({queries.length})
          </Typography>
          <Box sx={{ overflow: "auto", flex: 1, minHeight: 0 }}>
            {(expanded ? queries : queries.slice(-8)).map((q, i) => (
              <Box key={i} sx={{ py: 0.3, borderBottom: "1px solid rgba(255,255,255,0.04)", ...clickableRow }} onClick={() => onSelectEvidence(q as unknown as Record<string, unknown>)}>
                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="caption" sx={{ color: "grey.300", fontSize: 13, fontWeight: 500 }}>
                    {q.name}
                  </Typography>
                  <Typography variant="caption" sx={{ color: q.error ? COLORS.red : q.row_count === 0 ? "grey.600" : COLORS.green, fontSize: 13, fontFamily: "'JetBrains Mono'", flexShrink: 0 }}>
                    {q.error ? "ERROR" : `${q.row_count} rows`}
                  </Typography>
                </Box>
                {q.spl && (
                  <Typography variant="caption" sx={{ color: "grey.600", fontSize: 11, fontFamily: "'JetBrains Mono'", display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {q.spl}
                  </Typography>
                )}
              </Box>
            ))}
          </Box>
        </Box>
      )}
    </GlassCard>
  );
}

function InfoChip({ label, value, color }: { label: string; value: string; color?: string }) {
  const c = color === "green" ? COLORS.green : color === "red" ? COLORS.red : "grey.300";
  return (
    <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
      <Typography variant="caption" sx={{ color: "grey.500", fontSize: 12 }}>{label}:</Typography>
      <Typography variant="caption" sx={{ color: c, fontSize: 13, fontWeight: 600 }}>{value}</Typography>
    </Box>
  );
}

/* ---------- Timeline ---------- */

function TimelineSection({ analysis, onSelect }: { analysis: DataHook["analysis"]; onSelect: (d: Record<string, unknown>) => void }) {
  const tl = analysis.find((a) => a.type === "timeline");
  const entries = (tl?.data ?? []) as Array<Record<string, string>>;
  const summary = tl?.summary ?? "";

  return (
    <GlassCard title="Attack Findings" subtitle={`${entries.length} findings`} accent="red">
      {summary && <Typography variant="body2" sx={{ mb: 0.75, color: "grey.300", lineHeight: 1.5, fontSize: 14, ...SUMMARY_LINE_CLAMP }}>{summary}</Typography>}
      <AnimatePresence>
        {entries.map((step, i) => (
          <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }}>
            <Box sx={{ py: 0.5, borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", gap: 1, ...clickableRow }} onClick={() => onSelect(step)}>
              <Typography variant="caption" sx={{ color: COLORS.red, fontWeight: 700, minWidth: 60, fontSize: 13 }}>{step.technique_id}</Typography>
              <Typography variant="caption" sx={{ color: COLORS.amber, minWidth: 80, fontSize: 13 }}>{step.tactic}</Typography>
              <Typography variant="caption" sx={{ color: "grey.300", flex: 1, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{step.description}</Typography>
            </Box>
          </motion.div>
        ))}
      </AnimatePresence>
    </GlassCard>
  );
}

/* ---------- Gaps ---------- */

function GapsSection({ analysis, onSelect }: { analysis: DataHook["analysis"]; onSelect: (d: Record<string, unknown>) => void }) {
  const gapEvt = analysis.find((a) => a.type === "gaps");
  const gaps = (gapEvt?.data ?? []) as Array<Record<string, string>>;
  const coverage = gapEvt?.coverage ?? "";

  return (
    <GlassCard title="Detection Gaps" subtitle={`${gaps.length} gaps`} accent="red">
      {coverage && <Typography variant="body2" sx={{ mb: 0.75, color: "grey.400", fontSize: 14 }}>{coverage}</Typography>}
      {gaps.map((gap, i) => {
        const sev = gap.severity ?? "MEDIUM";
        const sc = SEVERITY_COLOR[sev] ?? "amber";
        return (
          <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.05 }}>
            <Box sx={{ py: 0.5, borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", gap: 1, alignItems: "center", ...clickableRow }} onClick={() => onSelect(gap)}>
              <Typography variant="caption" sx={{ px: 0.5, borderRadius: 0.5, background: `${COLORS[sc]}22`, color: COLORS[sc], fontWeight: 700, fontSize: 12, minWidth: 52, textAlign: "center" }}>{sev}</Typography>
              <Typography variant="caption" sx={{ color: COLORS.red, fontWeight: 600, fontSize: 13 }}>{gap.technique_id}</Typography>
              <Typography variant="caption" sx={{ color: "grey.300", flex: 1, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{gap.gap_description}</Typography>
            </Box>
          </motion.div>
        );
      })}
    </GlassCard>
  );
}

/* ---------- Detection Rules ---------- */

type DetectionRuleRow = {
  key: string;
  generated?: Record<string, string>;
  validation?: DataHook["analysis"][number];
};

function DetectionRulesSection({ analysis, validations, onSelect }: {
  analysis: DataHook["analysis"];
  validations: DataHook["analysis"];
  onSelect: (type: "usecase" | "validation", d: Record<string, unknown>) => void;
}) {
  const ucEvt = analysis.find((a) => a.type === "use_cases");
  const useCases = (ucEvt?.data ?? []) as Array<Record<string, string>>;
  const testedRules = dedupeRuleValidations(validations.filter((v) => v.type === "rule_validation"));
  const usedValidationIndexes = new Set<number>();
  const unmatchedGeneratedRows: DetectionRuleRow[] = [];

  const rows: DetectionRuleRow[] = [];
  useCases.forEach((uc, i) => {
    const matchIndex = testedRules.findIndex((rule, validationIndex) => {
      if (usedValidationIndexes.has(validationIndex)) return false;
      const sameName = normalizeRuleName(rule.rule_name) === normalizeRuleName(uc.name);
      const sameSpl = rule.spl && uc.spl_query && rule.spl.trim() === uc.spl_query.trim();
      return sameName || sameSpl;
    });
    const row = {
      key: `generated-${i}-${uc.name ?? "rule"}`,
      generated: uc,
      validation: matchIndex >= 0 ? testedRules[matchIndex] : undefined,
    };
    if (matchIndex >= 0) {
      usedValidationIndexes.add(matchIndex);
      rows.push(row);
    } else {
      unmatchedGeneratedRows.push(row);
    }
  });

  testedRules.forEach((rule, i) => {
    if (!usedValidationIndexes.has(i)) {
      rows.push({ key: `validated-${i}-${rule.rule_name ?? "rule"}`, validation: rule });
    }
  });

  const pendingSlots = Math.max(0, useCases.length - testedRules.length);
  rows.push(...unmatchedGeneratedRows.slice(0, pendingSlots));

  const sortedRows = sortDetectionRuleRows(rows);

  return (
    <GlassCard title="Detection Rules" subtitle={`${useCases.length} generated · ${testedRules.length} tested`} accent="green">
      {sortedRows.map((row, i) => {
        const generated = row.generated;
        const validation = row.validation;
        const priority = generated?.priority ?? "P3";
        const sc = SEVERITY_COLOR[priority] ?? "green";
        const name = generated?.name ?? validation?.rule_name ?? "Unnamed Rule";
        const technique = generated?.mitre_technique ?? "";
        const matchCount = validation?.match_count;
        const fired = (matchCount ?? 0) > 0;
        const detailType = validation ? "validation" : "usecase";
        const detailData = (validation ?? generated ?? {}) as Record<string, unknown>;

        return (
          <motion.div key={row.key} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
            <Box sx={{ py: 0.55, borderBottom: "1px solid rgba(255,255,255,0.06)", ...clickableRow }} onClick={() => onSelect(detailType, detailData)}>
              <Box sx={{ display: "flex", gap: 0.75, alignItems: "center", justifyContent: "space-between" }}>
                <Box sx={{ display: "flex", gap: 0.75, alignItems: "center", minWidth: 0 }}>
                  <Typography variant="caption" sx={{ px: 0.5, borderRadius: 0.5, background: `${COLORS[sc]}22`, color: COLORS[sc], fontWeight: 700, fontSize: 12, flexShrink: 0 }}>{priority}</Typography>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: "grey.200", fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{name}</Typography>
                  {technique && <Typography variant="caption" sx={{ color: COLORS.red, fontSize: 12, flexShrink: 0 }}>{technique}</Typography>}
                </Box>
                <Typography variant="caption" sx={{
                  px: 0.5, py: 0.15, borderRadius: 0.5,
                  background: validation ? fired ? `${COLORS.green}22` : `${COLORS.amber}22` : "rgba(255,255,255,0.06)",
                  color: validation ? fired ? COLORS.green : COLORS.amber : "grey.500",
                  fontSize: 11, fontWeight: 700, flexShrink: 0,
                }}>
                  {validation ? fired ? `${matchCount} MATCHES` : "0 MATCHES" : "PENDING"}
                </Typography>
              </Box>
            </Box>
          </motion.div>
        );
      })}
    </GlassCard>
  );
}

function normalizeRuleName(name?: string) {
  return (name ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function dedupeRuleValidations(rules: DataHook["analysis"]) {
  const byKey = new Map<string, DataHook["analysis"][number]>();
  for (const rule of rules) {
    const key = normalizeRuleName(rule.rule_name) || (rule.spl ?? "").trim();
    if (!key) continue;
    const existing = byKey.get(key);
    if (!existing || (rule.match_count ?? 0) > (existing.match_count ?? 0)) {
      byKey.set(key, rule);
    }
  }
  return [...byKey.values()];
}

function sortDetectionRuleRows(rows: DetectionRuleRow[]) {
  const priorityRank: Record<string, number> = { P1: 1, CRITICAL: 1, HIGH: 1, P2: 2, MEDIUM: 2, P3: 3, LOW: 3 };
  return [...rows].sort((a, b) => {
    const aMatches = a.validation?.match_count ?? 0;
    const bMatches = b.validation?.match_count ?? 0;
    if ((bMatches > 0) !== (aMatches > 0)) return bMatches > 0 ? 1 : -1;
    if (bMatches !== aMatches) return bMatches - aMatches;

    const aPriority = priorityRank[a.generated?.priority ?? "P3"] ?? 9;
    const bPriority = priorityRank[b.generated?.priority ?? "P3"] ?? 9;
    if (aPriority !== bPriority) return aPriority - bPriority;

    const aName = a.generated?.name ?? a.validation?.rule_name ?? "";
    const bName = b.generated?.name ?? b.validation?.rule_name ?? "";
    return aName.localeCompare(bName);
  });
}

/* ---------- Rule Match Alert Overlay ---------- */

function RuleMatchAlert({ analysis }: { analysis: DataHook["analysis"] }) {
  const seenRef = useRef<Set<string>>(new Set());
  const [alertRule, setAlertRule] = useState<{
    rule_name: string; match_count: number; spl?: string; sample_matches?: unknown[];
  } | null>(null);
  const dismissTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    const fired = analysis.filter(
      (a) => a.type === "rule_validation" && (a.match_count ?? 0) > 0
    );
    for (const rule of fired) {
      const key = `${rule.rule_name}::${rule.match_count}`;
      if (!seenRef.current.has(key)) {
        seenRef.current.add(key);
        setAlertRule({
          rule_name: rule.rule_name ?? "Unknown Rule",
          match_count: rule.match_count ?? 0,
          spl: rule.spl,
          sample_matches: rule.sample_matches,
        });
        clearTimeout(dismissTimerRef.current);
        dismissTimerRef.current = setTimeout(() => setAlertRule(null), 10000);
        break;
      }
    }
  }, [analysis]);

  useEffect(() => {
    if (!alertRule) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setAlertRule(null);
        clearTimeout(dismissTimerRef.current);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [alertRule]);

  useEffect(() => () => clearTimeout(dismissTimerRef.current), []);

  return (
    <AnimatePresence>
      {alertRule && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4 }}
          style={{
            position: "fixed", inset: 0, zIndex: 1000,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: "radial-gradient(ellipse at center, rgba(255,0,0,0.15) 0%, rgba(0,0,0,0.85) 70%)",
            backdropFilter: "blur(12px)",
          }}
          onClick={() => { setAlertRule(null); clearTimeout(dismissTimerRef.current); }}
        >
          <motion.div
            initial={{ scale: 0.96, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 1.05, opacity: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            onClick={(e) => e.stopPropagation()}
            style={{ width: "90%", maxWidth: 600 }}
          >
            <Box sx={{
              p: 4, borderRadius: 2,
              border: `2px solid ${COLORS.red}`,
              background: "rgba(20,0,0,0.95)",
              boxShadow: `0 0 60px ${COLORS.red}44, inset 0 0 30px ${COLORS.red}11`,
            }}>
              <motion.div animate={{ opacity: [0.7, 1, 0.7] }} transition={{ duration: 1.5, repeat: Infinity }}>
                <Typography sx={{
                  fontFamily: "'Orbitron'", fontWeight: 800, fontSize: 22, letterSpacing: 3,
                  color: COLORS.red, textAlign: "center", mb: 1,
                  textShadow: `0 0 20px ${COLORS.red}, 0 0 40px ${COLORS.red}88`,
                }}>
                  DETECTION RULE FIRED
                </Typography>
              </motion.div>

              <Typography sx={{
                fontFamily: "'Rajdhani'", fontWeight: 700, fontSize: 20,
                color: "grey.100", textAlign: "center", mb: 2,
              }}>
                {alertRule.rule_name}
              </Typography>

              <Box sx={{ display: "flex", justifyContent: "center", mb: 2 }}>
                <Box sx={{
                  px: 2, py: 0.5, borderRadius: 1,
                  background: `${COLORS.red}33`, border: `1px solid ${COLORS.red}`,
                }}>
                  <Typography sx={{
                    fontFamily: "'JetBrains Mono'", fontWeight: 700, fontSize: 18, color: COLORS.red,
                  }}>
                    {alertRule.match_count} MATCHES
                  </Typography>
                </Box>
              </Box>

              {alertRule.spl && (
                <Box sx={{ mb: 2, px: 2, py: 1, borderRadius: 1, background: "rgba(0,0,0,0.5)", border: `1px solid ${COLORS.cyan}33` }}>
                  <Typography sx={{
                    fontFamily: "'JetBrains Mono'", fontSize: 12, color: COLORS.cyan,
                    wordBreak: "break-all", lineHeight: 1.5,
                  }}>
                    {alertRule.spl}
                  </Typography>
                </Box>
              )}

              {alertRule.sample_matches && alertRule.sample_matches.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" sx={{ color: COLORS.amber, fontFamily: "'Orbitron'", fontSize: 11, mb: 0.5, display: "block" }}>
                    SAMPLE MATCHES
                  </Typography>
                  {(alertRule.sample_matches as Array<Record<string, unknown>>).slice(0, 3).map((m, i) => (
                    <Box key={i} sx={{ px: 1.5, py: 0.5, mb: 0.5, borderRadius: 0.5, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
                      <Typography variant="caption" sx={{ color: "grey.400", fontSize: 11, fontFamily: "'JetBrains Mono'", wordBreak: "break-all" }}>
                        {JSON.stringify(m).slice(0, 200)}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              )}

              <Box sx={{ display: "flex", justifyContent: "center" }}>
                <Button
                  variant="outlined"
                  onClick={() => { setAlertRule(null); clearTimeout(dismissTimerRef.current); }}
                  sx={{
                    fontFamily: "'Orbitron'", fontWeight: 700, letterSpacing: 2, fontSize: 13,
                    borderColor: COLORS.red, color: COLORS.red,
                    "&:hover": { background: `${COLORS.red}22`, borderColor: COLORS.red },
                  }}
                >
                  ACKNOWLEDGE
                </Button>
              </Box>
            </Box>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* ---------- Recommendations ---------- */

function RecommendSection({ recommendations, onSelect }: { recommendations: DataHook["recommendations"]; onSelect: (d: Record<string, unknown>) => void }) {
  const latest = recommendations[recommendations.length - 1];
  const recs = (latest?.data ?? []) as Array<Record<string, string>>;
  const summary = latest?.executive_summary ?? "";
  const visibleRecommendations = recs.slice(0, 3);

  return (
    <GlassCard title="Response Playbook" subtitle={summary ? "Complete" : `${recs.length} actions`} accent="amber">
      {summary && (
        <Box sx={{ mb: 1, pb: 0.75, borderBottom: `1px solid ${COLORS.green}33` }}>
          <Typography variant="caption" sx={{ color: COLORS.green, fontWeight: 700, fontFamily: "'Orbitron'", fontSize: 12, mb: 0.25, display: "block" }}>EXECUTIVE SUMMARY</Typography>
          <Typography variant="body2" sx={{ color: "grey.200", lineHeight: 1.6, fontSize: 14, ...SUMMARY_LINE_CLAMP }}>{summary}</Typography>
        </Box>
      )}
      {visibleRecommendations.map((rec, i) => (
        <motion.div key={i} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}>
          <Box sx={{ py: 0.5, borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", gap: 1, ...clickableRow }} onClick={() => onSelect(rec)}>
            <Typography variant="caption" sx={{ fontFamily: "'Orbitron'", color: COLORS.cyan, fontWeight: 700, minWidth: 20, fontSize: 13 }}>{i + 1}</Typography>
            <Box sx={{ flex: 1 }}>
              <Typography variant="caption" sx={{ fontWeight: 600, color: "grey.200", fontSize: 13 }}>
                {rec.category && `[${rec.category.toUpperCase()}] `}{rec.action?.slice(0, 160)}
              </Typography>
            </Box>
            {rec.risk_level && (
              <Typography variant="caption" sx={{
                px: 0.5, borderRadius: 0.5,
                background: `${COLORS[rec.risk_level === "HIGH" ? "red" : rec.risk_level === "MEDIUM" ? "amber" : "green"]}22`,
                color: COLORS[rec.risk_level === "HIGH" ? "red" : rec.risk_level === "MEDIUM" ? "amber" : "green"],
                fontSize: 11, alignSelf: "center",
              }}>{rec.risk_level}</Typography>
            )}
          </Box>
        </motion.div>
      ))}
      {recs.length > visibleRecommendations.length && (
        <Typography variant="caption" sx={{ color: "grey.500", fontFamily: "'Orbitron'", fontSize: 11, letterSpacing: 1, display: "block", mt: 0.75 }}>
          +{recs.length - visibleRecommendations.length} MORE ACTIONS
        </Typography>
      )}
    </GlassCard>
  );
}
