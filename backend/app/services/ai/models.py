from pathlib import Path
from typing import Any
import importlib.util
import pickle

from sklearn.ensemble import GradientBoostingClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.services.ai.torch_models import TorchSequenceClassifier

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover - depends on optional environment
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover - depends on optional environment
    LGBMClassifier = None


SUPPORTED_MODEL_TYPES = {"random_forest", "xgboost", "lightgbm", "lstm", "gru", "transformer"}
MODEL_DIR = Path(".tmp/models")


class ModelService:
    def create_model(self, model_type: str, params: dict | None = None) -> tuple[Any, dict]:
        normalized = normalize_model_type(model_type)
        params = params or {}

        if normalized == "random_forest":
            defaults = {"n_estimators": 120, "random_state": 42, "max_depth": 6}
            defaults.update(params)
            return RandomForestClassifier(**defaults), {"runtime_adapter": "sklearn.random_forest", **defaults}

        if normalized == "xgboost":
            defaults = {"n_estimators": 120, "max_depth": 4, "learning_rate": 0.05, "eval_metric": "logloss", "random_state": 42}
            defaults.update(params)
            if XGBClassifier is not None:
                return XGBClassifier(**defaults), {"runtime_adapter": "xgboost", **defaults}
            return GradientBoostingClassifier(random_state=42), {"runtime_adapter": "sklearn.gradient_boosting_fallback", **defaults}

        if normalized == "lightgbm":
            defaults = {"n_estimators": 120, "learning_rate": 0.05, "random_state": 42}
            defaults.update(params)
            if LGBMClassifier is not None:
                return LGBMClassifier(**defaults), {"runtime_adapter": "lightgbm", **defaults}
            return HistGradientBoostingClassifier(random_state=42), {"runtime_adapter": "sklearn.hist_gradient_boosting_fallback", **defaults}

        if normalized in {"lstm", "gru", "transformer"}:
            if is_package_available("torch"):
                defaults = {
                    "architecture": normalized,
                    "hidden_dim": 64 if normalized != "transformer" else 96,
                    "num_layers": 1,
                    "dropout": 0.1,
                    "sequence_length": 12,
                    "epochs": 20,
                    "batch_size": 32,
                    "learning_rate": 0.001,
                    "random_state": 42,
                    "num_heads": 4,
                }
                defaults.update({key: value for key, value in params.items() if key in defaults})
                return TorchSequenceClassifier(**defaults), {"runtime_adapter": f"pytorch.{normalized}", **defaults}

            hidden_layers = {
                "lstm": (64, 32),
                "gru": (48, 24),
                "transformer": (96, 48, 24),
            }[normalized]
            defaults = {"hidden_layer_sizes": hidden_layers, "max_iter": 500, "random_state": 42, "early_stopping": True}
            defaults.update({key: value for key, value in params.items() if key in defaults})
            model = Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("classifier", MLPClassifier(**defaults)),
                ]
            )
            return model, {"runtime_adapter": f"sklearn.mlp_{normalized}_fallback_missing_torch", **defaults}

        raise ValueError(f"Unsupported model type: {model_type}")

    def save_model(self, model: Any, *, name: str, symbol: str, timeframe: str, model_type: str, version: int) -> Path:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = name.lower().replace(" ", "-")
        path = MODEL_DIR / f"{safe_name}-{symbol.upper()}-{timeframe}-{model_type}-v{version}.pkl"
        with path.open("wb") as file:
            pickle.dump(model, file)
        return path

    def load_model(self, model_path: str) -> Any:
        with Path(model_path).open("rb") as file:
            return pickle.load(file)


def normalize_model_type(model_type: str) -> str:
    normalized = model_type.lower().replace("-", "_")
    if normalized not in SUPPORTED_MODEL_TYPES:
        raise ValueError(f"Unsupported model type: {model_type}")
    return normalized


def is_package_available(package_name: str) -> bool:
    return importlib.util.find_spec(package_name) is not None
