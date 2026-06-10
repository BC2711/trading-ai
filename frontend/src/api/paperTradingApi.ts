import { apiClient } from "../services/api";

export type PaperTradingAccount = {
  id: number;
  name: string;
  starting_balance: number;
  cash_balance: number;
  available_balance: number;
  paper_equity: number;
  margin_used: number;
  margin_available: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  open_positions: number;
  status: string;
  updated_at: string;
};

export type PaperTradingOrderRequest = {
  symbol: string;
  side: "buy" | "sell";
  order_type?: "market";
  quantity: number;
};

export type PaperTradingOrder = {
  id: number;
  symbol: string;
  side: string;
  order_type: string;
  quantity: number;
  requested_price: number;
  fill_price: number | null;
  status: string;
  risk_status: string;
  risk_message: string;
  execution_mode: string;
  failure_reason: string | null;
  created_at: string;
  filled_at: string | null;
};

export type PaperTradingPosition = {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  avg_entry_price: number;
  mark_price: number;
  notional_value: number;
  unrealized_pnl: number;
  realized_pnl: number;
  status: string;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
};

export type PaperTradingPerformancePoint = {
  timestamp: string;
  paper_equity: number;
  cash_balance: number;
  realized_pnl: number;
  unrealized_pnl: number;
  event_type: string;
};

export type PaperTradingPerformance = {
  starting_balance: number;
  current_equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  points: PaperTradingPerformancePoint[];
};

export type PaperTradingResetResponse = {
  account: PaperTradingAccount;
  reset_orders: number;
  reset_positions: number;
  reset_ledger_entries: number;
};

export async function fetchPaperAccount(): Promise<PaperTradingAccount> {
  const response = await apiClient.get<PaperTradingAccount>("/api/paper/account");
  return response.data;
}

export async function createPaperTradingOrder(payload: PaperTradingOrderRequest): Promise<PaperTradingOrder> {
  const response = await apiClient.post<PaperTradingOrder>("/api/paper/orders", payload);
  return response.data;
}

export async function fetchPaperTradingOrders(limit = 100): Promise<PaperTradingOrder[]> {
  const response = await apiClient.get<PaperTradingOrder[]>("/api/paper/orders", { params: { limit } });
  return response.data;
}

export async function fetchPaperTradingPositions(status: "open" | "closed" | "all" = "open"): Promise<PaperTradingPosition[]> {
  const response = await apiClient.get<PaperTradingPosition[]>("/api/paper/positions", { params: { status } });
  return response.data;
}

export async function closePaperTradingPosition(id: number): Promise<PaperTradingPosition> {
  const response = await apiClient.post<PaperTradingPosition>(`/api/paper/positions/${id}/close`);
  return response.data;
}

export async function fetchPaperTradingPerformance(): Promise<PaperTradingPerformance> {
  const response = await apiClient.get<PaperTradingPerformance>("/api/paper/performance");
  return response.data;
}

export async function resetPaperTradingAccount(startingBalance = 10000): Promise<PaperTradingResetResponse> {
  const response = await apiClient.post<PaperTradingResetResponse>("/api/paper/reset", { starting_balance: startingBalance });
  return response.data;
}
