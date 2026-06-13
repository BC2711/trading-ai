from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def asset_from_symbol(symbol: str) -> str:
    if symbol.endswith("USDT"):
        return symbol.removesuffix("USDT")
    if symbol.endswith("USD"):
        return symbol.removesuffix("USD")
    return symbol


def parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return " ".join(value.strip().split())
    return ""
