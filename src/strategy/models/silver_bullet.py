from __future__ import annotations

from src.analysis.sessions import session_of
from src.domain import Setup
from src.strategy.bias import bias_allows
from src.strategy.context import MarketContext
from src.strategy.models.base import EntryModel
from src.strategy.models.common import reward_risk, setup_id, targets_from_pools
from src.utils.timeutils import timeframe_delta


class SilverBulletModel(EntryModel):
    name = "silver_bullet"

    def __init__(self, expiry_bars: int = 4, stop_buffer_points: float = 0, neutral_bias_trades: bool = False):
        self.expiry_bars, self.stop_buffer_points, self.neutral_bias_trades = expiry_bars, stop_buffer_points, neutral_bias_trades

    def scan(self, ctx: MarketContext) -> list[Setup]:
        setups: list[Setup] = []
        for gap in ctx.fvgs:
            if session_of(gap.created_at, ctx.sessions) != "silver_bullet" or gap.invalidated:
                continue
            direction = "long" if gap.direction == "bullish" else "short"
            if not bias_allows(ctx.bias, direction, self.neutral_bias_trades):
                continue
            entry = gap.top if direction == "long" else gap.bottom
            candle = ctx.execution.iloc[gap.index]
            buffer = self.stop_buffer_points * ctx.specs.point
            stop = float(candle.low) - buffer if direction == "long" else float(candle.high) + buffer
            targets = targets_from_pools(ctx.pools, direction, entry)
            if not targets:
                continue
            setups.append(Setup(setup_id(ctx.symbol, self.name, direction, gap.created_at), ctx.symbol, ctx.timeframe, self.name, ctx.bias.method, ctx.bias.direction, direction, gap.created_at, entry, (gap.bottom, gap.top), stop, targets, reward_risk(entry, stop, targets[0]), 0, 0, "silver_bullet", ["First valid FVG in Silver Bullet window"], gap.created_at + timeframe_delta(ctx.timeframe) * self.expiry_bars, metadata={"fvg_index": gap.index}))
        return setups[:1]
