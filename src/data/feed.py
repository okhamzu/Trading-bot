from __future__ import annotations
import pandas as pd
from src.data.cache import DEFAULT_DIRECTORY, history_path, normalize_history

def utc_timestamp(value):
    value = pd.Timestamp(value)
    if pd.isna(value):
        raise ValueError("Invalid feed cutoff")
    return value.tz_localize("UTC") if value.tzinfo is None else value.tz_convert("UTC")

class HistoricalFeed:
    def __init__(self, directory=DEFAULT_DIRECTORY):
        self.directory = directory
        self._frames = {}

    def load(self, symbol, timeframe):
        key = (symbol, timeframe.upper())
        if key not in self._frames:
            path = history_path(symbol, timeframe, self.directory)
            if path.exists():
                frame = pd.read_parquet(path)
            elif path.with_suffix(".csv").exists():
                frame = pd.read_csv(path.with_suffix(".csv"))
            else:
                raise FileNotFoundError(f"No cached history for {symbol} {timeframe}: {path}")
            self._frames[key] = normalize_history(frame, timeframe)
        return self._frames[key].copy()

    def bars_until(self, symbol, timeframe, now):
        frame = self.load(symbol, timeframe)
        return frame.loc[frame.close_time <= utc_timestamp(now)].reset_index(drop=True)

    def get(self, symbol, timeframe, count, now):
        if count <= 0:
            raise ValueError("Candle count must be positive")
        return self.bars_until(symbol, timeframe, now).tail(count).reset_index(drop=True)

class LiveFeed:
    def __init__(self, client):
        self.client = client

    def get(self, symbol, timeframe, count, now=None):
        if count <= 0:
            raise ValueError("Candle count must be positive")
        frame = normalize_history(self.client.get_rates(symbol, timeframe, count), timeframe)
        cutoff = pd.Timestamp.now(tz="UTC") if now is None else utc_timestamp(now)
        return frame.loc[frame.close_time <= cutoff].tail(count).reset_index(drop=True)
