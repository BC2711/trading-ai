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

export type MarketDataSyncRequest = {
  symbols: string[];
  timeframe: string;
  limit?: number;
  regenerate_signals?: boolean;
};

export type MarketDataSyncResponse = {
  provider: string;
  timeframe: string;
  results: Array<{
    symbol: string;
    timeframe: string;
    fetched: number;
    inserted: number;
    updated: number;
  }>;
  signals: Signal[];
};

export async function syncMarketData(payload: MarketDataSyncRequest): Promise<MarketDataSyncResponse> {
  const response = await apiClient.post<MarketDataSyncResponse>("/api/market-data/sync", payload);
  return response.data;
}
