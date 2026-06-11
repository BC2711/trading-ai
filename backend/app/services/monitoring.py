import platform
import sys
import time
from datetime import datetime, timezone
from typing import Any

import redis
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.monitoring import api_metrics_recorder
from app.models import AIAnalysisRecord, PaperOrder, User
from app.schemas.monitoring import (
    ApiLatencyMetrics,
    BrokerMonitoringResponse,
    ComponentStatus,
    ExecutionBrokerStatus,
    MonitoringHealthResponse,
    MonitoringMetricsResponse,
    QueueStatus,
    SystemMonitoringResponse,
    WebSocketStatus,
    WorkerStatus,
    WorkerStatusResponse,
)
from app.services.execution.brokers import BrokerService
from app.services.market_data.websocket import market_data_websocket
from app.websockets.manager import websocket_manager

APP_STARTED_AT = time.time()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_health(db: Session) -> MonitoringHealthResponse:
    database = database_status(db)
    redis_state = redis_status(settings.redis_url, name="redis")
    celery_worker = celery_worker_status()
    broker_connection = broker_connection_status()
    websocket = websocket_status()
    api = api_status()
    status = aggregate_status([api, database, redis_state, celery_worker, broker_connection])
    return MonitoringHealthResponse(
        status=status,
        generated_at=utc_now(),
        api=api,
        database=database,
        redis=redis_state,
        celery_worker=celery_worker,
        broker_connection=broker_connection,
        websocket=websocket,
    )


def get_metrics(db: Session) -> MonitoringMetricsResponse:
    snapshot = api_metrics_recorder.snapshot()
    filled_trade_count = db.scalar(select(func.count()).select_from(PaperOrder).where(PaperOrder.status == "filled")) or 0
    failed_trade_count = (
        db.scalar(
            select(func.count())
            .select_from(PaperOrder)
            .where(or_(PaperOrder.status == "rejected", PaperOrder.risk_status == "blocked"))
        )
        or 0
    )
    trade_count = filled_trade_count + failed_trade_count
    return MonitoringMetricsResponse(
        generated_at=utc_now(),
        api_latency=ApiLatencyMetrics(
            average_ms=snapshot.average_latency_ms,
            p95_ms=snapshot.p95_latency_ms,
            recent_request_count=snapshot.recent_request_count,
        ),
        error_rate=snapshot.error_rate,
        requests_total=snapshot.requests_total,
        errors_total=snapshot.errors_total,
        active_users=db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0,
        ai_prediction_count=db.scalar(select(func.count()).select_from(AIAnalysisRecord)) or 0,
        trade_success_rate=round(filled_trade_count / trade_count, 4) if trade_count else 0.0,
        failed_trade_count=failed_trade_count,
        websocket_connections=websocket_status().total_connections,
    )


def get_workers() -> WorkerStatusResponse:
    broker = broker_connection_status()
    worker_component, workers, queues = celery_worker_details()
    return WorkerStatusResponse(
        generated_at=utc_now(),
        broker=broker,
        celery_worker=worker_component,
        workers=workers,
        queues=queues,
        active_task_count=sum(worker.active_tasks for worker in workers),
        reserved_task_count=sum(worker.reserved_tasks for worker in workers),
        scheduled_task_count=sum(worker.scheduled_tasks for worker in workers),
    )


def get_brokers(db: Session) -> BrokerMonitoringResponse:
    broker_service = BrokerService(db)
    return BrokerMonitoringResponse(
        generated_at=utc_now(),
        broker_connection=broker_connection_status(),
        execution_brokers=[
            ExecutionBrokerStatus(
                name=broker.name,
                display_name=broker.display_name,
                status=broker.status,
                connected=broker.connected,
                api_key_configured=broker.api_key_configured,
                last_sync_at=broker.last_sync_at,
                message=broker.message,
            )
            for broker in broker_service.list_brokers()
        ],
    )


def get_system(db: Session) -> SystemMonitoringResponse:
    return SystemMonitoringResponse(
        generated_at=utc_now(),
        app_name=settings.app_name,
        environment=settings.environment,
        uptime_seconds=round(time.time() - APP_STARTED_AT, 2),
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        database=database_status(db),
        redis=redis_status(settings.redis_url, name="redis"),
        celery_worker=celery_worker_status(),
        broker_connection=broker_connection_status(),
        websocket=websocket_status(),
        metrics=get_metrics(db),
    )


def api_status() -> ComponentStatus:
    snapshot = api_metrics_recorder.snapshot()
    healthy = snapshot.error_rate < 0.1
    return ComponentStatus(
        name="api",
        status="ok" if healthy else "degraded",
        healthy=healthy,
        message="API is accepting requests." if healthy else "Recent API error rate is elevated.",
        last_checked_at=utc_now(),
        latency_ms=snapshot.average_latency_ms,
        metadata={
            "p95_latency_ms": snapshot.p95_latency_ms,
            "error_rate": snapshot.error_rate,
            "recent_request_count": snapshot.recent_request_count,
        },
    )


def database_status(db: Session) -> ComponentStatus:
    started_at = time.perf_counter()
    try:
        db.execute(text("SELECT 1")).scalar_one()
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return ComponentStatus(
            name="database",
            status="ok",
            healthy=True,
            message="Database query succeeded.",
            last_checked_at=utc_now(),
            latency_ms=latency_ms,
        )
    except Exception as exc:
        return ComponentStatus(
            name="database",
            status="offline",
            healthy=False,
            message=str(exc),
            last_checked_at=utc_now(),
        )


def redis_status(url: str, *, name: str) -> ComponentStatus:
    started_at = time.perf_counter()
    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=0.5, socket_timeout=0.5)
        client.ping()
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return ComponentStatus(
            name=name,
            status="ok",
            healthy=True,
            message="Redis ping succeeded.",
            last_checked_at=utc_now(),
            latency_ms=latency_ms,
        )
    except Exception as exc:
        return ComponentStatus(
            name=name,
            status="offline",
            healthy=False,
            message=str(exc),
            last_checked_at=utc_now(),
        )


def broker_connection_status() -> ComponentStatus:
    broker_url = settings.celery_broker_url
    if broker_url.startswith("redis://") or broker_url.startswith("rediss://"):
        return redis_status(broker_url, name="celery_broker")

    started_at = time.perf_counter()
    try:
        with celery_app.connection_for_read() as connection:
            connection.ensure_connection(max_retries=1)
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return ComponentStatus(
            name="celery_broker",
            status="ok",
            healthy=True,
            message="Celery broker connection succeeded.",
            last_checked_at=utc_now(),
            latency_ms=latency_ms,
        )
    except Exception as exc:
        return ComponentStatus(
            name="celery_broker",
            status="offline",
            healthy=False,
            message=str(exc),
            last_checked_at=utc_now(),
        )


def celery_worker_status() -> ComponentStatus:
    worker_component, _workers, _queues = celery_worker_details()
    return worker_component


def celery_worker_details() -> tuple[ComponentStatus, list[WorkerStatus], list[QueueStatus]]:
    try:
        inspector = celery_app.control.inspect(timeout=0.5)
        ping = inspector.ping() or {}
        active = inspector.active() or {}
        reserved = inspector.reserved() or {}
        scheduled = inspector.scheduled() or {}
        active_queues = inspector.active_queues() or {}
    except Exception as exc:
        component = ComponentStatus(
            name="celery_worker",
            status="offline",
            healthy=False,
            message=str(exc),
            last_checked_at=utc_now(),
        )
        return component, [], [QueueStatus(name="celery", status="unknown", message="Queue depth unavailable.")]

    workers = [
        WorkerStatus(
            name=name,
            status="online",
            active_tasks=len(active.get(name, [])),
            reserved_tasks=len(reserved.get(name, [])),
            scheduled_tasks=len(scheduled.get(name, [])),
            queues=[queue.get("name", "unknown") for queue in active_queues.get(name, [])],
        )
        for name in sorted(ping)
    ]
    queues = queue_statuses(active_queues)
    component = ComponentStatus(
        name="celery_worker",
        status="ok" if workers else "offline",
        healthy=bool(workers),
        message=f"{len(workers)} Celery worker(s) online." if workers else "No Celery workers responded.",
        last_checked_at=utc_now(),
        metadata={"worker_count": len(workers)},
    )
    return component, workers, queues


def queue_statuses(active_queues: dict[str, list[dict[str, Any]]]) -> list[QueueStatus]:
    queue_names = {
        queue.get("name", "celery")
        for queues in active_queues.values()
        for queue in queues
    } or {"celery"}

    statuses: list[QueueStatus] = []
    for queue_name in sorted(queue_names):
        depth = redis_queue_depth(settings.celery_broker_url, queue_name)
        statuses.append(
            QueueStatus(
                name=queue_name,
                depth=depth,
                status="ok" if depth is not None else "unknown",
                message=f"{depth} queued task(s)." if depth is not None else "Queue depth unavailable.",
            )
        )
    return statuses


def redis_queue_depth(url: str, queue_name: str) -> int | None:
    if not (url.startswith("redis://") or url.startswith("rediss://")):
        return None
    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=0.5, socket_timeout=0.5)
        return int(client.llen(queue_name))
    except Exception:
        return None


def websocket_status() -> WebSocketStatus:
    stream_counts = websocket_manager.connection_counts()
    market_counts = {f"market_data:{key}": value for key, value in market_data_websocket.connection_counts().items()}
    total_connections = websocket_manager.total_connections() + market_data_websocket.total_connections()
    return WebSocketStatus(
        status="ok",
        healthy=True,
        total_connections=total_connections,
        streams={**stream_counts, **market_counts},
    )


def aggregate_status(components: list[ComponentStatus]) -> str:
    required = {"api", "database"}
    if any(component.name in required and not component.healthy for component in components):
        return "unhealthy"
    if any(not component.healthy for component in components):
        return "degraded"
    return "ok"
