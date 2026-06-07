import axios from "axios";

import type { Signal } from "../types/signal";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL
});

export async function fetchSignals(): Promise<Signal[]> {
  const response = await apiClient.get<Signal[]>("/api/signals");
  return response.data;
}

export type SymbolResource = {
  id: number;
  symbol: string;
  base_asset: string;
  quote_asset: string;
  market: string;
  exchange: string;
  status: string;
  created_at: string;
};

export type MarketCandle = {
  id: number;
  symbol: string;
  timeframe: string;
  opened_at: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type StrategyResource = {
  id: number;
  name: string;
  description: string;
  timeframe: string;
  status: string;
  created_at: string;
};

export type RiskSetting = {
  id: number;
  name: string;
  max_risk_per_trade: number;
  max_daily_loss: number;
  max_open_trades: number;
  max_symbol_exposure: number;
  status: string;
  created_at: string;
};

export type StrategyUpdateRequest = Partial<Pick<StrategyResource, "name" | "description" | "timeframe" | "status">>;

export type RiskSettingUpdateRequest = Partial<
  Pick<
    RiskSetting,
    "name" | "max_risk_per_trade" | "max_daily_loss" | "max_open_trades" | "max_symbol_exposure" | "status"
  >
>;

export type MarketDataRefreshRequest = {
  symbols?: string[];
  timeframe?: string;
  limit?: number;
  regenerate_signals?: boolean;
};

export type MarketDataSyncRequest = {
  symbols: string[];
  timeframe: string;
  limit?: number;
  regenerate_signals?: boolean;
};

export type MarketDataResult = {
  symbol: string;
  timeframe: string;
  fetched: number;
  inserted: number;
  updated: number;
};

export type MarketDataSyncResponse = {
  provider: string;
  timeframe: string;
  results: MarketDataResult[];
  signals: Signal[];
};

export type MarketDataRefreshResponse = {
  status: string;
  provider: string;
  symbols: string[];
  timeframe: string;
  limit: number;
  results: MarketDataResult[];
  generated_signal_count: number;
  error?: string | null;
};

export type MarketDataSchedule = {
  enabled: boolean;
  job_id: string;
  interval_minutes: number;
  symbols: string[];
  timeframe: string;
  limit: number;
  regenerate_signals: boolean;
};

export type BacktestRunRequest = {
  symbol?: string;
  timeframe?: string;
  initial_balance?: number;
  lookback?: number;
};

export type BacktestRun = {
  id: number;
  symbol: string;
  strategy: string | null;
  timeframe: string;
  initial_balance: number;
  ending_balance: number;
  total_return: number;
  win_rate: number;
  max_drawdown: number;
  trades_count: number;
  winning_trades: number;
  losing_trades: number;
  status: string;
  summary: string;
  created_at: string;
};

export type AIAnalysisRequest = {
  signal_id?: number;
  symbol?: string;
  timeframe?: string;
  lookback?: number;
};

export type AIAnalysis = {
  id: number;
  signal_id: number | null;
  provider: string;
  symbol: string;
  timeframe: string;
  direction: string;
  confidence: number;
  explanation: string;
  reasoning: string[];
  risk_notes: string[];
  suggested_action: string;
  indicators: Record<string, number>;
  backtest_summary: string | null;
  generated_at: string;
};

export async function fetchSymbols(): Promise<SymbolResource[]> {
  const response = await apiClient.get<SymbolResource[]>("/api/symbols");
  return response.data;
}

export async function fetchCandles(symbol = "BTCUSDT", timeframe = "15m", limit = 120): Promise<MarketCandle[]> {
  const response = await apiClient.get<MarketCandle[]>("/api/candles", {
    params: { symbol, timeframe, limit }
  });
  return response.data;
}

export async function fetchStrategies(): Promise<StrategyResource[]> {
  const response = await apiClient.get<StrategyResource[]>("/api/strategies");
  return response.data;
}

export async function fetchRiskSettings(): Promise<RiskSetting[]> {
  const response = await apiClient.get<RiskSetting[]>("/api/risk-settings");
  return response.data;
}

export async function updateStrategy(id: number, payload: StrategyUpdateRequest): Promise<StrategyResource> {
  const response = await apiClient.patch<StrategyResource>(`/api/strategies/${id}`, payload);
  return response.data;
}

export async function updateRiskSettings(id: number, payload: RiskSettingUpdateRequest): Promise<RiskSetting> {
  const response = await apiClient.patch<RiskSetting>(`/api/risk-settings/${id}`, payload);
  return response.data;
}

export async function fetchMarketDataSchedule(): Promise<MarketDataSchedule> {
  const response = await apiClient.get<MarketDataSchedule>("/api/market-data/schedule");
  return response.data;
}

export async function syncMarketData(payload: MarketDataSyncRequest): Promise<MarketDataSyncResponse> {
  const response = await apiClient.post<MarketDataSyncResponse>("/api/market-data/sync", payload);
  return response.data;
}

export async function refreshMarketData(payload: MarketDataRefreshRequest): Promise<MarketDataRefreshResponse> {
  const response = await apiClient.post<MarketDataRefreshResponse>("/api/market-data/refresh", payload);
  return response.data;
}

export async function fetchBacktests(limit = 5): Promise<BacktestRun[]> {
  const response = await apiClient.get<BacktestRun[]>("/api/backtests", {
    params: { limit }
  });
  return response.data;
}

export async function runBacktest(payload: BacktestRunRequest): Promise<BacktestRun> {
  const response = await apiClient.post<BacktestRun>("/api/backtests/run", payload);
  return response.data;
}

export async function analyzeSignal(payload: AIAnalysisRequest): Promise<AIAnalysis> {
  const response = await apiClient.post<AIAnalysis>("/api/ai/analyze-signal", payload);
  return response.data;
}

export async function fetchAIAnalyses(limit = 5): Promise<AIAnalysis[]> {
  const response = await apiClient.get<AIAnalysis[]>("/api/ai/analyses", {
    params: { limit }
  });
  return response.data;
}

export async function fetchAIAnalysis(id: number): Promise<AIAnalysis> {
  const response = await apiClient.get<AIAnalysis>(`/api/ai/analyses/${id}`);
  return response.data;
}
