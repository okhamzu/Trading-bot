from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.backtest.engine import BacktestEngine
from src.backtest.report import write_report
from src.backtest.runner import BIAS_METHODS, MODEL_NAMES, run_grid
from src.config import load_settings
from src.data.cache import read_symbol_specs
from src.data.feed import HistoricalFeed
from src.domain import SymbolSpecs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the no-lookahead ICT/SMC backtest grid")
    parser.add_argument("--grid", choices=["all"])
    parser.add_argument("--model", choices=MODEL_NAMES)
    parser.add_argument("--bias", choices=BIAS_METHODS)
    parser.add_argument("--symbol")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--config", default="config/settings.yaml")
    args = parser.parse_args()

    settings = load_settings(args.config)
    raw_specs = read_symbol_specs()
    specs = {name: SymbolSpecs(**values) for name, values in raw_specs.items()}
    feed = HistoricalFeed()
    engine = BacktestEngine(settings, feed, specs)
    config = settings.section("backtest")
    start = datetime.fromisoformat(args.start or config["start"])
    end = datetime.fromisoformat(args.end or config["end"])
    symbols = [args.symbol] if args.symbol else [item.name for item in settings.enabled_symbols]
    models = MODEL_NAMES if args.grid == "all" else [args.model or "sweep_mss_fvg"]
    biases = BIAS_METHODS if args.grid == "all" else [args.bias or "htf_structure"]
    summary, trades = run_grid(engine, symbols, models, biases, start, end, float(config.get("in_sample_pct", 70)))
    output = write_report(summary, trades, args.config)
    print(summary.to_string(index=False))
    print(f"Report written to {output}")


if __name__ == "__main__":
    main()
