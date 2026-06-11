from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ComponentStatus(BaseModel):
    name: str
    status: str
    healthy: bool
    message: str
    last_checked_at: datetime
    latency_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebSocketStatus(BaseModel):
    status: str
    healthy: bool
    total_connections: int
    streams: dict[str, int]


class ApiLatencyMetrics(BaseModel):
    average_ms: float
    p95_ms: float
    recent_request_count: int


class MonitoringMetricsResponse(BaseModel):
    generated_at: datetime
    api_latency: ApiLatencyMetrics
    error_rate: float
    requests_total: int
    errors_total: int
    active_users: int
    ai_prediction_count: int
    trade_success_rate: float
    failed_trade_count: int
    websocket_connections: int


class MonitoringHealthResponse(BaseModel):
    status: str
    generated_at: datetime
    api: ComponentStatus
    database: ComponentStatus
    redis: ComponentStatus
    celery_worker: ComponentStatus
    broker_connection: ComponentStatus
    websocket: WebSocketStatus


class WorkerStatus(BaseModel):
    name: str
    status: str
    active_tasks: int
    reserved_tasks: int
    scheduled_tasks: int
    queues: list[str]


class QueueStatus(BaseModel):
    name: str
    depth: int | None = None
    status: str
    message: str


class WorkerStatusResponse(BaseModel):
    generated_at: datetime
    broker: ComponentStatus
    celery_worker: ComponentStatus
    workers: list[WorkerStatus]
    queues: list[QueueStatus]
    active_task_count: int
    reserved_task_count: int
    scheduled_task_count: int


class ExecutionBrokerStatus(BaseModel):
    name: str
    display_name: str
    status: str
    connected: bool
    api_key_configured: bool
    last_sync_at: datetime | None
    message: str


class BrokerMonitoringResponse(BaseModel):
    generated_at: datetime
    broker_connection: ComponentStatus
    execution_brokers: list[ExecutionBrokerStatus]


class SystemMonitoringResponse(BaseModel):
    generated_at: datetime
    app_name: str
    environment: str
    uptime_seconds: float
    python_version: str
    platform: str
    database: ComponentStatus
    redis: ComponentStatus
    celery_worker: ComponentStatus
    broker_connection: ComponentStatus
    websocket: WebSocketStatus
    metrics: MonitoringMetricsResponse
