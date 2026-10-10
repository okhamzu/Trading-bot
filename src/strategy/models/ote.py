from __future__ import annotations

from src.analysis.ranges import ote_zone
from src.analysis.sessions import session_of
from src.domain import Setup
from src.strategy.bias import bias_allows
from src.strategy.context import MarketContext
from src.strategy.models.base import EntryModel
from src.strategy.models.common import reward_risk, setup_id, targets_from_pools
from src.utils.timeutils import timeframe_delta


class OTEModel(EntryModel):
    name = "ote"

    def __init__(self, expiry_bars: int = 12, stop_buffer_points: float = 0, neutral_bias_trades: bool = False):
        self.expiry_bars, self.stop_buffer_points, self.neutral_bias_trades = expiry_bars, stop_buffer_points, neutral_bias_trades

    def scan(self, ctx: MarketContext) -> list[Setup]:
        setups: list[Setup] = []
        for event in [item for item in ctx.structure if item.kind == "MSS"]:
            direction = "long" if event.direction == "bullish" else "short"
            if not bias_allows(ctx.bias, direction, self.neutral_bias_trades):
                continue
            origin_window = ctx.execution.iloc[max(0, event.index - 8) : event.index + 1]
            origin = float(origin_window.low.min()) if direction == "long" else float(origin_window.high.max())
            destination = float(ctx.execution.loc[event.index, "high"] if direction == "long" else ctx.execution.loc[event.index, "low"])
            zone_low, zone_high, entry = ote_zone(origin, destination)
            buffer = self.stop_buffer_points * ctx.specs.point
            stop = origin - buffer if direction == "long" else origin + buffer
            targets = [destination] + targets_from_pools(ctx.pools, direction, entry)
            targets = [value for value in dict.fromkeys(targets) if (value > entry if direction == "long" else value < entry)][:3]
            if not targets:
                continue
            setups.append(Setup(setup_id(ctx.symbol, self.name, direction, event.time), ctx.symbol, ctx.timeframe, self.name, ctx.bias.method, ctx.bias.direction, direction, event.time, entry, (zone_low, zone_high), stop, targets, reward_risk(entry, stop, targets[0]), 0, 0, session_of(event.time, ctx.sessions), ["Bias-direction MSS", "Entry at 70.5% OTE retracement"], event.time + timeframe_delta(ctx.timeframe) * self.expiry_bars, metadata={"mss_index": event.index}))
        return setups
