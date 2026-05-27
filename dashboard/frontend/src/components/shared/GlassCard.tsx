import { Box, Typography } from "@mui/material";
import type { ReactNode } from "react";
import { ACCENT_HEX, type AccentColor } from "../../theme";

interface Props {
  title?: string;
  subtitle?: string;
  accent?: AccentColor;
  noPadding?: boolean;
  children: ReactNode;
}

const cornerSize = 12;
const cornerThick = 2;

function Corner({ pos, color }: { pos: string; color: string }) {
  const base: Record<string, unknown> = {
    position: "absolute",
    width: cornerSize,
    height: cornerSize,
    borderColor: color,
    borderStyle: "solid",
    borderWidth: 0,
  };
  if (pos.includes("top")) base.top = -1;
  if (pos.includes("bottom")) base.bottom = -1;
  if (pos.includes("left")) base.left = -1;
  if (pos.includes("right")) base.right = -1;
  if (pos.includes("top")) base.borderTopWidth = cornerThick;
  if (pos.includes("bottom")) base.borderBottomWidth = cornerThick;
  if (pos.includes("left")) base.borderLeftWidth = cornerThick;
  if (pos.includes("right")) base.borderRightWidth = cornerThick;
  return <Box sx={base} />;
}

export default function GlassCard({ title, subtitle, accent = "cyan", noPadding, children }: Props) {
  const c = ACCENT_HEX[accent];

  return (
    <Box
      sx={{
        position: "relative",
        background: "linear-gradient(180deg, rgba(14,22,42,0.65) 0%, rgba(8,14,28,0.45) 100%)",
        border: `1px solid ${c}33`,
        backdropFilter: "blur(8px)",
        boxShadow: `inset 0 1px 0 ${c}18, 0 4px 24px rgba(0,0,0,0.4)`,
        borderRadius: 1,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        height: "100%",
      }}
    >
      <Corner pos="top-left" color={c} />
      <Corner pos="top-right" color={c} />
      <Corner pos="bottom-left" color={c} />
      <Corner pos="bottom-right" color={c} />

      {title && (
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            px: 1.5,
            py: 0.75,
            background: `linear-gradient(90deg, ${c}18 0%, transparent 100%)`,
            borderBottom: `1px solid ${c}22`,
          }}
        >
          <Typography
            variant="caption"
            sx={{
              fontFamily: "'Orbitron', sans-serif",
              fontSize: 13,
              fontWeight: 600,
              letterSpacing: 1.5,
              textTransform: "uppercase",
              color: c,
              textShadow: `0 0 8px ${c}55`,
            }}
          >
            {title}
          </Typography>
          {subtitle && (
            <Typography variant="caption" sx={{ color: "grey.500" }}>
              {subtitle}
            </Typography>
          )}
        </Box>
      )}

      <Box sx={{ flex: 1, overflow: "auto", minHeight: 0, ...(noPadding ? {} : { p: 1.5 }) }}>
        {children}
      </Box>
    </Box>
  );
}
