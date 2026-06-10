import { apiClient } from "../services/api";

export type RiskRejectedTrade = {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  risk_message: string;
  created_at: string;
};

export type RiskSummary = {
  risk_score: number;
  equity: number;
  daily_loss: number;
  weekly_loss: number;
  daily_loss_usage: number;
  weekly_loss_usage: number;
  drawdown: number;
  drawdown_usage: number;
  total_exposure: number;
  exposure_usage: number;
  max_loss_limit: number;
  max_weekly_loss_limit: number;
  max_drawdown_limit: number;
  open_trades: number;
  max_open_trades: number;
  leverage: number;
  max_leverage: number;
  circuit_breaker_enabled: boolean;
  recent_rejected_trades: RiskRejectedTrade[];
  warnings: string[];
};

export type RiskLimits = {
  id: number;
  max_risk_per_trade: number;
  max_daily_loss: number;
  max_weekly_loss: number;
  max_drawdown: number;
  max_open_trades: number;
  max_exposure_per_symbol: number;
  max_leverage: number;
  max_consecutive_losses: number;
  circuit_breaker_enabled: boolean;
  live_trading_enabled: boolean;
};

export type RiskTradeValidationRequest = {
  symbol: string;
  side: "buy" | "sell";
  price: number;
  quantity: number;
  stop_loss?: number | null;
  take_profit?: number | null;
  leverage?: number;
  execution_mode?: "paper" | "live";
};

export type RiskTradeValidation = {
  approved: boolean;
  message: string;
  risk_score: number;
  notional_value: number;
  risk_amount: number;
  risk_pct: number;
  projected_symbol_exposure_pct: number;
  projected_leverage: number;
  warnings: string[];
};

export type PositionSizeRequest = {
  symbol?: string;
  method: "fixed_amount" | "fixed_percentage_risk" | "atr_based" | "volatility_based" | "kelly";
  entry_price: number;
  stop_loss?: number | null;
  account_equity?: number;
  fixed_amount?: number;
  risk_percent?: number;
  atr?: number;
  volatility?: number;
  leverage?: number;
};

export type PositionSizeResponse = {
  symbol: string;
  method: string;
  quantity: number;
  notional_value: number;
  risk_amount: number;
  risk_pct: number;
  warnings: string[];
};

export async function fetchRiskSummary(): Promise<RiskSummary> {
  const response = await apiClient.get<RiskSummary>("/api/risk/summary");
  return response.data;
}

export async function fetchRiskLimits(): Promise<RiskLimits> {
  const response = await apiClient.get<RiskLimits>("/api/risk/limits");
  return response.data;
}

export async function updateRiskLimits(payload: Partial<RiskLimits>): Promise<RiskLimits> {
  const response = await apiClient.put<RiskLimits>("/api/risk/limits", payload);
  return response.data;
}

export async function validateRiskTrade(payload: RiskTradeValidationRequest): Promise<RiskTradeValidation> {
  const response = await apiClient.post<RiskTradeValidation>("/api/risk/validate-trade", payload);
  return response.data;
}

export async function calculatePositionSize(payload: PositionSizeRequest): Promise<PositionSizeResponse> {
  const response = await apiClient.post<PositionSizeResponse>("/api/risk/position-size", payload);
  return response.data;
}

export async function enableCircuitBreaker(): Promise<RiskLimits> {
  const response = await apiClient.post<RiskLimits>("/api/risk/circuit-breaker/enable");
  return response.data;
}

export async function disableCircuitBreaker(): Promise<RiskLimits> {
  const response = await apiClient.post<RiskLimits>("/api/risk/circuit-breaker/disable");
  return response.data;
}
