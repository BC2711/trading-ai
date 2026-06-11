from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candle, PortfolioSnapshot, Prediction, Signal, Tick, WarehouseTrade
from app.schemas.trading import (
    BacktestResultCreate,
    MarketCandleCreate,
    MarketDataImportRequest,
    MarketDataImportResponse,
    MarketDataSyncRequest,
    MarketDataSyncResponse,
    MarketDataSyncResult,
    MarketHistoryResponse,
    ModelMetricCreate,
    PortfolioSnapshotCreate,
    PortfolioSnapshotRead,
    PredictionCreate,
    PredictionRead,
    SignalRead,
    WarehouseCandleRead,
    WarehouseTickRead,
    WarehouseTradeCreate,
    WarehouseTradeRead,
)
from app.services.market_data.binance import fetch_binance_klines
from app.services.market_data.repository import MarketDataRepository, calculate_spread, normalize_market
from app.services.repository import get_symbol
from app.schemas.scanner import ScannerRead


class MarketWarehouseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MarketDataRepository(db)

    def import_candles(self, payload: MarketDataImportRequest) -> MarketDataImportResponse:
        market = normalize_market(payload.market)
        candle_inserted, candle_updated = self.repository.upsert_candles(
            payload.candles,
            market=market,
            exchange=payload.exchange,
        )
        tick_inserted, tick_updated = self.repository.upsert_ticks(payload.ticks, market=market)
        trade_inserted, trade_updated = self.repository.upsert_trades(payload.trades, market=market)
        order_book_inserted, order_book_updated = self.repository.upsert_order_books(payload.order_books, market=market)

        self._upsert_warehouse_candles(payload.candles, market=market, exchange=payload.exchange, source="import")
        self._upsert_warehouse_ticks(payload.ticks, market=market)
        self.db.commit()

        return MarketDataImportResponse(
            status="ok",
            candle_inserted=candle_inserted,
            candle_updated=candle_updated,
            tick_inserted=tick_inserted,
            tick_updated=tick_updated,
            trade_inserted=trade_inserted,
            trade_updated=trade_updated,
            order_book_inserted=order_book_inserted,
            order_book_updated=order_book_updated,
        )

    def sync_historical_data(self, payload: MarketDataSyncRequest) -> MarketDataSyncResponse:
        results: list[MarketDataSyncResult] = []
        for symbol in payload.symbols:
            normalized_symbol = symbol.upper()
            candles = fetch_binance_klines(normalized_symbol, payload.timeframe, payload.limit)
            inserted, updated = self.repository.upsert_candles(candles, market="crypto", exchange="binance")
            self._upsert_warehouse_candles(candles, market="crypto", exchange="binance", source="sync")
            results.append(
                MarketDataSyncResult(
                    symbol=normalized_symbol,
                    timeframe=payload.timeframe,
                    fetched=len(candles),
                    inserted=inserted,
                    updated=updated,
                )
            )

        self.db.commit()
        return MarketDataSyncResponse(provider="binance", timeframe=payload.timeframe, results=results, signals=[])

    def store_scanner_signal(self, scanner_signal: ScannerRead, *, strategy_id: int | None = None) -> Signal:
        symbol = self.repository.ensure_symbol(scanner_signal.symbol)
        signal = Signal(
            symbol_id=symbol.id,
            strategy_id=strategy_id,
            direction=scanner_signal.signal,
            confidence=scanner_signal.confidence,
            timeframe="scanner",
            reason=scanner_signal.recommended_action,
            status="active",
            created_at=scanner_signal.created_at,
        )
        self.db.add(signal)
        self.db.commit()
        self.db.refresh(signal)
        return signal

    def store_ai_prediction(self, payload: PredictionCreate) -> PredictionRead:
        symbol = self.repository.ensure_symbol(payload.symbol)
        prediction = Prediction(
            symbol_id=symbol.id,
            model_id=payload.model_id,
            signal_id=payload.signal_id,
            timeframe=payload.timeframe,
            prediction_time=payload.prediction_time or datetime.now(timezone.utc),
            target=payload.target,
            horizon=payload.horizon,
            direction=payload.direction,
            confidence=payload.confidence,
            predicted_value=payload.predicted_value,
            features=payload.features,
            prediction_metadata=payload.metadata,
        )
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction_to_schema(prediction)

    def store_trade(self, payload: WarehouseTradeCreate) -> WarehouseTradeRead:
        symbol = self.repository.ensure_symbol(payload.symbol)
        trade = WarehouseTrade(
            symbol_id=symbol.id,
            signal_id=payload.signal_id,
            prediction_id=payload.prediction_id,
            order_id=payload.order_id,
            exchange=payload.exchange.lower(),
            external_trade_id=payload.external_trade_id,
            side=payload.side,
            quantity=payload.quantity,
            price=payload.price,
            fee=payload.fee,
            realized_pnl=payload.realized_pnl,
            status=payload.status,
            source=payload.source,
            executed_at=payload.executed_at or datetime.now(timezone.utc),
            trade_metadata=payload.metadata,
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade_to_schema(trade)

    def store_backtest_result(self, payload: BacktestResultCreate) -> None:
        from app.models import BacktestResult

        symbol = self.repository.ensure_symbol(payload.symbol)
        self.db.add(
            BacktestResult(
                symbol_id=symbol.id,
                strategy_id=payload.strategy_id,
                model_id=payload.model_id,
                run_id=payload.run_id,
                timeframe=payload.timeframe,
                started_at=payload.started_at,
                ended_at=payload.ended_at,
                initial_balance=payload.initial_balance,
                final_balance=payload.final_balance,
                total_return=payload.total_return,
                win_rate=payload.win_rate,
                max_drawdown=payload.max_drawdown,
                sharpe_ratio=payload.sharpe_ratio,
                profit_factor=payload.profit_factor,
                trades_count=payload.trades_count,
                metrics=payload.metrics,
                equity_curve=payload.equity_curve,
                parameters=payload.parameters,
            )
        )
        self.db.commit()

    def store_model_metric(self, payload: ModelMetricCreate) -> None:
        from app.models import ModelMetric

        symbol_id = self.repository.ensure_symbol(payload.symbol).id if payload.symbol else None
        self.db.add(
            ModelMetric(
                model_id=payload.model_id,
                symbol_id=symbol_id,
                model_name=payload.model_name,
                model_type=payload.model_type,
                timeframe=payload.timeframe,
                dataset=payload.dataset,
                metric_name=payload.metric_name,
                metric_value=payload.metric_value,
                metrics=payload.metrics,
                training_window_start=payload.training_window_start,
                training_window_end=payload.training_window_end,
                evaluated_at=payload.evaluated_at or datetime.now(timezone.utc),
            )
        )
        self.db.commit()

    def store_portfolio_snapshot(self, payload: PortfolioSnapshotCreate) -> PortfolioSnapshotRead:
        snapshot = PortfolioSnapshot(
            account_id=payload.account_id,
            captured_at=payload.captured_at or datetime.now(timezone.utc),
            total_equity=payload.total_equity,
            cash_balance=payload.cash_balance,
            margin_used=payload.margin_used,
            total_exposure=payload.total_exposure,
            realized_pnl=payload.realized_pnl,
            unrealized_pnl=payload.unrealized_pnl,
            positions=payload.positions,
            allocation=payload.allocation,
            metrics=payload.metrics,
            source=payload.source,
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return portfolio_snapshot_to_schema(snapshot)

    def retrieve_market_history(
        self,
        symbol: str,
        *,
        timeframe: str = "15m",
        limit: int = 500,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> MarketHistoryResponse:
        normalized_symbol = symbol.upper()
        symbol_model = get_symbol(self.db, normalized_symbol)
        if symbol_model is None:
            return MarketHistoryResponse(symbol=normalized_symbol, timeframe=timeframe)

        candles = self._history_query(Candle, symbol_model.id, Candle.opened_at, timeframe, limit, start, end)
        ticks = self._history_query(Tick, symbol_model.id, Tick.tick_time, None, limit, start, end)
        signals = self._history_query(Signal, symbol_model.id, Signal.created_at, timeframe, limit, start, end)
        predictions = self._history_query(Prediction, symbol_model.id, Prediction.prediction_time, timeframe, limit, start, end)
        trades = self._history_query(WarehouseTrade, symbol_model.id, WarehouseTrade.executed_at, None, limit, start, end)
        snapshots = self._portfolio_snapshots(limit, start, end)

        return MarketHistoryResponse(
            symbol=normalized_symbol,
            timeframe=timeframe,
            candles=[candle_to_schema(candle) for candle in candles],
            ticks=[tick_to_schema(tick) for tick in ticks],
            signals=[signal_to_schema(signal) for signal in signals],
            predictions=[prediction_to_schema(prediction) for prediction in predictions],
            trades=[trade_to_schema(trade) for trade in trades],
            portfolio_snapshots=[portfolio_snapshot_to_schema(snapshot) for snapshot in snapshots],
        )

    def _upsert_warehouse_candles(
        self,
        candles: list[MarketCandleCreate],
        *,
        market: str,
        exchange: str,
        source: str,
    ) -> tuple[int, int]:
        inserted = 0
        updated = 0
        for candle in candles:
            symbol = self.repository.ensure_symbol(candle.symbol, market=market, exchange=exchange)
            existing = self.db.scalar(
                select(Candle).where(
                    Candle.symbol_id == symbol.id,
                    Candle.timeframe == candle.timeframe,
                    Candle.opened_at == candle.opened_at,
                )
            )
            if existing:
                existing.open = candle.open
                existing.high = candle.high
                existing.low = candle.low
                existing.close = candle.close
                existing.volume = candle.volume
                existing.spread = candle.spread
                existing.source = source
                updated += 1
            else:
                self.db.add(
                    Candle(
                        symbol_id=symbol.id,
                        timeframe=candle.timeframe,
                        opened_at=candle.opened_at,
                        open=candle.open,
                        high=candle.high,
                        low=candle.low,
                        close=candle.close,
                        volume=candle.volume,
                        spread=candle.spread,
                        source=source,
                    )
                )
                inserted += 1
        return inserted, updated

    def _upsert_warehouse_ticks(self, ticks, *, market: str) -> tuple[int, int]:
        inserted = 0
        updated = 0
        for tick in ticks:
            symbol = self.repository.ensure_symbol(tick.symbol, market=market, exchange=tick.exchange)
            spread = tick.spread if tick.spread is not None else calculate_spread(tick.bid, tick.ask)
            existing = self.db.scalar(
                select(Tick).where(
                    Tick.symbol_id == symbol.id,
                    Tick.exchange == tick.exchange.lower(),
                    Tick.tick_time == tick.tick_time,
                )
            )
            if existing:
                existing.bid = tick.bid
                existing.ask = tick.ask
                existing.price = tick.price
                existing.volume = tick.volume
                existing.spread = spread
                existing.source = tick.source
                updated += 1
            else:
                self.db.add(
                    Tick(
                        symbol_id=symbol.id,
                        exchange=tick.exchange.lower(),
                        tick_time=tick.tick_time,
                        bid=tick.bid,
                        ask=tick.ask,
                        price=tick.price,
                        volume=tick.volume,
                        spread=spread,
                        source=tick.source,
                    )
                )
                inserted += 1
        return inserted, updated

    def _history_query(self, model, symbol_id: int, timestamp_column, timeframe: str | None, limit: int, start: datetime | None, end: datetime | None):
        statement = select(model).where(model.symbol_id == symbol_id)
        if timeframe and hasattr(model, "timeframe"):
            statement = statement.where(model.timeframe == timeframe)
        if start:
            statement = statement.where(timestamp_column >= start)
        if end:
            statement = statement.where(timestamp_column <= end)
        statement = statement.order_by(timestamp_column.desc()).limit(limit)
        return list(reversed(self.db.scalars(statement).all()))

    def _portfolio_snapshots(self, limit: int, start: datetime | None, end: datetime | None) -> list[PortfolioSnapshot]:
        statement = select(PortfolioSnapshot)
        if start:
            statement = statement.where(PortfolioSnapshot.captured_at >= start)
        if end:
            statement = statement.where(PortfolioSnapshot.captured_at <= end)
        statement = statement.order_by(PortfolioSnapshot.captured_at.desc()).limit(limit)
        return list(reversed(self.db.scalars(statement).all()))


def candle_to_schema(candle: Candle) -> WarehouseCandleRead:
    return WarehouseCandleRead(
        id=candle.id,
        symbol=candle.symbol_ref.symbol,
        timeframe=candle.timeframe,
        opened_at=candle.opened_at,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
        spread=candle.spread,
        source=candle.source,
        created_at=candle.created_at,
    )


def tick_to_schema(tick: Tick) -> WarehouseTickRead:
    return WarehouseTickRead(
        id=tick.id,
        symbol=tick.symbol_ref.symbol,
        exchange=tick.exchange,
        tick_time=tick.tick_time,
        bid=tick.bid,
        ask=tick.ask,
        price=tick.price,
        volume=tick.volume,
        spread=tick.spread,
        source=tick.source,
        created_at=tick.created_at,
    )


def signal_to_schema(signal: Signal) -> SignalRead:
    return SignalRead(
        id=signal.id,
        symbol=signal.symbol_ref.symbol,
        direction=signal.direction,
        confidence=signal.confidence,
        timeframe=signal.timeframe,
        reason=signal.reason,
        status=signal.status,
        created_at=signal.created_at,
    )


def prediction_to_schema(prediction: Prediction) -> PredictionRead:
    return PredictionRead(
        id=prediction.id,
        symbol=prediction.symbol_ref.symbol,
        model_id=prediction.model_id,
        signal_id=prediction.signal_id,
        timeframe=prediction.timeframe,
        prediction_time=prediction.prediction_time,
        target=prediction.target,
        horizon=prediction.horizon,
        direction=prediction.direction,
        confidence=prediction.confidence,
        predicted_value=prediction.predicted_value,
        features=prediction.features,
        metadata=prediction.prediction_metadata,
        created_at=prediction.created_at,
    )


def trade_to_schema(trade: WarehouseTrade) -> WarehouseTradeRead:
    return WarehouseTradeRead(
        id=trade.id,
        symbol=trade.symbol_ref.symbol,
        signal_id=trade.signal_id,
        prediction_id=trade.prediction_id,
        order_id=trade.order_id,
        exchange=trade.exchange,
        external_trade_id=trade.external_trade_id,
        side=trade.side,
        quantity=trade.quantity,
        price=trade.price,
        fee=trade.fee,
        realized_pnl=trade.realized_pnl,
        status=trade.status,
        source=trade.source,
        executed_at=trade.executed_at,
        metadata=trade.trade_metadata,
        created_at=trade.created_at,
    )


def portfolio_snapshot_to_schema(snapshot: PortfolioSnapshot) -> PortfolioSnapshotRead:
    return PortfolioSnapshotRead(
        id=snapshot.id,
        account_id=snapshot.account_id,
        captured_at=snapshot.captured_at,
        total_equity=snapshot.total_equity,
        cash_balance=snapshot.cash_balance,
        margin_used=snapshot.margin_used,
        total_exposure=snapshot.total_exposure,
        realized_pnl=snapshot.realized_pnl,
        unrealized_pnl=snapshot.unrealized_pnl,
        positions=snapshot.positions,
        allocation=snapshot.allocation,
        metrics=snapshot.metrics,
        source=snapshot.source,
        created_at=snapshot.created_at,
    )
