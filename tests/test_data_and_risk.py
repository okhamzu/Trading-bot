from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.data.feed import HistoricalFeed
from src.domain import SymbolSpecs
from src.risk.sizing import calculate_position_size
from tests.helpers import candles


class DataAndRiskTests(unittest.TestCase):
    def test_historical_feed_never_returns_unclosed_bar(self):
        frame = candles([(1, 2, 0, 1)] * 5)
        with tempfile.TemporaryDirectory() as directory:
            frame.drop(columns=["close_time"]).to_csv(Path(directory) / "XAUUSD_M15.csv", index=False)
            feed = HistoricalFeed(directory)
            now = frame.iloc[2].close_time
            result = feed.bars_until("XAUUSD", "M15", now.to_pydatetime())
            self.assertEqual(len(result), 3)
            self.assertTrue((result.close_time <= now).all())

    def test_position_sizing_uses_tick_value_and_rounds_down(self):
        specs = SymbolSpecs(point=0.01, digits=2, trade_tick_size=0.01, trade_tick_value=1.0, volume_min=0.01, volume_max=100, volume_step=0.01, trade_contract_size=100)
        size = calculate_position_size(10_000, 0.75, 2000, 1997, specs)
        self.assertEqual(size.risk_amount, 75)
        self.assertEqual(size.lots, 0.25)
        self.assertEqual(size.actual_risk, 75)

    def test_minimum_lot_does_not_silently_exceed_risk(self):
        specs = SymbolSpecs(point=0.01, digits=2, trade_tick_size=0.01, trade_tick_value=10, volume_min=0.1, volume_max=100, volume_step=0.1, trade_contract_size=100)
        size = calculate_position_size(1000, 0.75, 100, 90, specs)
        self.assertEqual(size.lots, 0)
        self.assertIsNotNone(size.warning)


if __name__ == "__main__":
    unittest.main()
