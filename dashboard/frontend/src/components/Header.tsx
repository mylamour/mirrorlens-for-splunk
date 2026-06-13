import { useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import { motion } from "framer-motion";
import { useData } from "../data/context";
import { resetDemoData } from "../data/api";
import { COLORS } from "../theme";
import MetricCard from "./shared/MetricCard";

export default function Header({ showTrace = false, onOpenTrace }: { showTrace?: boolean; onOpenTrace?: () => void }) {
  const { discovery, evidence, analysis, status, statusEvents, watchEvents, investigationRunning } = useData();
  const [resetting, setResetting] = useState(false);

  const indexCount = discovery.find((d) => d.type === "indexes")?.count ?? 0;
  const hostCount = discovery.find((d) => d.type === "hosts")?.count ?? 0;
  const matchCount = analysis
    .filter((a) => a.type === "rule_validation")
    .reduce((sum, rule) => sum + (rule.match_count ?? 0), 0);
  const gapCount = analysis.find((a) => a.type === "gaps")?.data?.length ?? 0;
  const hasDashboardState =
    discovery.length > 0 ||
    evidence.length > 0 ||
    analysis.length > 0 ||
    statusEvents.length > 0;
  const sampleReplay = window.localStorage.getItem("mirrorlens_sample_replay") === "1";

  const handleReset = async () => {
    if (resetting || (investigationRunning && !sampleReplay)) return;
    setResetting(true);
    try {
      await resetDemoData();
      window.localStorage.removeItem("mirrorlens_sample_replay");
      window.location.reload();
    } catch {
      setResetting(false);
    }
  };

  return (
    <Box
      sx={{
        gridArea: "header",
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 3,
        px: 2,
        py: 1,
        borderBottom: `1px solid ${COLORS.cyan}22`,
        background: `linear-gradient(90deg, ${COLORS.cyan}08 0%, transparent 50%)`,
      }}
    >
      <Typography
        variant="h5"
        sx={{
          fontFamily: "'Orbitron', sans-serif",
          fontWeight: 700,
          color: COLORS.cyan,
          textShadow: `0 0 12px ${COLORS.cyan}66`,
          whiteSpace: "nowrap",
          letterSpacing: 2,
        }}
      >
        MIRRORLENS
      </Typography>

      <Box sx={{ ml: "auto", display: { xs: "none", md: "flex" }, gap: 2 }}>
        <MetricCard label="Indexes" value={indexCount} accent="cyan" />
        <MetricCard label="Hosts" value={hostCount} accent="green" />
        <MetricCard label="Matches" value={matchCount} accent="amber" />
        <MetricCard label="Gaps" value={gapCount} accent="red" />
      </Box>

      {(() => {
        const latestWatch = watchEvents.length > 0 ? watchEvents[watchEvents.length - 1] : null;
        const watching = latestWatch && latestWatch.event !== "stopped" && latestWatch.event !== "error";
        return watching ? (
          <motion.div animate={{ opacity: [0.6, 1, 0.6] }} transition={{ duration: 2.5, repeat: Infinity }}>
            <Box sx={{
              px: 1, py: 0.25, borderRadius: 1,
              border: `1px solid ${COLORS.amber}44`,
              background: `${COLORS.amber}15`,
            }}>
              <Typography variant="caption" sx={{ color: COLORS.amber, fontFamily: "'Orbitron'", fontSize: 10, fontWeight: 600, letterSpacing: 1 }}>
                WATCHING
              </Typography>
            </Box>
          </motion.div>
        ) : null;
      })()}

      {showTrace && (
        <Button
          variant="outlined"
          size="small"
          onClick={onOpenTrace}
          sx={{
            borderColor: `${COLORS.purple}55`,
            color: COLORS.purple,
            fontFamily: "'Orbitron'",
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: 1,
            minWidth: 128,
            px: 1,
            py: 0.25,
            "&:hover": { background: `${COLORS.purple}12`, borderColor: COLORS.purple },
          }}
        >
          AGENT TRACE / MCP PROOF
        </Button>
      )}

      {hasDashboardState && (!investigationRunning || sampleReplay) && (
        <Button
          variant="outlined"
          size="small"
          disabled={resetting}
          onClick={handleReset}
          sx={{
            borderColor: `${COLORS.cyan}55`,
            color: COLORS.cyan,
            fontFamily: "'Orbitron'",
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: 1,
            minWidth: 96,
            px: 1,
            py: 0.25,
            "&:hover": { background: `${COLORS.cyan}12`, borderColor: COLORS.cyan },
          }}
        >
          {resetting ? "RESETTING" : "RESET VIEW"}
        </Button>
      )}

      <Box
        sx={{
          px: 1,
          py: 0.25,
          borderRadius: 1,
          border: `1px solid ${status === "live" ? COLORS.green : "grey"}44`,
          background: status === "live" ? `${COLORS.green}15` : "transparent",
        }}
      >
        <Typography variant="caption" sx={{ color: status === "live" ? COLORS.green : "grey.500" }}>
          {status === "live" ? "● LIVE" : status.toUpperCase()}
        </Typography>
      </Box>
    </Box>
  );
}
