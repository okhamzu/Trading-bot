from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_settings
from src.mt5_client import MT5Client


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the latest closed MT5 candles to CSV")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tf", nargs="+", default=["M15"])
    parser.add_argument("--bars", type=int, default=500)
    parser.add_argument("--config", default="config/settings.yaml")
    args = parser.parse_args()

    settings = load_settings(args.config)
    client = MT5Client(settings)
    client.connect()
    output = Path("output/exports")
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        for timeframe in args.tf:
            frame = client.get_rates(args.symbol, timeframe.upper(), args.bars)
            exported = frame.rename(columns={"time": "time_utc", "tick_volume": "volume"})
            exported["time_pkt"] = exported["time_utc"].dt.tz_convert(ZoneInfo("Asia/Karachi"))
            exported = exported[["time_utc", "time_pkt", "open", "high", "low", "close", "volume"]]
            path = output / f"{args.symbol}_{timeframe.upper()}_{stamp}.csv"
            exported.to_csv(path, index=False)
            print(f"Exported {len(exported)} closed candles to {path}")
    finally:
        client.shutdown()


if __name__ == "__main__":
    main()
