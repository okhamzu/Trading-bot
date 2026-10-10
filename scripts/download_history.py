from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_settings
from src.data.cache import write_history, write_symbol_specs
from src.mt5_client import MT5Client


def monthly_ranges(start: pd.Timestamp, end: pd.Timestamp):
    cursor = start
    while cursor < end:
        next_month = min(cursor + pd.DateOffset(months=1), end)
        yield cursor.to_pydatetime(), next_month.to_pydatetime()
        cursor = next_month


def main() -> None:
    parser = argparse.ArgumentParser(description="Download MT5 history into the portable Parquet cache")
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--symbols", nargs="*")
    parser.add_argument("--timeframes", nargs="*", default=["M5", "M15", "H1", "H4", "D1"])
    parser.add_argument("--config", default="config/settings.yaml")
    args = parser.parse_args()

    settings, client = load_settings(args.config), None
    client = MT5Client(settings)
    client.connect()
    symbols = args.symbols or [item.name for item in settings.enabled_symbols]
    start, end = pd.Timestamp(args.start, tz="UTC"), pd.Timestamp(args.end, tz="UTC")
    specs = {}
    try:
        for symbol in symbols:
            specs[symbol] = client.specs_as_dict(symbol)
            for timeframe in args.timeframes:
                chunks = []
                for chunk_start, chunk_end in monthly_ranges(start, end):
                    chunks.append(client.get_rates_range(symbol, timeframe, chunk_start, chunk_end))
                frame = pd.concat(chunks, ignore_index=True).drop_duplicates("time").sort_values("time")
                path = write_history(frame, symbol, timeframe)
                print(f"{symbol} {timeframe}: {frame.time.min()} → {frame.time.max()} ({len(frame)} bars) · {path}")
        write_symbol_specs(specs)
    finally:
        client.shutdown()


if __name__ == "__main__":
    main()
