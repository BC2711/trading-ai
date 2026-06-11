import { apiClient } from "../services/api";

export type AnalyticsTrade = {
  id: number;
  symbol: string;
  strategy: string | null;
  side: string;
  quantity: number;
  entry_price: number;
  exit_price: number;
  realized_pnl: number;
  return_pct: number;
  opened_at: string;
  closed_at: string;
  outcome: "win" | "loss" | "flat";
};

export type AnalyticsEquityPoint = {
  timestamp: string;
  equity: number;
  realized_pnl: number;
  drawdown: number;
  event: string;
};

export type PerformanceSummary = {
  win_rate: number;
  loss_rate: number;
  average_win: number;
  average_loss: number;
  profit_factor: number;
  sharpe_ratio: number;
  max_drawdown: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  best_trade: AnalyticsTrade | null;
  worst_trade: AnalyticsTrade | null;
  net_pnl: number;
  gross_profit: number;
  gross_loss: number;
};

export type AnalyticsEquityCurve = {
  starting_equity: number;
  ending_equity: number;
  max_drawdown: number;
  points: AnalyticsEquityPoint[];
};

export type StrategyComparison = {
  id: string;
  strategy_id: number | null;
  strategy: string;
  total_trades: number;
  win_rate: number;
  total_return: number;
  profit_factor: number;
  sharpe_ratio: number;
  max_drawdown: number;
  best_trade: number | null;
  worst_trade: number | null;
  source: string;
};

export type StrategyComparisonResponse = {
  strategies: StrategyComparison[];
};

export async function fetchPerformanceSummary(): Promise<PerformanceSummary> {
  const response = await apiClient.get<PerformanceSummary>("/api/analytics/performance");
  return response.data;
}

export async function fetchAnalyticsEquityCurve(): Promise<AnalyticsEquityCurve> {
  const response = await apiClient.get<AnalyticsEquityCurve>("/api/analytics/equity-curve");
  return response.data;
}

export async function fetchStrategyComparison(): Promise<StrategyComparisonResponse> {
  const response = await apiClient.get<StrategyComparisonResponse>("/api/analytics/strategies");
  return response.data;
}

export async function fetchAnalyticsTrades(): Promise<AnalyticsTrade[]> {
  const response = await apiClient.get<AnalyticsTrade[]>("/api/analytics/trades");
  return response.data;
}
