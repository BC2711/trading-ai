from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PaperOrder, PaperPosition
from app.schemas.trading import EquityCurvePoint, EquityCurveResponse, PortfolioSummaryResponse
from app.services.execution.paper import PAPER_EQUITY, get_latest_price, update_mark_to_market


def get_portfolio_summary(db: Session) -> PortfolioSummaryResponse:
    positions = list(db.scalars(select(PaperPosition)).all())
    orders = list(db.scalars(select(PaperOrder)).all())

    for position in positions:
        latest_price = get_latest_price(db, position.symbol_ref.symbol)
        if latest_price is not None and position.status == "open":
            update_mark_to_market(position, latest_price)
    db.commit()

    open_positions = [position for position in positions if position.status == "open"]
    closed_positions = [position for position in positions if position.status == "closed"]
    realized_values = [position.realized_pnl for position in closed_positions]
    winning_positions = [pnl for pnl in realized_values if pnl > 0]
    losing_positions = [pnl for pnl in realized_values if pnl < 0]

    return PortfolioSummaryResponse(
        total_exposure=round(sum(position.quantity * position.mark_price for position in open_positions), 4),
        open_positions=len(open_positions),
        filled_orders=sum(1 for order in orders if order.status == "filled"),
        rejected_orders=sum(1 for order in orders if order.status == "rejected"),
        cancelled_orders=sum(1 for order in orders if order.status == "cancelled"),
        unrealized_pnl=round(sum(position.unrealized_pnl for position in open_positions), 4),
        realized_pnl=round(sum(realized_values), 4),
        closed_positions=len(closed_positions),
        winning_positions=len(winning_positions),
        losing_positions=len(losing_positions),
        win_rate=round(len(winning_positions) / len(closed_positions), 6) if closed_positions else 0.0,
        best_trade_pnl=round(max(realized_values), 4) if realized_values else None,
        worst_trade_pnl=round(min(realized_values), 4) if realized_values else None,
    )


def get_equity_curve(db: Session) -> EquityCurveResponse:
    closed_positions = list(
        db.scalars(
            select(PaperPosition)
            .where(PaperPosition.status == "closed", PaperPosition.closed_at.is_not(None))
            .order_by(PaperPosition.closed_at)
        ).all()
    )
    running_pnl = 0.0
    points: list[EquityCurvePoint] = []

    for position in closed_positions:
        running_pnl += position.realized_pnl
        points.append(
            EquityCurvePoint(
                timestamp=position.closed_at,
                equity=round(PAPER_EQUITY + running_pnl, 4),
                realized_pnl=round(running_pnl, 4),
            )
        )

    return EquityCurveResponse(starting_equity=PAPER_EQUITY, points=points)
