from __future__ import annotations

import pandas as pd


def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().rename("atr")


def with_atr(frame: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    result = frame.copy()
    result["atr"] = atr(result, period)
    return result
