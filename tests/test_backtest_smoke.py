from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.backtest.engine import BacktestEngine
from src.backtest.report import write_report
from src.config import load_settings
from src.data.feed import HistoricalFeed
from src.domain import SymbolSpecs
from src.utils.timeutils import add_close_time


def flat_history(start: str, periods: int, frequency: str, timeframe: str) -> pd.DataFrame:
    frame = pd.DataFrame({
        "time": pd.date_range(start, periods=periods, freq=frequency, tz="UTC"),
        "open": 100.0, "high": 100.2, "low": 99.8, "close": 100.0,
        "tick_volume": 100, "spread": 10,
    })
    return add_close_time(frame, timeframe)


class BacktestSmokeTests(unittest.TestCase):
    def test_engine_and_empty_report_complete_without_mt5(self):
        settings = load_settings(Path(__file__).resolve().parents[1] / "config/settings.yaml")
        specs = SymbolSpecs(0.01, 2, 0.01, 1, 0.01, 100, 0.01, 100)
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory) / "data"
            data_dir.mkdir()
            execution = flat_history("2026-01-01", 60, "15min", "M15")
            bias = flat_history("2025-12-20", 40, "4h", "H4")
            execution.drop(columns="close_time").to_csv(data_dir / "XAUUSD_M15.csv", index=False)
            bias.drop(columns="close_time").to_csv(data_dir / "XAUUSD_H4.csv", index=False)
            engine = BacktestEngine(settings, HistoricalFeed(data_dir), {"XAUUSD": specs})
            trades, metrics = engine.run("XAUUSD", "sweep_mss_fvg", "htf_structure", execution.iloc[29].close_time.to_pydatetime(), execution.iloc[-1].close_time.to_pydatetime())
            self.assertTrue(trades.empty)
            self.assertEqual(metrics["trades"], 0)
            output = write_report(pd.DataFrame(), trades, str(settings.path), Path(directory) / "reports")
            self.assertTrue((output / "report.md").exists())


if __name__ == "__main__":
    unittest.main()
