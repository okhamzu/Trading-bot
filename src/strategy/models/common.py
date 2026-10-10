from __future__ import annotations

import hashlib
from datetime import datetime

from src.domain import LiquidityPool


def setup_id(symbol: str, model: str, direction: str, key_time: datetime) -> str:
    raw = f"{symbol}|{model}|{direction}|{key_time.isoformat()}".encode()
    return hashlib.sha256(raw).hexdigest()[:20]


def targets_from_pools(pools: list[LiquidityPool], direction: str, entry: float, fallback: float | None = None) -> list[float]:
    if direction == "long":
        values = sorted({pool.price for pool in pools if pool.side == "buy" and pool.status == "active" and pool.price > entry})
    else:
        values = sorted({pool.price for pool in pools if pool.side == "sell" and pool.status == "active" and pool.price < entry}, reverse=True)
    if fallback is not None and ((direction == "long" and fallback > entry) or (direction == "short" and fallback < entry)):
        values.append(fallback)
    return list(dict.fromkeys(values))[:3]


def reward_risk(entry: float, stop: float, target: float) -> float:
    risk = abs(entry - stop)
    return abs(target - entry) / risk if risk else 0.0
