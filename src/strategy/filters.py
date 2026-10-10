from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.analysis.sessions import in_trade_session
from src.domain import Setup


@dataclass(frozen=True)
class FilterResult:
    passed: bool
    reasons: tuple[str, ...]


def apply_filters(
    setup: Setup,
    *,
    sessions: dict,
    min_rr: float,
    spread_points: float | None = None,
    max_spread_points: float | None = None,
    news_events: list[datetime] | None = None,
    news_window_minutes: int = 30,
    guard_allowed: bool = True,
    active_symbol: bool = False,
    daily_count: int = 0,
    max_daily_count: int = 3,
) -> FilterResult:
    rejected: list[str] = []
    if setup.rr < min_rr:
        rejected.append(f"R:R {setup.rr:.2f} is below {min_rr:.2f}")
    if not in_trade_session(setup.created_at, sessions):
        rejected.append("Outside configured trade sessions")
    if spread_points is not None and max_spread_points is not None and spread_points > max_spread_points:
        rejected.append(f"Spread {spread_points:.1f} exceeds {max_spread_points:.1f} points")
    if not guard_allowed:
        rejected.append("Risk guard is active")
    if active_symbol:
        rejected.append("Another setup is active for the symbol")
    if daily_count >= max_daily_count:
        rejected.append("Daily setup limit reached")
    for event in news_events or []:
        if abs((setup.created_at - event).total_seconds()) <= news_window_minutes * 60:
            rejected.append("Inside configured news blackout")
            break
    return FilterResult(not rejected, tuple(rejected))
