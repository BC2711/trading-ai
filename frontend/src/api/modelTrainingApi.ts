import { apiClient } from "../services/api";
import type { AIModelResource } from "../services/api";

export const MODEL_FEATURES = [
  "close",
  "volume",
  "return_1",
  "price_change",
  "volume_change",
  "candle_body_size",
  "upper_wick_size",
  "lower_wick_size",
  "volatility_20",
  "trend_direction",
  "support_distance",
  "resistance_distance",
  "rsi_14",
  "macd",
  "macd_signal",
  "macd_histogram",
  "ema_9",
  "ema_20",
  "ema_50",
  "sma_20",
  "sma_50",
  "atr_14",
  "adx_14",
  "bb_width",
  "volume_ratio",
  "obv"
];

export type ModelAlgorithm = "random_forest" | "xgboost" | "lightgbm" | "lstm" | "transformer";

export type ModelTrainingRequest = {
  name: string;
  symbol: string;
  timeframe: string;
  lookback: number;
  model_type: ModelAlgorithm;
  selected_features: string[];
  training_params?: Record<string, unknown>;
};

export async function trainModel(payload: ModelTrainingRequest): Promise<AIModelResource> {
  const response = await apiClient.post<AIModelResource>("/api/ai/train", payload);
  return response.data;
}
