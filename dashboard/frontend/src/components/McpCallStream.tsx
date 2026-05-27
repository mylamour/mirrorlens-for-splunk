import { Box, Typography } from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";
import GlassCard from "./shared/GlassCard";
import { useData } from "../data/context";
import { COLORS } from "../theme";

export default function McpCallStream() {
  const { mcpCalls } = useData();
  const items = [...mcpCalls].reverse().slice(0, 10);
  const running = items.filter((c) => c.status === "running").length;
  const done = mcpCalls.filter((c) => c.status === "done").length;
  const errors = mcpCalls.filter((c) => c.status === "error").length;

  return (
    <GlassCard
      title="MCP Calls"
      subtitle={`${done} done${errors ? ` / ${errors} err` : ""}${running ? ` / ${running} active` : ""}`}
      accent="cyan"
      noPadding
    >
      <Box sx={{ px: 1, py: 0.5, overflow: "auto", height: "100%" }}>
        <AnimatePresence initial={false}>
          {items.map((call, i) => {
            const isRunning = call.status === "running";
            const isError = call.status === "error";
            const color = isError ? COLORS.red : isRunning ? COLORS.amber : COLORS.cyan;

            return (
              <motion.div
                key={`${call.tool}-${mcpCalls.length - i}`}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Box
                  sx={{
                    py: 0.4,
                    px: 0.75,
                    mb: 0.25,
                    borderLeft: `2px solid ${color}`,
                    borderRadius: 0.5,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{ fontFamily: "'JetBrains Mono'", fontWeight: 600, color, fontSize: 10 }}
                  >
                    {call.tool}
                  </Typography>
                  <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
                    {call.row_count !== undefined && (
                      <Typography variant="caption" sx={{ color: COLORS.green, fontSize: 9 }}>
                        {call.row_count}r
                      </Typography>
                    )}
                    <Typography
                      variant="caption"
                      sx={{
                        fontSize: 8,
                        px: 0.5,
                        borderRadius: 0.5,
                        background: `${color}22`,
                        color,
                        fontWeight: 600,
                      }}
                    >
                      {isRunning ? "RUN" : isError ? "ERR" : "OK"}
                    </Typography>
                  </Box>
                </Box>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </Box>
    </GlassCard>
  );
}
