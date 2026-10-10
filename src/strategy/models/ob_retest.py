from __future__ import annotations

from src.analysis.sessions import session_of
from src.domain import Setup
from src.strategy.bias import bias_allows
from src.strategy.context import MarketContext
from src.strategy.models.base import EntryModel
from src.strategy.models.common import reward_risk, setup_id, targets_from_pools
from src.utils.timeutils import timeframe_delta


class OrderBlockRetestModel(EntryModel):
    name = "ob_retest"

    def __init__(self, expiry_bars: int = 12, stop_buffer_points: float = 0, neutral_bias_trades: bool = False):
        self.expiry_bars, self.stop_buffer_points, self.neutral_bias_trades = expiry_bars, stop_buffer_points, neutral_bias_trades

    def scan(self, ctx: MarketContext) -> list[Setup]:
        setups: list[Setup] = []
        for block in ctx.order_blocks:
            direction = "long" if block.direction == "bullish" else "short"
            if block.invalidated or not bias_allows(ctx.bias, direction, self.neutral_bias_trades):
                continue
            event = next((item for item in ctx.structure if item.index > block.index and item.direction == block.direction), None)
            if event is None:
                continue
            entry = block.top if direction == "long" else block.bottom
            buffer = self.stop_buffer_points * ctx.specs.point
            stop = block.bottom - buffer if direction == "long" else block.top + buffer
            targets = targets_from_pools(ctx.pools, direction, entry)
            if not targets:
                continue
            created = event.time
            setups.append(Setup(setup_id(ctx.symbol, self.name, direction, created), ctx.symbol, ctx.timeframe, self.name, ctx.bias.method, ctx.bias.direction, direction, created, entry, (block.bottom, block.top), stop, targets, reward_risk(entry, stop, targets[0]), 0, 0, session_of(created, ctx.sessions), ["Displacement structure break", "Uninvalidated opposing order block"], created + timeframe_delta(ctx.timeframe) * self.expiry_bars, metadata={"ob_index": block.index}))
        return setups
