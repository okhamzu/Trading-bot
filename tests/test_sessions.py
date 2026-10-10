from __future__ import annotations

import unittest

import pandas as pd

from src.analysis.sessions import in_trade_session, session_of


SESSIONS = {
    "asia": ["20:00", "00:00"],
    "london_kz": ["02:00", "05:00"],
    "ny_am_kz": ["07:00", "10:00"],
    "trade_sessions": ["london_kz", "ny_am_kz"],
}


class SessionTests(unittest.TestCase):
    def test_new_york_dst_conversion(self):
        # 12:00 UTC is 08:00 New York during summer DST.
        timestamp = pd.Timestamp("2026-06-15T12:00:00Z")
        self.assertEqual(session_of(timestamp, SESSIONS), "ny_am_kz")
        self.assertTrue(in_trade_session(timestamp, SESSIONS))


if __name__ == "__main__":
    unittest.main()
