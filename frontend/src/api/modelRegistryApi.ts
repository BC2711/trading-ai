import { apiClient } from "../services/api";
import type { AIModelPrediction, AIModelResource } from "../services/api";

export type ModelEvaluation = {
  model_id: number;
  name: string;
  symbol: string;
  timeframe: string;
  algorithm: string;
  version: number;
  status: string;
  deployed: boolean;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  profit_factor: number;
  roc_auc: number;
  samples: number;
  feature_rows: number;
  feature_count: number;
  metrics: Record<string, unknown>;
};

export type PredictionRequest = {
  symbol: string;
  timeframe?: string | null;
  model_id?: number | null;
  model_type?: string | null;
};

export async function fetchModelRegistry(): Promise<AIModelResource[]> {
  const response = await apiClient.get<AIModelResource[]>("/api/ai/models");
  return response.data;
}

export async function fetchModelDetails(modelId: number): Promise<AIModelResource> {
  const response = await apiClient.get<AIModelResource>(`/api/ai/models/${modelId}`);
  return response.data;
}

export async function activateModel(modelId: number): Promise<AIModelResource> {
  const response = await apiClient.post<AIModelResource>(`/api/ai/models/${modelId}/activate`);
  return response.data;
}

export async function fetchModelEvaluation(modelId: number): Promise<ModelEvaluation> {
  const response = await apiClient.get<ModelEvaluation>(`/api/ai/evaluation/${modelId}`);
  return response.data;
}

export async function predictWithModel(payload: PredictionRequest): Promise<AIModelPrediction> {
  const response = await apiClient.post<AIModelPrediction>("/api/ai/predict", payload);
  return response.data;
}
