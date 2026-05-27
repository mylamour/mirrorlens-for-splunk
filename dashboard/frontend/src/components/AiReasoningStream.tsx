import { Box, Typography } from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";
import GlassCard from "./shared/GlassCard";
import { useData } from "../data/context";
import { COLORS } from "../theme";

const TYPE_LABELS: Record<string, string> = {
  data_discovery: "Data Discovery",
  evidence_analysis: "Evidence Analysis",
  gap_analysis: "Detection Gap Analysis",
  usecase_generation: "Use Case Generation",
  response_recommendation: "Response Recommendations",
};

export default function AiReasoningStream() {
  const { aiCalls } = useData();
  const items = [...aiCalls].reverse().slice(0, 20);

  return (
    <GlassCard title="AI Reasoning" subtitle="Claude API" accent="purple" noPadding>
      <Box sx={{ px: 1, py: 0.5, overflow: "auto", height: "100%" }}>
        <AnimatePresence initial={false}>
          {items.map((call, i) => {
            const isRunning = call.status === "running";
            const label = TYPE_LABELS[call.type] ?? call.type;

            return (
              <motion.div
                key={`${call.type}-${call.status}-${aiCalls.length - i}`}
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5 }}
              >
                <Box
                  sx={{
                    py: 0.75,
                    px: 1,
                    mb: 0.5,
                    borderLeft: `2px solid ${isRunning ? COLORS.amber : COLORS.purple}`,
                    background: isRunning ? `${COLORS.amber}08` : "transparent",
                    borderRadius: 0.5,
                  }}
                >
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Typography
                      variant="caption"
                      sx={{
                        fontFamily: "'Orbitron'",
                        fontWeight: 600,
                        fontSize: 11,
                        color: isRunning ? COLORS.amber : COLORS.purple,
                      }}
                    >
                      {label}
                    </Typography>
                    {isRunning && (
                      <motion.div
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1.2, repeat: Infinity }}
                      >
                        <Typography variant="caption" sx={{ color: COLORS.amber, fontSize: 10 }}>
                          THINKING...
                        </Typography>
                      </motion.div>
                    )}
                  </Box>

                  {call.model && (
                    <Typography variant="caption" sx={{ color: "grey.500", fontSize: 10 }}>
                      Model: {call.model}
                    </Typography>
                  )}

                  {call.reasoning && (
                    <Typography variant="caption" sx={{ color: "grey.300", fontSize: 11, display: "block", mt: 0.5 }}>
                      {call.reasoning}
                    </Typography>
                  )}

                  {call.selected_indexes && (
                    <Box sx={{ mt: 0.5, display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                      {call.selected_indexes.map((idx) => (
                        <Typography
                          key={idx}
                          variant="caption"
                          sx={{
                            px: 0.75,
                            py: 0.1,
                            borderRadius: 0.5,
                            background: `${COLORS.green}22`,
                            color: COLORS.green,
                            fontSize: 10,
                          }}
                        >
                          {idx}
                        </Typography>
                      ))}
                    </Box>
                  )}

                  {(call.timeline_count ?? call.gap_count ?? call.usecase_count ?? call.rec_count) !== undefined && (
                    <Typography variant="caption" sx={{ color: COLORS.green, fontSize: 10 }}>
                      {call.timeline_count !== undefined && `${call.timeline_count} timeline entries`}
                      {call.gap_count !== undefined && `${call.gap_count} gaps found`}
                      {call.usecase_count !== undefined && `${call.usecase_count} use cases`}
                      {call.rec_count !== undefined && `${call.rec_count} recommendations`}
                    </Typography>
                  )}
                </Box>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </Box>
    </GlassCard>
  );
}
