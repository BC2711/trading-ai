import json
from typing import Protocol

import httpx

from app.core.config import settings
from app.models import BacktestRun, MarketCandle, RiskSetting, Signal, Strategy
from app.schemas.trading import AIAnalysisRequest
from app.services.indicators.technical import indicator_snapshot
from app.services.signals import build_signal_from_candles


class AIAnalysisResult:
    def __init__(
        self,
        provider: str,
        symbol: str,
        timeframe: str,
        direction: str,
        confidence: float,
        explanation: str,
        reasoning: list[str],
        risk_notes: list[str],
        suggested_action: str,
        indicators: dict[str, float],
        backtest_summary: str | None,
    ) -> None:
        self.provider = provider
        self.symbol = symbol
        self.timeframe = timeframe
        self.direction = direction
        self.confidence = confidence
        self.explanation = explanation
        self.reasoning = reasoning
        self.risk_notes = risk_notes
        self.suggested_action = suggested_action
        self.indicators = indicators
        self.backtest_summary = backtest_summary


class AIProvider(Protocol):
    provider_name: str

    def analyze(
        self,
        payload: AIAnalysisRequest,
        signal: Signal | None,
        candles: list[MarketCandle],
        strategy: Strategy,
        risk_settings: RiskSetting,
        latest_backtest: BacktestRun | None,
    ) -> AIAnalysisResult:
        ...


class RuleBasedAIProvider:
    provider_name = "rules-fallback"

    def analyze(
        self,
        payload: AIAnalysisRequest,
        signal: Signal | None,
        candles: list[MarketCandle],
        strategy: Strategy,
        risk_settings: RiskSetting,
        latest_backtest: BacktestRun | None,
    ) -> AIAnalysisResult:
        snapshot = indicator_snapshot(
            closes=[candle.close for candle in candles],
            highs=[candle.high for candle in candles],
            lows=[candle.low for candle in candles],
        )
        derived_signal = build_signal_from_candles(candles)

        direction = signal.direction if signal else str(derived_signal["direction"])
        confidence = signal.confidence if signal else float(derived_signal["confidence"])
        reason = signal.reason if signal else str(derived_signal["reason"])

        reasoning = self._build_reasoning(direction, confidence, reason, snapshot, strategy.name)
        risk_notes = self._build_risk_notes(direction, confidence, snapshot, risk_settings)
        backtest_summary = latest_backtest.summary if latest_backtest else None

        return AIAnalysisResult(
            provider=self.provider_name,
            symbol=signal.symbol_ref.symbol if signal else payload.symbol.upper(),
            timeframe=signal.timeframe if signal else payload.timeframe,
            direction=direction,
            confidence=round(confidence, 4),
            explanation=self._build_explanation(signal, direction, confidence, reason, snapshot, backtest_summary),
            reasoning=reasoning,
            risk_notes=risk_notes,
            suggested_action=self._build_suggested_action(direction, confidence, risk_notes),
            indicators={key: round(value, 4) for key, value in snapshot.items()},
            backtest_summary=backtest_summary,
        )

    def _build_reasoning(
        self,
        direction: str,
        confidence: float,
        reason: str,
        indicators: dict[str, float],
        strategy_name: str,
    ) -> list[str]:
        return [
            f"{strategy_name} classified the setup as {direction.upper()} with {confidence * 100:.1f}% confidence.",
            reason,
            f"Price is {indicators['close']:.2f}, EMA 9 is {indicators['ema_9']:.2f}, EMA 21 is {indicators['ema_21']:.2f}, and RSI 14 is {indicators['rsi_14']:.1f}.",
            f"ATR 14 is {indicators['atr_14']:.2f}, which helps frame near-term volatility and stop distance.",
        ]

    def _build_risk_notes(
        self,
        direction: str,
        confidence: float,
        indicators: dict[str, float],
        risk_settings: RiskSetting,
    ) -> list[str]:
        notes = [
            f"Risk per trade is capped at {risk_settings.max_risk_per_trade * 100:.1f}% with {risk_settings.max_open_trades} max open trades.",
            f"Symbol exposure limit is {risk_settings.max_symbol_exposure * 100:.1f}% and daily loss limit is {risk_settings.max_daily_loss * 100:.1f}%.",
        ]

        if direction == "watch":
            notes.append("Signal is observational; wait for clearer trend confirmation before adding exposure.")
        if confidence < 0.65:
            notes.append("Confidence is moderate, so position size should stay below normal deployment size.")
        if indicators["rsi_14"] > 72:
            notes.append("RSI is elevated; avoid chasing a late long entry without a pullback.")
        if indicators["rsi_14"] < 30:
            notes.append("RSI is compressed; short entries may be vulnerable to a relief bounce.")

        return notes

    def _build_explanation(
        self,
        signal: Signal | None,
        direction: str,
        confidence: float,
        reason: str,
        indicators: dict[str, float],
        backtest_summary: str | None,
    ) -> str:
        symbol = signal.symbol_ref.symbol if signal else "unknown"
        bias = "bullish" if direction == "buy" else "bearish" if direction == "sell" else "neutral"
        explanation = (
            f"{symbol} currently has a {bias} {direction.upper()} read with {confidence * 100:.1f}% confidence. "
            f"The main driver is: {reason} The latest close is {indicators['close']:.2f}, with RSI at {indicators['rsi_14']:.1f}."
        )
        if backtest_summary:
            explanation = f"{explanation} Latest backtest context: {backtest_summary}"
        return explanation

    def _build_suggested_action(self, direction: str, confidence: float, risk_notes: list[str]) -> str:
        if direction == "buy" and confidence >= 0.7:
            return "Consider a staged long entry within configured risk limits."
        if direction == "sell" and confidence >= 0.7:
            return "Consider reducing long exposure or testing a staged short setup within configured risk limits."
        if any("moderate" in note for note in risk_notes):
            return "Keep this on watch and require confirmation before execution."
        return "Monitor the setup and wait for stronger confirmation."


class OpenAIProvider(RuleBasedAIProvider):
    provider_name = "openai"

    def analyze(
        self,
        payload: AIAnalysisRequest,
        signal: Signal | None,
        candles: list[MarketCandle],
        strategy: Strategy,
        risk_settings: RiskSetting,
        latest_backtest: BacktestRun | None,
    ) -> AIAnalysisResult:
        if not settings.openai_api_key:
            raise ValueError("OpenAI provider requires OPENAI_API_KEY")

        snapshot = indicator_snapshot(
            closes=[candle.close for candle in candles],
            highs=[candle.high for candle in candles],
            lows=[candle.low for candle in candles],
        )
        derived_signal = build_signal_from_candles(candles)

        direction = signal.direction if signal else str(derived_signal["direction"])
        confidence = signal.confidence if signal else float(derived_signal["confidence"])
        reason = signal.reason if signal else str(derived_signal["reason"])
        backtest_summary = latest_backtest.summary if latest_backtest else None

        prompt = self._build_prompt(
            symbol=signal.symbol_ref.symbol if signal else payload.symbol.upper(),
            timeframe=signal.timeframe if signal else payload.timeframe,
            direction=direction,
            confidence=confidence,
            reason=reason,
            indicators=snapshot,
            strategy_name=strategy.name,
            risk_settings=risk_settings,
            backtest_summary=backtest_summary,
        )
        analysis = self._call_openai(prompt)

        try:
            parsed = self._parse_analysis(analysis)
            return AIAnalysisResult(
                provider=self.provider_name,
                symbol=signal.symbol_ref.symbol if signal else payload.symbol.upper(),
                timeframe=signal.timeframe if signal else payload.timeframe,
                direction=parsed["direction"],
                confidence=round(float(parsed["confidence"]), 4),
                explanation=parsed["explanation"],
                reasoning=parsed["reasoning"],
                risk_notes=parsed["risk_notes"],
                suggested_action=parsed["suggested_action"],
                indicators={key: float(parsed["indicators"][key]) for key in parsed["indicators"]},
                backtest_summary=backtest_summary,
            )
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return super().analyze(payload, signal, candles, strategy, risk_settings, latest_backtest)

    def _build_prompt(
        self,
        symbol: str,
        timeframe: str,
        direction: str,
        confidence: float,
        reason: str,
        indicators: dict[str, float],
        strategy_name: str,
        risk_settings: RiskSetting,
        backtest_summary: str | None,
    ) -> str:
        indicator_lines = "\n".join([f"- {name}: {value:.4f}" for name, value in indicators.items()])
        prompt = (
            f"You are a quantitative trading analyst. Provide a JSON-only response for a trading signal analysis.\n"
            f"Symbol: {symbol}\n"
            f"Timeframe: {timeframe}\n"
            f"Strategy: {strategy_name}\n"
            f"Signal direction: {direction}\n"
            f"Signal confidence: {confidence:.2f}\n"
            f"Reason: {reason}\n"
            f"Indicators:\n{indicator_lines}\n"
            f"Risk settings:\n"
            f"- max_risk_per_trade: {risk_settings.max_risk_per_trade:.4f}\n"
            f"- max_daily_loss: {risk_settings.max_daily_loss:.4f}\n"
            f"- max_open_trades: {risk_settings.max_open_trades}\n"
            f"- max_symbol_exposure: {risk_settings.max_symbol_exposure:.4f}\n"
        )
        if backtest_summary:
            prompt += f"Backtest summary: {backtest_summary}\n"
        prompt += (
            "\nReturn exactly valid JSON with keys: direction, confidence, explanation, reasoning, "
            "risk_notes, suggested_action, indicators. "
            "Make indicators a map of metric names to numeric values. "
            "Do not include any markdown formatting."
        )
        return prompt

    def _call_openai(self, prompt: str) -> str:
        url = f"{settings.openai_api_base_url.rstrip('/')}" + "/v1/chat/completions"
        request_body = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": "You are a helpful trading assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 400,
        }
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        response = httpx.post(url, json=request_body, headers=headers, timeout=30.0)
        response.raise_for_status()
        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]

    def _parse_analysis(self, content: str) -> dict:
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.split("```", 1)[1].strip()
        if cleaned.startswith("`") and cleaned.endswith("`"):
            cleaned = cleaned.strip("`")
        return json.loads(cleaned)


def get_ai_provider() -> AIProvider:
    if settings.ai_provider.lower() == "openai":
        return OpenAIProvider()
    return RuleBasedAIProvider()
