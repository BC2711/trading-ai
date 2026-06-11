from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.auth import require_permission
from app.db.deps import get_db
from app.models import User
from app.schemas.monitoring import (
    BrokerMonitoringResponse,
    MonitoringHealthResponse,
    MonitoringMetricsResponse,
    SystemMonitoringResponse,
    WorkerStatusResponse,
)
from app.services.monitoring import get_brokers, get_health, get_metrics, get_system, get_workers

router = APIRouter(tags=["monitoring"])


@router.get("/health", response_model=MonitoringHealthResponse)
def monitoring_health(db: Session = Depends(get_db)) -> MonitoringHealthResponse:
    return get_health(db)


@router.get("/metrics", response_model=MonitoringMetricsResponse)
def monitoring_metrics(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("logs:view")),
) -> MonitoringMetricsResponse:
    return get_metrics(db)


@router.get("/workers", response_model=WorkerStatusResponse)
def monitoring_workers(
    _user: User = Depends(require_permission("logs:view")),
) -> WorkerStatusResponse:
    return get_workers()


@router.get("/brokers", response_model=BrokerMonitoringResponse)
def monitoring_brokers(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("logs:view")),
) -> BrokerMonitoringResponse:
    return get_brokers(db)


@router.get("/system", response_model=SystemMonitoringResponse)
def monitoring_system(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("logs:view")),
) -> SystemMonitoringResponse:
    return get_system(db)
