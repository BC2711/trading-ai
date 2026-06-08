from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

try:
    from llama_cpp import Llama, LlamaGrammar
except ImportError:
    Llama = None
    LlamaGrammar = None

import logging
from app.core.config import settings
from app.models import BacktestRun, MarketCandle, RiskSetting, Signal, Strategy
from app.schemas.trading import AIAnalysisRequest
from app.services.indicators.technical import indicator_snapshot
from app.services.signals import build_signal_from_candles


logger = logging.getLogger(__name__)
_LOCAL_MODEL_INSTANCE = None


def get_local_llama_instance() -> Any | None:
    """
    Lazy-loader for the local LLM.
    Ensures the heavy model file is only loaded into RAM once.
    """
    global _LOCAL_MODEL_INSTANCE
    if _LOCAL_MODEL_INSTANCE is None:
        if Llama is None or not settings.local_model_path:
            logger.warning("Local Llama requested but llama-cpp-python is not installed or LOCAL_MODEL_PATH is unset.")
            return None

        try:
            logger.info("Loading local LLM from %s...", settings.local_model_path)
            _LOCAL_MODEL_INSTANCE = Llama(
                model_path=settings.local_model_path,
                n_ctx=2048,
                n_threads=settings.market_sync_interval_minutes,
                verbose=False,
                n_gpu_layers=-1 if "cuda" in (settings.database_url or "") else 0,
            )
            logger.info("Local LLM loaded successfully.")
        except Exception:
            logger.exception("Failed to load local LLM")
            return None

    return _LOCAL_MODEL_INSTANCE


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


class OllamaProvider(OpenAIProvider):
    """
    Provider for local LLMs via Ollama. 
    Reuses OpenAI parsing logic as Ollama can be prompted for JSON.
    """
    provider_name = "ollama"

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

        try:
            url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
            request_body = {
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
            response = httpx.post(url, json=request_body, timeout=60.0)
            response.raise_for_status()
            content = response.json().get("response", "")
            parsed = self._parse_analysis(content)
            
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
        except Exception:
            # Fallback to rules if local LLM fails or returns bad JSON
            return super(OpenAIProvider, self).analyze(payload, signal, candles, strategy, risk_settings, latest_backtest)


class LocalLlamaProvider(OpenAIProvider):
    """
    Advanced Provider for local LLMs using llama-cpp-python.
    Uses GBNF (Grammar-Based Next Token Selection) to force valid JSON output.
    """
    provider_name = "local-llama"

    # GBNF Grammar to force the LLM to strictly output the AIAnalysisResult JSON format
    JSON_GRAMMAR = r"""
    root   ::= object
    object ::= "{" space items "}"
    items  ::= pair ( "," space pair )*
    pair   ::= string ":" space value
    string ::= "\"" [^\"\\\n]* "\""
    value  ::= string | number | array | object | "true" | "false" | "null"
    number ::= [0-9]+ ("." [0-9]+)?
    array  ::= "[" space (value ( "," space value )*)? space "]"
    space  ::= [ \t\n\r]*
    """

    def analyze(
        self,
        payload: AIAnalysisRequest,
        signal: Signal | None,
        candles: list[MarketCandle],
        strategy: Strategy,
        risk_settings: RiskSetting,
        latest_backtest: BacktestRun | None,
    ) -> AIAnalysisResult:
        llm = get_local_llama_instance()
        if not llm:
            return self._fallback(payload, signal, candles, strategy, risk_settings, latest_backtest)

        # Gather context
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

        # Build prompt with explicit instruction formatting
        system_prompt = "You are a specialized financial analyst bot. You only output valid JSON."
        user_prompt = self._build_prompt(
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

        # Format for instruction models (ChatML style)
        full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"

        try:
            grammar = LlamaGrammar.from_string(self.JSON_GRAMMAR) if LlamaGrammar else None
            output = llm(
                full_prompt,
                max_tokens=600,
                stop=["<|im_end|>", "User:"],
                echo=False,
                grammar=grammar,
                temperature=0.1 # Low temperature for analytical consistency
            )
            
            content = output["choices"][0]["text"].strip()
            parsed = self._parse_analysis(content)
            
            # Ensure indicators map contains numeric values as expected by the schema
            formatted_indicators = {}
            for k, v in parsed.get("indicators", {}).items():
                try:
                    formatted_indicators[k] = float(v)
                except (ValueError, TypeError):
                    formatted_indicators[k] = snapshot.get(k, 0.0)

            # Merge with existing snapshot keys to ensure all required data is present
            for k, v in snapshot.items():
                if k not in formatted_indicators:
                    formatted_indicators[k] = float(v)

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
                indicators=formatted_indicators,
                backtest_summary=backtest_summary,
            )
        except Exception as e:
            logger.error(f"Local Llama analysis failed: {e}")
            return self._fallback(payload, signal, candles, strategy, risk_settings, latest_backtest)

    def _fallback(self, payload, signal, candles, strategy, risk_settings, latest_backtest):
        """Explicitly call the rule-based fallback when local LLM fails."""
        return RuleBasedAIProvider().analyze(payload, signal, candles, strategy, risk_settings, latest_backtest)


def get_ai_provider() -> AIProvider:
    provider_lower = settings.ai_provider.lower()
    if provider_lower == "openai":
        return OpenAIProvider()
    if provider_lower == "ollama":
        return OllamaProvider()
    if provider_lower == "local-llama":
        return LocalLlamaProvider()
    return RuleBasedAIProvider()
