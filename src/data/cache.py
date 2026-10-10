from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.utils.timeutils import add_close_time

DEFAULT_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "history"

def history_path(symbol, timeframe, directory=DEFAULT_DIRECTORY):
    if not symbol or any(c in symbol for c in "/\\") or symbol in {".", ".."}:
        raise ValueError("Invalid symbol")
    from src.utils.timeutils import timeframe_delta
    timeframe_delta(timeframe)
    return Path(directory) / f"{symbol}_{timeframe.upper()}.parquet"

def normalize_history(frame, timeframe):
    frame = frame.copy()
    if "time" not in frame and "time_utc" in frame:
        frame = frame.rename(columns={"time_utc": "time"})
    required = ["time", "open", "high", "low", "close"]
    if any(c not in frame for c in required):
        raise ValueError("History requires time and OHLC columns")
    frame["time"] = pd.to_datetime(frame["time"], utc=True, errors="raise")
    if frame.time.isna().any():
        raise ValueError("Missing candle timestamp")
    for c in required[1:]:
        frame[c] = pd.to_numeric(frame[c], errors="raise")
    if not np.isfinite(frame[required[1:]].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite OHLC value")
    if ((frame.high < frame[["open", "close", "low"]].max(axis=1)) |
        (frame.low > frame[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("Invalid OHLC range")
    if "tick_volume" not in frame:
        frame["tick_volume"] = frame.get("volume", 0)
    if "spread" not in frame:
        frame["spread"] = 0
    frame = frame.sort_values("time", kind="stable").drop_duplicates("time", keep="last")
    return add_close_time(frame, timeframe)

def write_history(frame, symbol, timeframe, directory=DEFAULT_DIRECTORY):
    path = history_path(symbol, timeframe, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_history(frame, timeframe)
    temporary = path.with_suffix(".tmp.parquet")
    normalized.to_parquet(temporary, index=False)
    temporary.replace(path)
    return path

def write_symbol_specs(specs, directory=DEFAULT_DIRECTORY):
    path = Path(directory) / "symbol_specs.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.json")
    temporary.write_text(json.dumps(specs, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)
    return path

def read_symbol_specs(directory=DEFAULT_DIRECTORY):
    return json.loads((Path(directory) / "symbol_specs.json").read_text(encoding="utf-8"))
