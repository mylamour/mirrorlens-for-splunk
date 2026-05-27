import { Box, Typography } from "@mui/material";
import { motion } from "framer-motion";
import { useData } from "../data/context";
import { COLORS } from "../theme";

const PHASES = ["Discover", "Explore", "Investigate", "Analyze", "Recommend"];

export default function PhaseProgress() {
  const { phases, aiCalls, watchEvents } = useData();

  const latest = new Map<string, string>();
  for (const p of phases) latest.set(p.name, p.status);

  const isReact = latest.has("ReAct Loop");

  const latestWatch = watchEvents.length > 0 ? watchEvents[watchEvents.length - 1] : null;
  const isWatching = latestWatch && latestWatch.event !== "stopped" && latestWatch.event !== "error";
  const isChecking = latestWatch?.event === "checking";
  const changesDetected = latestWatch?.event === "changes_detected";

  if (isReact) {
    const reactStatus = latest.get("ReAct Loop") ?? "running";
    const isDone = reactStatus === "done";
    const iteration = [...aiCalls].reverse().find((c) => c.iteration)?.iteration ?? 0;

    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        <motion.div
          animate={isDone ? {} : { opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 1.6, repeat: Infinity }}
        >
          <Box sx={{
            px: 2, py: 0.5, borderRadius: 1,
            border: `1px solid ${isDone ? COLORS.green : COLORS.purple}55`,
            background: isDone ? `${COLORS.green}15` : `${COLORS.purple}15`,
            boxShadow: isDone ? "none" : `0 0 12px ${COLORS.purple}33`,
          }}>
            <Typography variant="caption" sx={{
              fontFamily: "'Orbitron'", fontSize: 11, fontWeight: 700,
              letterSpacing: 1.5, color: isDone ? COLORS.green : COLORS.purple,
            }}>
              {isDone ? "✓ " : ""}ReAct LOOP
            </Typography>
          </Box>
        </motion.div>
        {iteration > 0 && (
          <Typography variant="caption" sx={{ color: COLORS.cyan, fontFamily: "'JetBrains Mono'", fontSize: 11, fontWeight: 600 }}>
            Iteration {iteration}
          </Typography>
        )}
        {!isDone && (
          <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
            {["REASON", "ACT", "OBSERVE"].map((step) => (
              <Typography key={step} variant="caption" sx={{
                px: 0.75, py: 0.15, borderRadius: 0.5,
                border: `1px solid ${COLORS.cyan}33`,
                color: COLORS.cyan, fontSize: 9, fontFamily: "'Orbitron'", letterSpacing: 0.5,
              }}>
                {step}
              </Typography>
            ))}
          </Box>
        )}
        {isDone && isWatching && (
          <motion.div
            animate={changesDetected ? { scale: [1, 1.1, 1] } : isChecking ? { opacity: [0.5, 1, 0.5] } : { opacity: [0.6, 1, 0.6] }}
            transition={{ duration: changesDetected ? 0.6 : 2, repeat: Infinity }}
          >
            <Box sx={{
              px: 1.5, py: 0.35, borderRadius: 1,
              border: `1px solid ${changesDetected ? COLORS.red : COLORS.amber}55`,
              background: changesDetected ? `${COLORS.red}15` : `${COLORS.amber}15`,
              boxShadow: `0 0 8px ${changesDetected ? COLORS.red : COLORS.amber}22`,
            }}>
              <Typography variant="caption" sx={{
                fontFamily: "'Orbitron'", fontSize: 10, fontWeight: 700,
                letterSpacing: 1.5,
                color: changesDetected ? COLORS.red : COLORS.amber,
              }}>
                {changesDetected ? "CHANGES DETECTED" : isChecking ? "CHECKING" : "WATCHING"}
              </Typography>
            </Box>
          </motion.div>
        )}
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      {PHASES.map((name, i) => {
        const status = latest.get(name) ?? "pending";
        const isDone = status === "done";
        const isRunning = status === "running";
        const color = isDone ? COLORS.green : isRunning ? COLORS.cyan : "grey.600";

        return (
          <Box key={name} sx={{ display: "flex", alignItems: "center" }}>
            <motion.div
              animate={
                isRunning
                  ? { opacity: [0.5, 1, 0.5], scale: [0.95, 1.05, 0.95] }
                  : { opacity: 1, scale: 1 }
              }
              transition={isRunning ? { duration: 1.4, repeat: Infinity } : {}}
            >
              <Box
                sx={{
                  px: 1.5,
                  py: 0.5,
                  borderRadius: 1,
                  border: `1px solid ${typeof color === "string" && color.startsWith("#") ? color + "55" : "rgba(150,150,150,0.3)"}`,
                  background: isDone
                    ? `${COLORS.green}15`
                    : isRunning
                      ? `${COLORS.cyan}15`
                      : "transparent",
                  boxShadow: isRunning ? `0 0 12px ${COLORS.cyan}33` : "none",
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    fontFamily: "'Orbitron', sans-serif",
                    fontSize: 11,
                    fontWeight: 600,
                    letterSpacing: 1,
                    color,
                    textShadow: isDone || isRunning ? `0 0 6px ${typeof color === "string" ? color : ""}55` : "none",
                  }}
                >
                  {isDone ? "✓ " : `${i + 1}. `}
                  {name.toUpperCase()}
                </Typography>
              </Box>
            </motion.div>
            {i < PHASES.length - 1 && (
              <Box
                sx={{
                  width: 24,
                  height: 1,
                  mx: 0.5,
                  background: isDone ? COLORS.green : "rgba(255,255,255,0.15)",
                }}
              />
            )}
          </Box>
        );
      })}
    </Box>
  );
}
