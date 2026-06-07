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
