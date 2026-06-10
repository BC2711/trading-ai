from dataclasses import dataclass

import pandas as pd

from app.models import MarketCandle


FEATURE_COLUMNS = [
    "close",
    "volume",
    "spread",
    "return_1",
    "price_change",
    "volume_change",
    "candle_body",
    "candle_body_size",
    "upper_wick_size",
    "lower_wick_size",
    "range_pct",
    "volatility_20",
    "trend_direction",
    "support_distance",
    "resistance_distance",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_histogram",
    "ema_9",
    "ema_20",
    "ema_21",
    "ema_50",
    "sma_20",
    "sma_50",
    "atr_14",
    "adx_14",
    "bb_mid",
    "bb_upper",
    "bb_lower",
    "bb_width",
    "volume_sma_20",
    "volume_ratio",
    "obv",
]


@dataclass
class FeatureDataset:
    features: list[list[float]]
    labels: list[int]
    feature_names: list[str]
    latest_features: list[float]
    latest_feature_map: dict[str, float]
    rows: int


class FeatureCalculator:
    def build_dataset(self, candles: list[MarketCandle], selected_features: list[str] | None = None) -> FeatureDataset:
        if len(candles) < 80:
            raise ValueError("At least 80 candles are required for feature engineering")

        feature_columns = validate_feature_columns(selected_features)
        frame = candles_to_frame(candles)
        enriched = add_features(frame)
        enriched["target"] = (enriched["close"].shift(-1) > enriched["close"]).astype(int)
        enriched = enriched.dropna().reset_index(drop=True)

        if len(enriched) < 40:
            raise ValueError("Not enough valid feature rows to train a model")

        training_rows = enriched.iloc[:-1]
        latest_row = enriched.iloc[-1]
        features = training_rows[feature_columns].astype("float64").values.tolist()
        labels = training_rows["target"].astype(int).tolist()
        latest_features = latest_row[feature_columns].astype("float64").tolist()
        latest_feature_map = {name: round(float(value), 8) for name, value in zip(feature_columns, latest_features)}

        return FeatureDataset(
            features=features,
            labels=labels,
            feature_names=feature_columns,
            latest_features=latest_features,
            latest_feature_map=latest_feature_map,
            rows=len(features),
        )

    def calculate_frame(self, candles: list[MarketCandle]) -> pd.DataFrame:
        if len(candles) < 80:
            raise ValueError("At least 80 candles are required for feature calculation")
        return add_features(candles_to_frame(candles)).dropna().reset_index(drop=True)

    def latest_feature_map(self, candles: list[MarketCandle]) -> dict[str, float]:
        enriched = self.calculate_frame(candles)
        latest = enriched.iloc[-1]
        return {name: round(float(latest[name]), 8) for name in FEATURE_COLUMNS}

    def indicator_value(self, candles: list[MarketCandle], indicator: str | None, period: int | None = None) -> float:
        if indicator is None:
            return 0.0
        frame = candles_to_frame(candles)
        close = frame["close"]
        normalized = indicator.upper()
        if normalized == "RSI":
            return round(float(rsi_series(close, period or 14).iloc[-1]), 6)
        if normalized == "EMA":
            return round(float(ema_series(close, period or 20).iloc[-1]), 6)
        if normalized == "SMA":
            return round(float(sma_series(close, period or 20).iloc[-1]), 6)
        if normalized == "MACD":
            macd_line, _signal, _histogram = macd_series(close)
            return round(float(macd_line.iloc[-1]), 6)
        if normalized == "BOLLINGER_BANDS":
            middle, upper, lower = bollinger_bands(close, period or 20, 2.0)
            width = float(upper.iloc[-1] - lower.iloc[-1]) or 1.0
            return round(float((close.iloc[-1] - lower.iloc[-1]) / width), 6)
        if normalized == "ATR":
            return round(float(atr_series(frame, period or 14).iloc[-1]), 6)
        if normalized == "VOLUME":
            return round(float(frame["volume"].iloc[-1]), 6)
        if normalized == "PRICE_CHANGE":
            lookback = period or 1
            if len(close) <= lookback:
                return 0.0
            previous = float(close.iloc[-lookback - 1])
            return 0.0 if previous == 0 else round(float((close.iloc[-1] - previous) / previous), 6)
        raise ValueError(f"Unsupported indicator: {indicator}")

    def builder_snapshot(self, candles: list[MarketCandle]) -> dict[str, float]:
        return {
            "RSI14": self.indicator_value(candles, "RSI", 14),
            "MACD": self.indicator_value(candles, "MACD"),
            "EMA20": self.indicator_value(candles, "EMA", 20),
            "EMA50": self.indicator_value(candles, "EMA", 50),
            "SMA20": self.indicator_value(candles, "SMA", 20),
            "BOLLINGER_BANDS20": self.indicator_value(candles, "BOLLINGER_BANDS", 20),
            "ATR14": self.indicator_value(candles, "ATR", 14),
            "VOLUME": self.indicator_value(candles, "VOLUME"),
            "PRICE_CHANGE": self.indicator_value(candles, "PRICE_CHANGE"),
        }


def candles_to_frame(candles: list[MarketCandle]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "opened_at": candle.opened_at,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
                "spread": getattr(candle, "spread", 0.0) or 0.0,
            }
            for candle in candles
        ]
    ).sort_values("opened_at")


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    previous_close = data["close"].shift(1)
    candle_range = (data["high"] - data["low"]).replace(0, pd.NA)
    body = data["close"] - data["open"]

    data["return_1"] = data["close"].pct_change()
    data["price_change"] = data["return_1"]
    data["volume_change"] = data["volume"].pct_change()
    data["candle_body"] = body / data["open"].replace(0, pd.NA)
    data["candle_body_size"] = body.abs() / candle_range
    data["upper_wick_size"] = (data["high"] - data[["open", "close"]].max(axis=1)) / candle_range
    data["lower_wick_size"] = (data[["open", "close"]].min(axis=1) - data["low"]) / candle_range
    data["range_pct"] = (data["high"] - data["low"]) / data["close"].replace(0, pd.NA)
    data["volatility_20"] = data["return_1"].rolling(window=20, min_periods=20).std()
    data["rsi_14"] = rsi_series(data["close"], 14)

    macd_line, macd_signal, macd_histogram = macd_series(data["close"])
    data["macd"] = macd_line
    data["macd_signal"] = macd_signal
    data["macd_histogram"] = macd_histogram

    data["ema_9"] = ema_series(data["close"], 9)
    data["ema_20"] = ema_series(data["close"], 20)
    data["ema_21"] = ema_series(data["close"], 21)
    data["ema_50"] = ema_series(data["close"], 50)
    data["sma_20"] = sma_series(data["close"], 20)
    data["sma_50"] = sma_series(data["close"], 50)
    data["atr_14"] = atr_series(data, 14)
    data["adx_14"] = adx_series(data, 14)

    bb_mid, bb_upper, bb_lower = bollinger_bands(data["close"], 20, 2.0)
    data["bb_mid"] = bb_mid
    data["bb_upper"] = bb_upper
    data["bb_lower"] = bb_lower
    data["bb_width"] = (bb_upper - bb_lower) / bb_mid.replace(0, pd.NA)

    support = data["low"].rolling(window=20, min_periods=20).min()
    resistance = data["high"].rolling(window=20, min_periods=20).max()
    data["support_distance"] = (data["close"] - support) / data["close"].replace(0, pd.NA)
    data["resistance_distance"] = (resistance - data["close"]) / data["close"].replace(0, pd.NA)
    data["trend_direction"] = trend_direction(data["ema_20"], data["ema_50"], data["close"], previous_close)

    data["volume_sma_20"] = data["volume"].rolling(window=20, min_periods=20).mean()
    data["volume_ratio"] = data["volume"] / data["volume_sma_20"].replace(0, pd.NA)
    data["obv"] = on_balance_volume(data["close"], data["volume"])
    return data.replace([float("inf"), float("-inf")], pd.NA)


def sma_series(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period, min_periods=period).mean()


def ema_series(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean()


def rsi_series(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.rolling(window=period, min_periods=period).mean()
    average_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = average_gain / average_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def macd_series(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast = ema_series(close, 12)
    slow = ema_series(close, 26)
    macd_line = fast - slow
    signal = ema_series(macd_line, 9)
    return macd_line, signal, macd_line - signal


def atr_series(frame: pd.DataFrame, period: int) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window=period, min_periods=period).mean()


def adx_series(frame: pd.DataFrame, period: int) -> pd.Series:
    high_diff = frame["high"].diff()
    low_diff = -frame["low"].diff()
    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0.0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0.0)
    atr = atr_series(frame, period).replace(0, pd.NA)
    plus_di = 100 * plus_dm.rolling(window=period, min_periods=period).sum() / atr
    minus_di = 100 * minus_dm.rolling(window=period, min_periods=period).sum() / atr
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)) * 100
    return dx.rolling(window=period, min_periods=period).mean()


def bollinger_bands(close: pd.Series, period: int, deviation: float) -> tuple[pd.Series, pd.Series, pd.Series]:
    middle = sma_series(close, period)
    std = close.rolling(window=period, min_periods=period).std()
    return middle, middle + (std * deviation), middle - (std * deviation)


def on_balance_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = close.diff().apply(lambda value: 1 if value > 0 else -1 if value < 0 else 0)
    return (direction * volume).fillna(0).cumsum()


def trend_direction(ema_fast: pd.Series, ema_slow: pd.Series, close: pd.Series, previous_close: pd.Series) -> pd.Series:
    direction = pd.Series(0.0, index=close.index)
    direction = direction.where(~((ema_fast > ema_slow) & (close > previous_close)), 1.0)
    direction = direction.where(~((ema_fast < ema_slow) & (close < previous_close)), -1.0)
    return direction


def validate_feature_columns(selected_features: list[str] | None = None) -> list[str]:
    if not selected_features:
        return FEATURE_COLUMNS
    unknown = [name for name in selected_features if name not in FEATURE_COLUMNS]
    if unknown:
        raise ValueError(f"Unsupported feature columns: {', '.join(unknown)}")
    return list(dict.fromkeys(selected_features))
