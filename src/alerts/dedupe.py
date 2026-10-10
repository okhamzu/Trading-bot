from __future__ import annotations

from src.state.store import StateStore


class AlertDedupe:
    def __init__(self, store: StateStore):
        self.store = store

    def already_sent(self, setup_id: str, alert_type: str = "SETUP") -> bool:
        return self.store.alert_exists(setup_id, alert_type)

    def mark_sent(self, setup_id: str, alert_type: str = "SETUP") -> None:
        self.store.save_alert(setup_id, alert_type)
