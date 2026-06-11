import { apiClient } from "../services/api";

export type SentimentStatus = "bullish" | "bearish" | "neutral";
export type ImpactLevel = "low" | "medium" | "high";

export type SentimentItem = {
  symbol: string;
  sentiment_score: number;
  status: SentimentStatus;
  headline: string;
  source: string;
  date: string;
  impact_level: ImpactLevel;
  related_asset: string;
};

export type SentimentResponse = {
  market_sentiment_score: number;
  market_status: SentimentStatus;
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
  items: SentimentItem[];
};

export async function fetchSentiment(): Promise<SentimentResponse> {
  const response = await apiClient.get<SentimentResponse>("/api/sentiment");
  return response.data;
}

export async function fetchSymbolSentiment(symbol: string): Promise<SentimentResponse> {
  const response = await apiClient.get<SentimentResponse>(`/api/sentiment/${symbol}`);
  return response.data;
}

export async function analyzeSentiment(symbol?: string): Promise<SentimentResponse> {
  const response = await apiClient.post<SentimentResponse>("/api/sentiment/analyze", { symbol: symbol || null });
  return response.data;
}
