import numpy as np
import pandas as pd
import pytest

from sqzlab import optimize as O
from sqzlab.fetch import path_for

needs_data = pytest.mark.skipif(not path_for("bitstamp", "BTC", "1d").exists(), reason="faltan datos de Bitstamp")


def test_plateau_smooth_averages_self_and_axis_neighbors():
    s = np.array([[0.0, 3.0, 0.0], [0.0, 0.0, 0.0]])
    sm = O.plateau_smooth(s)
    assert sm[0, 1] == pytest.approx(3.0 / 4)     # centro + vecino de abajo + izquierda + derecha
    assert sm[1, 1] == pytest.approx(3.0 / 4)     # centro + vecino de arriba (3) + izquierda + derecha
    assert sm[0, 0] == pytest.approx(3.0 / 3)     # esquina: 3 puntos, uno vale 3


def test_grid_expands_linked_dims_and_fixed():
    g = O.Grid({"cHot+cCold": [(60, 40), (70, 30)], "cLook": [6, 10, 15]}, {"useC": True})
    c = g.combos()
    assert len(c) == 6 and g.shape() == (2, 3)
    assert c[0] == {"useC": True, "cHot": 60, "cCold": 40, "cLook": 6} and c[-1]["cHot"] == 70 and c[-1]["cLook"] == 15


def test_switches_isolate_one_leg():
    s = O.switches({("C", -1)})
    assert s["useC"] and s["cShort"] and not s["cLong"]
    assert not any(s[k] for k in ("useA", "useB", "useD", "aLong", "bShort", "dLong"))


def test_best_row_prefers_smooth_plateau_over_isolated_peak():
    # 1 dimension, 5 puntos: pico aislado en el 0 (exp .9) vs meseta en 2..4 (exp .4)
    exp = np.array([0.9, -1.0, 0.4, 0.4, 0.4])
    df = pd.DataFrame({"exp": exp, "n": 100, "feasible": True})
    raw = np.where(df["feasible"], exp, -1.0)
    df["smooth"] = O.plateau_smooth(raw)
    assert O.best_row(df) == 3


@needs_data
def test_optimizer_is_deterministic_on_two_combos():
    ev = O.Evaluator("d1", ["BTC", "ETH"], workers=1)
    grid = O.Grid({"adxMin": [20, 25]}, O.switches({("A", 1), ("A", -1)}))
    win = (pd.Timestamp("2017-01-01"), pd.Timestamp("2023-12-31"))
    a = O.score_grid(grid, ev.run(grid.combos()), win, 5)
    b = O.score_grid(grid, ev.run(grid.combos()), win, 5)
    assert a.equals(b) and len(a) == 2 and (a["n"] > 0).all()
