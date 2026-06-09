from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiCredential, PaperOrder, PaperPosition
from app.services.repository import ensure_default_risk_settings

PAPER_EQUITY = 10000.0


@dataclass
class RiskDecision:
    approved: bool
    message: str


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

    if risk_settings.emergency_stop:
        return RiskDecision(False, "Blocked by emergency kill switch.")

    if execution_mode == "live":
        live_credential = db.scalar(
            select(ApiCredential).where(
                ApiCredential.mode == "live",
                ApiCredential.is_active.is_(True),
            )
        )
        if not risk_settings.live_trading_enabled:
            return RiskDecision(False, "Live trading is disabled in risk settings.")
        if live_credential is None:
            return RiskDecision(False, "Live trading requires an active live API credential.")

    open_positions = list(db.scalars(select(PaperPosition).where(PaperPosition.status == "open")).all())
    current_symbol_exposure = sum(position.quantity * position.mark_price for position in open_positions if position.symbol_id == symbol_id)

    if len(open_positions) >= risk_settings.max_open_trades:
        return RiskDecision(False, f"Blocked by risk guard: max open trades is {risk_settings.max_open_trades}.")

    if notional > PAPER_EQUITY * risk_settings.max_risk_per_trade:
        return RiskDecision(False, f"Blocked by risk guard: order exceeds {risk_settings.max_risk_per_trade * 100:.1f}% risk per trade.")

    if current_symbol_exposure + notional > PAPER_EQUITY * risk_settings.max_symbol_exposure:
        return RiskDecision(False, "Blocked by risk guard: combined symbol exposure would exceed the configured limit.")

    if daily_realized_loss(db) >= PAPER_EQUITY * risk_settings.max_daily_loss:
        return RiskDecision(False, f"Blocked by risk guard: daily loss limit is {risk_settings.max_daily_loss * 100:.1f}%.")

    if consecutive_losses(db) >= risk_settings.max_consecutive_losses:
        return RiskDecision(False, f"Blocked by risk guard: {risk_settings.max_consecutive_losses} consecutive losses reached.")

    return RiskDecision(True, f"Approved by {execution_mode} risk engine.")


def daily_realized_loss(db: Session) -> float:
    today = datetime.now(timezone.utc).date()
    closed_positions = db.scalars(select(PaperPosition).where(PaperPosition.status == "closed")).all()
    return abs(
        sum(
            position.realized_pnl
            for position in closed_positions
            if position.closed_at and position.closed_at.date() == today and position.realized_pnl < 0
        )
    )


def consecutive_losses(db: Session) -> int:
    orders = db.scalars(
        select(PaperOrder).where(PaperOrder.status == "filled").order_by(PaperOrder.created_at.desc()).limit(20)
    ).all()
    losses = 0
    for order in orders:
        if "realized PnL -" in order.risk_message:
            losses += 1
            continue
        break
    return losses
