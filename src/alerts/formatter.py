from __future__ import annotations

from zoneinfo import ZoneInfo

from src.domain import Setup


def format_setup(setup: Setup, digits: int, display_timezone: str = "Asia/Karachi", commentary: str | None = None) -> str:
    icon = "🟢" if setup.direction == "long" else "🔴"
    price = lambda value: f"{value:,.{digits}f}"
    lines = [
        f"{icon} {setup.direction.upper()} {setup.symbol} · {setup.timeframe} · {setup.model}",
        f"Entry: {price(setup.entry)} ({price(setup.entry_zone[0])}–{price(setup.entry_zone[1])})",
        f"Stop: {price(setup.stop)}",
    ]
    for index, target in enumerate(setup.targets, start=1):
        lines.append(f"TP{index}: {price(target)} (1:{setup.r_to_target(target):.2f})")
    lines.extend([
        f"Lots: {setup.lot_size:g} (risk {setup.risk_amount:,.2f})",
        f"Bias: {setup.bias_direction} via {setup.bias_method}",
        "Why: " + " · ".join(setup.reasons),
        f"Session: {setup.session or 'none'} · Expires {setup.expires_at.astimezone(ZoneInfo(display_timezone)):%Y-%m-%d %H:%M %Z}",
    ])
    if commentary:
        lines.append(f"AI: {commentary}")
    return "\n".join(lines)


def format_watch(symbol: str, side: str, price: float) -> str:
    return f"👀 WATCH {symbol}: {side}-side liquidity swept at {price}. Waiting for a closed-candle MSS."


def format_result(setup: Setup, status: str, result_r: float | None = None) -> str:
    suffix = f" ({result_r:+.2f}R)" if result_r is not None else ""
    return f"{setup.symbol} {setup.direction.upper()} · {status.upper()}{suffix} · {setup.id}"
