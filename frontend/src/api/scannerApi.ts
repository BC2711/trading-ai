import { apiClient } from "../services/api";

export type ScannerSignal = "buy" | "sell" | "hold";
export type ScannerRiskLevel = "low" | "medium" | "high";

export type ScannerResult = {
  symbol: string;
  current_price: number;
  signal: ScannerSignal;
  confidence: number;
  risk_level: ScannerRiskLevel;
  rsi: number;
  macd_signal: "bullish" | "bearish" | "neutral";
  trend_direction: "uptrend" | "downtrend" | "sideways";
  volatility: number;
  recommended_action: string;
  created_at: string;
};

export type ScannerRunRequest = {
  symbols?: string[];
  timeframe?: string;
  lookback?: number;
};

export type ScannerFilters = {
  symbol?: string;
  signal?: ScannerSignal | "";
  min_confidence?: number;
  risk_level?: ScannerRiskLevel | "";
  timeframe?: string;
};

export async function fetchScannerResults(filters: ScannerFilters = {}): Promise<ScannerResult[]> {
  const response = await apiClient.get<ScannerResult[]>("/api/scanner", {
    params: {
      symbol: filters.symbol || undefined,
      signal: filters.signal || undefined,
      min_confidence: filters.min_confidence,
      risk_level: filters.risk_level || undefined,
      timeframe: filters.timeframe
    }
  });
  return response.data;
}

export async function runScanner(payload: ScannerRunRequest = {}): Promise<ScannerResult[]> {
  const response = await apiClient.post<ScannerResult[]>("/api/scanner/run", payload);
  return response.data;
}

export async function fetchScannerSignals(minConfidence = 0.6): Promise<ScannerResult[]> {
  const response = await apiClient.get<ScannerResult[]>("/api/scanner/signals", {
    params: { min_confidence: minConfidence }
  });
  return response.data;
}
