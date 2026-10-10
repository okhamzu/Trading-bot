from __future__ import annotations

from src.analysis.sessions import session_of
from src.domain import Setup
from src.strategy.bias import bias_allows
from src.strategy.context import MarketContext
from src.strategy.models.base import EntryModel
from src.strategy.models.common import reward_risk, setup_id, targets_from_pools
from src.utils.timeutils import timeframe_delta


class SweepMSSFVGModel(EntryModel):
    name = "sweep_mss_fvg"

    def __init__(self, *, max_sweep_to_mss_bars: int = 10, expiry_bars: int = 12, entry_level: str = "edge", stop_buffer_points: float = 0, neutral_bias_trades: bool = False):
        self.max_bars = max_sweep_to_mss_bars
        self.expiry_bars = expiry_bars
        self.entry_level = entry_level
        self.stop_buffer_points = stop_buffer_points
        self.neutral_bias_trades = neutral_bias_trades

    def scan(self, ctx: MarketContext) -> list[Setup]:
        results: list[Setup] = []
        for pool in ctx.pools:
            if pool.status != "swept" or pool.resolved_index is None:
                continue
            direction = "long" if pool.side == "sell" else "short"
            event_direction = "bullish" if direction == "long" else "bearish"
            if not bias_allows(ctx.bias, direction, self.neutral_bias_trades):
                continue
            events = [event for event in ctx.structure if event.kind == "MSS" and event.direction == event_direction and pool.resolved_index <= event.index <= pool.resolved_index + self.max_bars]
            if not events:
                continue
            mss = events[0]
            gaps = [gap for gap in ctx.fvgs if gap.direction == event_direction and not gap.invalidated and pool.resolved_index <= gap.index + 1 <= mss.index + 2]
            if not gaps:
                continue
            gap = gaps[-1]
            entry = gap.ce if self.entry_level == "ce" else (gap.top if direction == "long" else gap.bottom)
            extreme = pool.extreme if pool.extreme is not None else pool.price
            buffer = self.stop_buffer_points * ctx.specs.point
            stop = extreme - buffer if direction == "long" else extreme + buffer
            fallback = ctx.dealing_range.high if direction == "long" and ctx.dealing_range else ctx.dealing_range.low if ctx.dealing_range else None
            targets = targets_from_pools(ctx.pools, direction, entry, fallback)
            if not targets:
                continue
            created = mss.time
            rr = reward_risk(entry, stop, targets[0])
            results.append(Setup(
                id=setup_id(ctx.symbol, self.name, direction, created), symbol=ctx.symbol, timeframe=ctx.timeframe,
                model=self.name, bias_method=ctx.bias.method, bias_direction=ctx.bias.direction, direction=direction,
                created_at=created, entry=entry, entry_zone=(gap.bottom, gap.top), stop=stop, targets=targets,
                rr=rr, lot_size=0, risk_amount=0, session=session_of(created, ctx.sessions),
                reasons=[f"Swept {pool.side}-side {pool.source} at {pool.price}", f"{event_direction.title()} MSS close beyond {mss.broken_level}", "Displacement left an FVG"],
                expires_at=created + timeframe_delta(ctx.timeframe) * self.expiry_bars,
                metadata={"pool_price": pool.price, "sweep_index": pool.resolved_index, "mss_index": mss.index, "fvg_index": gap.index},
            ))
        return results
