import { createContext, useContext, useState } from "react";

const NowContext = createContext(null);

const DEFAULT_NOW = "2025-11-17";

export function NowProvider({ children }) {
  const [now, setNow] = useState(DEFAULT_NOW);
  return (
    <NowContext.Provider value={{ now, setNow }}>{children}</NowContext.Provider>
  );
}

export function useNow() {
  const ctx = useContext(NowContext);
  if (!ctx) throw new Error("useNow must be used within NowProvider");
  return ctx;
}
