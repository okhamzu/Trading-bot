from __future__ import annotations

import unittest

import pandas as pd

from src.analysis.atr import with_atr
from src.analysis.fvg import detect_fvgs
from src.analysis.structure import detect_structure
from src.analysis.swings import detect_swings
from src.domain import Swing
from tests.helpers import candles


class AnalysisTests(unittest.TestCase):
    def test_swing_is_only_visible_after_right_confirmation_bar(self):
        frame = candles([
            (10, 11, 9, 10),
            (10, 12, 9.5, 11),
            (11, 15, 10, 12),
            (12, 13, 10.5, 11),
            (11, 12, 9, 10),
        ])
        self.assertEqual(detect_swings(frame.iloc[:3].reset_index(drop=True), 1), [])
        swings = detect_swings(frame.iloc[:4].reset_index(drop=True), 1)
        high = next(item for item in swings if item.kind == "high")
        self.assertEqual(high.index, 2)
        self.assertEqual(high.price, 15)
        self.assertEqual(high.confirmed_at, frame.iloc[3].close_time)

    def test_fvg_uses_three_closed_candles(self):
        frame = with_atr(candles([
            (100, 102, 99, 101),
            (101, 110, 101, 109),
            (109, 111, 104, 110),
            (110, 112, 107, 111),
        ]), period=2)
        gaps = detect_fvgs(frame, min_size_atr=0)
        bullish = next(item for item in gaps if item.direction == "bullish")
        self.assertEqual((bullish.bottom, bullish.top), (102, 104))
        self.assertEqual(bullish.created_at, frame.iloc[2].close_time)

    def test_structure_break_requires_close_by_default(self):
        frame = candles([
            (9, 9.5, 8.5, 9),
            (9, 10.8, 8.8, 9.8),  # wick above level, close below
            (9.8, 10.7, 9.5, 10.5),
        ])
        swing = Swing(0, frame.iloc[0].time, frame.iloc[0].close_time, 10.0, "high")
        events = detect_structure(frame, [swing], "close")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].index, 2)
        self.assertEqual(events[0].direction, "bullish")


if __name__ == "__main__":
    unittest.main()
