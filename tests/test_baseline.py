import numpy as np
import pytest

from sqzlab.baseline import CoinSeries, random_baseline


def fake_ind(n=400, seed=1):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
    o = np.r_[c[0], c[:-1]]
    h, l = np.maximum(o, c) * 1.004, np.minimum(o, c) * 0.996
    ema = c.copy()
    for i in range(1, n):
        ema[i] = ema[i - 1] + (c[i] - ema[i - 1]) * 2 / 21
    return dict(open=o, high=h, low=l, close=c, atr=np.full(n, 1.0), ema1=ema, ema3=ema)


def series(ind):
    return CoinSeries(ind, np.datetime64("2017-01-01") + np.arange(len(ind["close"])), None, None)


def test_trade_stop_with_gap_and_commission():
    ind = fake_ind()
    ind["close"][:] = 100.0
    ind["ema1"][:] = 90.0                       # nunca sale por EMA
    ind["open"][:], ind["low"][:], ind["high"][:] = 100.0, 99.5, 100.5
    ind["low"][5], ind["open"][5] = 90.0, 95.0  # gap: el stop (kd=2 -> 98) se llena a min(open, stop) = 95
    j, r = series(ind).trade(1, 2, 2.0, 0.0005)
    assert j == 5
    assert r == pytest.approx(((95.0 - 100.0) - 0.0005 * 195.0) / 2.0)


def test_trade_exits_on_close_below_ema():
    ind = fake_ind()
    ind["close"][:], ind["open"][:], ind["low"][:], ind["high"][:] = 100.0, 100.0, 99.9, 100.1
    ind["ema1"][:] = 90.0
    ind["ema1"][7] = 101.0                      # cierre 100 < ema 101 en la vela 7
    j, r = series(ind).trade(1, 2, 3.0, 0.0)
    assert j == 7 and r == pytest.approx(0.0)


def test_baseline_is_reproducible_and_changes_with_tag():
    cs = {"X": series(fake_ind())}
    a = random_baseline(cs, {"X": (5, 5)}, kd=1.5, reps=20, seed_tag="t")
    b = random_baseline(cs, {"X": (5, 5)}, kd=1.5, reps=20, seed_tag="t")
    c = random_baseline(cs, {"X": (5, 5)}, kd=1.5, reps=20, seed_tag="otro")
    assert a == b and a["mean"] != c["mean"]
    assert a["p95"] >= a["p50"]
