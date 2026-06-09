from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIAnalysisRecord, PaperOrder, PaperPosition, Signal
from app.models.trading import utc_now
from app.schemas.trading import PaperOrderRead, PaperOrderRequest, PaperPositionRead
from app.services.audit import record_event
from app.services.risk import PAPER_EQUITY, validate_trade
from app.services.repository import ensure_default_risk_settings, get_symbol, list_candles, seed_defaults


def create_paper_order(db: Session, payload: PaperOrderRequest) -> PaperOrder:
    seed_defaults(db)
    symbol = get_symbol(db, payload.symbol)
    if symbol is None:
        raise ValueError(f"Symbol {payload.symbol.upper()} is not configured")

    latest_price = get_latest_price(db, symbol.symbol)
    if latest_price is None:
        raise ValueError(f"No market price is available for {symbol.symbol}")

    side = resolve_order_side(db, payload)
    quantity = payload.quantity or suggested_quantity(db, latest_price)
    risk = validate_trade(db, symbol_id=symbol.id, price=latest_price, quantity=quantity, execution_mode="paper")
    now = utc_now()
    order = PaperOrder(
        symbol_id=symbol.id,
        signal_id=payload.signal_id,
        ai_analysis_id=payload.ai_analysis_id,
        side=side,
        order_type=payload.order_type,
        quantity=round(quantity, 8),
        requested_price=round(latest_price, 8),
        fill_price=round(latest_price, 8) if risk.approved else None,
        status="filled" if risk.approved else "rejected",
        risk_status="approved" if risk.approved else "blocked",
        risk_message=risk.message,
        execution_mode="paper",
        failure_reason=None if risk.approved else risk.message,
        filled_at=now if risk.approved else None,
    )
    db.add(order)

    if risk.approved:
        upsert_position(db, symbol.id, side, quantity, latest_price, now)

    db.commit()
    db.refresh(order)
    record_event(
        db,
        event_type=f"paper_order.{order.status}",
        entity_type="paper_order",
        entity_id=order.id,
        severity="info" if order.status == "filled" else "warning",
        message=f"Paper order {order.status} for {symbol.symbol} {order.side.upper()}: {order.risk_message}",
        metadata={
            "symbol": symbol.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "status": order.status,
            "risk_status": order.risk_status,
        },
        commit=True,
    )
    return order


def list_paper_orders(db: Session, limit: int = 20, status: str | None = None) -> list[PaperOrder]:
    statement = select(PaperOrder)
    if status and status != "all":
        statement = statement.where(PaperOrder.status == status)
    statement = statement.order_by(PaperOrder.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


def list_paper_positions(db: Session, status: str = "open") -> list[PaperPosition]:
    statement = select(PaperPosition)
    if status != "all":
        statement = statement.where(PaperPosition.status == status)
    statement = statement.order_by(PaperPosition.created_at.desc())
    positions = list(db.scalars(statement).all())
    for position in positions:
        latest_price = get_latest_price(db, position.symbol_ref.symbol)
        if latest_price is not None and position.status == "open":
            update_mark_to_market(position, latest_price)
    db.commit()
    return positions


def cancel_paper_order(db: Session, order_id: int) -> PaperOrder | None:
    order = db.get(PaperOrder, order_id)
    if order is None:
        return None

    if order.status == "filled":
        raise ValueError("Filled paper orders cannot be cancelled")

    order.status = "cancelled"
    order.risk_message = "Paper order cancelled by operator."
    db.commit()
    db.refresh(order)
    record_event(
        db,
        event_type="paper_order.cancelled",
        entity_type="paper_order",
        entity_id=order.id,
        severity="info",
        message=f"Cancelled paper order {order.id} for {order.symbol_ref.symbol}.",
        metadata={"symbol": order.symbol_ref.symbol, "side": order.side, "status": order.status},
        commit=True,
    )
    return order


def close_paper_position(db: Session, position_id: int) -> PaperPosition | None:
    position = db.get(PaperPosition, position_id)
    if position is None:
        return None
    if position.status != "open":
        raise ValueError("Only open paper positions can be closed")

    latest_price = get_latest_price(db, position.symbol_ref.symbol)
    if latest_price is None:
        raise ValueError(f"No market price is available for {position.symbol_ref.symbol}")

    now = utc_now()
    update_mark_to_market(position, latest_price)
    position.realized_pnl = position.unrealized_pnl
    position.unrealized_pnl = 0.0
    position.status = "closed"
    position.closed_at = now
    position.updated_at = now

    close_side = "sell" if position.side == "long" else "buy"
    db.add(
        PaperOrder(
            symbol_id=position.symbol_id,
            side=close_side,
            order_type="market",
            quantity=position.quantity,
            requested_price=round(latest_price, 8),
            fill_price=round(latest_price, 8),
            status="filled",
            risk_status="approved",
            risk_message=f"Closed {position.side} paper position with realized PnL {position.realized_pnl:.2f}.",
            filled_at=now,
        )
    )
    db.commit()
    db.refresh(position)
    record_event(
        db,
        event_type="paper_position.closed",
        entity_type="paper_position",
        entity_id=position.id,
        severity="info",
        message=f"Closed {position.side} paper position for {position.symbol_ref.symbol} with realized PnL {position.realized_pnl:.2f}.",
        metadata={
            "symbol": position.symbol_ref.symbol,
            "side": position.side,
            "quantity": position.quantity,
            "realized_pnl": position.realized_pnl,
        },
        commit=True,
    )
    return position


def resolve_order_side(db: Session, payload: PaperOrderRequest) -> str:
    if payload.side:
        return payload.side

    if payload.ai_analysis_id is not None:
        analysis = db.get(AIAnalysisRecord, payload.ai_analysis_id)
        if analysis and analysis.direction in {"buy", "sell"}:
            return analysis.direction

    if payload.signal_id is not None:
        signal = db.get(Signal, payload.signal_id)
        if signal and signal.direction in {"buy", "sell"}:
            return signal.direction

    raise ValueError("Paper order side is required when the linked signal is not buy or sell")


def get_latest_price(db: Session, symbol: str) -> float | None:
    candles = list_candles(db, symbol, "15m", 1)
    return candles[-1].close if candles else None


def suggested_quantity(db: Session, price: float) -> float:
    risk_settings = ensure_default_risk_settings(db)
    notional = PAPER_EQUITY * min(risk_settings.max_symbol_exposure, risk_settings.max_risk_per_trade * 10)
    return max(0.000001, notional / price)


def upsert_position(db: Session, symbol_id: int, order_side: str, quantity: float, price: float, timestamp) -> None:
    position_side = "long" if order_side == "buy" else "short"
    position = db.scalar(
        select(PaperPosition).where(
            PaperPosition.symbol_id == symbol_id,
            PaperPosition.side == position_side,
            PaperPosition.status == "open",
        )
    )

    if position is None:
        db.add(
            PaperPosition(
                symbol_id=symbol_id,
                side=position_side,
                quantity=round(quantity, 8),
                avg_entry_price=round(price, 8),
                mark_price=round(price, 8),
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                status="open",
                updated_at=timestamp,
            )
        )
        return

    combined_quantity = position.quantity + quantity
    position.avg_entry_price = ((position.avg_entry_price * position.quantity) + (price * quantity)) / combined_quantity
    position.quantity = round(combined_quantity, 8)
    position.mark_price = round(price, 8)
    position.unrealized_pnl = 0.0
    position.updated_at = timestamp


def update_mark_to_market(position: PaperPosition, latest_price: float) -> None:
    position.mark_price = round(latest_price, 8)
    if position.side == "long":
        position.unrealized_pnl = round((latest_price - position.avg_entry_price) * position.quantity, 4)
    else:
        position.unrealized_pnl = round((position.avg_entry_price - latest_price) * position.quantity, 4)
    position.updated_at = utc_now()


def order_to_schema(order: PaperOrder) -> PaperOrderRead:
    return PaperOrderRead(
        id=order.id,
        symbol=order.symbol_ref.symbol,
        side=order.side,
        order_type=order.order_type,
        quantity=order.quantity,
        requested_price=order.requested_price,
        fill_price=order.fill_price,
        status=order.status,
        risk_status=order.risk_status,
        risk_message=order.risk_message,
        execution_mode=order.execution_mode,
        exchange_order_id=order.exchange_order_id,
        failure_reason=order.failure_reason,
        signal_id=order.signal_id,
        ai_analysis_id=order.ai_analysis_id,
        created_at=order.created_at,
        filled_at=order.filled_at,
    )


def position_to_schema(position: PaperPosition) -> PaperPositionRead:
    return PaperPositionRead(
        id=position.id,
        symbol=position.symbol_ref.symbol,
        side=position.side,
        quantity=position.quantity,
        avg_entry_price=position.avg_entry_price,
        mark_price=position.mark_price,
        unrealized_pnl=position.unrealized_pnl,
        realized_pnl=position.realized_pnl,
        status=position.status,
        created_at=position.created_at,
        updated_at=position.updated_at,
        closed_at=position.closed_at,
    )
