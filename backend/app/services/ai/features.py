from dataclasses import dataclass

import pandas as pd

from app.models import MarketCandle


FEATURE_COLUMNS = [
    "close",
    "volume",
    "spread",
    "return_1",
    "candle_body",
    "range_pct",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_histogram",
    "ema_9",
    "ema_21",
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


class FeatureService:
    def build_dataset(self, candles: list[MarketCandle]) -> FeatureDataset:
        if len(candles) < 80:
            raise ValueError("At least 80 candles are required for feature engineering")

        frame = candles_to_frame(candles)
        enriched = add_features(frame)
        enriched["target"] = (enriched["close"].shift(-1) > enriched["close"]).astype(int)
        enriched = enriched.dropna().reset_index(drop=True)

        if len(enriched) < 40:
            raise ValueError("Not enough valid feature rows to train a model")

        training_rows = enriched.iloc[:-1]
        latest_row = enriched.iloc[-1]
        features = training_rows[FEATURE_COLUMNS].astype("float64").values.tolist()
        labels = training_rows["target"].astype(int).tolist()
        latest_features = latest_row[FEATURE_COLUMNS].astype("float64").tolist()
        latest_feature_map = {name: round(float(value), 8) for name, value in zip(FEATURE_COLUMNS, latest_features)}

        return FeatureDataset(
            features=features,
            labels=labels,
            feature_names=FEATURE_COLUMNS,
            latest_features=latest_features,
            latest_feature_map=latest_feature_map,
            rows=len(features),
        )


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
    data["return_1"] = data["close"].pct_change()
    data["candle_body"] = (data["close"] - data["open"]) / data["open"].replace(0, pd.NA)
    data["range_pct"] = (data["high"] - data["low"]) / data["close"].replace(0, pd.NA)
    data["rsi_14"] = rsi_series(data["close"], 14)

    macd_line, macd_signal, macd_histogram = macd_series(data["close"])
    data["macd"] = macd_line
    data["macd_signal"] = macd_signal
    data["macd_histogram"] = macd_histogram

    data["ema_9"] = data["close"].ewm(span=9, adjust=False).mean()
    data["ema_21"] = data["close"].ewm(span=21, adjust=False).mean()
    data["sma_20"] = data["close"].rolling(window=20, min_periods=20).mean()
    data["sma_50"] = data["close"].rolling(window=50, min_periods=50).mean()
    data["atr_14"] = atr_series(data, 14)
    data["adx_14"] = adx_series(data, 14)

    bb_mid, bb_upper, bb_lower = bollinger_bands(data["close"], 20, 2.0)
    data["bb_mid"] = bb_mid
    data["bb_upper"] = bb_upper
    data["bb_lower"] = bb_lower
    data["bb_width"] = (bb_upper - bb_lower) / bb_mid.replace(0, pd.NA)

    data["volume_sma_20"] = data["volume"].rolling(window=20, min_periods=20).mean()
    data["volume_ratio"] = data["volume"] / data["volume_sma_20"].replace(0, pd.NA)
    data["obv"] = on_balance_volume(data["close"], data["volume"])
    return data.replace([float("inf"), float("-inf")], pd.NA)


def rsi_series(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.rolling(window=period, min_periods=period).mean()
    average_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = average_gain / average_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def macd_series(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast = close.ewm(span=12, adjust=False).mean()
    slow = close.ewm(span=26, adjust=False).mean()
    macd_line = fast - slow
    signal = macd_line.ewm(span=9, adjust=False).mean()
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
    middle = close.rolling(window=period, min_periods=period).mean()
    std = close.rolling(window=period, min_periods=period).std()
    return middle, middle + (std * deviation), middle - (std * deviation)


def on_balance_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = close.diff().apply(lambda value: 1 if value > 0 else -1 if value < 0 else 0)
    return (direction * volume).fillna(0).cumsum()
