from __future__ import annotations

from datetime import time
from zoneinfo import ZoneInfo

import pandas as pd


NY = ZoneInfo("America/New_York")


def _parse(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":"))
    return time(hour, minute)


def _inside(value: time, start: time, end: time) -> bool:
    return start <= value < end if start < end else value >= start or value < end


def session_of(timestamp, sessions: dict) -> str | None:
    local_time = pd.Timestamp(timestamp).tz_convert(NY).time()
    for name, window in sessions.items():
        if name == "trade_sessions" or not isinstance(window, list) or len(window) != 2:
            continue
        if _inside(local_time, _parse(window[0]), _parse(window[1])):
            return name
    return None


def in_trade_session(timestamp, sessions: dict) -> bool:
    active = session_of(timestamp, sessions)
    return active in sessions.get("trade_sessions", [])


def forex_day(timestamp):
    local = pd.Timestamp(timestamp).tz_convert(NY)
    return (local - pd.Timedelta(hours=17)).date()


def session_range(frame: pd.DataFrame, session_name: str, sessions: dict) -> tuple[float, float] | None:
    mask = frame["time"].map(lambda item: session_of(item, sessions) == session_name)
    selected = frame.loc[mask]
    return (float(selected.low.min()), float(selected.high.max())) if not selected.empty else None
