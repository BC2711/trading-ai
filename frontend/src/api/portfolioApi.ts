import { apiClient } from "../services/api";

export type PortfolioExposureItem = {
  symbol: string;
  side: string;
  quantity: number;
  mark_price: number;
  notional_value: number;
  exposure_pct: number;
  unrealized_pnl: number;
};

export type PortfolioAllocationItem = {
  asset: string;
  value: number;
  percentage: number;
};

export type OpenPositionAllocationItem = {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  value: number;
  percentage: number;
  unrealized_pnl: number;
};

export type PortfolioSummary = {
  total_equity: number;
  available_balance: number;
  margin_used: number;
  margin_available: number;
  total_realized_pnl: number;
  total_unrealized_pnl: number;
  realized_pnl: number;
  unrealized_pnl: number;
  daily_pnl: number;
  weekly_pnl: number;
  monthly_pnl: number;
  total_exposure: number;
  open_positions: number;
  filled_orders: number;
  rejected_orders: number;
  cancelled_orders: number;
  closed_positions: number;
  winning_positions: number;
  losing_positions: number;
  win_rate: number;
  best_trade_pnl: number | null;
  worst_trade_pnl: number | null;
  exposure_by_symbol: PortfolioExposureItem[];
  allocation_by_asset: PortfolioAllocationItem[];
  open_position_allocation: OpenPositionAllocationItem[];
};

export type PortfolioPerformancePoint = {
  timestamp: string;
  equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  event: string;
};

export type PortfolioPerformance = {
  starting_equity: number;
  points: PortfolioPerformancePoint[];
};

export type PortfolioExposure = {
  total_exposure: number;
  total_equity: number;
  items: PortfolioExposureItem[];
};

export type PortfolioAllocation = {
  total_value: number;
  by_asset: PortfolioAllocationItem[];
  open_positions: OpenPositionAllocationItem[];
};

export type PortfolioPnl = {
  total_realized_pnl: number;
  total_unrealized_pnl: number;
  total_pnl: number;
  daily_pnl: number;
  weekly_pnl: number;
  monthly_pnl: number;
  win_rate: number;
  best_trade_pnl: number | null;
  worst_trade_pnl: number | null;
};

export async function fetchPortfolioSummary(): Promise<PortfolioSummary> {
  const response = await apiClient.get<PortfolioSummary>("/api/portfolio/summary");
  return response.data;
}

export async function fetchPortfolioPerformance(): Promise<PortfolioPerformance> {
  const response = await apiClient.get<PortfolioPerformance>("/api/portfolio/performance");
  return response.data;
}

export async function fetchPortfolioExposure(): Promise<PortfolioExposure> {
  const response = await apiClient.get<PortfolioExposure>("/api/portfolio/exposure");
  return response.data;
}

export async function fetchPortfolioAllocation(): Promise<PortfolioAllocation> {
  const response = await apiClient.get<PortfolioAllocation>("/api/portfolio/allocation");
  return response.data;
}

export async function fetchPortfolioPnl(): Promise<PortfolioPnl> {
  const response = await apiClient.get<PortfolioPnl>("/api/portfolio/pnl");
  return response.data;
}
