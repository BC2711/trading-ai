from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIAnalysisRecord, PaperOrder, Strategy
from app.schemas.copilot import CopilotChatResponse, CopilotInsightCard, CopilotMessage
from app.services.ai.inference import PredictionService
from app.services.backtesting.engine import list_backtest_runs
from app.services.portfolio import get_portfolio_summary
from app.services.risk import risk_summary
from app.services.scanner import get_scanner_results
from app.services.signals import list_signals


_HISTORY: list[CopilotMessage] = []
_NEXT_MESSAGE_ID = 1


def chat(db: Session, message: str) -> CopilotChatResponse:
    user_message = _new_message("user", message)
    assistant_message = _answer(db, message)
    _HISTORY.extend([user_message, assistant_message])
    del _HISTORY[:-40]
    return CopilotChatResponse(user_message=user_message, assistant_message=assistant_message)


def history() -> list[CopilotMessage]:
    return list(_HISTORY)


def _answer(db: Session, message: str) -> CopilotMessage:
    lowered = message.lower()
    if _mentions(lowered, ["reject", "denied", "blocked", "why trade"]):
        content, cards = _explain_trade_rejection(db)
    elif _mentions(lowered, ["portfolio risk", "risk", "drawdown", "exposure", "leverage"]):
        content, cards = _explain_portfolio_risk(db)
    elif _mentions(lowered, ["best", "worst", "performing strategy", "strategy performance"]):
        content, cards = _explain_strategy_performance(db)
    elif _mentions(lowered, ["market outlook", "outlook", "scanner", "market", "trend"]):
        content, cards = _explain_market_outlook(db)
    elif _mentions(lowered, ["model", "prediction", "ai decision", "decision explanation"]):
        content, cards = _explain_model_decision(db)
    else:
        content, cards = _explain_signal(db)

    return _new_message("assistant", content, cards=cards, suggested_questions=_suggested_questions())


def _explain_signal(db: Session) -> tuple[str, list[CopilotInsightCard]]:
    signals = list_signals(db)
    latest = signals[0] if signals else None
    if latest is None:
        return (
            "I could not find an active signal yet. Sync market data or generate signals, then I can explain the latest setup.",
            [],
        )

    content = (
        f"The latest {latest.symbol_ref.symbol} signal is {latest.direction.upper()} with "
        f"{latest.confidence * 100:.1f}% confidence. It was generated because: {latest.reason}"
    )
    cards = [
        _card("Signal", latest.direction.upper(), latest.reason, _signal_tone(latest.direction)),
        _card("Confidence", f"{latest.confidence * 100:.1f}%", f"Timeframe {latest.timeframe}", "info"),
    ]
    return content, cards


def _explain_trade_rejection(db: Session) -> tuple[str, list[CopilotInsightCard]]:
    order = db.scalars(
        select(PaperOrder)
        .where((PaperOrder.status == "rejected") | (PaperOrder.risk_status == "blocked"))
        .order_by(PaperOrder.created_at.desc())
        .limit(1)
    ).first()
    if order is None:
        summary = risk_summary(db)
        return (
            "I do not see a recent rejected trade. Current risk checks are available, and the latest risk score is "
            f"{summary.risk_score:.1f}/100.",
            [_card("Risk Score", f"{summary.risk_score:.1f}/100", "No rejected order found in recent paper orders.", "success")],
        )

    reason = order.risk_message or order.failure_reason or "The risk engine blocked the order without a detailed message."
    content = (
        f"The latest rejected trade was {order.side.upper()} {order.symbol_ref.symbol}. "
        f"It was rejected because {reason}"
    )
    cards = [
        _card("Rejected Trade", f"{order.side.upper()} {order.symbol_ref.symbol}", reason, "error"),
        _card("Quantity", f"{order.quantity:.8f}", f"Risk status: {order.risk_status}", "warning"),
    ]
    return content, cards


def _explain_portfolio_risk(db: Session) -> tuple[str, list[CopilotInsightCard]]:
    portfolio = get_portfolio_summary(db)
    risk = risk_summary(db)
    warnings = " ".join(risk.warnings) if risk.warnings else "No active risk warnings."
    content = (
        f"Portfolio risk is {risk.risk_score:.1f}/100. Exposure is {portfolio.total_exposure:.2f}, "
        f"open positions are {portfolio.open_positions}, leverage is {risk.leverage:.2f}x, and drawdown is "
        f"{risk.drawdown * 100:.2f}%. {warnings}"
    )
    cards = [
        _card("Risk Score", f"{risk.risk_score:.1f}/100", warnings, "warning" if risk.risk_score >= 50 else "success"),
        _card("Exposure", _currency(portfolio.total_exposure), f"{risk.exposure_usage * 100:.1f}% of configured symbol limit", "info"),
        _card("Leverage", f"{risk.leverage:.2f}x", f"Max {risk.max_leverage:.2f}x", "warning" if risk.leverage / max(risk.max_leverage, 1) >= 0.8 else "success"),
        _card("Drawdown", f"{risk.drawdown * 100:.2f}%", f"Limit {risk.max_drawdown_limit * 100:.1f}%", "info"),
    ]
    return content, cards


def _explain_strategy_performance(db: Session) -> tuple[str, list[CopilotInsightCard]]:
    runs = list_backtest_runs(db, limit=50)
    if not runs:
        strategies = db.scalars(select(Strategy).order_by(Strategy.created_at.desc()).limit(5)).all()
        names = ", ".join(strategy.name for strategy in strategies) if strategies else "no configured strategies"
        return (
            f"I do not see completed backtests yet. Configured strategies: {names}. Run backtests to rank best and worst performers.",
            [_card("Backtests", "None", "Strategy ranking needs completed backtest data.", "warning")],
        )

    best = max(runs, key=lambda run: run.total_return)
    worst = min(runs, key=lambda run: run.total_return)
    content = (
        f"The best recent strategy result is {best.strategy_ref.name if best.strategy_ref else 'Strategy'} on "
        f"{best.symbol_ref.symbol} with {best.total_return * 100:.2f}% return. The weakest is "
        f"{worst.strategy_ref.name if worst.strategy_ref else 'Strategy'} on {worst.symbol_ref.symbol} with "
        f"{worst.total_return * 100:.2f}% return."
    )
    cards = [
        _card("Best Strategy", best.strategy_ref.name if best.strategy_ref else "Strategy", f"{best.symbol_ref.symbol}: {best.summary}", "success"),
        _card("Worst Strategy", worst.strategy_ref.name if worst.strategy_ref else "Strategy", f"{worst.symbol_ref.symbol}: {worst.summary}", "error"),
    ]
    return content, cards


def _explain_market_outlook(db: Session) -> tuple[str, list[CopilotInsightCard]]:
    scanner = get_scanner_results(db)
    buys = [item for item in scanner if item.signal == "buy"]
    sells = [item for item in scanner if item.signal == "sell"]
    holds = [item for item in scanner if item.signal == "hold"]
    top = scanner[0] if scanner else None
    bias = "mixed"
    if len(buys) > len(sells):
        bias = "constructive"
    elif len(sells) > len(buys):
        bias = "defensive"

    content = (
        f"Current market outlook is {bias}. Scanner shows {len(buys)} buy setups, {len(sells)} sell setups, "
        f"and {len(holds)} neutral holds."
    )
    if top:
        content += f" The highest-confidence row is {top.symbol} {top.signal.upper()} at {top.confidence * 100:.1f}% confidence."
    cards = [
        _card("Market Bias", bias.title(), "Based on scanner signal balance.", "success" if bias == "constructive" else "warning"),
        _card("Buy Signals", str(len(buys)), "Scanner rows with buy action.", "success"),
        _card("Sell Signals", str(len(sells)), "Scanner rows with sell action.", "error"),
    ]
    if top:
        cards.append(_card("Top Scanner Row", f"{top.symbol} {top.signal.upper()}", top.recommended_action, _signal_tone(top.signal)))
    return content, cards


def _explain_model_decision(db: Session) -> tuple[str, list[CopilotInsightCard]]:
    analysis = db.scalars(select(AIAnalysisRecord).order_by(AIAnalysisRecord.created_at.desc()).limit(1)).first()
    if analysis:
        reasoning = " ".join(analysis.reasoning[:3])
        content = (
            f"The latest AI analysis chose {analysis.direction.upper()} for {analysis.symbol} with "
            f"{analysis.confidence * 100:.1f}% confidence. {analysis.explanation}"
        )
        cards = [
            _card("AI Direction", analysis.direction.upper(), reasoning or analysis.explanation, _signal_tone(analysis.direction)),
            _card("Provider", analysis.provider, analysis.suggested_action, "info"),
        ]
        return content, cards

    try:
        prediction = PredictionService(db).predict(symbol="BTCUSDT", timeframe="15m")
    except ValueError:
        return (
            "I do not see a deployed AI model or saved AI analysis yet. Train and deploy a model, or generate an AI analysis, then I can explain its decision.",
            [_card("AI Decision", "Unavailable", "No active model or saved analysis was found.", "warning")],
        )

    features = prediction.get("features", {})
    feature_detail = ", ".join(f"{key}: {value:.4f}" for key, value in list(features.items())[:4] if isinstance(value, int | float))
    content = (
        f"The active model predicts {prediction.get('direction', 'unknown').upper()} for {prediction.get('symbol', 'BTCUSDT')} "
        f"with {float(prediction.get('confidence', 0)) * 100:.1f}% confidence. Key features: {feature_detail or 'not available'}."
    )
    cards = [
        _card("Model Direction", str(prediction.get("direction", "unknown")).upper(), feature_detail or "No feature details returned.", _signal_tone(str(prediction.get("direction", "")))),
        _card("Confidence", f"{float(prediction.get('confidence', 0)) * 100:.1f}%", "Model probability from active prediction service.", "info"),
    ]
    return content, cards


def _new_message(
    role: str,
    content: str,
    *,
    cards: list[CopilotInsightCard] | None = None,
    suggested_questions: list[str] | None = None,
) -> CopilotMessage:
    global _NEXT_MESSAGE_ID
    message = CopilotMessage(
        id=_NEXT_MESSAGE_ID,
        role=role,
        content=content,
        cards=cards or [],
        suggested_questions=suggested_questions or [],
        created_at=datetime.now(timezone.utc),
    )
    _NEXT_MESSAGE_ID += 1
    return message


def _mentions(message: str, words: list[str]) -> bool:
    return any(word in message for word in words)


def _card(title: str, value: str, detail: str, tone: str) -> CopilotInsightCard:
    return CopilotInsightCard(title=title, value=value, detail=detail, tone=tone)


def _signal_tone(direction: str) -> str:
    if direction in {"buy", "bullish"}:
        return "success"
    if direction in {"sell", "bearish"}:
        return "error"
    return "warning"


def _currency(value: float) -> str:
    return f"${value:,.2f}"


def _suggested_questions() -> list[str]:
    return [
        "Why was the latest signal generated?",
        "What is my current portfolio risk?",
        "What is the current market outlook?",
        "Which strategy is performing best?",
        "Explain the latest AI model decision.",
    ]
