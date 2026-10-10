from __future__ import annotations

from datetime import timedelta

import pandas as pd


TIMEFRAME_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}


def timeframe_delta(timeframe: str) -> timedelta:
    try:
        return timedelta(minutes=TIMEFRAME_MINUTES[timeframe.upper()])
    except KeyError as exc:
        raise ValueError(f"Unsupported timeframe: {timeframe}") from exc


def ensure_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True)


def add_close_time(frame: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    result = frame.copy()
    result["time"] = ensure_utc(result["time"])
    result["close_time"] = result["time"] + timeframe_delta(timeframe)
    return result.reset_index(drop=True)
