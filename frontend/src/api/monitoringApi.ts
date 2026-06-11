import { apiClient } from "../services/api";

export type ComponentStatus = {
  name: string;
  status: string;
  healthy: boolean;
  message: string;
  last_checked_at: string;
  latency_ms: number | null;
  metadata: Record<string, unknown>;
};

export type WebSocketStatus = {
  status: string;
  healthy: boolean;
  total_connections: number;
  streams: Record<string, number>;
};

export type ApiLatencyMetrics = {
  average_ms: number;
  p95_ms: number;
  recent_request_count: number;
};

export type MonitoringMetricsResponse = {
  generated_at: string;
  api_latency: ApiLatencyMetrics;
  error_rate: number;
  requests_total: number;
  errors_total: number;
  active_users: number;
  ai_prediction_count: number;
  trade_success_rate: number;
  failed_trade_count: number;
  websocket_connections: number;
};

export type MonitoringHealthResponse = {
  status: string;
  generated_at: string;
  api: ComponentStatus;
  database: ComponentStatus;
  redis: ComponentStatus;
  celery_worker: ComponentStatus;
  broker_connection: ComponentStatus;
  websocket: WebSocketStatus;
};

export type WorkerStatus = {
  name: string;
  status: string;
  active_tasks: number;
  reserved_tasks: number;
  scheduled_tasks: number;
  queues: string[];
};

export type QueueStatus = {
  name: string;
  depth: number | null;
  status: string;
  message: string;
};

export type WorkerStatusResponse = {
  generated_at: string;
  broker: ComponentStatus;
  celery_worker: ComponentStatus;
  workers: WorkerStatus[];
  queues: QueueStatus[];
  active_task_count: number;
  reserved_task_count: number;
  scheduled_task_count: number;
};

export type ExecutionBrokerStatus = {
  name: string;
  display_name: string;
  status: string;
  connected: boolean;
  api_key_configured: boolean;
  last_sync_at: string | null;
  message: string;
};

export type BrokerMonitoringResponse = {
  generated_at: string;
  broker_connection: ComponentStatus;
  execution_brokers: ExecutionBrokerStatus[];
};

export type SystemMonitoringResponse = {
  generated_at: string;
  app_name: string;
  environment: string;
  uptime_seconds: number;
  python_version: string;
  platform: string;
  database: ComponentStatus;
  redis: ComponentStatus;
  celery_worker: ComponentStatus;
  broker_connection: ComponentStatus;
  websocket: WebSocketStatus;
  metrics: MonitoringMetricsResponse;
};

export async function fetchMonitoringHealth(): Promise<MonitoringHealthResponse> {
  const response = await apiClient.get<MonitoringHealthResponse>("/api/monitoring/health");
  return response.data;
}

export async function fetchMonitoringMetrics(): Promise<MonitoringMetricsResponse> {
  const response = await apiClient.get<MonitoringMetricsResponse>("/api/monitoring/metrics");
  return response.data;
}

export async function fetchMonitoringWorkers(): Promise<WorkerStatusResponse> {
  const response = await apiClient.get<WorkerStatusResponse>("/api/monitoring/workers");
  return response.data;
}

export async function fetchMonitoringBrokers(): Promise<BrokerMonitoringResponse> {
  const response = await apiClient.get<BrokerMonitoringResponse>("/api/monitoring/brokers");
  return response.data;
}

export async function fetchMonitoringSystem(): Promise<SystemMonitoringResponse> {
  const response = await apiClient.get<SystemMonitoringResponse>("/api/monitoring/system");
  return response.data;
}
