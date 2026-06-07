from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent
from app.schemas.trading import AuditEventRead


def record_event(
    db: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: int | None = None,
    severity: str = "info",
    message: str,
    metadata: dict[str, Any] | None = None,
    commit: bool = False,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        severity=severity,
        message=message,
        event_metadata=metadata or {},
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    return event


def list_audit_events(
    db: Session,
    *,
    limit: int = 50,
    event_type: str | None = None,
    severity: str | None = None,
    entity_type: str | None = None,
) -> list[AuditEvent]:
    statement = select(AuditEvent)
    if event_type:
        statement = statement.where(AuditEvent.event_type == event_type)
    if severity:
        statement = statement.where(AuditEvent.severity == severity)
    if entity_type:
        statement = statement.where(AuditEvent.entity_type == entity_type)

    statement = statement.order_by(AuditEvent.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


def audit_event_to_schema(event: AuditEvent) -> AuditEventRead:
    return AuditEventRead(
        id=event.id,
        event_type=event.event_type,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        severity=event.severity,
        message=event.message,
        metadata=event.event_metadata,
        created_at=event.created_at,
    )
