from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AuditEvent, PaperOrder, PaperPosition, Signal
from app.models.trading import utc_now
from app.schemas.automation import AutomatedTradeDecisionRead, AutomatedTradingRunResponse
from app.schemas.brokers import BrokerOrderCreate
from app.schemas.paper_trading import PaperTradingOrderCreate
from app.services.audit import record_event
from app.services.execution.brokers.service import BrokerService
from app.services.execution.paper import get_latest_price
from app.services.paper_trading import PaperTradingService
from app.services.repository import ensure_default_risk_settings, seed_defaults
from app.services.risk import get_current_equity


AUTOMATION_CONSUMED_EVENTS = {
    "automated_trading.order_executed",
    "automated_trading.order_rejected",
    "automated_trading.order_failed",
}


def run_automated_trading(db: Session) -> AutomatedTradingRunResponse:
    """Scan active signals and place strictly guarded automated orders."""
    execution_mode = settings.automated_trading_execution_mode
    result = AutomatedTradingRunResponse(
        enabled=settings.automated_trading_enabled,
        execution_mode=execution_mode,
        live_enabled=settings.automated_trading_live_enabled,
    )
    if not settings.automated_trading_enabled:
        return result

    seed_defaults(db)
    risk_settings = ensure_default_risk_settings(db)
    if risk_settings.emergency_stop:
        decision = _decision(None, "blocked", "Emergency stop is enabled.", execution_mode)
        result.decisions.append(decision)
        result.skipped_signals += 1
        record_event(
            db,
            event_type="automated_trading.blocked",
            entity_type="risk_setting",
            entity_id=risk_settings.id,
            severity="warning",
            message="Automated trading run blocked because emergency stop is enabled.",
            metadata={"execution_mode": execution_mode},
            commit=True,
        )
        return result

    for signal in _candidate_signals(db):
        result.checked_signals += 1
        if result.executed_orders >= settings.automated_trading_max_orders_per_run:
            break

        skip_reason = _skip_reason(db, signal)
        if skip_reason:
            result.skipped_signals += 1
            result.decisions.append(_decision(signal, "skipped", skip_reason, execution_mode))
            continue

        quantity = _order_quantity(db, signal)
        if quantity <= 0:
            result.skipped_signals += 1
            result.decisions.append(_decision(signal, "skipped", "Calculated quantity is zero.", execution_mode))
            continue

        try:
            if execution_mode == "live":
                decision = _execute_live_order(db, signal, quantity)
            else:
                decision = _execute_paper_order(db, signal, quantity)
        except Exception as exc:  # Defensive boundary: one bad signal must not stop the run.
            decision = _decision(signal, "failed", str(exc), execution_mode, quantity=quantity)
            record_event(
                db,
                event_type="automated_trading.order_failed",
                entity_type="signal",
                entity_id=signal.id,
                severity="error",
                message=f"Automated trading failed for signal {signal.id}: {exc}",
                metadata={"symbol": signal.symbol_ref.symbol, "direction": signal.direction, "execution_mode": execution_mode},
                commit=True,
            )

        if decision.status == "executed":
            result.executed_orders += 1
        else:
            result.skipped_signals += 1
        result.decisions.append(decision)

    return result


def automation_status() -> AutomatedTradingRunResponse:
    return AutomatedTradingRunResponse(
        enabled=settings.automated_trading_enabled,
        execution_mode=settings.automated_trading_execution_mode,
        live_enabled=settings.automated_trading_live_enabled,
    )


def _candidate_signals(db: Session) -> list[Signal]:
    cutoff = utc_now() - timedelta(minutes=settings.automated_trading_max_signal_age_minutes)
    statement = (
        select(Signal)
        .where(
            Signal.status == "active",
            Signal.direction.in_(["buy", "sell"]),
            Signal.confidence >= settings.automated_trading_min_confidence,
            Signal.created_at >= cutoff,
        )
        .order_by(Signal.created_at.desc())
        .limit(settings.automated_trading_max_orders_per_run * 5)
    )
    return list(db.scalars(statement).all())


def _skip_reason(db: Session, signal: Signal) -> str | None:
    if settings.automated_trading_require_strategy_enabled:
        strategy = signal.strategy_ref
        if strategy is None or not strategy.enabled or strategy.status != "active":
            return "Signal strategy is not enabled for automated trading."

    if _signal_consumed(db, signal):
        return "Signal was already consumed by automated trading."

    cooldown_start = utc_now() - timedelta(seconds=settings.automated_trading_cooldown_seconds)
    recent_order = db.scalar(
        select(PaperOrder.id)
        .where(PaperOrder.symbol_id == signal.symbol_id, PaperOrder.created_at >= cooldown_start)
        .limit(1)
    )
    if recent_order is not None:
        return "Symbol is inside the automated trading cooldown window."

    if settings.automated_trading_one_position_per_symbol:
        open_position = db.scalar(
            select(PaperPosition.id)
            .where(PaperPosition.symbol_id == signal.symbol_id, PaperPosition.status == "open")
            .limit(1)
        )
        if open_position is not None:
            return "Symbol already has an open position."

    return None


def _signal_consumed(db: Session, signal: Signal) -> bool:
    paper_order_id = db.scalar(select(PaperOrder.id).where(PaperOrder.signal_id == signal.id).limit(1))
    if paper_order_id is not None:
        return True
    audit_event_id = db.scalar(
        select(AuditEvent.id)
        .where(
            AuditEvent.entity_type == "signal",
            AuditEvent.entity_id == signal.id,
            AuditEvent.event_type.in_(AUTOMATION_CONSUMED_EVENTS),
        )
        .limit(1)
    )
    return audit_event_id is not None


def _order_quantity(db: Session, signal: Signal) -> float:
    price = get_latest_price(db, signal.symbol_ref.symbol)
    if price is None or price <= 0:
        return 0.0

    risk_settings = ensure_default_risk_settings(db)
    equity = max(get_current_equity(db), 0.0)
    max_notional = min(
        settings.automated_trading_order_notional_usd,
        equity * risk_settings.max_risk_per_trade,
        equity * risk_settings.max_symbol_exposure,
    )
    if max_notional <= 0:
        return 0.0
    return round(max_notional / price, 8)


def _execute_paper_order(db: Session, signal: Signal, quantity: float) -> AutomatedTradeDecisionRead:
    order = PaperTradingService(db).create_order(
        PaperTradingOrderCreate(
            symbol=signal.symbol_ref.symbol,
            side=signal.direction,
            order_type="market",
            quantity=quantity,
            signal_id=signal.id,
        )
    )
    status = "executed" if order.status == "filled" else "rejected"
    reason = order.risk_message if order.status == "filled" else order.failure_reason or order.risk_message
    record_event(
        db,
        event_type="automated_trading.order_executed" if status == "executed" else "automated_trading.order_rejected",
        entity_type="signal",
        entity_id=signal.id,
        severity="info" if status == "executed" else "warning",
        message=f"Automated paper order {order.status} for {signal.symbol_ref.symbol} {signal.direction.upper()}.",
        metadata={"order_id": order.id, "symbol": signal.symbol_ref.symbol, "quantity": quantity, "reason": reason},
        commit=True,
    )
    return _decision(signal, status, reason, "paper", quantity=quantity, order_id=str(order.id), created_at=order.created_at)


def _execute_live_order(db: Session, signal: Signal, quantity: float) -> AutomatedTradeDecisionRead:
    if not settings.automated_trading_live_enabled:
        return _decision(signal, "skipped", "Automated live trading is disabled.", "live", quantity=quantity)

    broker_service = BrokerService(db)
    broker_service.connect(settings.automated_trading_broker)
    order = broker_service.place_order(
        settings.automated_trading_broker,
        BrokerOrderCreate(symbol=signal.symbol_ref.symbol, side=signal.direction, order_type="market", quantity=quantity),
    )
    record_event(
        db,
        event_type="automated_trading.order_executed",
        entity_type="signal",
        entity_id=signal.id,
        severity="warning",
        message=f"Automated LIVE order submitted for {signal.symbol_ref.symbol} {signal.direction.upper()}.",
        metadata={"broker": settings.automated_trading_broker, "broker_order_id": order.id, "quantity": quantity},
        commit=True,
    )
    return _decision(signal, "executed", "Submitted live broker order.", "live", quantity=quantity, order_id=order.id, created_at=order.created_at)


def _decision(
    signal: Signal | None,
    status: str,
    reason: str,
    execution_mode: str,
    *,
    quantity: float | None = None,
    order_id: str | None = None,
    created_at=None,
) -> AutomatedTradeDecisionRead:
    return AutomatedTradeDecisionRead(
        signal_id=signal.id if signal else None,
        symbol=signal.symbol_ref.symbol if signal else None,
        direction=signal.direction if signal else None,
        status=status,
        reason=reason,
        execution_mode=execution_mode,
        quantity=quantity,
        order_id=order_id,
        created_at=created_at,
    )
