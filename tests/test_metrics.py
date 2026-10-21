import numpy as np
import pandas as pd
import pytest

from sqzlab.metrics import COLS, max_drawdown_r, summarize, window


def frame(rows):
    df = pd.DataFrame(rows, columns=COLS[:6])
    df["sd"] = 1.0
    df["entry_t"], df["exit_t"] = pd.to_datetime(df["entry_t"]), pd.to_datetime(df["exit_t"])
    return df


ROWS = [("A", "B", 1, "2017-02-01", "2017-02-05", 2.0), ("A", "A", -1, "2017-03-01", "2017-03-02", -1.0),
        ("B", "B", 1, "2018-01-01", "2018-01-09", -1.0), ("B", "C", -1, "2024-02-01", "2024-02-03", 3.0)]


def test_summarize_synthetic_trades():
    s = summarize(frame(ROWS))
    assert s["n"] == 4 and s["total"] == pytest.approx(3.0) and s["exp"] == pytest.approx(0.75)
    assert s["pf"] == pytest.approx(5.0 / 2.0) and s["win"] == pytest.approx(0.5)
    assert s["exp_ex_best"] == pytest.approx(0.0 / 3)          # sin el +3R: (2-1-1)/3
    assert s["med_coin"] == pytest.approx(np.median([0.5, 1.0]))  # A: (2-1)/2 ; B: (-1+3)/2


def test_drawdown_in_r_follows_exit_order():
    # equity 0 -> +2 -> +1 -> 0 -> +3 : pico 2, piso 0
    assert max_drawdown_r(frame(ROWS)) == pytest.approx(2.0)


def test_window_filters_by_entry_date_inclusive():
    w = window(frame(ROWS), "2017-01-01", "2023-12-31")
    assert len(w) == 3 and window(frame(ROWS), "2024-01-01")["R"].tolist() == [3.0]


def test_empty_summary_is_zero():
    assert summarize(frame([]))["n"] == 0


def test_trimmed_expectation_drops_top_two_percent():
    rows = [("A", "B", 1, "2020-01-01", "2020-01-02", r) for r in [-1.0] * 99 + [50.0]]
    s = summarize(frame(rows))
    assert s["exp"] == pytest.approx((-99 + 50) / 100) and s["exp_trim"] == pytest.approx(-1.0)   # ceil(2%*100)=2 mejores fuera
