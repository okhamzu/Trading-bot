from __future__ import annotations

import pandas as pd

from src.domain import LiquidityPool, Swing


def detect_liquidity_pools(
    frame: pd.DataFrame,
    swings: list[Swing],
    tolerance_atr: float = 0.1,
    min_touches: int = 2,
    point: float = 0.01,
    sweep_buffer_points: float = 0,
) -> list[LiquidityPool]:
    pools: list[LiquidityPool] = []
    for kind in ("high", "low"):
        candidates = [swing for swing in swings if swing.kind == kind]
        used: set[int] = set()
        for anchor_pos, anchor in enumerate(candidates):
            if anchor_pos in used:
                continue
            atr_at_anchor = float(frame.at[anchor.index, "atr"]) if "atr" in frame else 0.0
            tolerance = tolerance_atr * atr_at_anchor
            cluster = [(anchor_pos, anchor)]
            for position, candidate in enumerate(candidates[anchor_pos + 1 :], start=anchor_pos + 1):
                if abs(candidate.price - anchor.price) <= tolerance:
                    cluster.append((position, candidate))
            if len(cluster) >= min_touches:
                used.update(position for position, _ in cluster)
                members = [item for _, item in cluster]
                price = max(item.price for item in members) if kind == "high" else min(item.price for item in members)
                pools.append(LiquidityPool(price, "buy" if kind == "high" else "sell", f"equal_{kind}s", max(item.confirmed_at for item in members)))

    # Significant recent swings remain useful even when not equal highs/lows.
    for kind in ("high", "low"):
        same_kind = [swing for swing in swings if swing.kind == kind]
        if same_kind:
            swing = same_kind[-1]
            pools.append(LiquidityPool(swing.price, "buy" if kind == "high" else "sell", "swing", swing.confirmed_at))

    buffer = sweep_buffer_points * point
    for pool in pools:
        eligible = frame.index[frame["close_time"] >= pool.created_at].tolist()
        for index in eligible:
            bar = frame.loc[index]
            beyond = float(bar.high) >= pool.price + buffer if pool.side == "buy" else float(bar.low) <= pool.price - buffer
            if not beyond:
                continue
            next_bars = frame.loc[index : min(index + 2, len(frame) - 1)]
            returned_mask = next_bars.close < pool.price if pool.side == "buy" else next_bars.close > pool.price
            return_indices = next_bars.index[returned_mask].tolist()
            if return_indices:
                return_index = return_indices[0]
                swept_bars = frame.loc[index:return_index]
                pool.status, pool.resolved_index = "swept", index
                pool.resolved_at = frame.loc[return_index, "close_time"]
                pool.extreme = float(swept_bars.high.max() if pool.side == "buy" else swept_bars.low.min())
            else:
                follow_index = min(index + 1, len(frame) - 1)
                follow_close = float(frame.loc[follow_index, "close"])
                confirmed_break = follow_close > pool.price if pool.side == "buy" else follow_close < pool.price
                if confirmed_break:
                    pool.status, pool.resolved_index = "broken", index
                    pool.resolved_at = frame.loc[follow_index, "close_time"]
            if pool.status != "active":
                break
    return pools
