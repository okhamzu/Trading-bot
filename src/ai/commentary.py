from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date

from src.config import Settings
from src.domain import Setup

LOGGER = logging.getLogger(__name__)


class ClaudeCommentary:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.calls: dict[date, int] = {}

    def generate(self, setup: Setup) -> str | None:
        config = self.settings.section("ai")
        key = self.settings.secrets.anthropic_api_key
        today = date.today()
        if not config.get("enabled", True) or not key or self.calls.get(today, 0) >= int(config.get("max_calls_per_day", 50)):
            return None
        try:
            from anthropic import Anthropic
            payload = asdict(setup)
            for key_name in ("created_at", "expires_at"):
                payload[key_name] = payload[key_name].isoformat()
            client = Anthropic(api_key=key, timeout=float(config.get("timeout_seconds", 20)))
            response = client.messages.create(
                model=config.get("model", "claude-sonnet-4-5"), max_tokens=int(config.get("max_tokens", 300)),
                system="You are an ICT/SMC trading assistant. In 2–3 sentences, summarize the setup, name the single biggest risk to it, and say what would invalidate it. Do not give financial advice or change the levels.",
                messages=[{"role": "user", "content": json.dumps(payload, default=str)}],
            )
            self.calls[today] = self.calls.get(today, 0) + 1
            return "".join(block.text for block in response.content if getattr(block, "type", "") == "text").strip() or None
        except Exception:
            LOGGER.exception("Claude commentary failed; alert will continue without it")
            return None
