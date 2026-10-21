"""simulate(df, ind=compute(df, p)) tiene que dar exactamente lo mismo que simulate(df)."""
import pytest

from sqzlab.data import load
from sqzlab.fetch import path_for
from sqzlab.indicators import compute
from sqzlab.strategy import DEFAULTS, simulate, v2_params

pytestmark = pytest.mark.skipif(not path_for("bitstamp", "BTC", "4h").exists(), reason="faltan datos de Bitstamp")


@pytest.mark.parametrize("tf,start", [("1d", None), ("4h", "2024-01-01")])
def test_precomputed_indicators_give_identical_result(tf, start):
    df = load("bitstamp", "BTC", tf, start=start, end="2026-10-20")
    p = v2_params()
    a = simulate(df, **p)
    b = simulate(df, ind=compute(df, {**DEFAULTS, **p}), **p)
    assert len(a.trades) == len(b.trades) > 0
    assert a.final_equity == b.final_equity
    assert a.table().equals(b.table())
