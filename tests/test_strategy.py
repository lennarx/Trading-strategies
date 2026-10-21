import pytest

from sqzlab.data import load
from sqzlab.fetch import path_for
from sqzlab.strategy import DEFAULTS, simulate, v2_params

pytestmark = pytest.mark.skipif(not path_for("bitstamp", "BTC", "1d").exists(), reason="faltan datos de Bitstamp")


@pytest.fixture(scope="module")
def df():
    return load("bitstamp", "BTC", "1d", start="2017-01-01", end="2026-10-19")


def kinds(res):
    return {(t.kind, t.side) for t in res.trades}


def test_default_has_no_d_trades_and_v2_params_has_d(df):
    assert not any(k == "D" for k, _ in kinds(simulate(df)))
    assert any(k == "D" for k, _ in kinds(simulate(df, **v2_params())))


def test_side_toggles_are_respected(df):
    r = simulate(df, **v2_params(dict(dLong=False, cLong=False, aShort=False)))
    ks = kinds(r)
    assert ("D", 1) not in ks and ("C", 1) not in ks and ("A", -1) not in ks


def test_mintick_off_by_default_changes_nothing(df):
    a = simulate(df)
    b = simulate(df, mintick=None, tick_stop=True, tick_fill=True)
    assert [t.pnl_net for t in a.trades] == [t.pnl_net for t in b.trades]


def test_risk_is_1R_per_trade_on_stop_exits(df):
    r = simulate(df, **v2_params())
    stops = [t for t in r.trades if t.exit_reason == "stop" and t.kind != "B"]
    assert stops and all(-1.3 < t.r_net < -0.7 for t in stops)   # ~ -1R neto de comision (los gaps pueden pasarse)


def test_slippage_off_by_default_and_hurts_when_on(df):
    base = simulate(df, **v2_params())
    zero = simulate(df, **v2_params(dict(slip_pct=0.0)))
    assert [t.pnl_net for t in base.trades] == [t.pnl_net for t in zero.trades]
    slipped = simulate(df, **v2_params(dict(slip_pct=0.10)))
    assert len(slipped.trades) == len(base.trades)
    assert sum(t.pnl_net for t in slipped.trades) < sum(t.pnl_net for t in base.trades)
    t0, t1 = base.trades[0], slipped.trades[0]
    assert t1.entry_px == pytest.approx(t0.entry_px * (1 + t0.side * 0.001))


def test_variants_are_off_by_default_and_change_results_when_on(df):
    base = simulate(df, **v2_params())
    off = simulate(df, **v2_params(dict(trailK=0.0, beR=0.0, exitMid=False, regimeFilter=False)))
    assert [t.pnl_net for t in base.trades] == [t.pnl_net for t in off.trades]
    for over in (dict(trailK=3.0), dict(beR=0.5), dict(exitMid=True)):
        on = simulate(df, **v2_params(over))
        assert [t.pnl_net for t in on.trades] != [t.pnl_net for t in base.trades], over


def test_trailing_stop_only_moves_in_favor_and_keeps_initial_risk(df):
    r = simulate(df, **v2_params(dict(trailK=2.0)))
    stops = [t for t in r.trades if t.exit_reason == "stop"]
    assert stops and all(t.risk_cash > 0 for t in stops)
    assert any(t.r_net > 0 for t in stops)       # un stop trailing puede salir con ganancia (R medido contra el riesgo inicial)


def test_break_even_caps_the_loss_of_trades_that_reached_the_trigger(df):
    r = simulate(df, **v2_params(dict(beR=0.5)))
    be = [t for t in r.trades if t.exit_reason == "stop" and t.r_net > -0.5]
    assert be, "debe haber stops que salieron cerca de break-even"


def test_regime_filter_blocks_all_longs_when_flag_is_false(df):
    import numpy as np
    r = simulate(df, regime=np.zeros(len(df), bool), **v2_params(dict(regimeFilter=True)))
    assert r.trades and all(t.side == -1 for t in r.trades)
    r_all = simulate(df, regime=np.ones(len(df), bool), **v2_params(dict(regimeFilter=True)))
    base = simulate(df, **v2_params())
    assert [t.pnl_net for t in r_all.trades] == [t.pnl_net for t in base.trades]


def test_btc_regime_flags_use_yesterday_only():
    import pandas as pd
    from sqzlab.variants import _btc_bull, regime_flags
    bull = _btc_bull()
    day = pd.Timestamp("2021-03-10")
    got = regime_flags(pd.to_datetime(["2021-03-10 00:00", "2021-03-10 20:00"]))
    assert got[0] == got[1] == bool(bull.loc[pd.Timestamp("2021-03-09")])
    assert day in bull.index


def test_regime_flags_accept_a_series_like_simulate_passes(df):
    from sqzlab.variants import regime_flags
    assert len(regime_flags(df["time_utc"])) == len(df)
