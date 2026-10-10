from __future__ import annotations

import pandas as pd

from src.domain import StructureEvent, Swing


def detect_structure(
    frame: pd.DataFrame,
    swings: list[Swing],
    break_confirmation: str = "close",
    displacement: pd.Series | None = None,
) -> list[StructureEvent]:
    if break_confirmation not in {"close", "wick"}:
        raise ValueError("break_confirmation must be close or wick")
    events: list[StructureEvent] = []
    known: list[Swing] = []
    broken: set[int] = set()
    state = "undefined"
    protected_low: Swing | None = None
    protected_high: Swing | None = None

    for index, bar in frame.iterrows():
        known.extend(item for item in swings if item.confirmed_at == bar["close_time"] and item not in known)
        highs = [item for item in known if item.kind == "high" and item.index not in broken]
        lows = [item for item in known if item.kind == "low" and item.index not in broken]
        last_high = highs[-1] if highs else None
        last_low = lows[-1] if lows else None
        up_value = float(bar["close"] if break_confirmation == "close" else bar["high"])
        down_value = float(bar["close"] if break_confirmation == "close" else bar["low"])
        is_displacement = bool(displacement is not None and displacement.get(index, False))

        event: StructureEvent | None = None
        if state == "bullish" and protected_low and down_value < protected_low.price:
            event = StructureEvent(index, bar["close_time"], "MSS" if is_displacement else "CHOCH", "bearish", protected_low.price, protected_low.index)
            state, protected_high = "bearish", last_high
        elif state == "bearish" and protected_high and up_value > protected_high.price:
            event = StructureEvent(index, bar["close_time"], "MSS" if is_displacement else "CHOCH", "bullish", protected_high.price, protected_high.index)
            state, protected_low = "bullish", last_low
        elif last_high and up_value > last_high.price:
            event = StructureEvent(index, bar["close_time"], "BOS", "bullish", last_high.price, last_high.index)
            state, protected_low = "bullish", last_low
        elif last_low and down_value < last_low.price:
            event = StructureEvent(index, bar["close_time"], "BOS", "bearish", last_low.price, last_low.index)
            state, protected_high = "bearish", last_high

        if event and event.broken_swing_index not in broken:
            events.append(event)
            broken.add(event.broken_swing_index)
    return events


def structure_direction(events: list[StructureEvent]) -> str:
    return events[-1].direction if events else "neutral"
