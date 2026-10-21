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
