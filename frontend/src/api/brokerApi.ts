import { apiClient } from "../services/api";

export type BrokerStatus = {
  name: string;
  display_name: string;
  status: string;
  connected: boolean;
  api_key_configured: boolean;
  last_sync_at: string | null;
  message: string;
};

export type BrokerConnectionResponse = {
  broker: BrokerStatus;
};

export type BrokerBalanceItem = {
  asset: string;
  free: number;
  locked: number;
  total: number;
};

export type BrokerBalanceResponse = {
  broker: string;
  balances: BrokerBalanceItem[];
  last_sync_at: string;
};

export type BrokerPosition = {
  id: string;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number | null;
  mark_price: number | null;
  unrealized_pnl: number;
};

export type BrokerOrderRequest = {
  symbol: string;
  side: "buy" | "sell";
  order_type?: "market" | "limit";
  quantity: number;
  price?: number | null;
};

export type BrokerOrder = {
  id: string;
  symbol: string;
  side: string;
  order_type: string;
  quantity: number;
  price: number | null;
  status: string;
  created_at: string | null;
};

export async function fetchBrokers(): Promise<BrokerStatus[]> {
  const response = await apiClient.get<BrokerStatus[]>("/api/brokers");
  return response.data;
}

export async function connectBroker(broker: string): Promise<BrokerConnectionResponse> {
  const response = await apiClient.post<BrokerConnectionResponse>("/api/brokers/connect", { broker });
  return response.data;
}

export async function disconnectBroker(broker: string): Promise<BrokerConnectionResponse> {
  const response = await apiClient.post<BrokerConnectionResponse>("/api/brokers/disconnect", { broker });
  return response.data;
}

export async function fetchBrokerBalance(broker: string): Promise<BrokerBalanceResponse> {
  const response = await apiClient.get<BrokerBalanceResponse>(`/api/brokers/${broker}/balance`);
  return response.data;
}

export async function fetchBrokerPositions(broker: string): Promise<{ broker: string; positions: BrokerPosition[]; last_sync_at: string }> {
  const response = await apiClient.get<{ broker: string; positions: BrokerPosition[]; last_sync_at: string }>(`/api/brokers/${broker}/positions`);
  return response.data;
}

export async function placeBrokerOrder(broker: string, payload: BrokerOrderRequest): Promise<BrokerOrder> {
  const response = await apiClient.post<BrokerOrder>(`/api/brokers/${broker}/orders`, payload);
  return response.data;
}

export async function cancelBrokerOrder(broker: string, orderId: string): Promise<{ broker: string; order_id: string; cancelled: boolean; message: string }> {
  const response = await apiClient.delete<{ broker: string; order_id: string; cancelled: boolean; message: string }>(`/api/brokers/${broker}/orders/${orderId}`);
  return response.data;
}
