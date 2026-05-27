import { Box } from "@mui/material";
import Header from "./components/Header";
import CenterPanel from "./components/CenterPanel";
import AiActivityPanel from "./components/AiActivityPanel";
import { useData } from "./data/context";

export default function App() {
  const { phases } = useData();
  const isIdle = phases.length === 0;

  return (
    <Box
      sx={{
        width: "100vw",
        height: "100vh",
        display: "grid",
        gridTemplateRows: "auto 1fr",
        gridTemplateColumns: isIdle ? "1fr" : "1fr 280px",
        gridTemplateAreas: isIdle
          ? `"header" "main"`
          : `"header header" "main sidebar"`,
        overflow: "hidden",
        background: "#070B16",
      }}
    >
      <Box sx={{ gridArea: "header" }}>
        <Header />
      </Box>

      <Box sx={{ gridArea: "main", overflow: "hidden", p: 1, minHeight: 0 }}>
        <CenterPanel />
      </Box>

      {!isIdle && (
        <Box sx={{ gridArea: "sidebar", overflow: "hidden", p: 0.5, minHeight: 0, borderLeft: "1px solid rgba(0,229,255,0.1)" }}>
          <AiActivityPanel />
        </Box>
      )}
    </Box>
  );
}
