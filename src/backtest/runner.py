from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from src.backtest.engine import BacktestEngine
from src.backtest.metrics import calculate_metrics


BIAS_METHODS = ["htf_structure", "daily_structure", "premium_discount", "structure_plus_pd", "none"]
MODEL_NAMES = ["sweep_mss_fvg", "ob_retest", "ote", "silver_bullet"]


def run_grid(
    engine: BacktestEngine,
    symbols: list[str],
    models: list[str],
    biases: list[str],
    start: datetime,
    end: datetime,
    in_sample_pct: float = 70,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries, trade_frames = [], []
    split = pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start)) * (in_sample_pct / 100)
    risk_pct = float(engine.settings.section("risk").get("risk_per_trade_pct", 0.75))
    starting_balance = float(engine.settings.section("backtest").get("starting_balance", 10000))
    for symbol in symbols:
        for model in models:
            for bias in biases:
                trades, metrics = engine.run(symbol, model, bias, start, end)
                completed = trades.loc[trades.result_r.notna()].copy() if not trades.empty else trades
                if not completed.empty:
                    created = pd.to_datetime(completed["created_at"], utc=True)
                    split_utc = split.tz_localize("UTC") if split.tzinfo is None else split.tz_convert("UTC")
                    in_metrics = calculate_metrics(completed.loc[created <= split_utc], starting_balance, risk_pct)
                    out_metrics = calculate_metrics(completed.loc[created > split_utc], starting_balance, risk_pct)
                else:
                    in_metrics = calculate_metrics(completed, starting_balance, risk_pct)
                    out_metrics = in_metrics.copy()
                setups_count = int(len(trades))
                filled_count = int(trades["fill_time"].notna().sum()) if not trades.empty else 0
                metrics["setups"] = setups_count
                metrics["filled"] = filled_count
                metrics["fill_rate"] = filled_count / setups_count if setups_count else 0.0
                if not completed.empty:
                    fills = pd.to_datetime(completed["fill_time"], utc=True)
                    closes = pd.to_datetime(completed["close_time"], utc=True)
                    metrics["average_time_in_trade_minutes"] = float((closes - fills).dt.total_seconds().mean() / 60)
                    span_weeks = max((pd.Timestamp(end) - pd.Timestamp(start)).days / 7, 1 / 7)
                    metrics["trades_per_week"] = len(completed) / span_weeks
                    created = pd.to_datetime(completed["created_at"], utc=True)
                    metrics["r_by_session"] = json.dumps(completed.groupby("session", dropna=False)["result_r"].sum().round(3).to_dict(), default=str)
                    metrics["r_by_weekday"] = json.dumps(completed.groupby(created.dt.day_name())["result_r"].sum().round(3).to_dict())
                    metrics["r_by_month"] = json.dumps(completed.groupby(created.dt.strftime("%Y-%m"))["result_r"].sum().round(3).to_dict())
                else:
                    metrics.update(average_time_in_trade_minutes=0.0, trades_per_week=0.0, r_by_session="{}", r_by_weekday="{}", r_by_month="{}")
                metrics.update({f"in_{key}": value for key, value in in_metrics.items()})
                metrics.update({f"out_{key}": value for key, value in out_metrics.items()})
                metrics.update(symbol=symbol, model=model, bias_method=bias, meaningful=metrics["trades"] >= 50)
                summaries.append(metrics)
                if not trades.empty:
                    trades = trades.copy()
                    trades["grid_symbol"], trades["grid_model"], trades["grid_bias"] = symbol, model, bias
                    trade_frames.append(trades)
    summary = pd.DataFrame(summaries)
    if not summary.empty:
        summary = summary.sort_values(["out_expectancy", "out_trades"], ascending=[False, False])
    return summary, pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
