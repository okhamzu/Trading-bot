from __future__ import annotations

from src.analysis.ranges import DealingRange, position_in_range
from src.analysis.structure import structure_direction
from src.domain import Bias, StructureEvent


def calculate_bias(
    method: str,
    price: float,
    htf_events: list[StructureEvent],
    dealing_range: DealingRange | None,
    daily_events: list[StructureEvent] | None = None,
) -> Bias:
    htf_direction = structure_direction(htf_events)
    if method == "none":
        return Bias("neutral", "No directional filter (control baseline)", method)
    if method == "htf_structure":
        return Bias(htf_direction, f"Last confirmed HTF structure event is {htf_direction}", method)
    if method == "daily_structure":
        direction = structure_direction(daily_events or [])
        return Bias(direction, f"Last confirmed Daily structure event is {direction}", method)
    if method == "premium_discount":
        if dealing_range is None:
            return Bias("neutral", "No confirmed HTF dealing range", method)
        position = position_in_range(price, dealing_range)
        direction = "neutral" if 0.45 <= position <= 0.55 else "bullish" if position < 0.5 else "bearish"
        return Bias(direction, f"Price is at {position:.1%} of the HTF dealing range", method)
    if method == "structure_plus_pd":
        if dealing_range is None or htf_direction == "neutral":
            return Bias("neutral", "Structure or dealing range unavailable", method)
        position = position_in_range(price, dealing_range)
        aligned = (htf_direction == "bullish" and position < 0.5) or (htf_direction == "bearish" and position > 0.5)
        direction = htf_direction if aligned else "neutral"
        return Bias(direction, f"HTF {htf_direction}; price at {position:.1%} of dealing range", method)
    raise ValueError(f"Unknown bias method: {method}")


def bias_allows(bias: Bias, direction: str, neutral_bias_trades: bool = False) -> bool:
    desired = "bullish" if direction == "long" else "bearish"
    if bias.method == "none":
        return True
    if bias.direction == "neutral":
        return neutral_bias_trades
    return bias.direction == desired
