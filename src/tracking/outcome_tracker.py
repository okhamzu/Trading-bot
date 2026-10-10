from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.domain import Setup


@dataclass(frozen=True)
class Outcome:
    status: str
    result_r: float | None
    price: float | None


def update_outcome(setup: Setup, bar: pd.Series) -> Outcome | None:
    was_pending = setup.status == "pending"
    if bar.close_time <= setup.created_at:
        return None
    if setup.status == "pending":
        if bar.close_time > setup.expires_at:
            setup.status = "expired"
            return Outcome("expired", 0.0, None)
        touched = float(bar.low) <= setup.entry if setup.direction == "long" else float(bar.high) >= setup.entry
        invalidated = float(bar.close) < setup.entry_zone[0] if setup.direction == "long" else float(bar.close) > setup.entry_zone[1]
        target_before_entry = (float(bar.high) >= setup.targets[0] and float(bar.low) > setup.entry) if setup.direction == "long" else (float(bar.low) <= setup.targets[0] and float(bar.high) < setup.entry)
        if invalidated or target_before_entry:
            setup.status = "invalidated"
            return Outcome("invalidated", 0.0, float(bar.close))
        if touched:
            setup.status = "triggered"
        else:
            return None
    if setup.status != "triggered":
        return None
    stop_hit = float(bar.low) <= setup.stop if setup.direction == "long" else float(bar.high) >= setup.stop
    tp_hit = float(bar.high) >= setup.targets[0] if setup.direction == "long" else float(bar.low) <= setup.targets[0]
    if stop_hit:  # conservative when both are inside the same candle
        setup.status = "sl"
        return Outcome("sl", -1.0, setup.stop)
    if tp_hit:
        setup.status = "tp1"
        return Outcome("tp1", setup.r_to_target(setup.targets[0]), setup.targets[0])
    if was_pending and setup.status == "triggered":
        return Outcome("triggered", None, setup.entry)
    return None
