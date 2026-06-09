from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

try:
    import torch
    from torch import nn
except Exception:  # pragma: no cover - depends on optional local dependency install
    torch = None

    class _MissingModule:
        pass

    class _MissingNN:
        Module = _MissingModule

    nn = _MissingNN()


class TorchDependencyError(RuntimeError):
    pass


def ensure_torch() -> None:
    if torch is None:
        raise TorchDependencyError("PyTorch is required for native LSTM, GRU, and Transformer models")


class LSTMNetwork(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int, dropout: float) -> None:
        ensure_torch()
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.output = nn.Linear(hidden_dim, 1)

    def forward(self, values: Any) -> Any:
        output, _hidden = self.lstm(values)
        return self.output(output[:, -1, :]).squeeze(-1)


class GRUNetwork(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int, dropout: float) -> None:
        ensure_torch()
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.output = nn.Linear(hidden_dim, 1)

    def forward(self, values: Any) -> Any:
        output, _hidden = self.gru(values)
        return self.output(output[:, -1, :]).squeeze(-1)


class TransformerNetwork(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int, dropout: float, num_heads: int) -> None:
        ensure_torch()
        super().__init__()
        self.input_projection = nn.Linear(input_dim, hidden_dim)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.output = nn.Linear(hidden_dim, 1)

    def forward(self, values: Any) -> Any:
        encoded = self.encoder(self.input_projection(values))
        return self.output(encoded[:, -1, :]).squeeze(-1)


@dataclass
class TorchTrainingConfig:
    architecture: str
    hidden_dim: int = 64
    num_layers: int = 1
    dropout: float = 0.1
    sequence_length: int = 12
    epochs: int = 20
    batch_size: int = 32
    learning_rate: float = 0.001
    random_state: int = 42
    num_heads: int = 4


class TorchSequenceClassifier:
    def __init__(self, **kwargs: Any) -> None:
        self.config = TorchTrainingConfig(**kwargs)
        self.network = None
        self.feature_mean: np.ndarray | None = None
        self.feature_std: np.ndarray | None = None

    def fit(self, features: list[list[float]], labels: list[int]) -> "TorchSequenceClassifier":
        ensure_torch()
        torch.manual_seed(self.config.random_state)

        x = np.asarray(features, dtype=np.float32)
        y = np.asarray(labels, dtype=np.float32)
        self.feature_mean = x.mean(axis=0)
        self.feature_std = x.std(axis=0)
        self.feature_std[self.feature_std == 0] = 1.0
        x = (x - self.feature_mean) / self.feature_std

        sequences = to_sequences(x, self.config.sequence_length)
        x_tensor = torch.tensor(sequences, dtype=torch.float32)
        y_tensor = torch.tensor(y, dtype=torch.float32)
        dataset = torch.utils.data.TensorDataset(x_tensor, y_tensor)
        generator = torch.Generator().manual_seed(self.config.random_state)
        loader = torch.utils.data.DataLoader(
            dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            generator=generator,
        )

        self.network = build_network(self.config, input_dim=x.shape[1])
        optimizer = torch.optim.Adam(self.network.parameters(), lr=self.config.learning_rate)
        loss_fn = nn.BCEWithLogitsLoss()

        self.network.train()
        for _epoch in range(self.config.epochs):
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                logits = self.network(batch_x)
                loss = loss_fn(logits, batch_y)
                loss.backward()
                optimizer.step()
        return self

    def predict_proba(self, features: list[list[float]]) -> np.ndarray:
        ensure_torch()
        if self.network is None or self.feature_mean is None or self.feature_std is None:
            raise RuntimeError("Model has not been fitted")

        x = np.asarray(features, dtype=np.float32)
        x = (x - self.feature_mean) / self.feature_std
        sequences = to_sequences(x, self.config.sequence_length)
        self.network.eval()
        with torch.no_grad():
            logits = self.network(torch.tensor(sequences, dtype=torch.float32))
            probabilities = torch.sigmoid(logits).detach().cpu().numpy()
        return np.asarray([[1 - value, value] for value in probabilities], dtype=np.float32)

    def predict(self, features: list[list[float]]) -> np.ndarray:
        probabilities = self.predict_proba(features)[:, 1]
        return (probabilities >= 0.5).astype(int)


def build_network(config: TorchTrainingConfig, input_dim: int):
    architecture = config.architecture.lower()
    if architecture == "lstm":
        return LSTMNetwork(input_dim, config.hidden_dim, config.num_layers, config.dropout)
    if architecture == "gru":
        return GRUNetwork(input_dim, config.hidden_dim, config.num_layers, config.dropout)
    if architecture == "transformer":
        num_heads = choose_valid_heads(config.hidden_dim, config.num_heads)
        return TransformerNetwork(input_dim, config.hidden_dim, config.num_layers, config.dropout, num_heads)
    raise ValueError(f"Unsupported PyTorch architecture: {config.architecture}")


def choose_valid_heads(hidden_dim: int, requested_heads: int) -> int:
    for heads in range(max(1, requested_heads), 0, -1):
        if hidden_dim % heads == 0:
            return heads
    return 1


def to_sequences(features: np.ndarray, sequence_length: int) -> np.ndarray:
    sequence_length = max(1, sequence_length)
    sequences = []
    for index in range(len(features)):
        start = max(0, index - sequence_length + 1)
        window = features[start : index + 1]
        if len(window) < sequence_length:
            padding = np.repeat(window[:1], sequence_length - len(window), axis=0)
            window = np.vstack([padding, window])
        sequences.append(window)
    return np.asarray(sequences, dtype=np.float32)
