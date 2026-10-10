from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ai.commentary import ClaudeCommentary
from src.alerts.dedupe import AlertDedupe
from src.alerts.formatter import format_result, format_setup, format_watch
from src.alerts.whatsapp import build_provider
from src.charts.annotate import render_chart
from src.config import load_settings
from src.analysis.sessions import forex_day
from src.data.feed import LiveFeed
from src.journal.journal import Journal
from src.mt5_client import MT5Client
from src.state.store import StateStore
from src.risk.guards import RiskGuards
from src.strategy.pipeline import build_context, scan_context
from src.tracking.outcome_tracker import update_outcome
from src.utils.logging import configure_logging

LOGGER = logging.getLogger("live")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the alerts-only MT5 scanner")
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--once", action="store_true", help="Scan once and exit")
    parser.add_argument("--chart", metavar="SYMBOL", help="Render current state and exit")
    parser.add_argument("--reset-halt", action="store_true")
    args = parser.parse_args()
    configure_logging(logging.INFO)
    settings = load_settings(args.config)
    if not settings.dry_run:
        raise SystemExit("Safety stop: v1 requires mode.dry_run: true")

    client = MT5Client(settings)
    client.connect()
    feed, provider = LiveFeed(client), build_provider(settings)
    store, dedupe, journal = StateStore(), None, Journal()
    dedupe = AlertDedupe(store)
    commentary = ClaudeCommentary(settings)
    active = store.load_active_setups()
    last_close = {}
    account_at_start = client.get_account()
    risk_config = settings.section("risk")
    guards = RiskGuards(float(risk_config.get("max_daily_loss_pct", 2)), float(risk_config.get("max_drawdown_pct", 6)), int(risk_config.get("max_consecutive_losses", 3)), float(account_at_start["balance"]), manually_halted=store.get_value("risk_halted", "false") == "true")
    if args.reset_halt:
        guards.reset_halt()
        store.set_value("risk_halted", "false")
    seen_deals: set[int] = set()
    has_real_results = False
    daily_counts: dict = {}
    day_stats: dict = {}
    current_trading_day = None
    provider.send_text("SYSTEM: ICT/SMC alert bot started in DRY_RUN mode. No orders can be placed.")
    timeframes, history = settings.section("timeframes"), settings.section("history_bars")

    try:
        while True:
            client.ensure_connected()
            account_snapshot = client.get_account()
            for deal in client.get_closed_deals(datetime.now(timezone.utc) - timedelta(days=7)):
                ticket = int(deal.get("ticket", 0))
                pnl = float(deal.get("profit", 0)) + float(deal.get("commission", 0)) + float(deal.get("swap", 0))
                if not ticket or ticket in seen_deals or pnl == 0:
                    continue
                seen_deals.add(ticket)
                has_real_results = True
                deal_time = pd.Timestamp(deal.get("time", 0), unit="s", tz="UTC")
                guards.update(forex_day(deal_time), pnl, float(account_snapshot["equity"]))
            for symbol_config in settings.enabled_symbols:
                symbol = symbol_config.name
                execution = feed.get(symbol, timeframes["execution"], int(history.get(timeframes["execution"], 1500)))
                if execution.empty or (not args.once and last_close.get(symbol) == execution.iloc[-1].close_time):
                    continue
                last_close[symbol] = execution.iloc[-1].close_time
                bias_frame = feed.get(symbol, timeframes["bias"], int(history.get(timeframes["bias"], 600)))
                daily_frame = feed.get(symbol, "D1", int(history.get("D1", 500))) if settings.section("strategy").get("bias_method") == "daily_structure" else None
                specs, account = client.get_symbol_specs(symbol), client.get_account()
                context = build_context(settings, symbol_config, execution, bias_frame, specs, float(account["balance"]), daily_frame=daily_frame)
                if args.chart == symbol:
                    path = render_chart(execution, swings=context.swings, events=context.structure, fvgs=context.fvgs, pools=context.pools)
                    print(path)
                    return
                spread = client.get_spread(symbol)
                trading_day = forex_day(execution.iloc[-1].close_time)
                if current_trading_day is None:
                    current_trading_day = trading_day
                elif trading_day != current_trading_day:
                    stats = day_stats.get(current_trading_day, {"setups": 0, "results": 0, "r": 0.0})
                    provider.send_text(f"SYSTEM daily summary {current_trading_day}: {stats['setups']} setups, {stats['results']} results, {stats['r']:+.2f}R")
                    current_trading_day = trading_day
                guard_allowed, guard_reason = guards.allowed(trading_day, float(account["equity"]))
                if not guard_allowed and store.get_value("last_guard_reason") != guard_reason:
                    provider.send_text(f"SYSTEM: New alerts halted — {guard_reason}")
                    store.set_value("last_guard_reason", guard_reason)
                    if "drawdown" in guard_reason.lower():
                        store.set_value("risk_halted", "true")
                setups, _ = scan_context(settings, symbol_config, context, spread_points=spread, guard_allowed=guard_allowed, active_symbol=any(item.symbol == symbol and item.status in {"pending", "triggered"} for item in active), daily_count=daily_counts.get(trading_day, 0))
                for pool in context.pools:
                    watch_key = f"watch:{symbol}:{pool.side}:{pool.price}:{pool.resolved_at}"
                    if pool.status == "swept" and settings.section("alerts").get("send_watch_alerts", True) and not dedupe.already_sent(watch_key, "WATCH"):
                        provider.send_text(format_watch(symbol, pool.side, pool.price))
                        dedupe.mark_sent(watch_key, "WATCH")
                for setup in setups:
                    if setup.created_at != execution.iloc[-1].close_time or dedupe.already_sent(setup.id):
                        continue
                    ai_text = commentary.generate(setup)
                    chart = render_chart(execution, setup, swings=context.swings, events=context.structure, fvgs=context.fvgs, pools=context.pools)
                    message = format_setup(setup, specs.digits, settings.section("alerts").get("display_timezone", "Asia/Karachi"), ai_text)
                    provider.send_image(chart, message) if settings.section("alerts").get("attach_chart", True) else provider.send_text(message)
                    dedupe.mark_sent(setup.id)
                    store.save_setup(setup)
                    journal.append(setup, spread=spread, commentary=ai_text, chart_path=str(chart))
                    active.append(setup)
                    daily_counts[trading_day] = daily_counts.get(trading_day, 0) + 1
                    stats = day_stats.setdefault(trading_day, {"setups": 0, "results": 0, "r": 0.0})
                    stats["setups"] += 1
                current_bar = execution.iloc[-1]
                for setup in list(active):
                    outcome = update_outcome(setup, current_bar)
                    if outcome:
                        provider.send_text(format_result(setup, outcome.status, outcome.result_r))
                        store.update_status(setup.id, outcome.status)
                        journal.update_status(setup.id, outcome.status, result_r=outcome.result_r if outcome.result_r is not None else "", exit_price=outcome.price if outcome.price is not None else "")
                        if outcome.status not in {"triggered"}:
                            stats = day_stats.setdefault(trading_day, {"setups": 0, "results": 0, "r": 0.0})
                            stats["results"] += 1
                            stats["r"] += float(outcome.result_r or 0)
                            if not has_real_results:
                                pnl = setup.risk_amount * float(outcome.result_r or 0)
                                guards.update(trading_day, pnl, float(account["equity"]) + pnl)
                            active.remove(setup)
            if args.once:
                break
            time.sleep(10)
    except KeyboardInterrupt:
        provider.send_text("SYSTEM: ICT/SMC alert bot stopped.")
    finally:
        store.close()
        client.shutdown()


if __name__ == "__main__":
    main()
