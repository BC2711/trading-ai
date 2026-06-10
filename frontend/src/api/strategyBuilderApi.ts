import { apiClient } from "../services/api";
import type { StrategyResource } from "../services/api";

export type StrategyIndicator =
  | "RSI"
  | "MACD"
  | "EMA"
  | "SMA"
  | "BOLLINGER_BANDS"
  | "ATR"
  | "VOLUME"
  | "PRICE_CHANGE";

export type StrategyOperator = "<" | "<=" | ">" | ">=" | "==" | "!=";
export type StrategyAction = "BUY" | "SELL" | "HOLD" | "CLOSE_POSITION";

export type StrategyConditionInput = {
  sequence: number;
  indicator: StrategyIndicator;
  operator: StrategyOperator;
  value?: number | null;
  period?: number | null;
  compare_indicator?: StrategyIndicator | null;
  compare_period?: number | null;
  parameters?: Record<string, unknown>;
};

export type StrategyActionInput = {
  action: StrategyAction;
  parameters?: Record<string, unknown>;
};

export type StrategyRuleInput = {
  name: string;
  logic_operator: "AND";
  priority: number;
  enabled: boolean;
  conditions: StrategyConditionInput[];
  action: StrategyActionInput;
};

export type StrategyBuilderCreate = {
  name: string;
  description: string;
  timeframe: string;
  enabled: boolean;
  rules: StrategyRuleInput[];
};

export type StrategyConditionRead = StrategyConditionInput & {
  id: number;
  created_at: string;
};

export type StrategyActionRead = StrategyActionInput & {
  id: number;
  created_at: string;
};

export type StrategyRuleRead = Omit<StrategyRuleInput, "conditions" | "action"> & {
  id: number;
  strategy_id: number;
  conditions: StrategyConditionRead[];
  actions: StrategyActionRead[];
  created_at: string;
  updated_at: string;
};

export type StrategyBuilder = {
  id: number;
  name: string;
  description: string;
  timeframe: string;
  status: string;
  enabled: boolean;
  rules: StrategyRuleRead[];
  created_at: string;
};

export type StrategyEvaluationRequest = {
  symbol: string;
  timeframe: string;
  lookback: number;
};

export type StrategyConditionEvaluation = {
  condition_id: number;
  indicator: string;
  operator: string;
  left_value: number;
  right_value: number;
  passed: boolean;
};

export type StrategyRuleEvaluation = {
  rule_id: number;
  rule_name: string;
  action: StrategyAction;
  triggered: boolean;
  conditions: StrategyConditionEvaluation[];
};

export type StrategyEvaluationResponse = {
  strategy_id: number;
  strategy_name: string;
  symbol: string;
  timeframe: string;
  action: StrategyAction;
  triggered_rule_id: number | null;
  indicators: Record<string, number>;
  evaluations: StrategyRuleEvaluation[];
  message: string;
};

export async function createStrategyBuilder(payload: StrategyBuilderCreate): Promise<StrategyBuilder> {
  const response = await apiClient.post<StrategyBuilder>("/api/strategies/builder", payload);
  return response.data;
}

export async function fetchStrategyBuilders(): Promise<StrategyBuilder[]> {
  const response = await apiClient.get<StrategyBuilder[]>("/api/strategies/builder");
  return response.data;
}

export async function fetchStrategyRules(strategyId: number): Promise<StrategyRuleRead[]> {
  const response = await apiClient.get<StrategyRuleRead[]>(`/api/strategies/${strategyId}/rules`);
  return response.data;
}

export async function updateStrategyRules(strategyId: number, rules: StrategyRuleInput[]): Promise<StrategyRuleRead[]> {
  const response = await apiClient.put<StrategyRuleRead[]>(`/api/strategies/${strategyId}/rules`, { rules });
  return response.data;
}

export async function evaluateStrategy(strategyId: number, payload: StrategyEvaluationRequest): Promise<StrategyEvaluationResponse> {
  const response = await apiClient.post<StrategyEvaluationResponse>(`/api/strategies/${strategyId}/evaluate`, payload);
  return response.data;
}

export async function activateStrategy(strategyId: number): Promise<StrategyResource> {
  const response = await apiClient.post<StrategyResource>(`/api/strategies/${strategyId}/enable`);
  return response.data;
}

export async function deactivateStrategy(strategyId: number): Promise<StrategyResource> {
  const response = await apiClient.post<StrategyResource>(`/api/strategies/${strategyId}/disable`);
  return response.data;
}
