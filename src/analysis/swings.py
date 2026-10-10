from __future__ import annotations

from dataclasses import replace

import pandas as pd

from src.domain import Swing


def _raw_swings(frame: pd.DataFrame, lookback: int) -> list[Swing]:
    swings: list[Swing] = []
    if lookback < 1:
        raise ValueError("Swing lookback must be at least 1")
    for index in range(lookback, len(frame) - lookback):
        high = float(frame.at[index, "high"])
        low = float(frame.at[index, "low"])
        left_highs = frame.loc[index - lookback : index - 1, "high"]
        right_highs = frame.loc[index + 1 : index + lookback, "high"]
        left_lows = frame.loc[index - lookback : index - 1, "low"]
        right_lows = frame.loc[index + 1 : index + lookback, "low"]
        confirmed_at = frame.at[index + lookback, "close_time"]
        if high > float(left_highs.max()) and high >= float(right_highs.max()):
            swings.append(Swing(index, frame.at[index, "time"], confirmed_at, high, "high"))
        if low < float(left_lows.min()) and low <= float(right_lows.min()):
            swings.append(Swing(index, frame.at[index, "time"], confirmed_at, low, "low"))
    return sorted(swings, key=lambda item: (item.index, 0 if item.kind == "low" else 1))


def _alternate(swings: list[Swing]) -> list[Swing]:
    result: list[Swing] = []
    for swing in swings:
        if not result or result[-1].kind != swing.kind:
            result.append(swing)
            continue
        previous = result[-1]
        more_extreme = swing.price > previous.price if swing.kind == "high" else swing.price < previous.price
        if more_extreme:
            result[-1] = swing
    return result


def detect_swings(frame: pd.DataFrame, lookback: int = 3) -> list[Swing]:
    swings = _alternate(_raw_swings(frame, lookback))
    previous_price: dict[str, float] = {}
    labelled: list[Swing] = []
    for swing in swings:
        prior = previous_price.get(swing.kind)
        label = None
        pending = False
        if prior is not None:
            if swing.kind == "high":
                label = "HH" if swing.price > prior else "LH"
                pending = label == "LH"
            else:
                label = "HL" if swing.price > prior else "LL"
                pending = label == "HL"
        labelled.append(replace(swing, label=label, pending=pending))
        previous_price[swing.kind] = swing.price

    confirmed: list[Swing] = []
    for position, swing in enumerate(labelled):
        if not swing.pending:
            confirmed.append(swing)
            continue
        earlier_opposites = [item for item in labelled[:position] if item.kind != swing.kind]
        if not earlier_opposites:
            confirmed.append(swing)
            continue
        opposing = earlier_opposites[-1]
        later = frame.loc[frame["close_time"] >= swing.confirmed_at]
        if swing.kind == "low":
            confirmation_hits = later.index[later["close"] > opposing.price].tolist()
            invalidation_hits = later.index[later["close"] < swing.price].tolist()
        else:
            confirmation_hits = later.index[later["close"] < opposing.price].tolist()
            invalidation_hits = later.index[later["close"] > swing.price].tolist()
        confirmation_index = confirmation_hits[0] if confirmation_hits else None
        invalidation_index = invalidation_hits[0] if invalidation_hits else None
        if invalidation_index is not None and (confirmation_index is None or invalidation_index < confirmation_index):
            # A candidate HL/LH that fails first is not allowed to retain that label.
            confirmed.append(replace(swing, label=None, pending=False))
        else:
            confirmed.append(replace(swing, pending=confirmation_index is None))
    return confirmed
