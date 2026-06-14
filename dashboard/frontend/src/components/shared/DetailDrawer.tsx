import { Box, Typography, IconButton } from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";
import type { ReactNode } from "react";
import { ACCENT_HEX, type AccentColor } from "../../theme";

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  accent?: AccentColor;
  children: ReactNode;
  footer?: ReactNode;
}

export default function DetailDrawer({ open, onClose, title, accent = "cyan", children, footer }: Props) {
  const c = ACCENT_HEX[accent];

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{
              position: "fixed", inset: 0, zIndex: 900,
              background: "rgba(0,0,0,0.5)",
              backdropFilter: "blur(4px)",
            }}
            onClick={onClose}
          />

          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            style={{
              position: "fixed", top: 0, right: 0, bottom: 0,
              width: "min(520px, 85vw)", zIndex: 950,
              display: "flex", flexDirection: "column",
            }}
          >
            <Box sx={{
              height: "100%",
              display: "flex",
              flexDirection: "column",
              background: "linear-gradient(180deg, rgba(14,22,42,0.97) 0%, rgba(8,14,28,0.97) 100%)",
              borderLeft: `2px solid ${c}55`,
              boxShadow: `-8px 0 32px rgba(0,0,0,0.6)`,
            }}>
              <Box sx={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                px: 2.5, py: 1.5,
                borderBottom: `1px solid ${c}33`,
                background: `linear-gradient(90deg, ${c}15 0%, transparent 100%)`,
                flexShrink: 0,
              }}>
                <Typography sx={{
                  fontFamily: "'Orbitron'", fontWeight: 700, fontSize: 14,
                  letterSpacing: 1.5, color: c,
                  textShadow: `0 0 8px ${c}55`,
                }}>
                  {title}
                </Typography>
                <IconButton size="small" onClick={onClose} sx={{ color: "grey.500", fontSize: 16, "&:hover": { color: c } }}>
                  ✕
                </IconButton>
              </Box>

              <Box sx={{ flex: 1, overflow: "auto", p: 2.5, minHeight: 0 }}>
                {children}
              </Box>

              {footer && (
                <Box sx={{
                  px: 2.5, py: 1.5, flexShrink: 0,
                  borderTop: `1px solid ${c}22`,
                  background: `rgba(0,0,0,0.15)`,
                }}>
                  {footer}
                </Box>
              )}
            </Box>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export function DetailField({ label, value, mono, color }: {
  label: string;
  value: string | number | undefined | null;
  mono?: boolean;
  color?: string;
}) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <Box sx={{ mb: 1.5 }}>
      <Typography variant="caption" sx={{
        color: "grey.500", fontSize: 11, fontFamily: "'Orbitron'",
        letterSpacing: 1, textTransform: "uppercase", display: "block", mb: 0.25,
      }}>
        {label}
      </Typography>
      <Typography sx={{
        color: color ?? "grey.200", fontSize: 14,
        fontFamily: mono ? "'JetBrains Mono'" : "'Rajdhani'",
        lineHeight: 1.6, wordBreak: "break-all",
      }}>
        {String(value)}
      </Typography>
    </Box>
  );
}
