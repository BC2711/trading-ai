from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIAnalysisRecord, PaperOrder, PaperPosition, Signal
from app.models.trading import utc_now
from app.schemas.trading import PaperOrderRead, PaperOrderRequest, PaperPositionRead
from app.services.repository import ensure_default_risk_settings, get_symbol, list_candles, seed_defaults

PAPER_EQUITY = 10000.0


@dataclass
class RiskDecision:
    approved: bool
    message: str


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
    risk = evaluate_risk(db, symbol.id, latest_price, quantity)
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
        filled_at=now if risk.approved else None,
    )
    db.add(order)

    if risk.approved:
        upsert_position(db, symbol.id, side, quantity, latest_price, now)

    db.commit()
    db.refresh(order)
    return order


def list_paper_orders(db: Session, limit: int = 20) -> list[PaperOrder]:
    statement = select(PaperOrder).order_by(PaperOrder.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


def list_paper_positions(db: Session) -> list[PaperPosition]:
    statement = select(PaperPosition).where(PaperPosition.status == "open").order_by(PaperPosition.created_at.desc())
    positions = list(db.scalars(statement).all())
    for position in positions:
        latest_price = get_latest_price(db, position.symbol_ref.symbol)
        if latest_price is not None:
            update_mark_to_market(position, latest_price)
    db.commit()
    return positions


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


def evaluate_risk(db: Session, symbol_id: int, price: float, quantity: float) -> RiskDecision:
    risk_settings = ensure_default_risk_settings(db)
    notional = price * quantity
    open_positions = list(db.scalars(select(PaperPosition).where(PaperPosition.status == "open")).all())
    current_symbol_exposure = sum(position.quantity * position.mark_price for position in open_positions if position.symbol_id == symbol_id)

    if len(open_positions) >= risk_settings.max_open_trades:
        return RiskDecision(False, f"Blocked by risk guard: max open trades is {risk_settings.max_open_trades}.")

    if notional > PAPER_EQUITY * risk_settings.max_symbol_exposure:
        return RiskDecision(False, f"Blocked by risk guard: order exceeds {risk_settings.max_symbol_exposure * 100:.1f}% symbol exposure.")

    if current_symbol_exposure + notional > PAPER_EQUITY * risk_settings.max_symbol_exposure:
        return RiskDecision(False, "Blocked by risk guard: combined symbol exposure would exceed the configured limit.")

    return RiskDecision(True, "Approved by paper risk guard and filled at latest candle close.")


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
        status=position.status,
        created_at=position.created_at,
        updated_at=position.updated_at,
    )
