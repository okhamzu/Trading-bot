from __future__ import annotations

import csv
from pathlib import Path
from zoneinfo import ZoneInfo

from src.domain import Setup


FIELDS = ["setup_id", "created_at_utc", "created_at_pkt", "symbol", "timeframe", "model", "bias_method", "bias_direction", "direction", "session", "entry", "stop", "tp1", "tp2", "tp3", "rr_tp1", "lots", "risk_amount", "spread_at_alert", "reasons", "ai_commentary", "chart_path", "status", "triggered_at", "closed_at", "exit_price", "result_r", "notes"]


class Journal:
    def __init__(self, path: str | Path = "output/journal.csv"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, setup: Setup, *, spread: float | None = None, commentary: str | None = None, chart_path: str | None = None) -> None:
        row = {field: "" for field in FIELDS}
        row.update(setup_id=setup.id, created_at_utc=setup.created_at.isoformat(), created_at_pkt=setup.created_at.astimezone(ZoneInfo("Asia/Karachi")).isoformat(), symbol=setup.symbol, timeframe=setup.timeframe, model=setup.model, bias_method=setup.bias_method, bias_direction=setup.bias_direction, direction=setup.direction, session=setup.session or "", entry=setup.entry, stop=setup.stop, rr_tp1=setup.rr, lots=setup.lot_size, risk_amount=setup.risk_amount, spread_at_alert=spread if spread is not None else "", reasons=" | ".join(setup.reasons), ai_commentary=commentary or "", chart_path=chart_path or "", status=setup.status)
        for index, target in enumerate(setup.targets[:3], 1):
            row[f"tp{index}"] = target
        exists = self.path.exists()
        with self.path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            if not exists:
                writer.writeheader()
            writer.writerow(row)

    def update_status(self, setup_id: str, status: str, **updates) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            if row["setup_id"] == setup_id:
                row["status"] = status
                for key, value in updates.items():
                    if key in FIELDS:
                        row[key] = value
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
