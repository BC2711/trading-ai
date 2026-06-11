import axios from "axios";

import type { Signal } from "../types/signal";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: API_KEY ? { "X-API-Key": API_KEY } : undefined
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("trading_ai_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = {
  email: string;
  full_name: string;
  password: string;
  role?: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  refresh_token?: string | null;
};

export async function login(payload: LoginRequest): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>("/api/auth/login", payload);
  localStorage.setItem("trading_ai_token", response.data.access_token);
  if (response.data.refresh_token) {
    localStorage.setItem("trading_ai_refresh_token", response.data.refresh_token);
  }
  return response.data;
}

export async function refreshAccessToken(): Promise<TokenResponse> {
  const refreshToken = localStorage.getItem("trading_ai_refresh_token");
  if (!refreshToken) {
    throw new Error("Missing refresh token");
  }
  const response = await apiClient.post<TokenResponse>("/api/auth/refresh", { refresh_token: refreshToken });
  localStorage.setItem("trading_ai_token", response.data.access_token);
  if (response.data.refresh_token) {
    localStorage.setItem("trading_ai_refresh_token", response.data.refresh_token);
  }
  return response.data;
}

export async function register(payload: RegisterRequest): Promise<UserResource> {
  const response = await apiClient.post<UserResource>("/api/auth/register", payload);
  return response.data;
}

export function logout() {
  localStorage.removeItem("trading_ai_token");
  localStorage.removeItem("trading_ai_refresh_token");
}

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
  spread: number;
};

export type MarketCandleCreate = Omit<MarketCandle, "id">;

export type StrategyResource = {
  id: number;
  name: string;
  description: string;
  timeframe: string;
  status: string;
  parameters: Record<string, unknown>;
  enabled: boolean;
  performance: Record<string, unknown>;
  created_at: string;
};

export type RiskSetting = {
  id: number;
  name: string;
  max_risk_per_trade: number;
  max_daily_loss: number;
  max_weekly_loss: number;
  max_drawdown: number;
  max_open_trades: number;
  max_symbol_exposure: number;
  max_leverage: number;
  max_consecutive_losses: number;
  emergency_stop: boolean;
  live_trading_enabled: boolean;
  status: string;
  created_at: string;
};

export type StrategyUpdateRequest = Partial<Pick<StrategyResource, "name" | "description" | "timeframe" | "status" | "parameters" | "enabled" | "performance">>;
export type StrategyCreateRequest = Pick<StrategyResource, "name" | "description" | "timeframe" | "status" | "enabled"> & {
  parameters?: Record<string, unknown>;
};

export type RiskSettingUpdateRequest = Partial<
  Pick<
    RiskSetting,
    "name" | "max_risk_per_trade" | "max_daily_loss" | "max_weekly_loss" | "max_drawdown" | "max_open_trades" | "max_symbol_exposure" | "max_leverage" | "status"
  >
  & Pick<RiskSetting, "max_consecutive_losses" | "emergency_stop" | "live_trading_enabled">
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

export type MarketTick = {
  id: number;
  symbol: string;
  exchange: string;
  tick_time: string;
  bid: number | null;
  ask: number | null;
  price: number;
  volume: number;
  spread: number;
  source: string;
};

export type MarketTickCreate = Omit<MarketTick, "id" | "spread"> & { spread?: number | null };

export type MarketTrade = {
  id: number;
  symbol: string;
  exchange: string;
  trade_id: string;
  traded_at: string;
  price: number;
  quantity: number;
  side: "buy" | "sell" | "unknown";
  source: string;
};

export type MarketTradeCreate = Omit<MarketTrade, "id">;

export type MarketOrderBook = {
  id: number;
  symbol: string;
  exchange: string;
  captured_at: string;
  bids: number[][];
  asks: number[][];
  best_bid: number | null;
  best_ask: number | null;
  spread: number;
  depth: number;
  source: string;
};

export type MarketOrderBookCreate = Pick<MarketOrderBook, "symbol" | "exchange" | "captured_at" | "bids" | "asks" | "source">;

export type MarketDataImportRequest = {
  market?: "forex" | "stock" | "crypto" | "commodity" | "index" | "indices" | "commodities" | "stocks";
  exchange?: string;
  timeframe?: string;
  candles?: MarketCandleCreate[];
  ticks?: MarketTickCreate[];
  trades?: MarketTradeCreate[];
  order_books?: MarketOrderBookCreate[];
};

export type MarketDataImportResponse = {
  status: string;
  candle_inserted: number;
  candle_updated: number;
  tick_inserted: number;
  tick_updated: number;
  trade_inserted: number;
  trade_updated: number;
  order_book_inserted: number;
  order_book_updated: number;
};

export type MarketDataValidationResponse = {
  symbol: string;
  timeframe: string;
  checked_candles: number;
  missing_candles: Array<{ symbol: string; timeframe: string; expected_at: string }>;
  issues: Array<{ symbol: string; timeframe: string | null; timestamp: string | null; severity: string; code: string; message: string }>;
  valid: boolean;
};

export type MarketDataRepairRequest = {
  symbol: string;
  timeframe?: string;
  limit?: number;
  repair_missing?: boolean;
  regenerate_signals?: boolean;
};

export type MarketDataRepairResponse = {
  status: string;
  validation_before: MarketDataValidationResponse;
  validation_after: MarketDataValidationResponse | null;
  sync_result: MarketDataResult | null;
  error?: string | null;
};

export type MarketDataStreamEvent =
  | { channel: "candles"; payload: MarketCandleCreate }
  | { channel: "ticks"; payload: MarketTickCreate }
  | { channel: "trades"; payload: MarketTradeCreate }
  | { channel: "order_books"; payload: MarketOrderBookCreate };

export type BacktestRunRequest = {
  symbol?: string;
  timeframe?: string;
  initial_balance?: number;
  lookback?: number;
  fee_rate?: number;
  slippage_rate?: number;
  spread_rate?: number;
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
  fees: number;
  slippage: number;
  spread: number;
  profit_factor: number;
  sharpe_ratio: number;
  equity_curve: Array<Record<string, unknown>>;
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

export type AIAgent = {
  id: string;
  name: "Analyst" | "News" | "Risk" | "Execution" | "Portfolio" | "Supervisor";
  status: "idle" | "processing" | "alerting";
  last_action: string;
  metrics: {
    tasks_completed: number;
    accuracy?: number;
  };
};

export async function fetchAgents(): Promise<AIAgent[]> {
  const response = await apiClient.get<AIAgent[]>("/api/ai/agents");
  return response.data;
}

export type PaperOrderRequest = {
  symbol: string;
  side?: "buy" | "sell";
  order_type?: "market";
  quantity?: number;
  signal_id?: number | null;
  ai_analysis_id?: number | null;
};

export type PaperOrder = {
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
  signal_id: number | null;
  ai_analysis_id: number | null;
  created_at: string;
  filled_at: string | null;
};

export type PaperPosition = {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  avg_entry_price: number;
  mark_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  status: string;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
};

export type PortfolioSummary = {
  total_exposure: number;
  open_positions: number;
  filled_orders: number;
  rejected_orders: number;
  cancelled_orders: number;
  unrealized_pnl: number;
  realized_pnl: number;
  closed_positions: number;
  winning_positions: number;
  losing_positions: number;
  win_rate: number;
  best_trade_pnl: number | null;
  worst_trade_pnl: number | null;
};

export type EquityCurvePoint = {
  timestamp: string;
  equity: number;
  realized_pnl: number;
};

export type EquityCurve = {
  starting_equity: number;
  points: EquityCurvePoint[];
};

export type AuditEvent = {
  id: number;
  event_type: string;
  entity_type: string;
  entity_id: number | null;
  severity: "info" | "warning" | "error";
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AuditEventFilters = {
  limit?: number;
  event_type?: string;
  severity?: "info" | "warning" | "error";
  entity_type?: string;
};

export type UserResource = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

export type UserUpdateRequest = Partial<Pick<UserResource, "full_name" | "role" | "is_active">>;

export type ApiCredentialRequest = {
  exchange: string;
  api_key: string;
  api_secret: string;
  mode: "paper" | "live";
  is_active?: boolean;
};

export type ApiCredentialResource = {
  id: number;
  exchange: string;
  api_key: string;
  mode: "paper" | "live";
  is_active: boolean;
  created_at: string;
};

export type AIModelResource = {
  id: number;
  name: string;
  symbol: string;
  timeframe: string;
  model_type: string;
  version: number;
  parent_model_id: number | null;
  model_path: string;
  metrics: Record<string, number | string>;
  feature_names: string[];
  training_params: Record<string, unknown>;
  target: string;
  deployed: boolean;
  status: string;
  created_at: string;
};

export type AIModelTrainRequest = {
  name: string;
  symbol?: string;
  timeframe?: string;
  lookback?: number;
  model_type?: "random_forest" | "xgboost" | "lightgbm" | "lstm" | "gru" | "transformer";
  training_params?: Record<string, unknown>;
};

export type AIModelRetrainRequest = {
  lookback?: number;
  training_params?: Record<string, unknown>;
};

export type AIModelPrediction = {
  model_id: number;
  symbol: string;
  direction: string;
  confidence: number;
  features: Record<string, number>;
};

export type AIModelComparison = Pick<
  AIModelResource,
  "id" | "name" | "symbol" | "timeframe" | "model_type" | "version" | "status" | "deployed" | "metrics"
> & {
  rank: number;
};

export type NotificationResource = {
  id: number;
  title: string;
  message: string;
  severity: "info" | "warning" | "error";
  is_read: boolean;
  created_at: string;
};

export type NotificationCreateRequest = Pick<NotificationResource, "title" | "message" | "severity">;

export type SystemLogResource = {
  id: number;
  level: "info" | "warning" | "error";
  source: string;
  message: string;
  context: Record<string, unknown>;
  created_at: string;
};

export type CurrentUser = {
  id: number;
  name: string;
  role: string;
  permissions: string[];
};

export type PermissionResource = {
  id: number;
  name: string;
  description: string;
  created_at: string;
};

export type RoleResource = {
  id: number;
  name: string;
  slug: string;
  description: string;
  is_system: boolean;
  permissions: PermissionResource[];
  created_at: string;
  updated_at: string;
};

export type RoleRequest = {
  name: string;
  description?: string;
  permission_ids?: number[];
};

export type NavigationChild = {
  label: string;
  href: string;
  icon: string;
  permission: string;
  badge?: string | null;
  badge_color?: string | null;
};

export type NavigationItem = {
  label: string;
  href: string;
  icon: string;
  permission: string;
  children: NavigationChild[];
};

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const response = await apiClient.get<CurrentUser>("/api/me");
  return response.data;
}

export async function fetchNavigation(): Promise<NavigationItem[]> {
  const response = await apiClient.get<NavigationItem[]>("/api/navigation");
  return response.data;
}

export async function fetchUsers(): Promise<UserResource[]> {
  const response = await apiClient.get<UserResource[]>("/api/users");
  return response.data;
}

export async function fetchRoles(): Promise<RoleResource[]> {
  const response = await apiClient.get<RoleResource[]>("/api/roles");
  return response.data;
}

export async function createRole(payload: RoleRequest): Promise<RoleResource> {
  const response = await apiClient.post<RoleResource>("/api/roles", payload);
  return response.data;
}

export async function updateRole(id: number, payload: Partial<RoleRequest>): Promise<RoleResource> {
  const response = await apiClient.put<RoleResource>(`/api/roles/${id}`, payload);
  return response.data;
}

export async function deleteRole(id: number): Promise<{ deleted: boolean }> {
  const response = await apiClient.delete<{ deleted: boolean }>(`/api/roles/${id}`);
  return response.data;
}

export async function fetchPermissions(): Promise<PermissionResource[]> {
  const response = await apiClient.get<PermissionResource[]>("/api/permissions");
  return response.data;
}

export async function assignRolesToUser(userId: number, roleIds: number[]): Promise<UserResource> {
  const response = await apiClient.post<UserResource>(`/api/users/${userId}/roles`, { role_ids: roleIds });
  return response.data;
}

export async function fetchUserPermissions(userId: number): Promise<string[]> {
  const response = await apiClient.get<string[]>(`/api/users/${userId}/permissions`);
  return response.data;
}

export async function updateUser(id: number, payload: UserUpdateRequest): Promise<UserResource> {
  const response = await apiClient.patch<UserResource>(`/api/users/${id}`, payload);
  return response.data;
}

export async function deleteUser(id: number): Promise<{ deleted: boolean }> {
  const response = await apiClient.delete<{ deleted: boolean }>(`/api/users/${id}`);
  return response.data;
}

export async function fetchApiCredentials(): Promise<ApiCredentialResource[]> {
  const response = await apiClient.get<ApiCredentialResource[]>("/api/api-credentials");
  return response.data;
}

export async function createApiCredential(payload: ApiCredentialRequest): Promise<ApiCredentialResource> {
  const response = await apiClient.post<ApiCredentialResource>("/api/api-credentials", payload);
  return response.data;
}

export async function updateApiCredential(id: number, payload: Partial<ApiCredentialRequest>): Promise<ApiCredentialResource> {
  const response = await apiClient.patch<ApiCredentialResource>(`/api/api-credentials/${id}`, payload);
  return response.data;
}

export async function deleteApiCredential(id: number): Promise<{ deleted: boolean }> {
  const response = await apiClient.delete<{ deleted: boolean }>(`/api/api-credentials/${id}`);
  return response.data;
}

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

export async function createStrategy(payload: StrategyCreateRequest): Promise<StrategyResource> {
  const response = await apiClient.post<StrategyResource>("/api/strategies", payload);
  return response.data;
}

export async function deleteStrategy(id: number): Promise<{ deleted: boolean }> {
  const response = await apiClient.delete<{ deleted: boolean }>(`/api/strategies/${id}`);
  return response.data;
}

export async function enableStrategy(id: number): Promise<StrategyResource> {
  const response = await apiClient.post<StrategyResource>(`/api/strategies/${id}/enable`);
  return response.data;
}

export async function disableStrategy(id: number): Promise<StrategyResource> {
  const response = await apiClient.post<StrategyResource>(`/api/strategies/${id}/disable`);
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

export async function importMarketData(payload: MarketDataImportRequest): Promise<MarketDataImportResponse> {
  const response = await apiClient.post<MarketDataImportResponse>("/api/market-data/import", payload);
  return response.data;
}

export async function validateMarketData(symbol = "BTCUSDT", timeframe = "15m", limit = 500): Promise<MarketDataValidationResponse> {
  const response = await apiClient.get<MarketDataValidationResponse>("/api/market-data/validate", {
    params: { symbol, timeframe, limit }
  });
  return response.data;
}

export async function repairMarketData(payload: MarketDataRepairRequest): Promise<MarketDataRepairResponse> {
  const response = await apiClient.post<MarketDataRepairResponse>("/api/market-data/repair", payload);
  return response.data;
}

export async function fetchMarketTicks(symbol = "BTCUSDT", limit = 200): Promise<MarketTick[]> {
  const response = await apiClient.get<MarketTick[]>("/api/market-data/ticks", {
    params: { symbol, limit }
  });
  return response.data;
}

export async function fetchMarketTrades(symbol = "BTCUSDT", limit = 200): Promise<MarketTrade[]> {
  const response = await apiClient.get<MarketTrade[]>("/api/market-data/trades", {
    params: { symbol, limit }
  });
  return response.data;
}

export async function fetchMarketOrderBooks(symbol = "BTCUSDT", limit = 50): Promise<MarketOrderBook[]> {
  const response = await apiClient.get<MarketOrderBook[]>("/api/market-data/order-books", {
    params: { symbol, limit }
  });
  return response.data;
}

export async function ingestMarketDataStream(event: MarketDataStreamEvent): Promise<{ status: string; channel: string; inserted: number; updated: number }> {
  const response = await apiClient.post<{ status: string; channel: string; inserted: number; updated: number }>("/api/market-data/stream", event);
  return response.data;
}

export function marketDataWebsocketUrl(channels: Array<MarketDataStreamEvent["channel"]> = ["candles", "ticks", "order_books", "trades"]): string {
  const url = new URL(API_BASE_URL.replace(/^http/, "ws") + "/api/ws/market-data");
  url.searchParams.set("channels", channels.join(","));
  const token = localStorage.getItem("trading_ai_token");
  if (token) {
    url.searchParams.set("token", token);
  }
  return url.toString();
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

export type BacktestReport = {
  run: BacktestRun;
  equity_curve: Array<Record<string, unknown>>;
  metrics: Record<string, number>;
};

export async function fetchBacktestReport(id: number): Promise<BacktestReport> {
  const response = await apiClient.get<BacktestReport>(`/api/backtests/${id}/report`);
  return response.data;
}

export type AIProviderStatus = {
  provider: string;
  openai_available: boolean;
  available_providers: string[];
};

export async function analyzeSignal(payload: AIAnalysisRequest): Promise<AIAnalysis> {
  const response = await apiClient.post<AIAnalysis>("/api/ai/analyze-signal", payload);
  return response.data;
}

export async function fetchAIProviderStatus(): Promise<AIProviderStatus> {
  const response = await apiClient.get<AIProviderStatus>("/api/ai/provider");
  return response.data;
}

export async function setAIProvider(provider: string): Promise<AIProviderStatus> {
  const response = await apiClient.patch<AIProviderStatus>("/api/ai/provider", { provider });
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

export async function fetchAIModels(): Promise<AIModelResource[]> {
  const response = await apiClient.get<AIModelResource[]>("/api/ai/models");
  return response.data;
}

export async function trainAIModel(payload: AIModelTrainRequest): Promise<AIModelResource> {
  const response = await apiClient.post<AIModelResource>("/api/ai/models/train", payload);
  return response.data;
}

export async function retrainAIModel(id: number, payload: AIModelRetrainRequest = {}): Promise<AIModelResource> {
  const response = await apiClient.post<AIModelResource>(`/api/ai/models/${id}/retrain`, payload);
  return response.data;
}

export async function deployAIModel(id: number): Promise<AIModelResource> {
  const response = await apiClient.post<AIModelResource>(`/api/ai/models/${id}/deploy`);
  return response.data;
}

export async function disableAIModel(id: number): Promise<AIModelResource> {
  const response = await apiClient.post<AIModelResource>(`/api/ai/models/${id}/disable`);
  return response.data;
}

export async function compareAIModels(modelIds: number[]): Promise<AIModelComparison[]> {
  const response = await apiClient.post<AIModelComparison[]>("/api/ai/models/compare", { model_ids: modelIds });
  return response.data;
}

export async function predictAIModel(id: number): Promise<AIModelPrediction> {
  const response = await apiClient.post<AIModelPrediction>(`/api/ai/models/${id}/predict`);
  return response.data;
}

export type OrderStatusFilter = "filled" | "rejected" | "cancelled" | "all";
export type PositionStatusFilter = "open" | "closed" | "all";

export async function fetchOrders(limit = 20, status?: OrderStatusFilter): Promise<PaperOrder[]> {
  const response = await apiClient.get<PaperOrder[]>("/api/orders", {
    params: { limit, status }
  });
  return response.data;
}

export async function createPaperOrder(payload: PaperOrderRequest): Promise<PaperOrder> {
  const response = await apiClient.post<PaperOrder>("/api/orders/paper", payload);
  return response.data;
}

export async function cancelOrder(id: number): Promise<PaperOrder> {
  const response = await apiClient.post<PaperOrder>(`/api/orders/${id}/cancel`);
  return response.data;
}

export async function fetchPositions(status: PositionStatusFilter = "open"): Promise<PaperPosition[]> {
  const response = await apiClient.get<PaperPosition[]>("/api/positions", {
    params: { status }
  });
  return response.data;
}

export async function closePosition(id: number): Promise<PaperPosition> {
  const response = await apiClient.post<PaperPosition>(`/api/positions/${id}/close`);
  return response.data;
}

export async function fetchPortfolioSummary(): Promise<PortfolioSummary> {
  const response = await apiClient.get<PortfolioSummary>("/api/portfolio/summary");
  return response.data;
}

export async function fetchEquityCurve(): Promise<EquityCurve> {
  const response = await apiClient.get<EquityCurve>("/api/portfolio/equity-curve");
  return response.data;
}

export async function fetchAuditEvents(filters: AuditEventFilters = {}): Promise<AuditEvent[]> {
  const response = await apiClient.get<AuditEvent[]>("/api/audit/events", {
    params: filters
  });
  return response.data;
}

export async function fetchNotifications(unreadOnly = false): Promise<NotificationResource[]> {
  const response = await apiClient.get<NotificationResource[]>("/api/notifications", {
    params: { unread_only: unreadOnly }
  });
  return response.data;
}

export async function createNotification(payload: NotificationCreateRequest): Promise<NotificationResource> {
  const response = await apiClient.post<NotificationResource>("/api/notifications", payload);
  return response.data;
}

export async function markNotificationRead(id: number): Promise<NotificationResource> {
  const response = await apiClient.post<NotificationResource>(`/api/notifications/${id}/read`);
  return response.data;
}

export async function fetchSystemLogs(limit = 100, level?: "info" | "warning" | "error"): Promise<SystemLogResource[]> {
  const response = await apiClient.get<SystemLogResource[]>("/api/logs", {
    params: { limit, level }
  });
  return response.data;
}
