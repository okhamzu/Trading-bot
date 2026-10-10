from __future__ import annotations

import pandas as pd


def displacement_mask(frame: pd.DataFrame, min_body_atr: float = 1.2, min_body_to_range: float = 0.6) -> pd.Series:
    body = (frame["close"] - frame["open"]).abs()
    candle_range = (frame["high"] - frame["low"]).replace(0, float("nan"))
    atr_values = frame["atr"] if "atr" in frame else pd.Series(float("nan"), index=frame.index)
    return ((body >= min_body_atr * atr_values) & (body / candle_range >= min_body_to_range)).fillna(False)


def direction(frame: pd.DataFrame) -> pd.Series:
    return pd.Series(
        ["bullish" if close > open_ else "bearish" if close < open_ else "neutral" for open_, close in zip(frame.open, frame.close)],
        index=frame.index,
        name="candle_direction",
    )
