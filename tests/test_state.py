from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.state.store import StateStore
from tests.test_fills_and_safety import setup


class StateTests(unittest.TestCase):
    def test_alert_dedupe_and_active_setup_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.sqlite3"
            store = StateStore(path)
            item = setup()
            store.save_setup(item)
            store.save_alert(item.id, "SETUP")
            store.close()

            reopened = StateStore(path)
            self.assertTrue(reopened.alert_exists(item.id, "SETUP"))
            active = reopened.load_active_setups()
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0].entry_zone, item.entry_zone)
            reopened.update_status(item.id, "tp1")
            self.assertEqual(reopened.load_active_setups(), [])
            reopened.close()


if __name__ == "__main__":
    unittest.main()
