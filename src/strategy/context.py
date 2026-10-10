from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.analysis.ranges import DealingRange
from src.domain import Bias, FairValueGap, LiquidityPool, OrderBlock, StructureEvent, Swing, SymbolSpecs


@dataclass
class MarketContext:
    symbol: str
    timeframe: str
    execution: pd.DataFrame
    bias_frame: pd.DataFrame
    swings: list[Swing]
    structure: list[StructureEvent]
    bias_swings: list[Swing]
    bias_structure: list[StructureEvent]
    pools: list[LiquidityPool]
    fvgs: list[FairValueGap]
    order_blocks: list[OrderBlock]
    bias: Bias
    dealing_range: DealingRange | None
    specs: SymbolSpecs
    sessions: dict
    balance: float
