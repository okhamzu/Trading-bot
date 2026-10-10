from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

import pandas as pd

from src.backtest.fills import SimulatedTrade, update_trade
from src.backtest.metrics import calculate_metrics
from src.config import Settings
from src.data.feed import HistoricalFeed
from src.domain import SymbolSpecs
from src.analysis.sessions import forex_day
from src.risk.guards import RiskGuards
from src.strategy.pipeline import build_context, scan_context


class BacktestEngine:
    def __init__(self, settings: Settings, feed: HistoricalFeed, specs: dict[str, SymbolSpecs]):
        self.settings, self.feed, self.specs = settings, feed, specs

    def run(self, symbol: str, model: str, bias_method: str, start: datetime, end: datetime) -> tuple[pd.DataFrame, dict]:
        symbol_config = self.settings.symbol(symbol)
        timeframes = self.settings.section("timeframes")
        execution_tf, bias_tf = timeframes["execution"], timeframes["bias"]
        all_execution = self.feed.load(symbol, execution_tf)
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
        start_ts = start_ts.tz_localize("UTC") if start_ts.tzinfo is None else start_ts.tz_convert("UTC")
        end_ts = end_ts.tz_localize("UTC") if end_ts.tzinfo is None else end_ts.tz_convert("UTC")
        clock = all_execution.loc[(all_execution.close_time >= start_ts) & (all_execution.close_time <= end_ts), "close_time"]
        pending: list[SimulatedTrade] = []
        finished: list[SimulatedTrade] = []
        seen: set[str] = set()
        balance = float(self.settings.section("backtest").get("starting_balance", 10000))
        spread = float(self.settings.section("backtest").get("spread_points", {}).get(symbol, 0))
        slippage = float(self.settings.section("backtest").get("slippage_points", {}).get(symbol, 0))
        risk_pct = float(self.settings.section("risk").get("risk_per_trade_pct", 0.75))
        risk_config = self.settings.section("risk")
        guards = RiskGuards(float(risk_config.get("max_daily_loss_pct", 2)), float(risk_config.get("max_drawdown_pct", 6)), int(risk_config.get("max_consecutive_losses", 3)), balance)
        daily_counts: dict = {}

        for now in clock:
            current_bar = all_execution.loc[all_execution.close_time == now].iloc[-1]
            for trade in list(pending):
                update_trade(trade, current_bar, point=self.specs[symbol].point, spread_points=spread, slippage_points=slippage, same_bar_rule=self.settings.section("backtest").get("same_bar_tp_sl", "sl_first"))
                if trade.status not in {"pending", "triggered"}:
                    pending.remove(trade)
                    finished.append(trade)
                    pnl = trade.setup.risk_amount * float(trade.result_r or 0)
                    balance += pnl
                    guards.update(forex_day(now), pnl, balance)

            execution = self.feed.get(symbol, execution_tf, int(self.settings.section("history_bars").get(execution_tf, 1500)), now.to_pydatetime())
            bias_frame = self.feed.get(symbol, bias_tf, int(self.settings.section("history_bars").get(bias_tf, 600)), now.to_pydatetime())
            daily_frame = self.feed.get(symbol, "D1", int(self.settings.section("history_bars").get("D1", 500)), now.to_pydatetime()) if bias_method == "daily_structure" else None
            if len(execution) < 30 or len(bias_frame) < 10:
                continue
            context = build_context(self.settings, symbol_config, execution, bias_frame, self.specs[symbol], balance, bias_method, daily_frame)
            day = forex_day(now)
            guard_allowed, _ = guards.allowed(day, balance)
            setups, _ = scan_context(self.settings, symbol_config, context, [model], spread_points=spread, guard_allowed=guard_allowed, active_symbol=bool(pending), daily_count=daily_counts.get(day, 0))
            for setup in setups:
                if setup.id in seen or pd.Timestamp(setup.created_at) != pd.Timestamp(now):
                    continue
                seen.add(setup.id)
                pending.append(SimulatedTrade(setup))
                daily_counts[day] = daily_counts.get(day, 0) + 1

        finished.extend(pending)
        rows = []
        for trade in finished:
            row = asdict(trade.setup)
            row.update(status=trade.status, fill_time=trade.fill_time, fill_price=trade.fill_price, close_time=trade.close_time, exit_price=trade.exit_price, result_r=trade.result_r)
            rows.append(row)
        trades = pd.DataFrame(rows)
        return trades, calculate_metrics(trades.loc[trades.result_r.notna()] if not trades.empty else trades, float(self.settings.section("backtest").get("starting_balance", 10000)), risk_pct)
