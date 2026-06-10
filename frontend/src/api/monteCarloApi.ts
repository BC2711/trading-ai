import { apiClient } from "../services/api";

export type MonteCarloRequest = {
  starting_balance: number;
  win_rate: number;
  average_win: number;
  average_loss: number;
  number_of_trades: number;
  number_of_simulations: number;
  risk_per_trade: number;
  ruin_threshold?: number;
};

export type MonteCarloDistributionPoint = {
  bucket: string;
  count: number;
  min_equity: number;
  max_equity: number;
};

export type MonteCarloResponse = {
  id: number;
  starting_balance: number;
  win_rate: number;
  average_win: number;
  average_loss: number;
  number_of_trades: number;
  number_of_simulations: number;
  risk_per_trade: number;
  probability_of_ruin: number;
  expected_drawdown: number;
  maximum_drawdown: number;
  best_case: number;
  worst_case: number;
  median_case: number;
  confidence_intervals: Record<string, Record<string, number>>;
  ending_equity_distribution: MonteCarloDistributionPoint[];
  risk_recommendation: string;
  created_at: string;
};

export async function runMonteCarlo(payload: MonteCarloRequest): Promise<MonteCarloResponse> {
  const response = await apiClient.post<MonteCarloResponse>("/api/risk/monte-carlo", payload);
  return response.data;
}

export async function fetchMonteCarloRun(id: number): Promise<MonteCarloResponse> {
  const response = await apiClient.get<MonteCarloResponse>(`/api/risk/monte-carlo/${id}`);
  return response.data;
}
