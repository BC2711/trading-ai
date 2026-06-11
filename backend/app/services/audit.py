from typing import Any
from datetime import datetime

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


def record_compliance_event(
    db: Session,
    *,
    action: str,
    module: str,
    status: str,
    message: str,
    user_id: int | None = None,
    user_email: str | None = None,
    user_name: str | None = None,
    ip_address: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    severity: str | None = None,
    details: dict[str, Any] | None = None,
    commit: bool = False,
) -> AuditEvent:
    normalized_status = status.lower()
    event_severity = severity or ("error" if normalized_status in {"failed", "rejected"} else "info")
    metadata = {
        "action": action,
        "module": module,
        "status": normalized_status,
        "user_id": user_id,
        "user": user_email or user_name or "anonymous",
        "user_name": user_name,
        "ip_address": ip_address,
        "details": details or {},
    }
    return record_event(
        db,
        event_type=action,
        entity_type=entity_type or module,
        entity_id=entity_id,
        severity=event_severity,
        message=message,
        metadata={key: value for key, value in metadata.items() if value is not None},
        commit=commit,
    )


def list_audit_events(
    db: Session,
    *,
    limit: int = 50,
    event_type: str | None = None,
    severity: str | None = None,
    entity_type: str | None = None,
    module: str | None = None,
    action_type: str | None = None,
    status: str | None = None,
    user: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[AuditEvent]:
    statement = select(AuditEvent)
    if event_type or action_type:
        statement = statement.where(AuditEvent.event_type == (event_type or action_type))
    if severity:
        statement = statement.where(AuditEvent.severity == severity)
    if entity_type:
        statement = statement.where(AuditEvent.entity_type == entity_type)
    if start_date:
        statement = statement.where(AuditEvent.created_at >= start_date)
    if end_date:
        statement = statement.where(AuditEvent.created_at <= end_date)

    fetch_limit = max(limit, 500) if any([module, status, user]) else limit
    statement = statement.order_by(AuditEvent.created_at.desc()).limit(fetch_limit)
    events = list(db.scalars(statement).all())

    if module:
        events = [
            event
            for event in events
            if str(event.event_metadata.get("module", event.entity_type)).lower() == module.lower()
        ]
    if status:
        events = [event for event in events if str(event.event_metadata.get("status", "")).lower() == status.lower()]
    if user:
        user_query = user.lower()
        events = [
            event
            for event in events
            if user_query in str(event.event_metadata.get("user", "")).lower()
            or user_query in str(event.event_metadata.get("user_name", "")).lower()
            or user_query == str(event.event_metadata.get("user_id", "")).lower()
        ]

    return events[:limit]


def audit_event_to_schema(event: AuditEvent) -> AuditEventRead:
    metadata = event.event_metadata or {}
    details = metadata.get("details")
    return AuditEventRead(
        id=event.id,
        event_type=event.event_type,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        severity=event.severity,
        message=event.message,
        metadata=metadata,
        action=str(metadata.get("action") or event.event_type),
        user=metadata.get("user"),
        module=str(metadata.get("module") or event.entity_type),
        ip_address=metadata.get("ip_address"),
        status=str(metadata.get("status") or event.severity),
        details=details if isinstance(details, dict) else {},
        created_at=event.created_at,
    )
