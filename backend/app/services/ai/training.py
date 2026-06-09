from pathlib import Path
import pickle

from sqlalchemy.orm import Session
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from app.models import AIModelMetadata, MarketCandle
from app.services.audit import record_event
from app.services.indicators.technical import atr, ema, rsi
from app.services.repository import get_symbol, list_candles, seed_defaults

MODEL_DIR = Path(".tmp/models")


def build_dataset(candles: list[MarketCandle]) -> tuple[list[list[float]], list[int]]:
    features: list[list[float]] = []
    labels: list[int] = []
    closes = [candle.close for candle in candles]
    highs = [candle.high for candle in candles]
    lows = [candle.low for candle in candles]

    for index in range(30, len(candles) - 1):
        window = closes[: index + 1]
        current = candles[index]
        next_close = candles[index + 1].close
        feature = [
            current.close,
            current.volume,
            ema(window[-12:], min(12, len(window[-12:]))),
            ema(window[-26:], min(26, len(window[-26:]))),
            rsi(window[-15:], 14),
            atr(highs[max(0, index - 14) : index + 1], lows[max(0, index - 14) : index + 1], closes[max(0, index - 14) : index + 1], 14),
            (current.close - current.open) / current.open if current.open else 0,
        ]
        features.append(feature)
        labels.append(1 if next_close > current.close else 0)

    return features, labels


def train_model(db: Session, *, name: str, symbol: str, timeframe: str, lookback: int) -> AIModelMetadata:
    seed_defaults(db)
    symbol_model = get_symbol(db, symbol)
    if symbol_model is None:
        raise ValueError(f"Symbol {symbol.upper()} is not configured")

    candles = list_candles(db, symbol_model.symbol, timeframe, lookback)
    features, labels = build_dataset(candles)
    if len(features) < 40 or len(set(labels)) < 2:
        raise ValueError("Not enough varied candle history to train a model")

    train_features, test_features, train_labels, test_labels = train_test_split(
        features,
        labels,
        test_size=0.25,
        shuffle=False,
    )
    model = RandomForestClassifier(n_estimators=80, random_state=42, max_depth=5)
    model.fit(train_features, train_labels)
    predictions = model.predict(test_features)
    probabilities = model.predict_proba(test_features)

    metrics = {
        "accuracy": round(float(accuracy_score(test_labels, predictions)), 6),
        "precision": round(float(precision_score(test_labels, predictions, zero_division=0)), 6),
        "recall": round(float(recall_score(test_labels, predictions, zero_division=0)), 6),
        "samples": len(features),
        "confidence": round(float(max(probabilities[-1])), 6) if len(probabilities) else 0.0,
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / f"{name.lower().replace(' ', '-')}-{symbol_model.symbol}-{timeframe}.pkl"
    with model_path.open("wb") as file:
        pickle.dump(model, file)

    metadata = AIModelMetadata(
        name=name,
        symbol=symbol_model.symbol,
        timeframe=timeframe,
        model_type="random_forest",
        model_path=str(model_path),
        metrics=metrics,
        status="trained",
    )
    db.add(metadata)
    db.commit()
    db.refresh(metadata)
    record_event(
        db,
        event_type="ai_model.trained",
        entity_type="ai_model",
        entity_id=metadata.id,
        message=f"Trained AI model {metadata.name} for {metadata.symbol}.",
        metadata=metrics,
        commit=True,
    )
    return metadata


def predict(db: Session, model_id: int) -> dict:
    metadata = db.get(AIModelMetadata, model_id)
    if metadata is None:
        raise ValueError("AI model not found")

    candles = list_candles(db, metadata.symbol, metadata.timeframe, 80)
    features, _labels = build_dataset(candles)
    if not features:
        raise ValueError("Not enough candle history to predict")

    with Path(metadata.model_path).open("rb") as file:
        model = pickle.load(file)

    probabilities = model.predict_proba([features[-1]])[0]
    up_confidence = float(probabilities[1]) if len(probabilities) > 1 else 0.0
    direction = "buy" if up_confidence >= 0.5 else "sell"
    confidence = up_confidence if direction == "buy" else 1 - up_confidence
    return {
        "model_id": metadata.id,
        "symbol": metadata.symbol,
        "direction": direction,
        "confidence": round(confidence, 6),
        "features": {
            "close": features[-1][0],
            "volume": features[-1][1],
            "ema_fast": features[-1][2],
            "ema_slow": features[-1][3],
            "rsi": features[-1][4],
            "atr": features[-1][5],
            "candle_return": features[-1][6],
        },
    }
