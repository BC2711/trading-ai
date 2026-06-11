from datetime import datetime, timezone

from sqlalchemy import Boolean, JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    base_asset: Mapped[str] = mapped_column(String(16))
    quote_asset: Mapped[str] = mapped_column(String(16))
    market: Mapped[str] = mapped_column(String(24), default="crypto")
    exchange: Mapped[str] = mapped_column(String(32), default="binance_testnet")
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    candles: Mapped[list["MarketCandle"]] = relationship(back_populates="symbol_ref")
    ticks: Mapped[list["MarketTick"]] = relationship(back_populates="symbol_ref")
    order_books: Mapped[list["MarketOrderBookSnapshot"]] = relationship(back_populates="symbol_ref")
    trades: Mapped[list["MarketTrade"]] = relationship(back_populates="symbol_ref")
    signals: Mapped[list["Signal"]] = relationship(back_populates="symbol_ref")
    orders: Mapped[list["PaperOrder"]] = relationship(back_populates="symbol_ref")
    positions: Mapped[list["PaperPosition"]] = relationship(back_populates="symbol_ref")
    market_features: Mapped[list["MarketFeature"]] = relationship(back_populates="symbol_ref")
    feature_logs: Mapped[list["FeatureCalculationLog"]] = relationship(back_populates="symbol_ref")


class MarketCandle(Base):
    __tablename__ = "market_candles"
    __table_args__ = (
        UniqueConstraint("symbol_id", "timeframe", "opened_at", name="uq_market_candle_symbol_timeframe_opened"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    spread: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="candles")


class MarketTick(Base):
    __tablename__ = "market_ticks"
    __table_args__ = (
        UniqueConstraint("symbol_id", "exchange", "tick_time", name="uq_market_tick_symbol_exchange_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    exchange: Mapped[str] = mapped_column(String(32), default="binance")
    tick_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    ask: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    spread: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(32), default="import")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="ticks")


class MarketOrderBookSnapshot(Base):
    __tablename__ = "market_order_books"
    __table_args__ = (
        UniqueConstraint("symbol_id", "exchange", "captured_at", name="uq_order_book_symbol_exchange_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    exchange: Mapped[str] = mapped_column(String(32), default="binance")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    bids: Mapped[list[list[float]]] = mapped_column(JSON, default=list)
    asks: Mapped[list[list[float]]] = mapped_column(JSON, default=list)
    best_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_ask: Mapped[float | None] = mapped_column(Float, nullable=True)
    spread: Mapped[float] = mapped_column(Float, default=0.0)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(32), default="stream")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="order_books")


class MarketTrade(Base):
    __tablename__ = "market_trades"
    __table_args__ = (
        UniqueConstraint("symbol_id", "exchange", "trade_id", name="uq_market_trade_symbol_exchange_trade"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    exchange: Mapped[str] = mapped_column(String(32), default="binance")
    trade_id: Mapped[str] = mapped_column(String(80), index=True)
    traded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[float] = mapped_column(Float)
    side: Mapped[str] = mapped_column(String(12), default="unknown")
    source: Mapped[str] = mapped_column(String(32), default="stream")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="trades")


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("symbol_id", "timeframe", "opened_at", name="uq_candle_symbol_timeframe_opened"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    spread: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(32), default="import", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    symbol_ref: Mapped[Symbol] = relationship()


class Tick(Base):
    __tablename__ = "ticks"
    __table_args__ = (
        UniqueConstraint("symbol_id", "exchange", "tick_time", name="uq_tick_symbol_exchange_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    exchange: Mapped[str] = mapped_column(String(32), default="binance", index=True)
    tick_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    ask: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    spread: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(32), default="import", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    symbol_ref: Mapped[Symbol] = relationship()


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("ai_model_metadata.id", ondelete="SET NULL"), nullable=True, index=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id", ondelete="SET NULL"), nullable=True, index=True)
    timeframe: Mapped[str] = mapped_column(String(8), default="15m", index=True)
    prediction_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    target: Mapped[str] = mapped_column(String(80), default="next_close_direction", index=True)
    horizon: Mapped[str] = mapped_column(String(24), default="next_candle")
    direction: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    predicted_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    prediction_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    symbol_ref: Mapped[Symbol] = relationship()
    model_ref: Mapped["AIModelMetadata | None"] = relationship()
    signal_ref: Mapped["Signal | None"] = relationship()


class WarehouseTrade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id", ondelete="SET NULL"), nullable=True, index=True)
    prediction_id: Mapped[int | None] = mapped_column(ForeignKey("predictions.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("paper_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    exchange: Mapped[str] = mapped_column(String(32), default="paper", index=True)
    external_trade_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    side: Mapped[str] = mapped_column(String(12), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="filled", index=True)
    source: Mapped[str] = mapped_column(String(32), default="paper", index=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    trade_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    symbol_ref: Mapped[Symbol] = relationship()
    signal_ref: Mapped["Signal | None"] = relationship()
    prediction_ref: Mapped[Prediction | None] = relationship()
    order_ref: Mapped["PaperOrder | None"] = relationship()


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True, index=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("ai_model_metadata.id", ondelete="SET NULL"), nullable=True, index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("backtest_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    timeframe: Mapped[str] = mapped_column(String(8), default="15m", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    initial_balance: Mapped[float] = mapped_column(Float, default=10000.0)
    final_balance: Mapped[float] = mapped_column(Float, default=10000.0)
    total_return: Mapped[float] = mapped_column(Float, default=0.0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    sharpe_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    trades_count: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    equity_curve: Mapped[list[dict]] = mapped_column(JSON, default=list)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    symbol_ref: Mapped[Symbol] = relationship()
    strategy_ref: Mapped["Strategy | None"] = relationship()
    model_ref: Mapped["AIModelMetadata | None"] = relationship()
    run_ref: Mapped["BacktestRun | None"] = relationship()


class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("ai_model_metadata.id", ondelete="SET NULL"), nullable=True, index=True)
    symbol_id: Mapped[int | None] = mapped_column(ForeignKey("symbols.id", ondelete="SET NULL"), nullable=True, index=True)
    model_name: Mapped[str] = mapped_column(String(160), default="", index=True)
    model_type: Mapped[str] = mapped_column(String(64), default="", index=True)
    timeframe: Mapped[str] = mapped_column(String(8), default="15m", index=True)
    dataset: Mapped[str] = mapped_column(String(80), default="validation", index=True)
    metric_name: Mapped[str] = mapped_column(String(80), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    training_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    training_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    model_ref: Mapped["AIModelMetadata | None"] = relationship()
    symbol_ref: Mapped[Symbol | None] = relationship()


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("paper_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    total_equity: Mapped[float] = mapped_column(Float, default=0.0)
    cash_balance: Mapped[float] = mapped_column(Float, default=0.0)
    margin_used: Mapped[float] = mapped_column(Float, default=0.0)
    total_exposure: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    positions: Mapped[list[dict]] = mapped_column(JSON, default=list)
    allocation: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(32), default="portfolio", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    account_ref: Mapped["PaperAccount | None"] = relationship()


class FeatureSet(Base):
    __tablename__ = "feature_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    features: Mapped[list[str]] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    market_features: Mapped[list["MarketFeature"]] = relationship(back_populates="feature_set_ref")
    calculation_logs: Mapped[list["FeatureCalculationLog"]] = relationship(back_populates="feature_set_ref")


class MarketFeature(Base):
    __tablename__ = "market_features"
    __table_args__ = (
        UniqueConstraint("symbol_id", "feature_set_id", "timeframe", "candle_opened_at", name="uq_market_feature_symbol_set_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    feature_set_id: Mapped[int] = mapped_column(ForeignKey("feature_sets.id", ondelete="CASCADE"), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    candle_opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    feature_values: Mapped[dict] = mapped_column("values", JSON, default=dict)
    source: Mapped[str] = mapped_column(String(32), default="calculated")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="market_features")
    feature_set_ref: Mapped[FeatureSet] = relationship(back_populates="market_features")


class FeatureCalculationLog(Base):
    __tablename__ = "feature_calculation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int | None] = mapped_column(ForeignKey("symbols.id", ondelete="SET NULL"), nullable=True, index=True)
    feature_set_id: Mapped[int | None] = mapped_column(ForeignKey("feature_sets.id", ondelete="SET NULL"), nullable=True, index=True)
    timeframe: Mapped[str] = mapped_column(String(8), default="15m", index=True)
    lookback: Mapped[int] = mapped_column(Integer, default=240)
    rows_calculated: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="completed", index=True)
    message: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    symbol_ref: Mapped[Symbol | None] = relationship(back_populates="feature_logs")
    feature_set_ref: Mapped[FeatureSet | None] = relationship(back_populates="calculation_logs")


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    timeframe: Mapped[str] = mapped_column(String(8), default="15m")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    performance: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    signals: Mapped[list["Signal"]] = relationship(back_populates="strategy_ref")
    backtest_runs: Mapped[list["BacktestRun"]] = relationship(back_populates="strategy_ref")
    builder_rules: Mapped[list["StrategyRule"]] = relationship(
        back_populates="strategy_ref",
        cascade="all, delete-orphan",
        order_by="StrategyRule.priority",
    )


class StrategyRule(Base):
    __tablename__ = "strategy_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), default="Rule")
    logic_operator: Mapped[str] = mapped_column(String(8), default="AND")
    priority: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    strategy_ref: Mapped[Strategy] = relationship(back_populates="builder_rules")
    conditions: Mapped[list["StrategyCondition"]] = relationship(
        back_populates="rule_ref",
        cascade="all, delete-orphan",
        order_by="StrategyCondition.sequence",
    )
    actions: Mapped[list["StrategyAction"]] = relationship(
        back_populates="rule_ref",
        cascade="all, delete-orphan",
        order_by="StrategyAction.id",
    )


class StrategyCondition(Base):
    __tablename__ = "strategy_conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("strategy_rules.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    indicator: Mapped[str] = mapped_column(String(40), index=True)
    operator: Mapped[str] = mapped_column(String(16), default="<")
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    period: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compare_indicator: Mapped[str | None] = mapped_column(String(40), nullable=True)
    compare_period: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    rule_ref: Mapped[StrategyRule] = relationship(back_populates="conditions")


class StrategyAction(Base):
    __tablename__ = "strategy_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("strategy_rules.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(24), index=True)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    rule_ref: Mapped[StrategyRule] = relationship(back_populates="actions")


class RiskSetting(Base):
    __tablename__ = "risk_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    max_risk_per_trade: Mapped[float] = mapped_column(Float, default=0.01)
    max_daily_loss: Mapped[float] = mapped_column(Float, default=0.03)
    max_weekly_loss: Mapped[float] = mapped_column(Float, default=0.08)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.15)
    max_open_trades: Mapped[int] = mapped_column(Integer, default=3)
    max_symbol_exposure: Mapped[float] = mapped_column(Float, default=0.2)
    max_leverage: Mapped[float] = mapped_column(Float, default=1.0)
    max_consecutive_losses: Mapped[int] = mapped_column(Integer, default=3)
    emergency_stop: Mapped[bool] = mapped_column(Boolean, default=False)
    live_trading_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True)
    direction: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    timeframe: Mapped[str] = mapped_column(String(8), default="15m")
    reason: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="signals")
    strategy_ref: Mapped[Strategy | None] = relationship(back_populates="signals")
    ai_analyses: Mapped[list["AIAnalysisRecord"]] = relationship(back_populates="signal_ref")
    paper_orders: Mapped[list["PaperOrder"]] = relationship(back_populates="signal_ref")


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True)
    timeframe: Mapped[str] = mapped_column(String(8), default="15m")
    initial_balance: Mapped[float] = mapped_column(Float, default=10000.0)
    ending_balance: Mapped[float] = mapped_column(Float, default=10000.0)
    total_return: Mapped[float] = mapped_column(Float, default=0.0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    slippage: Mapped[float] = mapped_column(Float, default=0.0)
    spread: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    sharpe_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    equity_curve: Mapped[list[dict]] = mapped_column(JSON, default=list)
    trades_count: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="completed")
    summary: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    symbol_ref: Mapped[Symbol] = relationship()
    strategy_ref: Mapped[Strategy | None] = relationship(back_populates="backtest_runs")


class WalkForwardRun(Base):
    __tablename__ = "walk_forward_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True)
    timeframe: Mapped[str] = mapped_column(String(8), default="15m")
    training_period: Mapped[int] = mapped_column(Integer)
    validation_period: Mapped[int] = mapped_column(Integer)
    test_period: Mapped[int] = mapped_column(Integer)
    rolling_windows: Mapped[int] = mapped_column(Integer)
    initial_balance: Mapped[float] = mapped_column(Float, default=10000.0)
    optimization_results: Mapped[list[dict]] = mapped_column(JSON, default=list)
    out_of_sample_results: Mapped[list[dict]] = mapped_column(JSON, default=list)
    window_metrics: Mapped[list[dict]] = mapped_column(JSON, default=list)
    aggregated_result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="completed", index=True)
    warning: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    symbol_ref: Mapped[Symbol] = relationship()
    strategy_ref: Mapped[Strategy | None] = relationship()


class AIAnalysisRecord(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id", ondelete="SET NULL"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(48), default="rules-fallback")
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    direction: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(String(1200))
    reasoning: Mapped[list[str]] = mapped_column(JSON)
    risk_notes: Mapped[list[str]] = mapped_column(JSON)
    suggested_action: Mapped[str] = mapped_column(String(500))
    indicators: Mapped[dict[str, float]] = mapped_column(JSON)
    backtest_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    signal_ref: Mapped[Signal | None] = relationship(back_populates="ai_analyses")
    paper_orders: Mapped[list["PaperOrder"]] = relationship(back_populates="ai_analysis_ref")


class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id", ondelete="SET NULL"), nullable=True, index=True)
    ai_analysis_id: Mapped[int | None] = mapped_column(ForeignKey("ai_analyses.id", ondelete="SET NULL"), nullable=True, index=True)
    side: Mapped[str] = mapped_column(String(12), index=True)
    order_type: Mapped[str] = mapped_column(String(16), default="market")
    quantity: Mapped[float] = mapped_column(Float)
    requested_price: Mapped[float] = mapped_column(Float)
    fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="filled", index=True)
    risk_status: Mapped[str] = mapped_column(String(16), default="approved")
    risk_message: Mapped[str] = mapped_column(String(500), default="")
    execution_mode: Mapped[str] = mapped_column(String(16), default="paper")
    exchange_order_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="orders")
    signal_ref: Mapped[Signal | None] = relationship(back_populates="paper_orders")
    ai_analysis_ref: Mapped[AIAnalysisRecord | None] = relationship(back_populates="paper_orders")


class PaperPosition(Base):
    __tablename__ = "paper_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    side: Mapped[str] = mapped_column(String(12), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    avg_entry_price: Mapped[float] = mapped_column(Float)
    mark_price: Mapped[float] = mapped_column(Float)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="positions")


class PaperAccount(Base):
    __tablename__ = "paper_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, default="default")
    starting_balance: Mapped[float] = mapped_column(Float, default=10000.0)
    cash_balance: Mapped[float] = mapped_column(Float, default=10000.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ledger_entries: Mapped[list["PaperTradeLedger"]] = relationship(back_populates="account_ref")


class PaperTradeLedger(Base):
    __tablename__ = "paper_trade_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("paper_accounts.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("paper_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    position_id: Mapped[int | None] = mapped_column(ForeignKey("paper_positions.id", ondelete="SET NULL"), nullable=True, index=True)
    symbol_id: Mapped[int | None] = mapped_column(ForeignKey("symbols.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(12), default="account")
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    balance_after: Mapped[float] = mapped_column(Float, default=0.0)
    equity_after: Mapped[float] = mapped_column(Float, default=0.0)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    account_ref: Mapped[PaperAccount] = relationship(back_populates="ledger_entries")
    symbol_ref: Mapped[Symbol | None] = relationship()
    order_ref: Mapped[PaperOrder | None] = relationship()
    position_ref: Mapped[PaperPosition | None] = relationship()


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(16), default="info", index=True)
    message: Mapped[str] = mapped_column(String(500))
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class MonteCarloRun(Base):
    __tablename__ = "monte_carlo_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    starting_balance: Mapped[float] = mapped_column(Float)
    win_rate: Mapped[float] = mapped_column(Float)
    average_win: Mapped[float] = mapped_column(Float)
    average_loss: Mapped[float] = mapped_column(Float)
    number_of_trades: Mapped[int] = mapped_column(Integer)
    number_of_simulations: Mapped[int] = mapped_column(Integer)
    risk_per_trade: Mapped[float] = mapped_column(Float)
    probability_of_ruin: Mapped[float] = mapped_column(Float)
    expected_drawdown: Mapped[float] = mapped_column(Float)
    maximum_drawdown: Mapped[float] = mapped_column(Float)
    best_case: Mapped[float] = mapped_column(Float)
    worst_case: Mapped[float] = mapped_column(Float)
    median_case: Mapped[float] = mapped_column(Float)
    confidence_intervals: Mapped[dict] = mapped_column(JSON, default=dict)
    ending_equity_distribution: Mapped[list[dict]] = mapped_column(JSON, default=list)
    risk_recommendation: Mapped[str] = mapped_column(String(800))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    hashed_password: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(24), default="trader", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    role_assignments: Mapped[list["UserRole"]] = relationship(
        back_populates="user_ref",
        cascade="all, delete-orphan",
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user_assignments: Mapped[list["UserRole"]] = relationship(
        back_populates="role_ref",
        cascade="all, delete-orphan",
    )
    permission_assignments: Mapped[list["RolePermission"]] = relationship(
        back_populates="role_ref",
        cascade="all, delete-orphan",
    )


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    role_assignments: Mapped[list["RolePermission"]] = relationship(
        back_populates="permission_ref",
        cascade="all, delete-orphan",
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    user_ref: Mapped[User] = relationship(back_populates="role_assignments")
    role_ref: Mapped[Role] = relationship(back_populates="user_assignments")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    role_ref: Mapped[Role] = relationship(back_populates="permission_assignments")
    permission_ref: Mapped[Permission] = relationship(back_populates="role_assignments")


class ApiCredential(Base):
    __tablename__ = "api_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exchange: Mapped[str] = mapped_column(String(48), index=True)
    api_key: Mapped[str] = mapped_column(String(255))
    encrypted_api_secret: Mapped[str] = mapped_column(String(1000))
    mode: Mapped[str] = mapped_column(String(16), default="paper", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class AIModelMetadata(Base):
    __tablename__ = "ai_model_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), default="15m")
    model_type: Mapped[str] = mapped_column(String(64), default="random_forest")
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_model_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    model_path: Mapped[str] = mapped_column(String(500))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    feature_names: Mapped[list[str]] = mapped_column(JSON, default=list)
    training_params: Mapped[dict] = mapped_column(JSON, default=dict)
    target: Mapped[str] = mapped_column(String(80), default="next_close_direction")
    deployed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="trained", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(String(800))
    severity: Mapped[str] = mapped_column(String(16), default="info", index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    level: Mapped[str] = mapped_column(String(16), default="info", index=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    message: Mapped[str] = mapped_column(String(1000))
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
