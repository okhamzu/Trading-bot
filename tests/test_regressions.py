from datetime import timedelta
from unittest.mock import Mock
import pandas as pd
import pytest
from src.data.cache import normalize_history, write_history, write_symbol_specs, read_symbol_specs
from src.data.feed import HistoricalFeed, LiveFeed
from src.backtest.metrics import calculate_metrics
from src.backtest.fills import SimulatedTrade, update_trade
from src.tracking.outcome_tracker import update_outcome
from src.alerts.whatsapp import build_provider, LoggingProvider
from src.config import load_settings
from src.risk.sizing import calculate_position_size
from src.domain import SymbolSpecs
from tests.helpers import candles
from tests.test_fills_and_safety import setup


def test_cache_roundtrip_and_close_cutoff(tmp_path):
    frame = candles([(1, 2, 0, 1)] * 5)
    write_history(frame, 'XAUUSD', 'M15', tmp_path)
    feed = HistoricalFeed(tmp_path)
    assert len(feed.get('XAUUSD', 'M15', 10, frame.iloc[2].close_time)) == 3
    assert len(feed.get('XAUUSD', 'M15', 10, frame.iloc[2].close_time - timedelta(seconds=1))) == 2
    write_symbol_specs({'XAUUSD': {'point': .01}}, tmp_path)
    assert read_symbol_specs(tmp_path)['XAUUSD']['point'] == .01


def test_feed_normalizes_order_and_ignores_supplied_close_time():
    frame = candles([(1, 2, 0, 1)] * 3)
    frame['close_time'] = frame.time
    result = normalize_history(frame.iloc[::-1], 'M15')
    assert result.time.is_monotonic_increasing
    assert (result.close_time - result.time == timedelta(minutes=15)).all()


@pytest.mark.parametrize('value', [float('nan'), float('inf')])
def test_bad_prices_rejected(value):
    frame = candles([(1., 2., 0., 1.)])
    frame.loc[0, 'high'] = value
    with pytest.raises(ValueError):
        normalize_history(frame, 'M15')


def test_live_feed_excludes_future_bars():
    frame = candles([(1, 2, 0, 1)] * 3)
    client = Mock(); client.get_rates.return_value = frame
    assert len(LiveFeed(client).get('XAUUSD', 'M15', 3, frame.iloc[0].close_time)) == 1


def test_drawdown_includes_loss_from_start():
    assert calculate_metrics(pd.DataFrame({'result_r': [-1., -1.]}))['max_drawdown_r'] == 2


def test_unfilled_setups_not_counted_as_trades():
    metrics = calculate_metrics(pd.DataFrame({'status': ['expired', 'invalidated', 'sl'], 'result_r': [0, 0, -1]}))
    assert metrics['trades'] == 1
    assert metrics['max_drawdown_r'] == 1


def bar(low=94, high=111, close=101, now=None):
    return pd.Series({'low': low, 'high': high, 'close': close, 'close_time': now or setup().created_at + timedelta(minutes=15)})


def test_creation_candle_cannot_fill_or_resolve():
    trade = SimulatedTrade(setup())
    update_trade(trade, bar(now=setup().created_at), point=.01, spread_points=0, slippage_points=0)
    assert trade.status == 'pending'
    assert update_outcome(setup(), bar(now=setup().created_at)) is None


def test_costs_reduce_net_result():
    trade = SimulatedTrade(setup())
    update_trade(trade, bar(), point=.01, spread_points=10, slippage_points=20)
    assert trade.result_r == pytest.approx(-1.06)


def test_tp_first_configuration_is_honored():
    trade = SimulatedTrade(setup())
    update_trade(trade, bar(), point=.01, spread_points=0, slippage_points=0, same_bar_rule='tp_first')
    assert trade.status == 'tp1'


def test_live_outcome_resolves_stop_on_fill_candle():
    outcome = update_outcome(setup(), bar())
    assert outcome.status == 'sl'


def test_dry_run_never_builds_sending_provider():
    settings = load_settings('config/settings.yaml')
    assert isinstance(build_provider(settings), LoggingProvider)


@pytest.mark.parametrize('step', [0, -1, float('nan')])
def test_invalid_volume_step_rejected(step):
    specs = SymbolSpecs(.01, 2, .01, 1, .01, 100, step, 100)
    with pytest.raises(ValueError):
        calculate_position_size(10000, .75, 100, 95, specs)
