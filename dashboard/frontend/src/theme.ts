import { createTheme } from "@mui/material/styles";

export const COLORS = {
  bg: "#070B16",
  cyan: "#00E5FF",
  green: "#00FF94",
  red: "#FF3B5C",
  amber: "#FFB020",
  purple: "#B388FF",
} as const;

export type AccentColor = "cyan" | "green" | "red" | "amber" | "purple";

export const ACCENT_HEX: Record<AccentColor, string> = {
  cyan: COLORS.cyan,
  green: COLORS.green,
  red: COLORS.red,
  amber: COLORS.amber,
  purple: COLORS.purple,
};

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: COLORS.cyan },
    secondary: { main: COLORS.green },
    error: { main: COLORS.red },
    warning: { main: COLORS.amber },
    background: { default: COLORS.bg, paper: "rgba(14,22,42,0.65)" },
  },
  typography: {
    fontFamily: "'Rajdhani', sans-serif",
    h1: { fontFamily: "'Orbitron', sans-serif", letterSpacing: 2 },
    h2: { fontFamily: "'Orbitron', sans-serif", letterSpacing: 2 },
    h3: { fontFamily: "'Orbitron', sans-serif", letterSpacing: 1.5 },
    h4: { fontFamily: "'Orbitron', sans-serif", letterSpacing: 1 },
    h5: { fontFamily: "'Orbitron', sans-serif", letterSpacing: 1 },
    h6: { fontFamily: "'Orbitron', sans-serif", letterSpacing: 1 },
    body1: { fontFamily: "'Rajdhani', sans-serif", fontSize: 15 },
    body2: { fontFamily: "'Rajdhani', sans-serif", fontSize: 13 },
    caption: { fontFamily: "'JetBrains Mono', monospace", fontSize: 11 },
  },
  shape: { borderRadius: 4 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: COLORS.bg,
          color: "#E0E0E0",
          margin: 0,
          overflow: "hidden",
        },
      },
    },
  },
});

export default theme;
