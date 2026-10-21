import numpy as np
import pandas as pd

from sqzlab.data import to_weekly
from sqzlab.indicators import ema, linreg_end, pivots, rma, rsi, sma


def test_ema_seed_sma_is_nan_until_n_and_seeded_with_sma():
    x = np.arange(1, 11, dtype=float)
    e = ema(x, 4, seed="sma")
    assert np.isnan(e[:3]).all()
    assert e[3] == x[:4].mean()
    assert np.isclose(e[4], 0.4 * x[4] + 0.6 * e[3])


def test_ema_seed_first_starts_at_first_value():
    e = ema(np.array([5.0, 7.0]), 3, seed="first")
    assert e[0] == 5.0 and np.isclose(e[1], 0.5 * 7 + 0.5 * 5)


def test_rma_seed_is_sma_ignoring_leading_nan():
    r = rma(np.array([np.nan, 1.0, 2.0, 3.0, 4.0]), 3)
    assert np.isnan(r[:3]).all() and r[3] == 2.0 and np.isclose(r[4], (4 + 2 * 2.0) / 3)


def test_linreg_end_on_a_line_returns_last_value():
    x = 3.0 + 2.0 * np.arange(30)
    assert np.allclose(linreg_end(x, 20)[19:], x[19:])


def test_rsi_all_gains_is_100():
    assert rsi(np.arange(1.0, 40.0), 14)[-1] == 100.0


def test_pivot_low_and_high_with_confirmation_delay():
    x = np.array([5, 4, 3, 2, 1, 2, 3, 4, 5, 6, 7], float)
    lo = pivots(x, 3, 3, "low")
    assert lo[7] == 1.0 and np.isnan(np.delete(lo, 7)).all()      # pivote en indice 4, confirmado en 4+3
    hi = pivots(-x, 3, 3, "high")
    assert hi[7] == -1.0


def test_pivot_tie_on_left_invalidates_tie_on_right_does_not():
    left_tie = pivots(np.array([3, 1, 1, 2, 3], float), 2, 1, "low")[3]
    right_tie = pivots(np.array([3, 2, 1, 1, 2], float), 2, 1, "low")[3]
    assert np.isnan(left_tie) and right_tie == 1.0


def test_weekly_starts_monday_utc():
    idx = pd.date_range("2011-08-18", periods=20, freq="D")      # arranca un jueves
    d = pd.DataFrame(dict(time_utc=idx, open=1.0, high=2.0, low=0.5, close=1.5, volume=1.0))
    w = to_weekly(d)
    assert w.time_utc.iloc[0] == pd.Timestamp("2011-08-15")
    assert (w.time_utc.dt.dayofweek == 0).all()
