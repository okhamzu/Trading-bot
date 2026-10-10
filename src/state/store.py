from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.domain import Setup


class StateStore:
    def __init__(self, path: str | Path = "output/state.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("CREATE TABLE IF NOT EXISTS alerts (setup_id TEXT, alert_type TEXT, sent_at TEXT, PRIMARY KEY(setup_id, alert_type))")
        self.connection.execute("CREATE TABLE IF NOT EXISTS setups (setup_id TEXT PRIMARY KEY, payload TEXT, status TEXT, updated_at TEXT)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS bot_state (key TEXT PRIMARY KEY, value TEXT)")
        self.connection.commit()

    def alert_exists(self, setup_id: str, alert_type: str) -> bool:
        row = self.connection.execute("SELECT 1 FROM alerts WHERE setup_id=? AND alert_type=?", (setup_id, alert_type)).fetchone()
        return row is not None

    def save_alert(self, setup_id: str, alert_type: str) -> None:
        self.connection.execute("INSERT OR IGNORE INTO alerts VALUES (?, ?, ?)", (setup_id, alert_type, datetime.now(timezone.utc).isoformat()))
        self.connection.commit()

    def save_setup(self, setup: Setup) -> None:
        payload = asdict(setup)
        payload["created_at"], payload["expires_at"] = setup.created_at.isoformat(), setup.expires_at.isoformat()
        self.connection.execute("INSERT OR REPLACE INTO setups VALUES (?, ?, ?, ?)", (setup.id, json.dumps(payload), setup.status, datetime.now(timezone.utc).isoformat()))
        self.connection.commit()

    def update_status(self, setup_id: str, status: str) -> None:
        self.connection.execute("UPDATE setups SET status=?, updated_at=? WHERE setup_id=?", (status, datetime.now(timezone.utc).isoformat(), setup_id))
        self.connection.commit()

    def load_active_setups(self) -> list[Setup]:
        rows = self.connection.execute("SELECT payload, status FROM setups WHERE status IN ('pending', 'triggered')").fetchall()
        setups = []
        for raw, status in rows:
            payload = json.loads(raw)
            payload["created_at"] = datetime.fromisoformat(payload["created_at"])
            payload["expires_at"] = datetime.fromisoformat(payload["expires_at"])
            payload["entry_zone"] = tuple(payload["entry_zone"])
            payload["status"] = status
            setups.append(Setup(**payload))
        return setups

    def get_value(self, key: str, default: str | None = None) -> str | None:
        row = self.connection.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_value(self, key: str, value: str) -> None:
        self.connection.execute("INSERT OR REPLACE INTO bot_state VALUES (?, ?)", (key, value))
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
