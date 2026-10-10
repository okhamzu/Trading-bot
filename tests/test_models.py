from __future__ import annotations

import unittest

from src.domain import Bias, FairValueGap, LiquidityPool, StructureEvent, SymbolSpecs
from src.strategy.context import MarketContext
from src.strategy.models.sweep_mss_fvg import SweepMSSFVGModel
from tests.helpers import candles


class ModelTests(unittest.TestCase):
    def test_sweep_mss_fvg_requires_confirmed_mss_and_builds_levels(self):
        frame = candles([(100, 102, 98, 101)] * 20)
        sweep_time = frame.iloc[10].close_time
        mss_time = frame.iloc[12].close_time
        sell_pool = LiquidityPool(99, "sell", "equal_lows", frame.iloc[5].close_time, "swept", sweep_time, 10, 97)
        buy_pool = LiquidityPool(108, "buy", "swing", frame.iloc[6].close_time)
        mss = StructureEvent(12, mss_time, "MSS", "bullish", 103, 8)
        gap = FairValueGap(11, frame.iloc[12].close_time, "bullish", 100, 101, 100.5)
        specs = SymbolSpecs(0.01, 2, 0.01, 1, 0.01, 100, 0.01, 100)
        context = MarketContext("XAUUSD", "M15", frame, frame, [], [mss], [], [], [sell_pool, buy_pool], [gap], [], Bias("neutral", "baseline", "none"), None, specs, {"ny_am_kz": ["07:00", "10:00"], "trade_sessions": ["ny_am_kz"]}, 10000)
        model = SweepMSSFVGModel(stop_buffer_points=30)
        setups = model.scan(context)
        self.assertEqual(len(setups), 1)
        self.assertEqual(setups[0].entry, 101)
        self.assertAlmostEqual(setups[0].stop, 96.7)
        self.assertEqual(setups[0].targets[0], 108)
        self.assertEqual(setups[0].created_at, mss_time)


if __name__ == "__main__":
    unittest.main()
