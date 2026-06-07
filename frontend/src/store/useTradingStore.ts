import { create } from "zustand";

type Timeframe = "1h" | "4h" | "1d";

type TradingState = {
  timeframe: Timeframe;
  setTimeframe: (timeframe: Timeframe) => void;
};

export const useTradingStore = create<TradingState>((set) => ({
  timeframe: "4h",
  setTimeframe: (timeframe) => set({ timeframe })
}));
