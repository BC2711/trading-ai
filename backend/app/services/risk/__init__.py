import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ApiCredential, PaperOrder, PaperPosition, RiskSetting
from app.schemas.risk import (
    PositionSizeRequest,
    PositionSizeResponse,
    RiskLimitsRead,
    RiskLimitsUpdate,
    RiskRejectedTradeRead,
    RiskSummaryResponse,
    RiskTradeValidationRequest,
    RiskTradeValidationResponse,
)
from app.services.repository import ensure_default_risk_settings, get_symbol

logger = logging.getLogger(__name__)
INITIAL_PAPER_BALANCE = 10000.0
PAPER_EQUITY = INITIAL_PAPER_BALANCE


@dataclass
class RiskDecision:
    approved: bool
    message: str
    risk_score: float = 0.0
    warnings: list[str] | None = None


def get_current_equity(db: Session) -> float:
    realized = db.scalar(select(func.sum(PaperPosition.realized_pnl)).where(PaperPosition.status == "closed")) or 0.0
    unrealized = db.scalar(select(func.sum(PaperPosition.unrealized_pnl)).where(PaperPosition.status == "open")) or 0.0
    return INITIAL_PAPER_BALANCE + float(realized) + float(unrealized)


def validate_trade(
    db: Session,
    *,
    symbol_id: int,
    side: str = "buy",
    price: float,
    quantity: float,
    execution_mode: str = "paper",
    reduce_only: bool = False,
) -> RiskDecision:
    symbol = db.get(get_symbol_model(), symbol_id)
    payload = RiskTradeValidationRequest(
        symbol=symbol.symbol if symbol else "UNKNOWN",
        side=side,
        price=price,
        quantity=quantity,
        execution_mode=execution_mode,
        reduce_only=reduce_only,
    )
    result = validate_trade_request(db, payload, symbol_id=symbol_id)
    return RiskDecision(result.approved, result.message, result.risk_score, result.warnings)


def get_symbol_model():
    from app.models import Symbol

    return Symbol


def validate_trade_request(
    db: Session,
    payload: RiskTradeValidationRequest,
    symbol_id: int | None = None,
) -> RiskTradeValidationResponse:
    settings = ensure_default_risk_settings(db)
    symbol = get_symbol(db, payload.symbol) if symbol_id is None else db.get(get_symbol_model(), symbol_id)
    if symbol is None:
        return _validation(False, "Symbol is not configured.", 100.0, payload, 0.0, 0.0, 0.0, 0.0, ["Unknown symbol."])

    equity = get_current_equity(db)
    notional = payload.price * payload.quantity
    risk_amount = 0.0 if payload.reduce_only else _trade_risk_amount(payload)
    risk_pct = risk_amount / equity if equity else 1.0
    warnings = stop_loss_take_profit_warnings(payload)

    daily_loss = daily_realized_loss(db)
    weekly_loss = realized_loss_since(db, datetime.now(timezone.utc) - timedelta(days=7))
    drawdown = max_drawdown(db)
    open_trades = open_trade_count(db)
    symbol_exposure = exposure_for_symbol(db, symbol.id)
    total_exposure = total_open_exposure(db)
    exposure_delta = -notional if payload.reduce_only else notional
    projected_symbol_exposure = max(0.0, symbol_exposure + exposure_delta)
    projected_total_exposure = max(0.0, total_exposure + exposure_delta)
    projected_symbol_exposure_pct = projected_symbol_exposure / equity if equity else 1.0
    projected_leverage = projected_total_exposure / equity if equity else payload.leverage

    if settings.emergency_stop:
        return _validation(False, "Emergency stop is enabled.", 100.0, payload, notional, risk_amount, risk_pct, projected_symbol_exposure_pct, projected_leverage, warnings)

    if payload.execution_mode == "live":
        live_credential = db.scalar(select(ApiCredential).where(ApiCredential.mode == "live", ApiCredential.is_active.is_(True)))
        if not settings.live_trading_enabled or live_credential is None:
            return _validation(False, "Live trading is disabled or no active live credential exists.", 100.0, payload, notional, risk_amount, risk_pct, projected_symbol_exposure_pct, projected_leverage, warnings)

    denials = []
    if not payload.reduce_only and open_trades >= settings.max_open_trades:
        denials.append(f"Max open trades reached ({settings.max_open_trades}).")
    if not payload.reduce_only and risk_pct > settings.max_risk_per_trade:
        denials.append(f"Trade risk exceeds {settings.max_risk_per_trade * 100:.1f}% per-trade limit.")
    if not payload.reduce_only and projected_symbol_exposure_pct > settings.max_symbol_exposure:
        denials.append(f"Symbol exposure would exceed {settings.max_symbol_exposure * 100:.1f}% limit.")
    if daily_loss >= equity * settings.max_daily_loss:
        denials.append(f"Daily loss limit reached ({settings.max_daily_loss * 100:.1f}%).")
    if weekly_loss >= equity * settings.max_weekly_loss:
        denials.append(f"Weekly loss limit reached ({settings.max_weekly_loss * 100:.1f}%).")
    if drawdown >= settings.max_drawdown:
        denials.append(f"Max drawdown limit reached ({settings.max_drawdown * 100:.1f}%).")
    if payload.leverage > settings.max_leverage or projected_leverage > settings.max_leverage:
        denials.append(f"Leverage exceeds {settings.max_leverage:.2f}x limit.")
    if warnings:
        denials.extend([warning for warning in warnings if "invalid" in warning.lower()])

    score = risk_score(
        daily_loss_usage=_usage(daily_loss, equity * settings.max_daily_loss),
        weekly_loss_usage=_usage(weekly_loss, equity * settings.max_weekly_loss),
        drawdown_usage=_usage(drawdown, settings.max_drawdown),
        exposure_usage=_usage(projected_symbol_exposure_pct, settings.max_symbol_exposure),
        leverage_usage=_usage(projected_leverage, settings.max_leverage),
    )

    if denials:
        return _validation(False, " ".join(denials), max(score, 85.0), payload, notional, risk_amount, risk_pct, projected_symbol_exposure_pct, projected_leverage, warnings)

    return _validation(True, "Approved by advanced risk engine.", score, payload, notional, risk_amount, risk_pct, projected_symbol_exposure_pct, projected_leverage, warnings)


def position_size(db: Session, payload: PositionSizeRequest) -> PositionSizeResponse:
    equity = payload.account_equity or get_current_equity(db)
    warnings: list[str] = []
    risk_budget = equity * payload.risk_percent

    if payload.method == "fixed_amount":
        amount = payload.fixed_amount or risk_budget
        quantity = amount / payload.entry_price
        risk_amount = amount
    elif payload.method == "fixed_percentage_risk":
        stop_distance = _stop_distance(payload.entry_price, payload.stop_loss, warnings)
        quantity = risk_budget / stop_distance if stop_distance else 0.0
        risk_amount = risk_budget
    elif payload.method == "atr_based":
        atr = payload.atr or 0.0
        if atr <= 0:
            warnings.append("ATR is required for ATR-based sizing.")
            quantity = 0.0
        else:
            quantity = risk_budget / (atr * 2)
        risk_amount = risk_budget
    elif payload.method == "volatility_based":
        volatility = payload.volatility or 0.0
        if volatility <= 0:
            warnings.append("Volatility is required for volatility-based sizing.")
            quantity = 0.0
        else:
            quantity = risk_budget / (payload.entry_price * volatility)
        risk_amount = risk_budget
    else:
        warnings.append("Kelly Criterion sizing is a placeholder; using half fixed-percentage risk.")
        stop_distance = _stop_distance(payload.entry_price, payload.stop_loss, warnings)
        quantity = (risk_budget * 0.5) / stop_distance if stop_distance else 0.0
        risk_amount = risk_budget * 0.5

    notional = quantity * payload.entry_price
    limits = ensure_default_risk_settings(db)
    if notional / equity > limits.max_symbol_exposure:
        warnings.append("Calculated size exceeds max symbol exposure.")
    if payload.leverage > limits.max_leverage:
        warnings.append("Requested leverage exceeds max leverage.")

    return PositionSizeResponse(
        symbol=payload.symbol.upper(),
        method=payload.method,
        quantity=round(max(0.0, quantity), 8),
        notional_value=round(max(0.0, notional), 4),
        risk_amount=round(max(0.0, risk_amount), 4),
        risk_pct=round((risk_amount / equity) if equity else 0.0, 6),
        warnings=warnings,
    )


def risk_summary(db: Session) -> RiskSummaryResponse:
    settings = ensure_default_risk_settings(db)
    equity = get_current_equity(db)
    daily_loss = daily_realized_loss(db)
    weekly_loss = realized_loss_since(db, datetime.now(timezone.utc) - timedelta(days=7))
    drawdown = max_drawdown(db)
    exposure = total_open_exposure(db)
    leverage = exposure / equity if equity else 0.0
    daily_usage = _usage(daily_loss, equity * settings.max_daily_loss)
    weekly_usage = _usage(weekly_loss, equity * settings.max_weekly_loss)
    drawdown_usage = _usage(drawdown, settings.max_drawdown)
    exposure_usage = _usage(exposure / equity if equity else 0.0, settings.max_symbol_exposure)
    leverage_usage = _usage(leverage, settings.max_leverage)
    warnings = risk_warnings(settings, daily_usage, weekly_usage, drawdown_usage, exposure_usage, leverage_usage)

    return RiskSummaryResponse(
        risk_score=risk_score(daily_usage, weekly_usage, drawdown_usage, exposure_usage, leverage_usage),
        equity=round(equity, 4),
        daily_loss=round(daily_loss, 4),
        weekly_loss=round(weekly_loss, 4),
        daily_loss_usage=round(daily_usage, 6),
        weekly_loss_usage=round(weekly_usage, 6),
        drawdown=round(drawdown, 6),
        drawdown_usage=round(drawdown_usage, 6),
        total_exposure=round(exposure, 4),
        exposure_usage=round(exposure_usage, 6),
        max_loss_limit=round(equity * settings.max_daily_loss, 4),
        max_weekly_loss_limit=round(equity * settings.max_weekly_loss, 4),
        max_drawdown_limit=settings.max_drawdown,
        open_trades=open_trade_count(db),
        max_open_trades=settings.max_open_trades,
        leverage=round(leverage, 6),
        max_leverage=settings.max_leverage,
        circuit_breaker_enabled=settings.emergency_stop,
        recent_rejected_trades=recent_rejected_trades(db),
        warnings=warnings,
    )


def get_limits(db: Session) -> RiskLimitsRead:
    return limits_to_schema(ensure_default_risk_settings(db))


def update_limits(db: Session, payload: RiskLimitsUpdate) -> RiskLimitsRead:
    settings = ensure_default_risk_settings(db)
    changes = payload.model_dump(exclude_unset=True)
    if "max_exposure_per_symbol" in changes:
        changes["max_symbol_exposure"] = changes.pop("max_exposure_per_symbol")
    for field, value in changes.items():
        if value is not None:
            setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return limits_to_schema(settings)


def set_circuit_breaker(db: Session, enabled: bool) -> RiskLimitsRead:
    settings = ensure_default_risk_settings(db)
    settings.emergency_stop = enabled
    db.commit()
    db.refresh(settings)
    return limits_to_schema(settings)


def limits_to_schema(settings: RiskSetting) -> RiskLimitsRead:
    return RiskLimitsRead(
        id=settings.id,
        max_risk_per_trade=settings.max_risk_per_trade,
        max_daily_loss=settings.max_daily_loss,
        max_weekly_loss=settings.max_weekly_loss,
        max_drawdown=settings.max_drawdown,
        max_open_trades=settings.max_open_trades,
        max_exposure_per_symbol=settings.max_symbol_exposure,
        max_leverage=settings.max_leverage,
        max_consecutive_losses=settings.max_consecutive_losses,
        circuit_breaker_enabled=settings.emergency_stop,
        live_trading_enabled=settings.live_trading_enabled,
    )


def stop_loss_take_profit_warnings(payload: RiskTradeValidationRequest) -> list[str]:
    warnings = []
    if payload.stop_loss is None:
        warnings.append("Stop loss is missing.")
    elif payload.side == "buy" and payload.stop_loss >= payload.price:
        warnings.append("Invalid stop loss for buy trade.")
    elif payload.side == "sell" and payload.stop_loss <= payload.price:
        warnings.append("Invalid stop loss for sell trade.")

    if payload.take_profit is None:
        warnings.append("Take profit is missing.")
    elif payload.side == "buy" and payload.take_profit <= payload.price:
        warnings.append("Invalid take profit for buy trade.")
    elif payload.side == "sell" and payload.take_profit >= payload.price:
        warnings.append("Invalid take profit for sell trade.")
    return warnings


def _validation(
    approved: bool,
    message: str,
    score: float,
    payload: RiskTradeValidationRequest,
    notional: float,
    risk_amount: float,
    risk_pct: float,
    projected_symbol_exposure_pct: float,
    projected_leverage: float,
    warnings: list[str],
) -> RiskTradeValidationResponse:
    if not approved:
        logger.warning("Risk Management Denied Trade: %s", message)
    return RiskTradeValidationResponse(
        approved=approved,
        message=message,
        risk_score=round(score, 4),
        notional_value=round(notional, 4),
        risk_amount=round(risk_amount, 4),
        risk_pct=round(risk_pct, 6),
        projected_symbol_exposure_pct=round(projected_symbol_exposure_pct, 6),
        projected_leverage=round(projected_leverage, 6),
        warnings=warnings,
    )


def _trade_risk_amount(payload: RiskTradeValidationRequest) -> float:
    if payload.stop_loss is None:
        return payload.price * payload.quantity
    return abs(payload.price - payload.stop_loss) * payload.quantity


def _stop_distance(entry_price: float, stop_loss: float | None, warnings: list[str]) -> float:
    if stop_loss is None:
        warnings.append("Stop loss is required for this sizing method.")
        return 0.0
    return abs(entry_price - stop_loss)


def _usage(value: float, limit: float) -> float:
    if limit <= 0:
        return 1.0
    return max(0.0, min(1.5, value / limit))


def risk_score(
    daily_loss_usage: float,
    weekly_loss_usage: float,
    drawdown_usage: float,
    exposure_usage: float,
    leverage_usage: float,
) -> float:
    weighted = (
        daily_loss_usage * 25
        + weekly_loss_usage * 20
        + drawdown_usage * 25
        + exposure_usage * 20
        + leverage_usage * 10
    )
    return round(min(100.0, weighted), 4)


def risk_warnings(settings: RiskSetting, daily_usage: float, weekly_usage: float, drawdown_usage: float, exposure_usage: float, leverage_usage: float) -> list[str]:
    warnings = []
    if settings.emergency_stop:
        warnings.append("Emergency stop is enabled.")
    if daily_usage >= 0.8:
        warnings.append("Daily loss usage is elevated.")
    if weekly_usage >= 0.8:
        warnings.append("Weekly loss usage is elevated.")
    if drawdown_usage >= 0.8:
        warnings.append("Drawdown is near the maximum limit.")
    if exposure_usage >= 0.8:
        warnings.append("Portfolio exposure is near the configured limit.")
    if leverage_usage >= 0.8:
        warnings.append("Leverage usage is elevated.")
    return warnings


def daily_realized_loss(db: Session) -> float:
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return realized_loss_since(db, start_of_day)


def realized_loss_since(db: Session, since: datetime) -> float:
    result = db.scalar(
        select(func.sum(PaperPosition.realized_pnl)).where(
            PaperPosition.status == "closed",
            PaperPosition.updated_at >= since,
            PaperPosition.realized_pnl < 0,
        )
    )
    return abs(float(result or 0.0))


def max_drawdown(db: Session) -> float:
    positions = list(
        db.scalars(
            select(PaperPosition)
            .where(PaperPosition.status == "closed")
            .order_by(PaperPosition.closed_at.nulls_last(), PaperPosition.updated_at)
        ).all()
    )
    equity = INITIAL_PAPER_BALANCE
    peak = equity
    max_dd = 0.0
    for position in positions:
        equity += position.realized_pnl
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)
    return max_dd


def open_trade_count(db: Session) -> int:
    return int(db.scalar(select(func.count(PaperPosition.id)).where(PaperPosition.status == "open")) or 0)


def exposure_for_symbol(db: Session, symbol_id: int) -> float:
    return float(
        db.scalar(
            select(func.sum(PaperPosition.quantity * PaperPosition.mark_price)).where(
                PaperPosition.status == "open",
                PaperPosition.symbol_id == symbol_id,
            )
        )
        or 0.0
    )


def total_open_exposure(db: Session) -> float:
    return float(db.scalar(select(func.sum(PaperPosition.quantity * PaperPosition.mark_price)).where(PaperPosition.status == "open")) or 0.0)


def recent_rejected_trades(db: Session) -> list[RiskRejectedTradeRead]:
    orders = list(
        db.scalars(
            select(PaperOrder)
            .where((PaperOrder.status == "rejected") | (PaperOrder.risk_status == "blocked"))
            .order_by(PaperOrder.created_at.desc())
            .limit(8)
        ).all()
    )
    return [
        RiskRejectedTradeRead(
            id=order.id,
            symbol=order.symbol_ref.symbol,
            side=order.side,
            quantity=order.quantity,
            risk_message=order.risk_message,
            created_at=order.created_at.isoformat(),
        )
        for order in orders
    ]


def consecutive_losses(db: Session) -> int:
    positions = db.scalars(
        select(PaperPosition)
        .where(PaperPosition.status == "closed")
        .order_by(PaperPosition.updated_at.desc())
        .limit(20)
    ).all()
    losses = 0
    for position in positions:
        if position.realized_pnl < 0:
            losses += 1
        else:
            break
    return losses
