from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import PaperOrder, PaperPosition
from app.schemas.portfolio import (
    EquityCurvePoint,
    EquityCurveResponse,
    OpenPositionAllocationItem,
    PortfolioAllocationItem,
    PortfolioAllocationResponse,
    PortfolioExposureItem,
    PortfolioExposureResponse,
    PortfolioPerformancePoint,
    PortfolioPerformanceResponse,
    PortfolioPnlResponse,
    PortfolioSummaryResponse,
)
from app.services.execution.paper import PAPER_EQUITY, get_latest_price, update_mark_to_market
from app.services.portfolio.repository import PortfolioRepository


@dataclass
class PortfolioState:
    orders: list[PaperOrder]
    positions: list[PaperPosition]
    open_positions: list[PaperPosition]
    closed_positions: list[PaperPosition]
    realized_values: list[float]
    total_realized_pnl: float
    total_unrealized_pnl: float
    total_exposure: float
    total_equity: float


class PortfolioService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PortfolioRepository(db)

    def summary(self) -> PortfolioSummaryResponse:
        state = self._state()
        pnl = self.pnl(state)
        exposure = self.exposure(state)
        allocation = self.allocation(state)
        winning_positions = [pnl_value for pnl_value in state.realized_values if pnl_value > 0]
        losing_positions = [pnl_value for pnl_value in state.realized_values if pnl_value < 0]
        margin_used = state.total_exposure
        margin_available = max(0.0, state.total_equity - margin_used)

        return PortfolioSummaryResponse(
            total_equity=round(state.total_equity, 4),
            available_balance=round(margin_available, 4),
            margin_used=round(margin_used, 4),
            margin_available=round(margin_available, 4),
            total_realized_pnl=pnl.total_realized_pnl,
            total_unrealized_pnl=pnl.total_unrealized_pnl,
            realized_pnl=pnl.total_realized_pnl,
            unrealized_pnl=pnl.total_unrealized_pnl,
            daily_pnl=pnl.daily_pnl,
            weekly_pnl=pnl.weekly_pnl,
            monthly_pnl=pnl.monthly_pnl,
            total_exposure=round(state.total_exposure, 4),
            open_positions=len(state.open_positions),
            filled_orders=sum(1 for order in state.orders if order.status == "filled"),
            rejected_orders=sum(1 for order in state.orders if order.status == "rejected"),
            cancelled_orders=sum(1 for order in state.orders if order.status == "cancelled"),
            closed_positions=len(state.closed_positions),
            winning_positions=len(winning_positions),
            losing_positions=len(losing_positions),
            win_rate=round(len(winning_positions) / len(state.closed_positions), 6) if state.closed_positions else 0.0,
            best_trade_pnl=round(max(state.realized_values), 4) if state.realized_values else None,
            worst_trade_pnl=round(min(state.realized_values), 4) if state.realized_values else None,
            exposure_by_symbol=exposure.items,
            allocation_by_asset=allocation.by_asset,
            open_position_allocation=allocation.open_positions,
        )

    def performance(self, state: PortfolioState | None = None) -> PortfolioPerformanceResponse:
        state = state or self._state()
        closed_positions = self.repository.list_closed_positions()
        running_realized = 0.0
        points: list[PortfolioPerformancePoint] = []

        for position in closed_positions:
            running_realized += position.realized_pnl
            timestamp = position.closed_at or position.updated_at
            points.append(
                PortfolioPerformancePoint(
                    timestamp=timestamp,
                    equity=round(PAPER_EQUITY + running_realized, 4),
                    realized_pnl=round(running_realized, 4),
                    unrealized_pnl=0.0,
                    total_pnl=round(running_realized, 4),
                    event=f"closed {position.symbol_ref.symbol} {position.side}",
                )
            )

        if state.open_positions:
            points.append(
                PortfolioPerformancePoint(
                    timestamp=datetime.now(timezone.utc),
                    equity=round(state.total_equity, 4),
                    realized_pnl=round(state.total_realized_pnl, 4),
                    unrealized_pnl=round(state.total_unrealized_pnl, 4),
                    total_pnl=round(state.total_realized_pnl + state.total_unrealized_pnl, 4),
                    event="current open positions",
                )
            )

        return PortfolioPerformanceResponse(starting_equity=PAPER_EQUITY, points=points)

    def exposure(self, state: PortfolioState | None = None) -> PortfolioExposureResponse:
        state = state or self._state()
        by_symbol: dict[str, dict[str, float | set[str]]] = {}

        for position in state.open_positions:
            symbol = position.symbol_ref.symbol
            notional = abs(position.quantity * position.mark_price)
            current = by_symbol.setdefault(
                symbol,
                {"notional": 0.0, "quantity": 0.0, "unrealized_pnl": 0.0, "mark_price": position.mark_price, "sides": set()},
            )
            current["notional"] = float(current["notional"]) + notional
            current["quantity"] = float(current["quantity"]) + position.quantity
            current["unrealized_pnl"] = float(current["unrealized_pnl"]) + position.unrealized_pnl
            current["mark_price"] = position.mark_price
            sides = current["sides"]
            if isinstance(sides, set):
                sides.add(position.side)

        items = []
        for symbol, values in sorted(by_symbol.items()):
            sides = values["sides"]
            side = next(iter(sides)) if isinstance(sides, set) and len(sides) == 1 else "mixed"
            notional_value = float(values["notional"])
            items.append(
                PortfolioExposureItem(
                    symbol=symbol,
                    side=side,
                    quantity=round(float(values["quantity"]), 8),
                    mark_price=round(float(values["mark_price"]), 8),
                    notional_value=round(notional_value, 4),
                    exposure_pct=round(notional_value / state.total_equity, 6) if state.total_equity else 0.0,
                    unrealized_pnl=round(float(values["unrealized_pnl"]), 4),
                )
            )

        return PortfolioExposureResponse(
            total_exposure=round(state.total_exposure, 4),
            total_equity=round(state.total_equity, 4),
            items=items,
        )

    def allocation(self, state: PortfolioState | None = None) -> PortfolioAllocationResponse:
        state = state or self._state()
        by_asset: dict[str, float] = {}
        open_allocations: list[OpenPositionAllocationItem] = []

        for position in state.open_positions:
            value = abs(position.quantity * position.mark_price)
            asset = position.symbol_ref.base_asset or position.symbol_ref.symbol
            by_asset[asset] = by_asset.get(asset, 0.0) + value
            open_allocations.append(
                OpenPositionAllocationItem(
                    id=position.id,
                    symbol=position.symbol_ref.symbol,
                    side=position.side,
                    quantity=round(position.quantity, 8),
                    value=round(value, 4),
                    percentage=round(value / state.total_exposure, 6) if state.total_exposure else 0.0,
                    unrealized_pnl=round(position.unrealized_pnl, 4),
                )
            )

        allocations = [
            PortfolioAllocationItem(
                asset=asset,
                value=round(value, 4),
                percentage=round(value / state.total_exposure, 6) if state.total_exposure else 0.0,
            )
            for asset, value in sorted(by_asset.items())
        ]

        return PortfolioAllocationResponse(
            total_value=round(state.total_exposure, 4),
            by_asset=allocations,
            open_positions=open_allocations,
        )

    def pnl(self, state: PortfolioState | None = None) -> PortfolioPnlResponse:
        state = state or self._state()
        now = datetime.now(timezone.utc)
        daily = self._period_realized_pnl(state.closed_positions, now - timedelta(days=1)) + state.total_unrealized_pnl
        weekly = self._period_realized_pnl(state.closed_positions, now - timedelta(days=7)) + state.total_unrealized_pnl
        monthly = self._period_realized_pnl(state.closed_positions, now - timedelta(days=30)) + state.total_unrealized_pnl
        winning_positions = [pnl_value for pnl_value in state.realized_values if pnl_value > 0]

        return PortfolioPnlResponse(
            total_realized_pnl=round(state.total_realized_pnl, 4),
            total_unrealized_pnl=round(state.total_unrealized_pnl, 4),
            total_pnl=round(state.total_realized_pnl + state.total_unrealized_pnl, 4),
            daily_pnl=round(daily, 4),
            weekly_pnl=round(weekly, 4),
            monthly_pnl=round(monthly, 4),
            win_rate=round(len(winning_positions) / len(state.closed_positions), 6) if state.closed_positions else 0.0,
            best_trade_pnl=round(max(state.realized_values), 4) if state.realized_values else None,
            worst_trade_pnl=round(min(state.realized_values), 4) if state.realized_values else None,
        )

    def equity_curve(self) -> EquityCurveResponse:
        running_pnl = 0.0
        points: list[EquityCurvePoint] = []

        for position in self.repository.list_closed_positions():
            running_pnl += position.realized_pnl
            points.append(
                EquityCurvePoint(
                    timestamp=position.closed_at or position.updated_at,
                    equity=round(PAPER_EQUITY + running_pnl, 4),
                    realized_pnl=round(running_pnl, 4),
                )
            )

        return EquityCurveResponse(starting_equity=PAPER_EQUITY, points=points)

    def _state(self) -> PortfolioState:
        positions = self.repository.list_positions()
        orders = self.repository.list_orders()

        for position in positions:
            latest_price = get_latest_price(self.db, position.symbol_ref.symbol)
            if latest_price is not None and position.status == "open":
                update_mark_to_market(position, latest_price)
        self.db.commit()

        open_positions = [position for position in positions if position.status == "open"]
        closed_positions = [position for position in positions if position.status == "closed"]
        realized_values = [position.realized_pnl for position in closed_positions]
        total_realized_pnl = sum(realized_values)
        total_unrealized_pnl = sum(position.unrealized_pnl for position in open_positions)
        total_exposure = sum(abs(position.quantity * position.mark_price) for position in open_positions)
        total_equity = PAPER_EQUITY + total_realized_pnl + total_unrealized_pnl

        return PortfolioState(
            orders=orders,
            positions=positions,
            open_positions=open_positions,
            closed_positions=closed_positions,
            realized_values=realized_values,
            total_realized_pnl=total_realized_pnl,
            total_unrealized_pnl=total_unrealized_pnl,
            total_exposure=total_exposure,
            total_equity=total_equity,
        )

    def _period_realized_pnl(self, positions: list[PaperPosition], since: datetime) -> float:
        return sum(position.realized_pnl for position in positions if self._closed_after(position, since))

    def _closed_after(self, position: PaperPosition, since: datetime) -> bool:
        closed_at = position.closed_at or position.updated_at
        if closed_at.tzinfo is None:
            closed_at = closed_at.replace(tzinfo=timezone.utc)
        return closed_at >= since


def get_portfolio_summary(db: Session) -> PortfolioSummaryResponse:
    return PortfolioService(db).summary()


def get_portfolio_performance(db: Session) -> PortfolioPerformanceResponse:
    return PortfolioService(db).performance()


def get_portfolio_exposure(db: Session) -> PortfolioExposureResponse:
    return PortfolioService(db).exposure()


def get_portfolio_allocation(db: Session) -> PortfolioAllocationResponse:
    return PortfolioService(db).allocation()


def get_portfolio_pnl(db: Session) -> PortfolioPnlResponse:
    return PortfolioService(db).pnl()


def get_equity_curve(db: Session) -> EquityCurveResponse:
    return PortfolioService(db).equity_curve()
