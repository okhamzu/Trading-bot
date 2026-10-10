from __future__ import annotations

import math
from dataclasses import dataclass

from src.domain import SymbolSpecs


@dataclass(frozen=True)
class PositionSize:
    lots: float
    risk_amount: float
    actual_risk: float
    warning: str | None = None


def calculate_position_size(balance: float, risk_pct: float, entry: float, stop: float, specs: SymbolSpecs) -> PositionSize:
    risk_amount = balance * risk_pct / 100
    distance = abs(entry - stop)
    if distance <= 0 or specs.trade_tick_size <= 0 or specs.trade_tick_value <= 0:
        raise ValueError("Entry, stop, tick size and tick value must define positive risk")
    loss_per_lot = distance / specs.trade_tick_size * specs.trade_tick_value
    raw_lots = risk_amount / loss_per_lot
    lots = math.floor((raw_lots + 1e-12) / specs.volume_step) * specs.volume_step
    if lots < specs.volume_min:
        actual = loss_per_lot * specs.volume_min
        return PositionSize(0.0, risk_amount, actual, f"Minimum {specs.volume_min:g} lot would risk {actual:.2f}, above the {risk_pct:.2f}% target")
    lots = min(lots, specs.volume_max)
    precision = max(0, len(str(specs.volume_step).split(".")[-1].rstrip("0")))
    lots = round(lots, precision)
    return PositionSize(lots, risk_amount, loss_per_lot * lots)
