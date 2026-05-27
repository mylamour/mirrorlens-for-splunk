import { Box, Typography } from "@mui/material";
import { motion } from "framer-motion";
import { useData } from "../data/context";
import { COLORS } from "../theme";
import MetricCard from "./shared/MetricCard";
import PhaseProgress from "./PhaseProgress";

export default function Header() {
  const { discovery, evidence, analysis, status, watchEvents } = useData();

  const indexCount = discovery.find((d) => d.type === "indexes")?.count ?? 0;
  const hostCount = discovery.find((d) => d.type === "hosts")?.count ?? 0;
  const evtCount = evidence.find((e) => e.type === "collection_complete")?.deduplicated ?? 0;
  const gapCount = analysis.find((a) => a.type === "gaps")?.data?.length ?? 0;

  return (
    <Box
      sx={{
        gridArea: "header",
        display: "flex",
        alignItems: "center",
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

      <PhaseProgress />

      <Box sx={{ ml: "auto", display: "flex", gap: 2 }}>
        <MetricCard label="Indexes" value={indexCount} accent="cyan" />
        <MetricCard label="Hosts" value={hostCount} accent="green" />
        <MetricCard label="Events" value={evtCount} accent="amber" />
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
