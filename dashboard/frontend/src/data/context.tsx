import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { DashboardData } from "./types";
import { connectStream, createInitialData, fetchSnapshot } from "./api";

const Ctx = createContext<DashboardData | null>(null);

export function useData(): DashboardData {
  const v = useContext(Ctx);
  if (!v) throw new Error("useData must be used inside <DataProvider>");
  return v;
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<DashboardData>(createInitialData);

  useEffect(() => {
    fetchSnapshot().then(setData);
    const stop = connectStream(setData);
    return stop;
  }, []);

  return <Ctx value={data}>{children}</Ctx>;
}
