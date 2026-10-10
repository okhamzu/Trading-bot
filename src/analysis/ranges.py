from __future__ import annotations

from dataclasses import dataclass

from src.domain import StructureEvent, Swing


@dataclass(frozen=True)
class DealingRange:
    low: float
    high: float
    origin_index: int
    destination_index: int

    @property
    def equilibrium(self) -> float:
        return (self.low + self.high) / 2


def current_dealing_range(swings: list[Swing], events: list[StructureEvent]) -> DealingRange | None:
    if not events:
        return None
    event = events[-1]
    before = [swing for swing in swings if swing.index <= event.index]
    highs = [swing for swing in before if swing.kind == "high"]
    lows = [swing for swing in before if swing.kind == "low"]
    if not highs or not lows:
        return None
    high, low = highs[-1], lows[-1]
    return DealingRange(low.price, high.price, low.index, high.index)


def position_in_range(price: float, dealing_range: DealingRange) -> float:
    width = dealing_range.high - dealing_range.low
    return (price - dealing_range.low) / width if width else 0.5


def ote_zone(start: float, end: float) -> tuple[float, float, float]:
    move = end - start
    values = (end - move * 0.79, end - move * 0.62, end - move * 0.705)
    return min(values[0], values[1]), max(values[0], values[1]), values[2]
