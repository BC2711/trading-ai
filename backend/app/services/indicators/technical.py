import pandas as pd


def moving_average_snapshot(prices: list[float]) -> dict[str, float]:
    series = pd.Series(prices, dtype="float64")

    return {
        "latest": round(float(series.iloc[-1]), 4),
        "sma_3": round(float(series.rolling(window=3).mean().iloc[-1]), 4),
        "sma_5": round(float(series.rolling(window=5).mean().iloc[-1]), 4),
    }


def ema(values: list[float], period: int) -> float:
    series = pd.Series(values, dtype="float64")
    return round(float(series.ewm(span=period, adjust=False).mean().iloc[-1]), 4)


def rsi(values: list[float], period: int = 14) -> float:
    series = pd.Series(values, dtype="float64")
    delta = series.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    average_gain = gains.rolling(window=period, min_periods=period).mean()
    average_loss = losses.rolling(window=period, min_periods=period).mean()
    latest_loss = float(average_loss.iloc[-1])

    if latest_loss == 0:
        return 100.0

    relative_strength = float(average_gain.iloc[-1]) / latest_loss
    return round(float(100 - (100 / (1 + relative_strength))), 4)


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float:
    frame = pd.DataFrame({"high": highs, "low": lows, "close": closes}, dtype="float64")
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return round(float(true_range.rolling(window=period, min_periods=period).mean().iloc[-1]), 4)


def indicator_snapshot(
    closes: list[float],
    highs: list[float] | None = None,
    lows: list[float] | None = None,
) -> dict[str, float]:
    highs = highs or closes
    lows = lows or closes

    return {
        "close": round(float(closes[-1]), 4),
        "ema_9": ema(closes, 9),
        "ema_21": ema(closes, 21),
        "ema_200": ema(closes, min(200, len(closes))),
        "rsi_14": rsi(closes, 14),
        "atr_14": atr(highs, lows, closes, 14),
    }
