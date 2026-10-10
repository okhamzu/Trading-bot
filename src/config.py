from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in minimal test environments
    load_dotenv = None


@dataclass(frozen=True)
class SymbolConfig:
    name: str
    enabled: bool
    max_spread_points: float
    sweep_buffer_points: float
    stop_buffer_points: float


@dataclass(frozen=True)
class Secrets:
    mt5_login: int | None
    mt5_password: str | None
    mt5_server: str | None
    mt5_path: str | None
    anthropic_api_key: str | None
    twilio_account_sid: str | None
    twilio_auth_token: str | None
    twilio_whatsapp_from: str | None
    whatsapp_to: str | None
    callmebot_api_key: str | None
    meta_whatsapp_token: str | None
    meta_phone_number_id: str | None


@dataclass(frozen=True)
class Settings:
    raw: dict[str, Any]
    symbols: tuple[SymbolConfig, ...]
    secrets: Secrets
    path: Path

    def section(self, name: str) -> dict[str, Any]:
        value = self.raw.get(name, {})
        if not isinstance(value, dict):
            raise ValueError(f"Config section {name!r} must be a mapping")
        return value

    @property
    def dry_run(self) -> bool:
        return bool(self.section("mode").get("dry_run", True))

    @property
    def enabled_symbols(self) -> tuple[SymbolConfig, ...]:
        return tuple(symbol for symbol in self.symbols if symbol.enabled)

    def symbol(self, name: str) -> SymbolConfig:
        for symbol in self.symbols:
            if symbol.name == name:
                return symbol
        raise KeyError(f"Unknown symbol: {name}")


def _optional_int(value: str | None) -> int | None:
    return int(value) if value and value.strip() else None


def load_settings(path: str | Path = "config/settings.yaml") -> Settings:
    config_path = Path(path).resolve()
    if load_dotenv:
        load_dotenv(config_path.parent.parent / ".env")
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    mode = raw.setdefault("mode", {})
    if mode.get("dry_run") is not True:
        raise ValueError("Safety violation: mode.dry_run must remain true in v1")

    symbols = tuple(SymbolConfig(**item) for item in raw.get("symbols", []))
    secrets = Secrets(
        mt5_login=_optional_int(os.getenv("MT5_LOGIN")),
        mt5_password=os.getenv("MT5_PASSWORD"),
        mt5_server=os.getenv("MT5_SERVER"),
        mt5_path=os.getenv("MT5_PATH"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        twilio_whatsapp_from=os.getenv("TWILIO_WHATSAPP_FROM"),
        whatsapp_to=os.getenv("WHATSAPP_TO"),
        callmebot_api_key=os.getenv("CALLMEBOT_API_KEY"),
        meta_whatsapp_token=os.getenv("META_WHATSAPP_TOKEN"),
        meta_phone_number_id=os.getenv("META_PHONE_NUMBER_ID"),
    )
    return Settings(raw=raw, symbols=symbols, secrets=secrets, path=config_path)
