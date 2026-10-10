from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src.domain import Setup


@dataclass
class SimulatedTrade:
    setup: Setup
    status: str = "pending"
    fill_time: datetime | None = None
    fill_price: float | None = None
    close_time: datetime | None = None
    exit_price: float | None = None
    result_r: float | None = None


def update_trade(
    trade: SimulatedTrade,
    bar: pd.Series,
    *,
    point: float,
    spread_points: float,
    slippage_points: float,
    same_bar_rule: str = "sl_first",
) -> SimulatedTrade:
    setup = trade.setup
    timestamp = bar["close_time"]
    if trade.status == "pending":
        if timestamp > setup.expires_at:
            trade.status, trade.close_time, trade.result_r = "expired", timestamp, 0.0
            return trade
        touched = float(bar.low) <= setup.entry if setup.direction == "long" else float(bar.high) >= setup.entry
        invalidated = float(bar.close) < setup.entry_zone[0] if setup.direction == "long" else float(bar.close) > setup.entry_zone[1]
        target_before_entry = (float(bar.high) >= setup.targets[0] and float(bar.low) > setup.entry) if setup.direction == "long" else (float(bar.low) <= setup.targets[0] and float(bar.high) < setup.entry)
        if invalidated or target_before_entry:
            trade.status, trade.close_time, trade.result_r = "invalidated", timestamp, 0.0
            return trade
        if touched:
            spread = spread_points * point
            trade.status, trade.fill_time = "triggered", timestamp
            trade.fill_price = setup.entry + spread if setup.direction == "long" else setup.entry
        else:
            return trade

    if trade.status != "triggered":
        return trade
    stop_hit = float(bar.low) <= setup.stop if setup.direction == "long" else float(bar.high) >= setup.stop
    target = setup.targets[0]
    tp_hit = float(bar.high) >= target if setup.direction == "long" else float(bar.low) <= target
    if stop_hit and tp_hit and same_bar_rule == "sl_first":
        tp_hit = False
    if stop_hit:
        slip = slippage_points * point
        trade.status, trade.close_time, trade.result_r = "sl", timestamp, -1.0
        trade.exit_price = setup.stop - slip if setup.direction == "long" else setup.stop + slip
    elif tp_hit:
        trade.status, trade.close_time, trade.result_r = "tp1", timestamp, setup.r_to_target(target)
        trade.exit_price = target
    return trade
