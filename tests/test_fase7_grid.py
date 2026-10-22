"""Fase 7: conteo de la grilla (96 / 128 / 16), vecinos, meseta, factibilidad y criterios de SIRVE."""
import numpy as np

from sqzlab import fase7 as F


def test_grid_sizes_match_protocol():
    assert len(F.grid("h4")) == 96
    assert len(F.grid("d1")) == 128
    assert len(F.grid("w1")) == 16
    assert len(set(F.grid("h4"))) == 96


def test_neighbors_are_one_step_on_one_axis():
    c = F.Cfg(p1="off", p2=False, p3=20, p4=100, p5="risk")
    nb = F.neighbors("h4", c)
    # p1 (off->bear), p2 (->True), p3 (10 y 40), p4 (50; 100 es el ultimo), p5 (->vol)
    assert len(nb) == 6
    assert F.Cfg(p1="bear", p2=False, p3=20, p4=100, p5="risk") in nb and F.Cfg(p1="off", p2=False, p3=20, p4=50, p5="risk") in nb
    assert all(sum(getattr(x, k) != getattr(c, k) for k in ("p1", "p2", "p3", "p4", "p5")) == 1 for x in nb)
    corner = F.Cfg(p1="off", p2=False, p3=0, p4=0, p5="risk")
    assert len(F.neighbors("h4", corner)) == 5           # EMA20 y 'apagado' solo tienen un vecino por eje


def test_plateau_prefers_flat_region_over_isolated_peak():
    pts = F.grid("d1")
    calmar = {c: 1.0 for c in pts}
    feas = {c: True for c in pts}
    peak = F.Cfg(p1="off", p2=True, p3=20, p4=20, p5="vol")
    calmar[peak] = 5.0
    for n in F.neighbors("d1", peak):
        feas[n] = False                                    # pico aislado: todos los vecinos infactibles
    plateau_pt = F.Cfg(p1="bear", p2=False, p3=10, p4=10, p5="risk")
    calmar[plateau_pt] = 1.6
    for n in F.neighbors("d1", plateau_pt):
        calmar[n] = 1.6
    best = F.choose("d1", calmar, feas)
    assert best != peak and best == plateau_pt
    sc = F.plateau_scores("d1", calmar, feas)
    assert sc[peak] == (5.0 + -1.0 * len(F.neighbors("d1", peak))) / (1 + len(F.neighbors("d1", peak)))


def test_choose_none_when_nothing_feasible_and_tie_goes_to_first():
    pts = F.grid("w1")
    assert F.choose("w1", {c: 1.0 for c in pts}, {c: False for c in pts}) is None
    assert F.choose("w1", {c: 1.0 for c in pts}, {c: True for c in pts}) == pts[0]


def _rep(**kw):
    base = dict(n=150, cagr=0.5, dd=0.2, calmar=2.5, pnl_mediana_moneda=10.0, conc_max=0.3, cagr_sin_mejor=0.3,
                bh_btc_calmar=0.8, bh_btc_dd=0.6, bh_ew_calmar=0.7)
    base.update(kw)
    return base


def test_sirve_criteria_each_clause_can_fail():
    assert F.verdict_group(_rep()) == "CUMPLE"
    assert F.verdict_group(_rep(n=99)) == "SIN MUESTRA"
    for kw in (dict(cagr=-0.1), dict(calmar=0.5), dict(dd=0.4), dict(cagr_sin_mejor=-0.01), dict(pnl_mediana_moneda=-1.0),
               dict(conc_max=0.41), dict(conc_max=float("nan")), dict(bh_ew_calmar=3.0)):
        assert F.verdict_group(_rep(**kw)) == "NO CUMPLE", kw
    assert F.feasible_train(_rep()) and not F.feasible_train(_rep(n=99)) and not F.feasible_train(_rep(conc_max=0.5))
