import { useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import Header from "./components/Header";
import CenterPanel from "./components/CenterPanel";
import AiActivityPanel from "./components/AiActivityPanel";
import { useData } from "./data/context";
import { COLORS } from "./theme";

export default function App() {
  const { phases, aiCalls, mcpCalls, statusEvents, investigationRunning } = useData();
  const [traceOpen, setTraceOpen] = useState(false);
  const isIdle = phases.length === 0;
  const hasTrace = aiCalls.length > 0 || mcpCalls.length > 0 || statusEvents.length > 0 || investigationRunning;
  const showTrace = !isIdle && hasTrace;

  return (
    <Box
      sx={{
        width: "100vw",
        height: "100vh",
        display: "grid",
        gridTemplateRows: "auto 1fr",
        gridTemplateColumns: "1fr",
        gridTemplateAreas: `"header" "main"`,
        overflow: "hidden",
        background: "#070B16",
      }}
    >
      <Box sx={{ gridArea: "header" }}>
        <Header showTrace={showTrace} onOpenTrace={() => setTraceOpen(true)} />
      </Box>

      <Box sx={{ gridArea: "main", overflow: "hidden", p: 1, minHeight: 0 }}>
        <CenterPanel />
      </Box>

      <AgentTraceDrawer open={traceOpen && showTrace} onClose={() => setTraceOpen(false)} />
    </Box>
  );
}

function AgentTraceDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;

  return (
    <>
      <Box
        onClick={onClose}
        sx={{
          position: "fixed",
          inset: 0,
          zIndex: 850,
          background: "rgba(0,0,0,0.45)",
          backdropFilter: "blur(3px)",
        }}
      />
      <Box
        sx={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          zIndex: 900,
          width: "min(520px, 92vw)",
          display: "flex",
          flexDirection: "column",
          background: "linear-gradient(180deg, rgba(14,22,42,0.98) 0%, rgba(8,14,28,0.98) 100%)",
          borderLeft: `2px solid ${COLORS.cyan}55`,
          boxShadow: "-8px 0 32px rgba(0,0,0,0.6)",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            px: 2,
            py: 1.25,
            borderBottom: `1px solid ${COLORS.cyan}33`,
            background: `linear-gradient(90deg, ${COLORS.cyan}15 0%, transparent 100%)`,
            flexShrink: 0,
          }}
        >
          <Box>
            <Typography sx={{ fontFamily: "'Orbitron'", fontWeight: 700, fontSize: 13, letterSpacing: 1.5, color: COLORS.cyan }}>
              AGENT TRACE / MCP PROOF
            </Typography>
            <Typography variant="caption" sx={{ color: "grey.500", fontSize: 11 }}>
              AI reasoning, tool calls, SPL, rows
            </Typography>
          </Box>
          <Button
            variant="outlined"
            size="small"
            onClick={onClose}
            sx={{
              borderColor: `${COLORS.cyan}55`,
              color: COLORS.cyan,
              fontFamily: "'Orbitron'",
              fontSize: 10,
              minWidth: 64,
              "&:hover": { background: `${COLORS.cyan}12`, borderColor: COLORS.cyan },
            }}
          >
            CLOSE
          </Button>
        </Box>
        <Box sx={{ flex: 1, minHeight: 0, overflow: "hidden", p: 0.75 }}>
          <AiActivityPanel />
        </Box>
      </Box>
    </>
  );
}
