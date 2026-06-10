import { apiClient } from "../services/api";

export type WalkForwardRequest = {
  strategy_id?: number | null;
  symbol: string;
  timeframe: string;
  initial_balance: number;
  training_period: number;
  validation_period: number;
  test_period: number;
  rolling_windows: number;
};

export type WalkForwardMetrics = {
  total_return: number;
  ending_balance: number;
  win_rate: number;
  max_drawdown: number;
  trades_count: number;
  profit_factor: number;
  sharpe_ratio: number;
};

export type WalkForwardWindowResult = {
  window: number;
  train_start: string;
  train_end: string;
  validation_start: string;
  validation_end: string;
  test_start: string;
  test_end: string;
  selected_parameters: Record<string, number>;
  optimization_score: number;
  training_metrics: WalkForwardMetrics;
  validation_metrics: WalkForwardMetrics;
  test_metrics: WalkForwardMetrics;
};

export type WalkForwardAggregatedResult = {
  windows: number;
  cumulative_return: number;
  average_test_return: number;
  average_validation_return: number;
  average_win_rate: number;
  max_drawdown: number;
  total_trades: number;
  profit_factor: number;
  sharpe_ratio: number;
  robustness_score: number;
};

export type WalkForwardRun = {
  id: number;
  symbol: string;
  strategy: string | null;
  strategy_id: number | null;
  timeframe: string;
  training_period: number;
  validation_period: number;
  test_period: number;
  rolling_windows: number;
  initial_balance: number;
  optimization_results: Array<Record<string, unknown>>;
  out_of_sample_results: Array<Record<string, unknown>>;
  window_metrics: WalkForwardWindowResult[];
  aggregated_result: WalkForwardAggregatedResult;
  status: string;
  warning: string | null;
  created_at: string;
};

export async function runWalkForward(payload: WalkForwardRequest): Promise<WalkForwardRun> {
  const response = await apiClient.post<WalkForwardRun>("/api/backtests/walk-forward", payload);
  return response.data;
}

export async function fetchWalkForwardRun(id: number): Promise<WalkForwardRun> {
  const response = await apiClient.get<WalkForwardRun>(`/api/backtests/walk-forward/${id}`);
  return response.data;
}
