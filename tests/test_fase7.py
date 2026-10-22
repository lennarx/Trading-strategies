"""Fase 7: regresion de defaults, no-lookahead, Donchian, vol objetivo, equity marcada a mercado, topes de cartera."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sqzlab import universe as U
from sqzlab.donchian import days_to_bars, donchian_subtrades, half, vol_ann, vol_weight
from sqzlab.genpine import load_params
from sqzlab.htf import htf_flags
from sqzlab.optimize import BASE
from sqzlab.pf7 import Rules, run_cartera
from sqzlab.strategy import prev_close_max, prev_close_min, simulate

GOLDEN = Path(__file__).parent / "golden" / "simulate_pre_fase7.json"


def _digest(res) -> dict:
    rows = [(int(a.entry_i), int(a.exit_i), int(a.side), a.kind, round(float(a.entry_px), 8), round(float(a.exit_px), 8),
             round(float(a.pnl_net), 6)) for a in res.trades]
    return dict(n=len(rows), pnl=round(sum(x[6] for x in rows), 4), hash=hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
                final_equity=round(float(res.final_equity), 4))


@pytest.mark.skipif(not GOLDEN.exists(), reason="sin fixture dorado")
def test_defaults_regression_identical_to_pre_fase7():
    """Con las palancas apagadas (defaults) los trades son EXACTAMENTE los de antes de la Fase 7."""
    gold = json.loads(GOLDEN.read_text(encoding="utf-8"))
    for sym, code, tf in [("BTC", "1d", "d1"), ("ETH", "4h", "h4"), ("SOL", "1w", "w1"), ("DOGE", "1d", "d1")]:
        try:
            df = U.load_coin(sym, code)
        except FileNotFoundError:
            pytest.skip("sin datos en data/")
        assert _digest(simulate(df)) == gold[f"{sym}_{code}_defaults"], f"{sym} {code} defaults"
        assert _digest(simulate(df, **{**BASE, **load_params(tf)})) == gold[f"{sym}_{code}_vigente"], f"{sym} {code} vigente"


def _ohlc(close, start="2020-01-01", freq="D"):
    c = np.asarray(close, float)
    t = pd.date_range(start, periods=len(c), freq=freq)
    return pd.DataFrame(dict(time_utc=t, open=c, high=c * 1.01, low=c * 0.99, close=c, volume=1.0))


# ----------------------------------------------------------------------------------------------- Donchian
def test_donchian_prev_windows_exclude_current_bar():
    c = np.array([5.0, 3, 4, 8, 2, 9])
    assert np.isnan(prev_close_max(c, 3)[:3]).all()
    assert prev_close_max(c, 3)[3] == 5.0 and prev_close_max(c, 3)[4] == 8.0     # max de [5,3,4], luego [3,4,8]
    assert prev_close_min(c, 2)[2] == 3.0 and prev_close_min(c, 2)[5] == 2.0      # min de [3,4]; luego [8,2]


def test_donchian_entry_exit_by_hand():
    # N = 4 velas (D1: 4 dias no esta en los lookbacks; uso days_to_bars via tf d1 con d=4) -> salida con half = 2
    c = [10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 12, 20]
    df = _ohlc(c)
    sub = donchian_subtrades(df, "d1", [4], "X")
    # i=4: close 14 > max(10,11,12,13)=13 -> entra a 14. Sale cuando close < min de los 2 cierres previos:
    # i=6: 14 < min(14,15)? previos de i=6 son [14,15]->14: 14<14 no. i=7: 13 < min(15,14)=14 -> sale a 13
    t1 = sub.iloc[0]
    assert (t1.entry_i, t1.exit_i, t1.entry_px, t1.exit_px, t1.stop) == (4, 7, 14, 13, 12)   # nivel de salida al entrar = min de los 2 cierres previos [12, 13]
    assert not t1.open
    # reentrada: i=11 close 20 > max de [12,13,...]? previos 4: [13? ] -> cierres i=7..10 = 13,12,11,12 -> max 13 -> entra y queda abierta
    t2 = sub.iloc[1]
    assert (t2.entry_i, t2.exit_i, t2.open) == (11, 11, True)
    assert t2.w == 1.0


def test_donchian_ensemble_weights_and_conversion():
    assert [days_to_bars(d, "h4") for d in (20, 250)] == [120, 1500]
    assert [days_to_bars(d, "w1") for d in (5, 20, 60, 150, 250, 360)] == [4, 4, 9, 21, 36, 51]   # floor(d/7+.5), minimo 4
    assert half(1500) == 750 and half(4) == 2
    df = _ohlc(np.r_[np.linspace(100, 200, 120), np.linspace(200, 100, 60)])
    sub = donchian_subtrades(df, "d1", [5, 10], "X")
    assert set(sub["w"]) == {0.5}
    assert set(sub["lb"]) == {5, 10}


def test_donchian_no_lookahead():
    rng = np.random.default_rng(1)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 600)))
    full = donchian_subtrades(_ohlc(c), "d1", [10, 30], "X")
    cut = 400
    part = donchian_subtrades(_ohlc(c[:cut]), "d1", [10, 30], "X")
    a = full[(full["exit_i"] < cut - 1) & ~full["open"]].reset_index(drop=True)
    b = part[~part["open"]].reset_index(drop=True)
    cols = ["lb", "entry_i", "exit_i", "entry_px", "exit_px", "stop"]
    pd.testing.assert_frame_equal(a[cols].sort_values(cols).reset_index(drop=True), b[cols].sort_values(cols).reset_index(drop=True))


# ----------------------------------------------------------------------------------------------- vol objetivo
def test_vol_target_by_hand():
    rng = np.random.default_rng(7)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 300)))
    v = vol_ann(c, "d1")
    assert np.isnan(v[:90]).all() and not np.isnan(v[90])
    manual = np.std(np.diff(np.log(c))[1 + 0:90 + 0][-90:], ddof=1) * math.sqrt(365) if False else None
    lr = np.diff(np.log(c))
    expect = np.std(lr[100 - 90:100], ddof=1) * math.sqrt(365)      # retornos de las velas 11..100 (hasta el cierre de la 100)
    assert v[100] == pytest.approx(expect)
    # H4: ventana 540 velas y 2190 velas por anio
    c4 = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 800)))
    v4 = vol_ann(c4, "h4")
    assert np.isnan(v4[:540]).all() and not np.isnan(v4[540])
    assert v4[600] == pytest.approx(np.std(np.diff(np.log(c4))[600 - 540:600], ddof=1) * math.sqrt(2190))
    # peso: 0,25 / vol con tope 2
    assert vol_weight(0.5) == pytest.approx(0.5)
    assert vol_weight(0.05) == 2.0
    assert math.isnan(vol_weight(float("nan")))


def test_vol_mode_sizing_in_cartera():
    t = pd.date_range("2020-01-01", periods=6)
    cl = {"A": (t.to_numpy(), np.array([100.0, 100, 100, 100, 100, 100]))}
    tr = _trade("A", 1, 4, 100.0, 100.0, vol=0.5)
    r = run_cartera(tr, cl, t[0], t[-1], Rules(mode="vol", commission=0, slippage=0, max_pos=None))
    assert r["trades"].iloc[0]["notional"] == pytest.approx(10000 * 0.5)       # 0,25/0,5 = 0,5 de la equity


def _trade(coin, ke, kx, entry_px, exit_px, vol=0.5, sd=0.1, w=1.0, side=1, tid=None, is_open=False, start="2020-01-01"):
    t = pd.date_range(start, periods=max(kx, ke) + 5)
    return pd.DataFrame([dict(id=tid or f"{coin}-{ke}-{kx}", coin=coin, kind="A", side=side, entry_t=t[ke], exit_t=t[kx],
                              entry_px=entry_px, exit_px=exit_px, sd=sd, w=w, vol=vol, open=is_open)])


# ----------------------------------------------------------------------------------------------- equity marcada a mercado
def test_mark_to_market_equity_synthetic_case():
    t = pd.date_range("2020-01-01", periods=6)
    close = np.array([100.0, 100, 110, 120, 90, 90])
    cl = {"A": (t.to_numpy(), close)}
    tr = _trade("A", 1, 4, 100.0, 90.0)         # largo a 100 con stop a 10% -> riesgo 1% = 100 USD -> nocional 1000 -> qty 10
    r = run_cartera(tr, cl, t[0], t[-1], Rules(mode="risk", commission=0, slippage=0))
    assert r["eq"].tolist() == pytest.approx([10000, 10000, 10100, 10200, 9900, 9900])        # marcada a mercado
    assert r["eq_closed"].tolist() == pytest.approx([10000, 10000, 10000, 10000, 9900, 9900])  # solo realizada
    row = r["trades"].iloc[0]
    assert row["closed"] and row["pnl"] == pytest.approx(-100.0) and row["R"] == pytest.approx(-1.0)


def test_costs_commission_and_slippage_both_sides():
    t = pd.date_range("2020-01-01", periods=6)
    close = np.array([100.0, 100, 100, 100, 100, 100])
    cl = {"A": (t.to_numpy(), close)}
    tr = _trade("A", 1, 4, 100.0, 100.0)
    r = run_cartera(tr, cl, t[0], t[-1], Rules(mode="risk", commission=0.0005, slippage=0.0005))
    efill, xfill = 100 * 1.0005, 100 * (1 - 0.0005)
    qty = 1000 / efill
    expect = qty * (xfill - efill) - qty * efill * 0.0005 - qty * xfill * 0.0005
    assert r["trades"].iloc[0]["pnl"] == pytest.approx(expect)
    assert r["eq"][-1] == pytest.approx(10000 + expect)


def test_open_trade_at_end_is_marked_and_not_counted():
    t = pd.date_range("2020-01-01", periods=6)
    close = np.array([100.0, 100, 110, 120, 130, 130])
    cl = {"A": (t.to_numpy(), close)}
    tr = _trade("A", 1, 5, 100.0, 130.0, is_open=True)
    r = run_cartera(tr, cl, t[0], t[-1], Rules(mode="risk", commission=0, slippage=0))
    assert r["eq"][-1] == pytest.approx(10000 + 10 * 30)
    assert not r["trades"].iloc[0]["closed"]


def test_truncated_trade_at_window_end_is_cut():
    t = pd.date_range("2020-01-01", periods=10)
    close = np.array([100.0, 100, 110, 120, 130, 130, 50, 50, 50, 50])
    cl = {"A": (t.to_numpy(), close)}
    tr = _trade("A", 1, 8, 100.0, 50.0)         # sale despues del fin del tramo
    r = run_cartera(tr, cl, t[0], t[4], Rules(mode="risk", commission=0, slippage=0))
    assert len(r["eq"]) == 5 and r["eq"][-1] == pytest.approx(10000 + 10 * 30)       # no usa el cierre posterior (50)
    assert not r["trades"].iloc[0]["closed"]


def test_max_positions_and_gross_cap_and_order_exits_before_entries():
    t = pd.date_range("2020-01-01", periods=8)
    flat = np.full(8, 100.0)
    cl = {c: (t.to_numpy(), flat) for c in "ABC"}
    tr = pd.concat([_trade(c, 1, 5, 100.0, 100.0, sd=0.5) for c in "ABC"], ignore_index=True)
    r = run_cartera(tr, cl, t[0], t[-1], Rules(mode="risk", commission=0, slippage=0, max_pos=2, open_risk_cap=None))
    assert len(r["trades"]) == 2 and [s[1] for s in r["skipped"]] == ["cupo"]
    # tope de riesgo abierto 5%: cada trade arriesga 1% -> el 6.o se saltea
    cl6 = {f"C{i}": (t.to_numpy(), flat) for i in range(7)}
    tr6 = pd.concat([_trade(f"C{i}", 1, 5, 100.0, 100.0) for i in range(7)], ignore_index=True)
    r6 = run_cartera(tr6, cl6, t[0], t[-1], Rules(mode="risk", commission=0, slippage=0, max_pos=None, open_risk_cap=5.0))
    assert len(r6["trades"]) == 5 and all(s[1] == "riesgo" for s in r6["skipped"])
    # modo vol: vol 0,1 -> peso 2 -> el tope bruto 1,0 lo achica; el segundo no tiene hueco
    cl2 = {c: (t.to_numpy(), flat) for c in "AB"}
    tr2 = pd.concat([_trade("A", 1, 5, 100.0, 100.0, vol=0.1), _trade("B", 1, 5, 100.0, 100.0, vol=0.1)], ignore_index=True)
    r2 = run_cartera(tr2, cl2, t[0], t[-1], Rules(mode="vol", commission=0, slippage=0, max_pos=None))
    assert r2["trades"]["notional"].tolist() == pytest.approx([10000.0]) and [s[1] for s in r2["skipped"]] == ["tope"]
    # una salida y una entrada en la misma vela: la salida libera el cupo
    tr3 = pd.concat([_trade("A", 1, 4, 100.0, 100.0), _trade("B", 4, 6, 100.0, 100.0)], ignore_index=True)
    r3 = run_cartera(tr3, {c: (t.to_numpy(), flat) for c in "AB"}, t[0], t[-1], Rules(mode="risk", commission=0, slippage=0, max_pos=1))
    assert len(r3["trades"]) == 2 and r3["skipped"] == []


# ----------------------------------------------------------------------------------------------- HTF (P4/P1) sin lookahead
def test_htf_uses_previous_closed_bar():
    d1 = _ohlc([10.0] * 5 + [100.0] * 5, start="2020-01-01")                   # el cierre salta recien el dia 6 (2020-01-06)
    d1["close"] = [10.0] * 5 + [100.0] * 5
    h4_t = pd.date_range("2020-01-01", periods=10 * 6, freq="4h")
    fl = htf_flags(h4_t.to_numpy(), d1, 3)
    # EMA(3) con semilla SMA: valida desde el 3.er dia. Dia 6 (indice 5): close=100 > EMA, pero las H4 de ese dia usan el dia 5 (close 10)
    day = (h4_t - pd.Timestamp("2020-01-01")).days
    assert not fl["bull"][day == 5].any()            # H4 del dia 6 todavia NO ve el cierre del dia 6
    assert fl["bull"][day == 6].all()                # H4 del dia 7 ya ve el cierre del dia 6 (D-1)
    assert not fl["bull"][day <= 2].any()            # sin TF mayor cerrado o EMA aun NaN -> False


def test_htf_flags_truncation_invariance():
    rng = np.random.default_rng(3)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 400)))
    d1 = _ohlc(c)
    lt = pd.date_range("2020-01-01", periods=400 * 6, freq="4h")
    full = htf_flags(lt.to_numpy(), d1, 10)
    cut_day = 250
    d1c = d1.iloc[:cut_day]
    ltc = lt[lt < d1c["time_utc"].iloc[-1] + pd.Timedelta(days=1)]
    part = htf_flags(ltc.to_numpy(), d1c, 10)
    n = len(ltc)
    assert (full["bull"][:n] == part["bull"]).all() and (full["bear"][:n] == part["bear"]).all()


# ----------------------------------------------------------------------------------------------- palancas en simulate
def _tendencia(n=700, seed=5):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0008, 0.025, n)))
    return c


def _real_df():
    try:
        return U.load_coin("ETH", "1d")
    except FileNotFoundError:
        pytest.skip("sin datos en data/")


def test_levers_off_by_default_are_noops_on_real_data():
    df = _real_df()
    p = {**BASE, **load_params("d1")}
    a = simulate(df, **p)
    b = simulate(df, **{**p, "longHtf": False, "shortHtf": False, "donchExit": 0})
    assert a.table().equals(b.table())


def test_p3_donchian_exit_only_changes_a_and_b_exits():
    df = _real_df()
    p = {**BASE, **load_params("d1")}
    base = simulate(df, **p)
    on = simulate(df, **{**p, "donchExit": 20})
    reasons = {(t.kind, t.exit_reason) for t in on.trades}
    assert not any(k in "AB" and r == "ema" for k, r in reasons)          # A y B ya no salen por la EMA20
    assert any(k in "AB" and r == "donch" for k, r in reasons)
    assert all(r != "donch" for k, r in reasons if k in "CD")
    assert base.table().shape != on.table().shape or not base.table().equals(on.table())


def test_p4_filter_blocks_longs_when_htf_bearish_and_p1_blocks_shorts():
    df = _real_df()
    p = {**BASE, **load_params("d1")}
    n = len(df)
    none = dict(bull=np.zeros(n, bool), bear=np.zeros(n, bool))
    r = simulate(df, **{**p, "longHtf": True, "shortHtf": True}, htf=none)
    assert len(r.trades) == 0 and r.open_trade is None
    allp = dict(bull=np.ones(n, bool), bear=np.ones(n, bool))
    ra = simulate(df, **{**p, "longHtf": True, "shortHtf": True}, htf=allp)
    assert ra.table().equals(simulate(df, **p).table())
    with pytest.raises(ValueError):
        simulate(df, **{**p, "longHtf": True})


def test_levers_no_lookahead_truncation():
    """La senal en t no cambia si se truncan los datos en t: los trades cerrados antes del corte son identicos."""
    df = _real_df()
    p = {**BASE, **load_params("d1"), "donchExit": 20}
    n = len(df)
    rng = np.random.default_rng(0)
    bull = rng.random(n) > 0.3
    htf = dict(bull=bull, bear=~bull)
    full = simulate(df, **{**p, "longHtf": True, "shortHtf": True}, htf=htf)
    cut = n - 80
    part = simulate(df.iloc[:cut].reset_index(drop=True), **{**p, "longHtf": True, "shortHtf": True},
                    htf=dict(bull=bull[:cut], bear=(~bull)[:cut]))
    key = lambda r: [(t.entry_i, t.exit_i, t.side, t.kind, round(t.entry_px, 8), round(t.exit_px, 8)) for t in r.trades if t.exit_i < cut - 1]
    assert key(full) == key(part)


# ----------------------------------------------------------------------------------------------- revision independiente (2026-10-21)
def test_w1_r1_subtrades_have_unique_ids_and_full_weight():
    """Varios lookbacks de W1 caen en 4 velas: tienen que ser sub-senales distintas con ids unicos (K=9, peso 1/9 cada una)."""
    from sqzlab import fase7 as F
    from sqzlab.donchian import R1_DAYS
    df = _real_df()
    cd_key = ("w1", "ETH")
    F._COIN.pop(cd_key, None)
    try:
        t = F.e_trades("w1", "ETH", R1_DAYS)
    except FileNotFoundError:
        pytest.skip("sin datos")
    assert t["id"].is_unique and len(t) > 0
    assert set(t["w"].round(6)) == {round(1 / 9, 6)}
    assert t.groupby("entry_t").size().max() >= 4          # los 4 lookbacks de 4 velas entran a la vez: 4 filas, no 1


def test_run_cartera_rejects_duplicate_ids_and_keeps_accounting_identity():
    t = pd.date_range("2020-01-01", periods=8)
    cl = {"A": (t.to_numpy(), np.array([100.0, 100, 105, 110, 120, 120, 120, 120]))}
    one = _trade("A", 1, 5, 100.0, 120.0, vol=0.5, w=0.25, tid="x")
    with pytest.raises(ValueError):
        run_cartera(pd.concat([one, one], ignore_index=True), cl, t[0], t[-1], Rules(mode="vol", max_pos=None))
    two = pd.concat([one, one.assign(id="y")], ignore_index=True)
    r = run_cartera(two, cl, t[0], t[-1], Rules(mode="vol", max_pos=None))
    assert len(r["trades"]) == 2
    assert r["eq"][-1] - 10000 == pytest.approx(r["trades"]["pnl"].sum())          # eq final - capital = suma de PnL


def test_episodes_count_overlapping_e_subtrades_once():
    from sqzlab.pf7 import e_episodes
    t = pd.date_range("2020-01-01", periods=30)
    rows = [dict(kind="E", coin="A", entry_t=t[0], exit_t=t[10]), dict(kind="E", coin="A", entry_t=t[2], exit_t=t[6]),
            dict(kind="E", coin="A", entry_t=t[8], exit_t=t[15]), dict(kind="E", coin="A", entry_t=t[20], exit_t=t[25]),
            dict(kind="E", coin="B", entry_t=t[1], exit_t=t[3]), dict(kind="A", coin="B", entry_t=t[1], exit_t=t[3])]
    assert e_episodes(pd.DataFrame(rows)) == 3             # A: [0-15] (3 solapadas), A: [20-25]; B: [1-3]


def test_priority_changes_who_gets_the_slot_and_is_deterministic():
    t = pd.date_range("2020-01-01", periods=8)
    flat = np.full(8, 100.0)
    cl = {c: (t.to_numpy(), flat) for c in "ABC"}
    tr = pd.concat([_trade(c, 1, 5, 100.0, 100.0) for c in "ABC"], ignore_index=True)
    rules = Rules(mode="risk", commission=0, slippage=0, max_pos=1, open_risk_cap=None)
    a = run_cartera(tr, cl, t[0], t[-1], rules, priority={"A": 2, "B": 1, "C": 0})
    b = run_cartera(tr, cl, t[0], t[-1], rules, priority={"A": 0, "B": 1, "C": 2})
    assert a["trades"]["coin"].tolist() == ["C"] and b["trades"]["coin"].tolist() == ["A"]
    from sqzlab.fase7 import N_SEEDS, priorities
    p1, p2 = priorities(["A", "B", "C", "D", "E", "F"]), priorities(["F", "E", "D", "C", "B", "A"])
    assert p1 == p2 and len(p1) == N_SEEDS and len({tuple(sorted(x.items())) for x in p1}) > 1


def test_best_trade_removed_is_the_one_with_most_pnl_not_most_r():
    from sqzlab import fase7 as F
    t = pd.date_range("2020-01-01", periods=12)
    close = np.r_[100.0, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
    big = _trade("A", 1, 4, 100.0, 160.0, sd=0.5, tid="grande", vol=0.5)      # PnL alto, R = pnl/(notional*sd) moderado
    tiny = _trade("A", 5, 8, 100.0, 101.0, sd=0.001, tid="chico", vol=0.5)    # PnL chico, R enorme por sd diminuto
    tr = pd.concat([big, tiny], ignore_index=True)
    cl = {"A": (t.to_numpy(), close)}
    res = run_cartera(tr, cl, t[0], t[-1], Rules(mode="vol", max_pos=None, commission=0, slippage=0))
    cl_ = res["trades"][res["trades"]["closed"]]
    assert cl_.loc[cl_["R"].idxmax(), "id"] == "chico" and cl_.loc[cl_["pnl"].idxmax(), "id"] == "grande"
