import { useRef, useEffect } from "react";
import { Box, Typography } from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";
import GlassCard from "./shared/GlassCard";
import { useData } from "../data/context";
import { COLORS } from "../theme";

const STAGE_LABELS: Record<string, { label: string; desc: string }> = {
  react_reasoning: { label: "Reasoning", desc: "Deciding next investigation step" },
  data_discovery: { label: "Data Discovery", desc: "Selecting security-relevant data" },
  evidence_analysis: { label: "Timeline Analysis", desc: "Building attack timeline" },
  gap_analysis: { label: "Gap Analysis", desc: "Finding detection gaps" },
  usecase_generation: { label: "Use Case Gen", desc: "Generating detection rules" },
  response_recommendation: { label: "Recommendations", desc: "Building response playbook" },
};

export default function AiActivityPanel() {
  const { aiCalls, mcpCalls } = useData();

  const reasoningCalls = aiCalls.filter((c) => c.type !== "react_tool_call");
  const recentAi = [...reasoningCalls].reverse().slice(0, 10);
  const recentMcp = [...mcpCalls].reverse().slice(0, 12);
  const mcpDone = mcpCalls.filter((c) => c.status === "done").length;
  const mcpErr = mcpCalls.filter((c) => c.status === "error").length;

  const aiScrollRef = useRef<HTMLDivElement>(null);
  const mcpScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    aiScrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [reasoningCalls.length]);

  useEffect(() => {
    mcpScrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [mcpCalls.length]);

  const latestIteration = [...aiCalls].reverse().find((c) => c.iteration)?.iteration ?? 0;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, height: "100%", overflow: "hidden" }}>
      {/* AI Reasoning — top half */}
      <Box sx={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
        <GlassCard title="AI Reasoning" subtitle={latestIteration > 0 ? `Iteration ${latestIteration}` : "Claude"} accent="purple" noPadding>
          <Box ref={aiScrollRef} sx={{ px: 0.75, py: 0.5, overflow: "auto", height: "100%" }}>
            <AnimatePresence initial={false}>
              {recentAi.map((call, i) => {
                const isRunning = call.status === "running";
                const stage = STAGE_LABELS[call.type];
                const label = stage?.label ?? call.type;
                const desc = stage?.desc ?? "";

                return (
                  <motion.div
                    key={`ai-${call.type}-${call.status}-${reasoningCalls.length - i}`}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <Box
                      sx={{
                        py: 0.5,
                        px: 0.75,
                        mb: 0.3,
                        borderLeft: `2px solid ${isRunning ? COLORS.amber : COLORS.purple}`,
                        borderRadius: 0.5,
                      }}
                    >
                      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
                          {call.iteration && (
                            <Typography variant="caption" sx={{ color: "grey.600", fontSize: 10 }}>
                              #{call.iteration}
                            </Typography>
                          )}
                          <Typography
                            variant="caption"
                            sx={{ fontFamily: "'Orbitron'", fontWeight: 600, fontSize: 11, color: isRunning ? COLORS.amber : COLORS.purple }}
                          >
                            {label}
                          </Typography>
                        </Box>
                        {isRunning && (
                          <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity }}>
                            <Typography variant="caption" sx={{ color: COLORS.amber, fontSize: 10 }}>
                              {call.type === "react_reasoning" ? "THINKING" : "ANALYZING"}
                            </Typography>
                          </motion.div>
                        )}
                      </Box>

                      {call.reasoning ? (
                        <Typography variant="caption" sx={{ color: "grey.400", fontSize: 11, display: "block", mt: 0.25, lineHeight: 1.35 }}>
                          {call.reasoning.slice(0, 160)}
                        </Typography>
                      ) : desc && isRunning ? (
                        <Typography variant="caption" sx={{ color: "grey.600", fontSize: 11, display: "block", mt: 0.15 }}>
                          {desc}
                        </Typography>
                      ) : null}

                      {call.selected_indexes && (
                        <Box sx={{ mt: 0.25, display: "flex", gap: 0.3, flexWrap: "wrap" }}>
                          {call.selected_indexes.slice(0, 5).map((idx) => (
                            <Typography key={idx} variant="caption" sx={{ px: 0.4, borderRadius: 0.5, background: `${COLORS.green}22`, color: COLORS.green, fontSize: 10 }}>
                              {idx}
                            </Typography>
                          ))}
                        </Box>
                      )}

                      {(call.timeline_count ?? call.gap_count ?? call.usecase_count ?? call.rec_count) !== undefined && (
                        <Typography variant="caption" sx={{ color: COLORS.green, fontSize: 10 }}>
                          {call.timeline_count !== undefined && `${call.timeline_count} timeline entries`}
                          {call.gap_count !== undefined && `${call.gap_count} gaps`}
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
      </Box>

      {/* MCP Calls — bottom half, compact with SPL */}
      <Box sx={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
        <GlassCard title="Splunk MCP" subtitle={`${mcpDone} calls${mcpErr ? ` · ${mcpErr} err` : ""}`} accent="cyan" noPadding>
          <Box ref={mcpScrollRef} sx={{ px: 0.75, py: 0.5, overflow: "auto", height: "100%" }}>
            <AnimatePresence initial={false}>
              {recentMcp.map((call, i) => {
                const isRunning = call.status === "running";
                const isError = call.status === "error";
                const color = isError ? COLORS.red : isRunning ? COLORS.amber : COLORS.cyan;

                return (
                  <motion.div
                    key={`mcp-${call.tool}-${mcpCalls.length - i}`}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                  >
                    <Box
                      sx={{
                        py: 0.35,
                        px: 0.75,
                        mb: 0.3,
                        borderLeft: `2px solid ${color}`,
                        borderRadius: 0.5,
                      }}
                    >
                      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <Typography variant="caption" sx={{ fontFamily: "'JetBrains Mono'", fontWeight: 600, color, fontSize: 11 }}>
                          {call.tool}
                        </Typography>
                        <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
                          {call.row_count !== undefined && (
                            <Typography variant="caption" sx={{ color: COLORS.green, fontSize: 10 }}>
                              {call.row_count}r
                            </Typography>
                          )}
                          <Typography variant="caption" sx={{ fontSize: 9, px: 0.4, borderRadius: 0.5, background: `${color}22`, color }}>
                            {isRunning ? "RUN" : isError ? "ERR" : "OK"}
                          </Typography>
                        </Box>
                      </Box>

                      {call.spl && (
                        <Typography
                          variant="caption"
                          sx={{
                            color: "grey.600",
                            fontSize: 10,
                            fontFamily: "'JetBrains Mono'",
                            display: "block",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            mt: 0.15,
                          }}
                        >
                          {call.spl}
                        </Typography>
                      )}

                      {call.error && (
                        <Typography variant="caption" sx={{ color: COLORS.red, fontSize: 10 }}>{call.error}</Typography>
                      )}
                    </Box>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </Box>
        </GlassCard>
      </Box>
    </Box>
  );
}
