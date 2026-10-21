import numpy as np

from sqzlab import optimize as O


def test_probes_include_numpy_ints_and_floats_but_not_bools_or_zero():
    tuned = {"adxMin": np.int64(30), "atrMult": np.float64(0.1), "needMom": True, "invBars": 0, "minSqz": 12}
    probes = O.plateau_probes(tuned)
    names = {k for k, _, _ in probes}
    assert names == {"adxMin", "atrMult", "minSqz"}          # bool y 0 (apagado) no se mueven
    vals = {(k, s): v for k, s, v in probes}
    assert vals[("minSqz", "-20%")] == 10 and vals[("minSqz", "+20%")] == 14
    assert vals[("adxMin", "+20%")] == 36 and vals[("atrMult", "-20%")] == 0.08


def test_small_ints_still_move_by_one_step():
    probes = {(k, s): v for k, s, v in O.plateau_probes({"pbBars": 3})}
    assert probes[("pbBars", "-20%")] == 2 and probes[("pbBars", "+20%")] == 4
