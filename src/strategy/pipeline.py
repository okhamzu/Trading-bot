from __future__ import annotations

import logging
from dataclasses import replace

import pandas as pd

from src.analysis.atr import with_atr
from src.analysis.displacement import displacement_mask
from src.analysis.fvg import detect_fvgs
from src.analysis.liquidity import detect_liquidity_pools
from src.analysis.order_blocks import detect_order_blocks
from src.analysis.ranges import current_dealing_range
from src.analysis.structure import detect_structure
from src.analysis.swings import detect_swings
from src.config import Settings, SymbolConfig
from src.domain import Setup, SymbolSpecs
from src.risk.sizing import calculate_position_size
from src.strategy.bias import calculate_bias
from src.strategy.context import MarketContext
from src.strategy.filters import FilterResult, apply_filters
from src.strategy.models import MODELS

LOGGER = logging.getLogger(__name__)


def build_context(
    settings: Settings,
    symbol: SymbolConfig,
    execution: pd.DataFrame,
    bias_frame: pd.DataFrame,
    specs: SymbolSpecs,
    balance: float,
    bias_method: str | None = None,
    daily_frame: pd.DataFrame | None = None,
) -> MarketContext:
    atr_config = settings.section("displacement")
    period = int(atr_config.get("atr_period", 14))
    execution = with_atr(execution, period)
    bias_frame = with_atr(bias_frame, period)
    swing_config = settings.section("swings").get("lookback", {})
    execution_tf = settings.section("timeframes")["execution"]
    bias_tf = settings.section("timeframes")["bias"]
    swings = detect_swings(execution, int(swing_config.get(execution_tf, 3)))
    bias_swings = detect_swings(bias_frame, int(swing_config.get(bias_tf, 3)))
    displacement = displacement_mask(
        execution,
        float(atr_config.get("min_body_atr", 1.2)),
        float(atr_config.get("min_body_to_range", 0.6)),
    )
    structure = detect_structure(execution, swings, settings.section("structure").get("break_confirmation", "close"), displacement)
    bias_structure = detect_structure(bias_frame, bias_swings, settings.section("structure").get("break_confirmation", "close"))
    liquidity = settings.section("liquidity")
    pools = detect_liquidity_pools(
        execution,
        swings,
        float(liquidity.get("equal_level_tolerance_atr", 0.1)),
        int(liquidity.get("min_touches", 2)),
        specs.point,
        symbol.sweep_buffer_points,
    )
    fvgs = detect_fvgs(execution, float(settings.section("fvg").get("min_size_atr", 0.1)))
    blocks = detect_order_blocks(execution, structure, settings.section("order_blocks").get("zone", "full_range"))
    dealing_range = current_dealing_range(bias_swings, bias_structure)
    method = bias_method or settings.section("strategy").get("bias_method", "htf_structure")
    daily_events = None
    if daily_frame is not None and not daily_frame.empty:
        daily = with_atr(daily_frame, period)
        daily_swings = detect_swings(daily, int(swing_config.get("D1", 3)))
        daily_events = detect_structure(daily, daily_swings)
    bias = calculate_bias(method, float(execution.iloc[-1].close), bias_structure, dealing_range, daily_events)
    return MarketContext(symbol.name, execution_tf, execution, bias_frame, swings, structure, bias_swings, bias_structure, pools, fvgs, blocks, bias, dealing_range, specs, settings.section("sessions"), balance)


def scan_context(
    settings: Settings,
    symbol_config: SymbolConfig,
    context: MarketContext,
    model_names: list[str] | None = None,
    spread_points: float | None = None,
    guard_allowed: bool = True,
    active_symbol: bool = False,
    daily_count: int = 0,
) -> tuple[list[Setup], dict[str, FilterResult]]:
    strategy = settings.section("strategy")
    names = model_names or list(strategy.get("active_models", ["sweep_mss_fvg"]))
    accepted: list[Setup] = []
    rejected: dict[str, FilterResult] = {}
    for name in names:
        model_class = MODELS[name]
        kwargs = {
            "expiry_bars": int(strategy.get("setup_expiry_bars", 12)),
            "stop_buffer_points": symbol_config.stop_buffer_points,
            "neutral_bias_trades": bool(strategy.get("neutral_bias_trades", False)),
        }
        if name == "sweep_mss_fvg":
            kwargs["max_sweep_to_mss_bars"] = int(strategy.get("max_sweep_to_mss_bars", 10))
            kwargs["entry_level"] = settings.section("fvg").get("entry_level", "edge")
        model = model_class(**kwargs)
        for setup in model.scan(context):
            size = calculate_position_size(context.balance, float(settings.section("risk").get("risk_per_trade_pct", 0.75)), setup.entry, setup.stop, context.specs)
            sized = replace(setup, lot_size=size.lots, risk_amount=size.risk_amount)
            result = apply_filters(
                sized,
                sessions=context.sessions,
                min_rr=float(strategy.get("min_rr", 2.0)),
                spread_points=spread_points,
                max_spread_points=symbol_config.max_spread_points,
                guard_allowed=guard_allowed,
                active_symbol=active_symbol,
                daily_count=daily_count,
                max_daily_count=int(settings.section("risk").get("max_setups_per_day", 3)),
                news_window_minutes=int(settings.section("news_blackout").get("window_minutes", 30)),
                news_events=[_utc_datetime(value) for value in settings.section("news_blackout").get("events", [])],
            )
            if result.passed:
                accepted.append(sized)
            else:
                rejected[sized.id] = result
                LOGGER.debug("Rejected %s: %s", sized.id, "; ".join(result.reasons))
    return accepted, rejected


def _utc_datetime(value: str):
    timestamp = pd.Timestamp(value)
    timestamp = timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
    return timestamp.to_pydatetime()
