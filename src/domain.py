from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


Direction = Literal["bullish", "bearish"]
TradeDirection = Literal["long", "short"]


@dataclass(frozen=True)
class Swing:
    index: int
    time: datetime
    confirmed_at: datetime
    price: float
    kind: Literal["high", "low"]
    label: str | None = None
    pending: bool = False


@dataclass(frozen=True)
class StructureEvent:
    index: int
    time: datetime
    kind: Literal["BOS", "CHOCH", "MSS"]
    direction: Direction
    broken_level: float
    broken_swing_index: int


@dataclass
class LiquidityPool:
    price: float
    side: Literal["buy", "sell"]
    source: str
    created_at: datetime
    status: Literal["active", "swept", "broken"] = "active"
    resolved_at: datetime | None = None
    resolved_index: int | None = None
    extreme: float | None = None


@dataclass
class FairValueGap:
    index: int
    created_at: datetime
    direction: Direction
    bottom: float
    top: float
    ce: float
    mitigated: bool = False
    invalidated: bool = False
    fill_pct: float = 0.0


@dataclass
class OrderBlock:
    index: int
    created_at: datetime
    direction: Direction
    bottom: float
    top: float
    mitigated: bool = False
    invalidated: bool = False


@dataclass(frozen=True)
class Bias:
    direction: Literal["bullish", "bearish", "neutral"]
    reason: str
    method: str


@dataclass(frozen=True)
class SymbolSpecs:
    point: float
    digits: int
    trade_tick_size: float
    trade_tick_value: float
    volume_min: float
    volume_max: float
    volume_step: float
    trade_contract_size: float
    currency: str = "USD"


@dataclass
class Setup:
    id: str
    symbol: str
    timeframe: str
    model: str
    bias_method: str
    bias_direction: str
    direction: TradeDirection
    created_at: datetime
    entry: float
    entry_zone: tuple[float, float]
    stop: float
    targets: list[float]
    rr: float
    lot_size: float
    risk_amount: float
    session: str | None
    reasons: list[str]
    expires_at: datetime
    status: Literal[
        "pending", "triggered", "tp1", "tp2", "tp3", "sl", "expired", "invalidated"
    ] = "pending"
    metadata: dict = field(default_factory=dict)

    def r_to_target(self, target: float) -> float:
        risk = abs(self.entry - self.stop)
        return abs(target - self.entry) / risk if risk else 0.0
