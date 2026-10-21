import pandas as pd
import pytest

from sqzlab.portfolio import concurrency, curve_stats, run_portfolio


def frame(rows):
    df = pd.DataFrame(rows, columns=["coin", "entry_t", "exit_t", "R"])
    df["entry_t"], df["exit_t"] = pd.to_datetime(df["entry_t"]), pd.to_datetime(df["exit_t"])
    return df


TR = frame([("BTC", "2020-01-01", "2020-01-10", 2.0), ("ETH", "2020-01-02", "2020-01-05", -1.0),
            ("SOL", "2020-01-03", "2020-01-20", 0.5), ("BTC", "2020-02-01", "2020-02-03", -1.0)])


def test_no_caps_fixed_risk_reproduces_sum_of_R():
    cv, tk = run_portfolio(TR, risk_pct=1.0, compound=False)
    assert len(tk) == 4
    assert cv["equity"].iloc[-1] == pytest.approx(10000 * (1 + 0.01 * TR["R"].sum()))


def test_caps_skip_trades_and_max_pos_limits_concurrency():
    _, tk = run_portfolio(TR, risk_pct=1.0, max_pos=2, compound=False)
    assert list(tk["coin"]) == ["ETH", "BTC", "BTC"] or len(tk) == 3     # SOL entra con 2 abiertas -> se saltea
    assert "SOL" not in set(tk["coin"])
    _, tk2 = run_portfolio(TR, risk_pct=1.0, cap_pct=2.0, compound=False)   # 2% de tope = 2 trades de 1% a la vez
    assert "SOL" not in set(tk2["coin"])


def test_exit_before_entry_at_same_time_frees_risk():
    tr = frame([("BTC", "2020-01-01", "2020-01-05", 1.0), ("ETH", "2020-01-05", "2020-01-08", 1.0)])
    _, tk = run_portfolio(tr, risk_pct=1.0, max_pos=1, compound=False)
    assert len(tk) == 2


def test_curve_stats_drawdown_and_concurrency():
    cv, tk = run_portfolio(TR, risk_pct=1.0, compound=False)
    s = curve_stats(cv)
    assert 0 < s["dd"] < 0.05 and s["final"] > 10000
    assert concurrency(tk)["max_abiertas"] == 3
