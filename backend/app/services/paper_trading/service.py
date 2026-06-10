from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import PaperAccount, PaperOrder, PaperPosition, PaperTradeLedger
from app.models.trading import utc_now
from app.schemas.paper_trading import (
    PaperTradingAccountRead,
    PaperTradingLedgerRead,
    PaperTradingOrderCreate,
    PaperTradingOrderRead,
    PaperTradingPerformancePoint,
    PaperTradingPerformanceResponse,
    PaperTradingPositionRead,
    PaperTradingResetResponse,
)
from app.services.audit import record_event
from app.services.execution.paper import get_latest_price, update_mark_to_market
from app.services.paper_trading.repository import PaperTradingRepository
from app.services.repository import get_symbol, seed_defaults


DEFAULT_STARTING_BALANCE = 10000.0


class PaperTradingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PaperTradingRepository(db)

    def get_account(self) -> PaperTradingAccountRead:
        account = self.ensure_account()
        self._mark_open_positions()
        return self._account_to_schema(account)

    def create_order(self, payload: PaperTradingOrderCreate) -> PaperTradingOrderRead:
        seed_defaults(self.db)
        account = self.ensure_account()
        symbol = get_symbol(self.db, payload.symbol)
        if symbol is None:
            raise ValueError(f"Symbol {payload.symbol.upper()} is not configured")

        fill_price = get_latest_price(self.db, symbol.symbol)
        if fill_price is None:
            raise ValueError(f"No market price is available for {symbol.symbol}")

        now = utc_now()
        quantity = round(payload.quantity, 8)
        notional = quantity * fill_price
        self._mark_open_positions()
        available_balance = self._available_balance(account)

        if notional > available_balance:
            order = PaperOrder(
                symbol_id=symbol.id,
                side=payload.side,
                order_type=payload.order_type,
                quantity=quantity,
                requested_price=round(fill_price, 8),
                fill_price=None,
                status="rejected",
                risk_status="blocked",
                risk_message="Paper order exceeds available virtual balance.",
                execution_mode="paper",
                failure_reason="Insufficient paper buying power.",
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)
            self._record_ledger(
                account,
                event_type="order_rejected",
                symbol_id=symbol.id,
                order_id=order.id,
                side=payload.side,
                quantity=quantity,
                price=fill_price,
                metadata={"reason": order.failure_reason},
            )
            return self._order_to_schema(order)

        order = PaperOrder(
            symbol_id=symbol.id,
            side=payload.side,
            order_type=payload.order_type,
            quantity=quantity,
            requested_price=round(fill_price, 8),
            fill_price=round(fill_price, 8),
            status="filled",
            risk_status="approved",
            risk_message="Filled by paper trading engine. No broker execution was used.",
            execution_mode="paper",
            filled_at=now,
        )
        self.db.add(order)
        self.db.flush()
        position = self._upsert_position(symbol.id, payload.side, quantity, fill_price, now)
        self._mark_open_positions()
        account.updated_at = now
        self.db.commit()
        self.db.refresh(order)
        self.db.refresh(position)
        self._record_ledger(
            account,
            event_type="order_filled",
            symbol_id=symbol.id,
            order_id=order.id,
            position_id=position.id,
            side=payload.side,
            quantity=quantity,
            price=fill_price,
            unrealized_pnl=position.unrealized_pnl,
            metadata={"simulated_fill": True, "broker_execution": False},
        )
        record_event(
            self.db,
            event_type="paper_trading.order_filled",
            entity_type="paper_order",
            entity_id=order.id,
            message=f"Paper order filled for {symbol.symbol} {payload.side.upper()} with no broker execution.",
            metadata={"symbol": symbol.symbol, "side": payload.side, "quantity": quantity, "fill_price": fill_price},
            commit=True,
        )
        return self._order_to_schema(order)

    def list_orders(self, limit: int = 100) -> list[PaperTradingOrderRead]:
        return [self._order_to_schema(order) for order in self.repository.list_orders(limit)]

    def list_positions(self, status: str = "open") -> list[PaperTradingPositionRead]:
        self._mark_open_positions()
        return [self._position_to_schema(position) for position in self.repository.list_positions(status)]

    def close_position(self, position_id: int) -> PaperTradingPositionRead | None:
        account = self.ensure_account()
        position = self.db.get(PaperPosition, position_id)
        if position is None:
            return None
        if position.status != "open":
            raise ValueError("Only open paper positions can be closed")

        latest_price = get_latest_price(self.db, position.symbol_ref.symbol)
        if latest_price is None:
            raise ValueError(f"No market price is available for {position.symbol_ref.symbol}")

        now = utc_now()
        update_mark_to_market(position, latest_price)
        realized_pnl = position.unrealized_pnl
        position.realized_pnl = realized_pnl
        position.unrealized_pnl = 0.0
        position.status = "closed"
        position.closed_at = now
        position.updated_at = now
        account.cash_balance = round(account.cash_balance + realized_pnl, 4)
        account.realized_pnl = round(account.realized_pnl + realized_pnl, 4)
        account.updated_at = now
        close_side = "sell" if position.side == "long" else "buy"
        order = PaperOrder(
            symbol_id=position.symbol_id,
            side=close_side,
            order_type="market",
            quantity=position.quantity,
            requested_price=round(latest_price, 8),
            fill_price=round(latest_price, 8),
            status="filled",
            risk_status="approved",
            risk_message=f"Closed paper {position.side} position with realized PnL {realized_pnl:.2f}.",
            execution_mode="paper",
            filled_at=now,
        )
        self.db.add(order)
        self.db.flush()
        self.db.commit()
        self.db.refresh(order)
        self.db.refresh(position)
        self._record_ledger(
            account,
            event_type="position_closed",
            symbol_id=position.symbol_id,
            order_id=order.id,
            position_id=position.id,
            side=close_side,
            quantity=position.quantity,
            price=latest_price,
            realized_pnl=realized_pnl,
            metadata={"closed_side": position.side},
        )
        record_event(
            self.db,
            event_type="paper_trading.position_closed",
            entity_type="paper_position",
            entity_id=position.id,
            message=f"Closed paper {position.side} position for {position.symbol_ref.symbol} with realized PnL {realized_pnl:.2f}.",
            metadata={"symbol": position.symbol_ref.symbol, "realized_pnl": realized_pnl, "broker_execution": False},
            commit=True,
        )
        return self._position_to_schema(position)

    def performance(self) -> PaperTradingPerformanceResponse:
        account = self.ensure_account()
        self._mark_open_positions()
        ledger = self.repository.list_ledger()
        points = [
            PaperTradingPerformancePoint(
                timestamp=entry.created_at,
                paper_equity=entry.equity_after,
                cash_balance=entry.balance_after,
                realized_pnl=entry.realized_pnl,
                unrealized_pnl=entry.unrealized_pnl,
                event_type=entry.event_type,
            )
            for entry in ledger
        ]
        current_account = self._account_to_schema(account)
        return PaperTradingPerformanceResponse(
            starting_balance=account.starting_balance,
            current_equity=current_account.paper_equity,
            realized_pnl=current_account.realized_pnl,
            unrealized_pnl=current_account.unrealized_pnl,
            points=points,
        )

    def reset(self, starting_balance: float = DEFAULT_STARTING_BALANCE) -> PaperTradingResetResponse:
        account = self.ensure_account()
        reset_orders = len(self.repository.list_orders(100000))
        reset_positions = len(self.repository.list_positions("all"))
        reset_ledger_entries = len(self.repository.list_ledger(100000))
        self.db.execute(delete(PaperTradeLedger))
        self.db.execute(delete(PaperOrder))
        self.db.execute(delete(PaperPosition))
        now = utc_now()
        account.starting_balance = starting_balance
        account.cash_balance = starting_balance
        account.realized_pnl = 0.0
        account.status = "active"
        account.updated_at = now
        account.reset_at = now
        self.db.commit()
        self.db.refresh(account)
        self._record_ledger(
            account,
            event_type="account_reset",
            side="account",
            quantity=0.0,
            price=0.0,
            metadata={"starting_balance": starting_balance},
        )
        record_event(
            self.db,
            event_type="paper_trading.account_reset",
            entity_type="paper_account",
            entity_id=account.id,
            message="Paper trading account was reset.",
            metadata={"starting_balance": starting_balance},
            commit=True,
        )
        return PaperTradingResetResponse(
            account=self._account_to_schema(account),
            reset_orders=reset_orders,
            reset_positions=reset_positions,
            reset_ledger_entries=reset_ledger_entries,
        )

    def ensure_account(self) -> PaperAccount:
        account = self.repository.get_account()
        if account is not None:
            return account
        now = utc_now()
        account = PaperAccount(
            name="default",
            starting_balance=DEFAULT_STARTING_BALANCE,
            cash_balance=DEFAULT_STARTING_BALANCE,
            realized_pnl=0.0,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        self._record_ledger(account, event_type="account_created", side="account", metadata={"starting_balance": DEFAULT_STARTING_BALANCE})
        return account

    def _upsert_position(self, symbol_id: int, order_side: str, quantity: float, price: float, timestamp: datetime) -> PaperPosition:
        position_side = "long" if order_side == "buy" else "short"
        position = self.db.scalar(
            select(PaperPosition).where(
                PaperPosition.symbol_id == symbol_id,
                PaperPosition.side == position_side,
                PaperPosition.status == "open",
            )
        )
        if position is None:
            position = PaperPosition(
                symbol_id=symbol_id,
                side=position_side,
                quantity=round(quantity, 8),
                avg_entry_price=round(price, 8),
                mark_price=round(price, 8),
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                status="open",
                created_at=timestamp,
                updated_at=timestamp,
            )
            self.db.add(position)
            self.db.flush()
            return position

        combined_quantity = position.quantity + quantity
        position.avg_entry_price = round(((position.avg_entry_price * position.quantity) + (price * quantity)) / combined_quantity, 8)
        position.quantity = round(combined_quantity, 8)
        position.mark_price = round(price, 8)
        position.updated_at = timestamp
        return position

    def _mark_open_positions(self) -> None:
        changed = False
        for position in self.repository.list_positions("open"):
            latest_price = get_latest_price(self.db, position.symbol_ref.symbol)
            if latest_price is not None:
                update_mark_to_market(position, latest_price)
                changed = True
        if changed:
            self.db.commit()

    def _account_to_schema(self, account: PaperAccount) -> PaperTradingAccountRead:
        open_positions = self.repository.list_positions("open")
        margin_used = sum(abs(position.quantity * position.mark_price) for position in open_positions)
        unrealized_pnl = sum(position.unrealized_pnl for position in open_positions)
        paper_equity = account.cash_balance + unrealized_pnl
        margin_available = max(0.0, paper_equity - margin_used)
        return PaperTradingAccountRead(
            id=account.id,
            name=account.name,
            starting_balance=round(account.starting_balance, 4),
            cash_balance=round(account.cash_balance, 4),
            available_balance=round(margin_available, 4),
            paper_equity=round(paper_equity, 4),
            margin_used=round(margin_used, 4),
            margin_available=round(margin_available, 4),
            realized_pnl=round(account.realized_pnl, 4),
            unrealized_pnl=round(unrealized_pnl, 4),
            total_pnl=round(account.realized_pnl + unrealized_pnl, 4),
            open_positions=len(open_positions),
            status=account.status,
            updated_at=account.updated_at,
        )

    def _available_balance(self, account: PaperAccount) -> float:
        return self._account_to_schema(account).available_balance

    def _record_ledger(
        self,
        account: PaperAccount,
        *,
        event_type: str,
        symbol_id: int | None = None,
        order_id: int | None = None,
        position_id: int | None = None,
        side: str = "account",
        quantity: float = 0.0,
        price: float = 0.0,
        realized_pnl: float = 0.0,
        unrealized_pnl: float | None = None,
        metadata: dict | None = None,
    ) -> PaperTradeLedger:
        current = self._account_to_schema(account)
        entry = PaperTradeLedger(
            account_id=account.id,
            order_id=order_id,
            position_id=position_id,
            symbol_id=symbol_id,
            event_type=event_type,
            side=side,
            quantity=round(quantity, 8),
            price=round(price, 8),
            realized_pnl=round(realized_pnl, 4),
            unrealized_pnl=round(current.unrealized_pnl if unrealized_pnl is None else unrealized_pnl, 4),
            balance_after=current.cash_balance,
            equity_after=current.paper_equity,
            event_metadata=metadata or {},
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def _order_to_schema(self, order: PaperOrder) -> PaperTradingOrderRead:
        return PaperTradingOrderRead(
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
            failure_reason=order.failure_reason,
            created_at=order.created_at,
            filled_at=order.filled_at,
        )

    def _position_to_schema(self, position: PaperPosition) -> PaperTradingPositionRead:
        return PaperTradingPositionRead(
            id=position.id,
            symbol=position.symbol_ref.symbol,
            side=position.side,
            quantity=position.quantity,
            avg_entry_price=position.avg_entry_price,
            mark_price=position.mark_price,
            notional_value=round(abs(position.quantity * position.mark_price), 4),
            unrealized_pnl=position.unrealized_pnl,
            realized_pnl=position.realized_pnl,
            status=position.status,
            created_at=position.created_at,
            updated_at=position.updated_at,
            closed_at=position.closed_at,
        )

    def ledger_to_schema(self, entry: PaperTradeLedger) -> PaperTradingLedgerRead:
        return PaperTradingLedgerRead(
            id=entry.id,
            event_type=entry.event_type,
            symbol=entry.symbol_ref.symbol if entry.symbol_ref else None,
            side=entry.side,
            quantity=entry.quantity,
            price=entry.price,
            realized_pnl=entry.realized_pnl,
            unrealized_pnl=entry.unrealized_pnl,
            balance_after=entry.balance_after,
            equity_after=entry.equity_after,
            metadata=entry.event_metadata,
            created_at=entry.created_at,
        )
