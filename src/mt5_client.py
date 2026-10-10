from __future__ import annotations

import logging
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from src.config import Settings
from src.domain import SymbolSpecs
from src.utils.timeutils import add_close_time

LOGGER = logging.getLogger(__name__)

try:  # MT5 is Windows-only; analysis/backtests must still import elsewhere.
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover - platform dependent
    mt5 = None


class MT5UnavailableError(RuntimeError):
    pass


class MT5Client:
    TIMEFRAMES: dict[str, str] = {
        "M1": "TIMEFRAME_M1",
        "M5": "TIMEFRAME_M5",
        "M15": "TIMEFRAME_M15",
        "M30": "TIMEFRAME_M30",
        "H1": "TIMEFRAME_H1",
        "H4": "TIMEFRAME_H4",
        "D1": "TIMEFRAME_D1",
    }

    def __init__(self, settings: Settings):
        self.settings = settings
        self.offset = timedelta(hours=float(settings.section("mt5").get("broker_utc_offset_hours", 0)))

    def _require_mt5(self) -> None:
        if mt5 is None:
            raise MT5UnavailableError("MetaTrader5 is only available on Windows with the MT5 terminal installed")

    def connect(self) -> None:
        self._require_mt5()
        secret = self.settings.secrets
        kwargs: dict[str, Any] = {}
        if secret.mt5_path:
            kwargs["path"] = secret.mt5_path
        if secret.mt5_login:
            kwargs.update(login=secret.mt5_login, password=secret.mt5_password, server=secret.mt5_server)
        attempts = int(self.settings.section("mt5").get("reconnect_attempts", 5))
        for attempt in range(attempts):
            if mt5.initialize(**kwargs):
                for symbol in self.settings.enabled_symbols:
                    self.select_symbol(symbol.name)
                return
            LOGGER.error("MT5 initialize failed: %s", mt5.last_error())
            if attempt + 1 < attempts:
                time.sleep(2 ** (attempt + 1))
        raise ConnectionError(f"Unable to connect to MT5 after {attempts} attempts: {mt5.last_error()}")

    def ensure_connected(self) -> None:
        self._require_mt5()
        if mt5.terminal_info() is None or mt5.account_info() is None:
            self.connect()

    def shutdown(self) -> None:
        if mt5 is not None:
            mt5.shutdown()

    def select_symbol(self, symbol: str) -> None:
        self._require_mt5()
        if mt5.symbol_select(symbol, True):
            return
        base = symbol.replace("USD", "").lower()
        similar = [item.name for item in (mt5.symbols_get() or []) if base in item.name.lower()][:15]
        raise LookupError(f"Broker symbol {symbol!r} not found. Similar symbols: {similar}")

    def _tf(self, timeframe: str) -> int:
        self._require_mt5()
        try:
            return getattr(mt5, self.TIMEFRAMES[timeframe.upper()])
        except KeyError as exc:
            raise ValueError(f"Unsupported timeframe: {timeframe}") from exc

    def _rates_frame(self, rates: Any, timeframe: str) -> pd.DataFrame:
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"MT5 returned no rates: {mt5.last_error() if mt5 else ''}")
        frame = pd.DataFrame(rates)
        source_time = pd.to_datetime(frame["time"], unit="s", utc=True) - self.offset
        frame["time"] = source_time
        frame = frame.rename(columns={"tick_volume": "tick_volume"})
        required = ["time", "open", "high", "low", "close", "tick_volume", "spread"]
        return add_close_time(frame[required], timeframe)

    def get_rates(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        self.ensure_connected()
        rates = mt5.copy_rates_from_pos(symbol, self._tf(timeframe), 0, count + 1)
        frame = self._rates_frame(rates, timeframe)
        return frame.iloc[:-1].tail(count).reset_index(drop=True)  # drop forming bar

    def get_rates_range(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
        self.ensure_connected()
        rates = mt5.copy_rates_range(symbol, self._tf(timeframe), start, end)
        frame = self._rates_frame(rates, timeframe)
        now = pd.Timestamp.now(tz="UTC")
        return frame.loc[frame["close_time"] <= now].reset_index(drop=True)

    def get_symbol_specs(self, symbol: str) -> SymbolSpecs:
        self.ensure_connected()
        info = mt5.symbol_info(symbol)
        if info is None:
            raise LookupError(f"No symbol info for {symbol}")
        account = mt5.account_info()
        return SymbolSpecs(
            point=float(info.point), digits=int(info.digits), trade_tick_size=float(info.trade_tick_size),
            trade_tick_value=float(info.trade_tick_value), volume_min=float(info.volume_min),
            volume_max=float(info.volume_max), volume_step=float(info.volume_step),
            trade_contract_size=float(info.trade_contract_size), currency=str(account.currency),
        )

    def get_spread(self, symbol: str) -> float:
        self.ensure_connected()
        info, tick = mt5.symbol_info(symbol), mt5.symbol_info_tick(symbol)
        if info is None or tick is None:
            raise RuntimeError(f"No live tick for {symbol}")
        return (float(tick.ask) - float(tick.bid)) / float(info.point)

    def get_account(self) -> dict[str, float | str]:
        self.ensure_connected()
        account = mt5.account_info()
        return {"balance": float(account.balance), "equity": float(account.equity), "currency": str(account.currency)}

    def get_closed_deals(self, since: datetime) -> list[dict[str, Any]]:
        self.ensure_connected()
        deals = mt5.history_deals_get(since, datetime.now(timezone.utc)) or []
        return [item._asdict() for item in deals]

    def specs_as_dict(self, symbol: str) -> dict[str, Any]:
        return asdict(self.get_symbol_specs(symbol))
