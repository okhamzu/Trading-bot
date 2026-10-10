from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml

from src.backtest.fills import SimulatedTrade, update_trade
from src.config import load_settings
from src.domain import Setup


def setup() -> Setup:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Setup("id", "XAUUSD", "M15", "test", "none", "neutral", "long", now, 100, (99, 100), 95, [110], 2, 0.1, 75, "ny_am_kz", ["test"], now + timedelta(hours=3))


class FillAndSafetyTests(unittest.TestCase):
    def test_same_bar_stop_and_target_uses_stop_first(self):
        trade = SimulatedTrade(setup())
        bar = pd.Series({"low": 94, "high": 111, "close": 101, "close_time": setup().created_at + timedelta(minutes=15)})
        update_trade(trade, bar, point=0.01, spread_points=0, slippage_points=0)
        self.assertEqual(trade.status, "sl")
        self.assertEqual(trade.result_r, -1)

    def test_pending_setup_invalidates_when_zone_breaks(self):
        trade = SimulatedTrade(setup())
        bar = pd.Series({"low": 98, "high": 99.5, "close": 98.5, "close_time": setup().created_at + timedelta(minutes=15)})
        update_trade(trade, bar, point=0.01, spread_points=0, slippage_points=0)
        self.assertEqual(trade.status, "invalidated")
        self.assertEqual(trade.result_r, 0)

    def test_config_refuses_non_dry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.yaml"
            path.write_text(yaml.safe_dump({"mode": {"dry_run": False}, "symbols": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_settings(path)

    def test_source_contains_no_order_send_call(self):
        root = Path(__file__).resolve().parents[1]
        sources = "\n".join(path.read_text(encoding="utf-8") for path in (root / "src").rglob("*.py"))
        forbidden = "order" + "_send("  # avoid embedding the forbidden call in the source scan itself
        self.assertNotIn(forbidden, sources)


if __name__ == "__main__":
    unittest.main()
