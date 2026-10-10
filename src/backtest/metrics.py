from __future__ import annotations

from math import inf

import pandas as pd


def calculate_metrics(trades: pd.DataFrame, starting_balance: float = 10000.0, risk_pct: float = 0.75) -> dict:
    if trades.empty:
        return {"trades": 0, "win_rate": 0.0, "average_r": 0.0, "expectancy": 0.0, "total_r": 0.0, "profit_factor": 0.0, "max_drawdown_r": 0.0, "max_drawdown_pct": 0.0, "longest_losing_streak": 0}
    results = pd.to_numeric(trades["result_r"], errors="coerce").dropna()
    wins, losses = results[results > 0], results[results < 0]
    cumulative = results.cumsum()
    drawdown_r = cumulative.cummax() - cumulative
    streak = longest = 0
    for value in results:
        streak = streak + 1 if value < 0 else 0
        longest = max(longest, streak)
    gross_profit, gross_loss = float(wins.sum()), abs(float(losses.sum()))
    return {
        "trades": int(len(results)),
        "win_rate": float((results > 0).mean()),
        "average_r": float(results.mean()),
        "expectancy": float(results.mean()),
        "total_r": float(results.sum()),
        "profit_factor": gross_profit / gross_loss if gross_loss else (inf if gross_profit else 0.0),
        "max_drawdown_r": float(drawdown_r.max()),
        "max_drawdown_pct": float(drawdown_r.max() * risk_pct),
        "longest_losing_streak": longest,
    }
