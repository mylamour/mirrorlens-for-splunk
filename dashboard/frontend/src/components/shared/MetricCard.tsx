import { Box, Typography } from "@mui/material";
import { motion } from "framer-motion";
import { ACCENT_HEX, type AccentColor } from "../../theme";

interface Props {
  label: string;
  value: string | number;
  accent?: AccentColor;
}

export default function MetricCard({ label, value, accent = "cyan" }: Props) {
  const c = ACCENT_HEX[accent];
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <Box
        sx={{
          px: 1.5,
          py: 0.75,
          borderLeft: `2px solid ${c}`,
          background: `linear-gradient(90deg, ${c}0A 0%, transparent 100%)`,
        }}
      >
        <Typography variant="caption" sx={{ color: "grey.500", textTransform: "uppercase", letterSpacing: 1 }}>
          {label}
        </Typography>
        <Typography
          sx={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 20,
            fontWeight: 600,
            color: c,
            textShadow: `0 0 6px ${c}55`,
          }}
        >
          {value}
        </Typography>
      </Box>
    </motion.div>
  );
}
