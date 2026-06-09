import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import ApiCredential, PaperOrder, PaperPosition
from app.services.repository import ensure_default_risk_settings

logger = logging.getLogger(__name__)
INITIAL_PAPER_BALANCE = 10000.0
PAPER_EQUITY = INITIAL_PAPER_BALANCE


@dataclass
class RiskDecision:
    approved: bool
    message: str


def get_current_equity(db: Session) -> float:
    """Calculates current paper equity: initial balance + sum of realized PnL."""
    total_realized_pnl = db.scalar(
        select(func.sum(PaperPosition.realized_pnl))
        .where(PaperPosition.status == "closed")
    ) or 0.0
    return INITIAL_PAPER_BALANCE + float(total_realized_pnl)


def validate_trade(
    db: Session,
    *,
    symbol_id: int,
    price: float,
    quantity: float,
    execution_mode: str = "paper",
) -> RiskDecision:
    risk_settings = ensure_default_risk_settings(db)
    notional = price * quantity
    equity = get_current_equity(db)

    if risk_settings.emergency_stop:
        return _deny("Blocked by emergency kill switch.")

    if execution_mode == "live":
        if not risk_settings.live_trading_enabled:
            return _deny("Live trading is disabled in risk settings.")

        live_credential = db.scalar(
            select(ApiCredential).where(
                ApiCredential.mode == "live",
                ApiCredential.is_active.is_(True),
            )
        )
        if live_credential is None:
            return _deny("Live trading requires an active live API credential.")

    # Use a lock-safe aggregate for institutional accuracy
    stats = db.execute(
        select(
            func.count(PaperPosition.id).label("count"),
            func.sum(PaperPosition.quantity * PaperPosition.mark_price).label("exposure")
        ).where(PaperPosition.status == "open")
    ).first()

    open_trades_count = stats.count or 0
    total_portfolio_exposure = stats.exposure or 0.0


    if open_trades_count >= risk_settings.max_open_trades:
        return _deny(f"Max open trades reached ({risk_settings.max_open_trades}).")

    if notional > equity * risk_settings.max_risk_per_trade:
        return _deny(f"Order exceeds {risk_settings.max_risk_per_trade * 100:.1f}% risk per trade.")

    # Calculate relative exposure to total equity
    if (total_portfolio_exposure + notional) > (equity * risk_settings.max_symbol_exposure):
        return _deny(f"Total exposure would exceed limit of {risk_settings.max_symbol_exposure * 100:.1f}% of equity.")

    if daily_realized_loss(db) >= equity * risk_settings.max_daily_loss:
        return _deny(f"Daily loss limit reached ({risk_settings.max_daily_loss * 100:.1f}%).")

    if consecutive_losses(db) >= risk_settings.max_consecutive_losses:
        return _deny(f"Consecutive losses limit reached ({risk_settings.max_consecutive_losses}).")

    return RiskDecision(True, f"Approved by {execution_mode} risk engine.")


def _deny(message: str) -> RiskDecision:
    logger.warning(f"Risk Management Denied Trade: {message}")
    return RiskDecision(False, f"Blocked by risk guard: {message}")


def daily_realized_loss(db: Session) -> float:
    # NOTE: Using updated_at as fallback since closed_at is missing from baseline migrations
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = db.scalar(
        select(func.sum(PaperPosition.realized_pnl))
        .where(
            PaperPosition.status == "closed",
            PaperPosition.updated_at >= start_of_day,
            PaperPosition.realized_pnl < 0
        )
    )
    return abs(float(result or 0.0))


def consecutive_losses(db: Session) -> int:
    positions = db.scalars(
        select(PaperPosition)
        .where(PaperPosition.status == "closed")
        .order_by(PaperPosition.updated_at.desc())
        .limit(20)
    ).all()
    
    losses = 0
    for pos in positions:
        if pos.realized_pnl < 0:
            losses += 1
        else:
            break
    return losses
