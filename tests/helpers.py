from __future__ import annotations

import pandas as pd

from src.utils.timeutils import add_close_time


def candles(rows, timeframe: str = "M15") -> pd.DataFrame:
    time = pd.date_range("2026-01-05 07:00", periods=len(rows), freq="15min", tz="UTC")
    frame = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    frame.insert(0, "time", time)
    frame["tick_volume"] = 100
    frame["spread"] = 10
    return add_close_time(frame, timeframe)
