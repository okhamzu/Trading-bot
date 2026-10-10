from __future__ import annotations

import pandas as pd

from src.domain import FairValueGap


def detect_fvgs(frame: pd.DataFrame, min_size_atr: float = 0.1) -> list[FairValueGap]:
    gaps: list[FairValueGap] = []
    for middle in range(1, len(frame) - 1):
        left, right = frame.iloc[middle - 1], frame.iloc[middle + 1]
        atr_value = float(frame.iloc[middle].get("atr", 0) or 0)
        minimum = min_size_atr * atr_value
        if float(right.low) > float(left.high) and float(right.low - left.high) >= minimum:
            bottom, top, direction = float(left.high), float(right.low), "bullish"
        elif float(right.high) < float(left.low) and float(left.low - right.high) >= minimum:
            bottom, top, direction = float(right.high), float(left.low), "bearish"
        else:
            continue
        gap = FairValueGap(middle, right.close_time, direction, bottom, top, (bottom + top) / 2)
        for _, bar in frame.iloc[middle + 2 :].iterrows():
            if direction == "bullish":
                overlap = max(0.0, top - max(bottom, float(bar.low)))
                gap.fill_pct = max(gap.fill_pct, min(1.0, overlap / (top - bottom)))
                gap.mitigated = gap.mitigated or float(bar.low) <= top
                if float(bar.close) < bottom:
                    gap.invalidated = True
                    break
            else:
                overlap = max(0.0, min(top, float(bar.high)) - bottom)
                gap.fill_pct = max(gap.fill_pct, min(1.0, overlap / (top - bottom)))
                gap.mitigated = gap.mitigated or float(bar.high) >= bottom
                if float(bar.close) > top:
                    gap.invalidated = True
                    break
        gaps.append(gap)
    return gaps
