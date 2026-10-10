from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import pandas as pd

from src.domain import FairValueGap, LiquidityPool, Setup, StructureEvent, Swing


def render_chart(frame: pd.DataFrame, setup: Setup | None = None, *, swings: list[Swing] | None = None, events: list[StructureEvent] | None = None, fvgs: list[FairValueGap] | None = None, pools: list[LiquidityPool] | None = None, output: str | Path | None = None, display_timezone: str = "Asia/Karachi") -> Path:
    selected = frame.tail(150).copy()
    figure, axis = plt.subplots(figsize=(12, 7), dpi=100)
    x = range(len(selected))
    colors = ["#22c55e" if close >= open_ else "#ef4444" for open_, close in zip(selected.open, selected.close)]
    axis.vlines(x, selected.low, selected.high, color=colors, linewidth=0.8)
    axis.bar(x, selected.close - selected.open, bottom=selected.open, color=colors, width=0.6)
    index_map = {original: display for display, original in enumerate(selected.index)}
    for swing in swings or []:
        if swing.index in index_map:
            axis.text(index_map[swing.index], swing.price, swing.label or swing.kind, fontsize=7, ha="center")
    for event in events or []:
        if event.index in index_map:
            axis.axhline(event.broken_level, color="#60a5fa", linewidth=0.7, alpha=0.7)
            axis.text(index_map[event.index], event.broken_level, event.kind, fontsize=7, color="#2563eb")
    for gap in fvgs or []:
        if gap.index in index_map and not gap.invalidated:
            axis.axhspan(gap.bottom, gap.top, color="#22c55e" if gap.direction == "bullish" else "#ef4444", alpha=0.12)
    for pool in pools or []:
        axis.axhline(pool.price, linestyle="--", linewidth=0.6, color="#64748b")
    if setup:
        axis.axhline(setup.entry, color="#2563eb", label="Entry")
        axis.axhline(setup.stop, color="#dc2626", label="Stop")
        for index, target in enumerate(setup.targets, 1):
            axis.axhline(target, color="#16a34a", linestyle=":", label=f"TP{index}")
        local_time = setup.created_at.astimezone(ZoneInfo(display_timezone))
        axis.set_title(f"{setup.symbol} {setup.timeframe} · {setup.model} {setup.direction.upper()} · {local_time:%Y-%m-%d %H:%M %Z}")
        axis.legend(loc="best")
    else:
        axis.set_title("ICT/SMC market state")
    tick_positions = list(range(0, len(selected), max(1, len(selected) // 8)))
    axis.set_xticks(tick_positions)
    axis.set_xticklabels([selected.iloc[position].time.strftime("%m-%d\n%H:%M") for position in tick_positions], fontsize=7)
    axis.grid(alpha=0.15)
    figure.tight_layout()
    target = Path(output or (f"output/charts/{setup.id}.png" if setup else "output/charts/market_state.png"))
    target.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target)
    plt.close(figure)
    return target
