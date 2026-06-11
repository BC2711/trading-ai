import { apiClient } from "../services/api";

export type CopilotInsightCard = {
  title: string;
  value: string;
  detail: string;
  tone: "info" | "success" | "warning" | "error" | string;
};

export type CopilotMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  cards: CopilotInsightCard[];
  suggested_questions: string[];
  created_at: string;
};

export type CopilotChatResponse = {
  user_message: CopilotMessage;
  assistant_message: CopilotMessage;
};

export async function fetchCopilotHistory(): Promise<CopilotMessage[]> {
  const response = await apiClient.get<CopilotMessage[]>("/api/copilot/history");
  return response.data;
}

export async function sendCopilotMessage(message: string): Promise<CopilotChatResponse> {
  const response = await apiClient.post<CopilotChatResponse>("/api/copilot/chat", { message });
  return response.data;
}
