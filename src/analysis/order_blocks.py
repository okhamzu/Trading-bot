from __future__ import annotations

import pandas as pd

from src.domain import OrderBlock, StructureEvent


def detect_order_blocks(frame: pd.DataFrame, events: list[StructureEvent], zone: str = "full_range") -> list[OrderBlock]:
    if zone not in {"full_range", "body"}:
        raise ValueError("Order-block zone must be full_range or body")
    blocks: list[OrderBlock] = []
    for event in events:
        preceding = frame.iloc[max(0, event.index - 6) : event.index]
        opposing = preceding[preceding.close < preceding.open] if event.direction == "bullish" else preceding[preceding.close > preceding.open]
        if opposing.empty:
            continue
        index = int(opposing.index[-1])
        candle = frame.loc[index]
        if zone == "full_range":
            bottom, top = float(candle.low), float(candle.high)
        elif event.direction == "bullish":
            bottom, top = float(candle.low), float(candle.open)
        else:
            bottom, top = float(candle.open), float(candle.high)
        block = OrderBlock(index, candle.close_time, event.direction, bottom, top)
        for _, bar in frame.loc[event.index + 1 :].iterrows():
            block.mitigated = block.mitigated or (float(bar.low) <= top and float(bar.high) >= bottom)
            if (event.direction == "bullish" and float(bar.close) < bottom) or (event.direction == "bearish" and float(bar.close) > top):
                block.invalidated = True
                break
        blocks.append(block)
    return blocks
