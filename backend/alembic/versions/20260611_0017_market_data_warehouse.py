"""market data warehouse

Revision ID: 20260611_0017
Revises: 20260611_0016
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0017"
down_revision: str | None = "20260611_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not has_table("candles"):
        op.create_table(
            "candles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol_id", sa.Integer(), nullable=False),
            sa.Column("timeframe", sa.String(length=8), nullable=False),
            sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("open", sa.Float(), nullable=False),
            sa.Column("high", sa.Float(), nullable=False),
            sa.Column("low", sa.Float(), nullable=False),
            sa.Column("close", sa.Float(), nullable=False),
            sa.Column("volume", sa.Float(), nullable=False),
            sa.Column("spread", sa.Float(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("symbol_id", "timeframe", "opened_at", name="uq_candle_symbol_timeframe_opened"),
        )
        op.create_index(op.f("ix_candles_id"), "candles", ["id"], unique=False)
        op.create_index(op.f("ix_candles_symbol_id"), "candles", ["symbol_id"], unique=False)
        op.create_index(op.f("ix_candles_timeframe"), "candles", ["timeframe"], unique=False)
        op.create_index(op.f("ix_candles_opened_at"), "candles", ["opened_at"], unique=False)
        op.create_index(op.f("ix_candles_source"), "candles", ["source"], unique=False)
        op.create_index(op.f("ix_candles_created_at"), "candles", ["created_at"], unique=False)

    if not has_table("ticks"):
        op.create_table(
            "ticks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol_id", sa.Integer(), nullable=False),
            sa.Column("exchange", sa.String(length=32), nullable=False),
            sa.Column("tick_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("bid", sa.Float(), nullable=True),
            sa.Column("ask", sa.Float(), nullable=True),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("volume", sa.Float(), nullable=False),
            sa.Column("spread", sa.Float(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("symbol_id", "exchange", "tick_time", name="uq_tick_symbol_exchange_time"),
        )
        op.create_index(op.f("ix_ticks_id"), "ticks", ["id"], unique=False)
        op.create_index(op.f("ix_ticks_symbol_id"), "ticks", ["symbol_id"], unique=False)
        op.create_index(op.f("ix_ticks_exchange"), "ticks", ["exchange"], unique=False)
        op.create_index(op.f("ix_ticks_tick_time"), "ticks", ["tick_time"], unique=False)
        op.create_index(op.f("ix_ticks_source"), "ticks", ["source"], unique=False)
        op.create_index(op.f("ix_ticks_created_at"), "ticks", ["created_at"], unique=False)

    if not has_table("predictions"):
        op.create_table(
            "predictions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol_id", sa.Integer(), nullable=False),
            sa.Column("model_id", sa.Integer(), nullable=True),
            sa.Column("signal_id", sa.Integer(), nullable=True),
            sa.Column("timeframe", sa.String(length=8), nullable=False),
            sa.Column("prediction_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("target", sa.String(length=80), nullable=False),
            sa.Column("horizon", sa.String(length=24), nullable=False),
            sa.Column("direction", sa.String(length=16), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("predicted_value", sa.Float(), nullable=True),
            sa.Column("features", sa.JSON(), nullable=False),
            sa.Column("prediction_metadata", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["model_id"], ["ai_model_metadata.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_predictions_id"), "predictions", ["id"], unique=False)
        op.create_index(op.f("ix_predictions_symbol_id"), "predictions", ["symbol_id"], unique=False)
        op.create_index(op.f("ix_predictions_model_id"), "predictions", ["model_id"], unique=False)
        op.create_index(op.f("ix_predictions_signal_id"), "predictions", ["signal_id"], unique=False)
        op.create_index(op.f("ix_predictions_timeframe"), "predictions", ["timeframe"], unique=False)
        op.create_index(op.f("ix_predictions_prediction_time"), "predictions", ["prediction_time"], unique=False)
        op.create_index(op.f("ix_predictions_target"), "predictions", ["target"], unique=False)
        op.create_index(op.f("ix_predictions_direction"), "predictions", ["direction"], unique=False)
        op.create_index(op.f("ix_predictions_created_at"), "predictions", ["created_at"], unique=False)

    if not has_table("trades"):
        op.create_table(
            "trades",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol_id", sa.Integer(), nullable=False),
            sa.Column("signal_id", sa.Integer(), nullable=True),
            sa.Column("prediction_id", sa.Integer(), nullable=True),
            sa.Column("order_id", sa.Integer(), nullable=True),
            sa.Column("exchange", sa.String(length=32), nullable=False),
            sa.Column("external_trade_id", sa.String(length=80), nullable=True),
            sa.Column("side", sa.String(length=12), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("fee", sa.Float(), nullable=False),
            sa.Column("realized_pnl", sa.Float(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("trade_metadata", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["order_id"], ["paper_orders.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_trades_id"), "trades", ["id"], unique=False)
        op.create_index(op.f("ix_trades_symbol_id"), "trades", ["symbol_id"], unique=False)
        op.create_index(op.f("ix_trades_signal_id"), "trades", ["signal_id"], unique=False)
        op.create_index(op.f("ix_trades_prediction_id"), "trades", ["prediction_id"], unique=False)
        op.create_index(op.f("ix_trades_order_id"), "trades", ["order_id"], unique=False)
        op.create_index(op.f("ix_trades_exchange"), "trades", ["exchange"], unique=False)
        op.create_index(op.f("ix_trades_external_trade_id"), "trades", ["external_trade_id"], unique=False)
        op.create_index(op.f("ix_trades_side"), "trades", ["side"], unique=False)
        op.create_index(op.f("ix_trades_status"), "trades", ["status"], unique=False)
        op.create_index(op.f("ix_trades_source"), "trades", ["source"], unique=False)
        op.create_index(op.f("ix_trades_executed_at"), "trades", ["executed_at"], unique=False)
        op.create_index(op.f("ix_trades_created_at"), "trades", ["created_at"], unique=False)

    if not has_table("backtest_results"):
        op.create_table(
            "backtest_results",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol_id", sa.Integer(), nullable=False),
            sa.Column("strategy_id", sa.Integer(), nullable=True),
            sa.Column("model_id", sa.Integer(), nullable=True),
            sa.Column("run_id", sa.Integer(), nullable=True),
            sa.Column("timeframe", sa.String(length=8), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("initial_balance", sa.Float(), nullable=False),
            sa.Column("final_balance", sa.Float(), nullable=False),
            sa.Column("total_return", sa.Float(), nullable=False),
            sa.Column("win_rate", sa.Float(), nullable=False),
            sa.Column("max_drawdown", sa.Float(), nullable=False),
            sa.Column("sharpe_ratio", sa.Float(), nullable=False),
            sa.Column("profit_factor", sa.Float(), nullable=False),
            sa.Column("trades_count", sa.Integer(), nullable=False),
            sa.Column("metrics", sa.JSON(), nullable=False),
            sa.Column("equity_curve", sa.JSON(), nullable=False),
            sa.Column("parameters", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["model_id"], ["ai_model_metadata.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["run_id"], ["backtest_runs.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_backtest_results_id"), "backtest_results", ["id"], unique=False)
        op.create_index(op.f("ix_backtest_results_symbol_id"), "backtest_results", ["symbol_id"], unique=False)
        op.create_index(op.f("ix_backtest_results_strategy_id"), "backtest_results", ["strategy_id"], unique=False)
        op.create_index(op.f("ix_backtest_results_model_id"), "backtest_results", ["model_id"], unique=False)
        op.create_index(op.f("ix_backtest_results_run_id"), "backtest_results", ["run_id"], unique=False)
        op.create_index(op.f("ix_backtest_results_timeframe"), "backtest_results", ["timeframe"], unique=False)
        op.create_index(op.f("ix_backtest_results_started_at"), "backtest_results", ["started_at"], unique=False)
        op.create_index(op.f("ix_backtest_results_ended_at"), "backtest_results", ["ended_at"], unique=False)
        op.create_index(op.f("ix_backtest_results_created_at"), "backtest_results", ["created_at"], unique=False)

    if not has_table("model_metrics"):
        op.create_table(
            "model_metrics",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("model_id", sa.Integer(), nullable=True),
            sa.Column("symbol_id", sa.Integer(), nullable=True),
            sa.Column("model_name", sa.String(length=160), nullable=False),
            sa.Column("model_type", sa.String(length=64), nullable=False),
            sa.Column("timeframe", sa.String(length=8), nullable=False),
            sa.Column("dataset", sa.String(length=80), nullable=False),
            sa.Column("metric_name", sa.String(length=80), nullable=False),
            sa.Column("metric_value", sa.Float(), nullable=False),
            sa.Column("metrics", sa.JSON(), nullable=False),
            sa.Column("training_window_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("training_window_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["model_id"], ["ai_model_metadata.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_model_metrics_id"), "model_metrics", ["id"], unique=False)
        op.create_index(op.f("ix_model_metrics_model_id"), "model_metrics", ["model_id"], unique=False)
        op.create_index(op.f("ix_model_metrics_symbol_id"), "model_metrics", ["symbol_id"], unique=False)
        op.create_index(op.f("ix_model_metrics_model_name"), "model_metrics", ["model_name"], unique=False)
        op.create_index(op.f("ix_model_metrics_model_type"), "model_metrics", ["model_type"], unique=False)
        op.create_index(op.f("ix_model_metrics_timeframe"), "model_metrics", ["timeframe"], unique=False)
        op.create_index(op.f("ix_model_metrics_dataset"), "model_metrics", ["dataset"], unique=False)
        op.create_index(op.f("ix_model_metrics_metric_name"), "model_metrics", ["metric_name"], unique=False)
        op.create_index(op.f("ix_model_metrics_evaluated_at"), "model_metrics", ["evaluated_at"], unique=False)
        op.create_index(op.f("ix_model_metrics_created_at"), "model_metrics", ["created_at"], unique=False)

    if not has_table("portfolio_snapshots"):
        op.create_table(
            "portfolio_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=True),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("total_equity", sa.Float(), nullable=False),
            sa.Column("cash_balance", sa.Float(), nullable=False),
            sa.Column("margin_used", sa.Float(), nullable=False),
            sa.Column("total_exposure", sa.Float(), nullable=False),
            sa.Column("realized_pnl", sa.Float(), nullable=False),
            sa.Column("unrealized_pnl", sa.Float(), nullable=False),
            sa.Column("positions", sa.JSON(), nullable=False),
            sa.Column("allocation", sa.JSON(), nullable=False),
            sa.Column("metrics", sa.JSON(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["paper_accounts.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_portfolio_snapshots_id"), "portfolio_snapshots", ["id"], unique=False)
        op.create_index(op.f("ix_portfolio_snapshots_account_id"), "portfolio_snapshots", ["account_id"], unique=False)
        op.create_index(op.f("ix_portfolio_snapshots_captured_at"), "portfolio_snapshots", ["captured_at"], unique=False)
        op.create_index(op.f("ix_portfolio_snapshots_source"), "portfolio_snapshots", ["source"], unique=False)
        op.create_index(op.f("ix_portfolio_snapshots_created_at"), "portfolio_snapshots", ["created_at"], unique=False)


def downgrade() -> None:
    for table_name in [
        "portfolio_snapshots",
        "model_metrics",
        "backtest_results",
        "trades",
        "predictions",
        "ticks",
        "candles",
    ]:
        if has_table(table_name):
            op.drop_table(table_name)
