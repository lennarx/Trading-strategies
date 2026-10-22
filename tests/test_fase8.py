"""Fase 8 (R1-fiel): universo sin lookahead, senal/trailing a mano, vol-target y tope, costos, marcado a mercado, deslistadas,
anualizacion y regresion del golden de `simulate`."""
import math

import numpy as np
import pandas as pd
import pytest

from sqzlab import pf8
from sqzlab import r1fiel as R
from sqzlab import universe_dyn as UD
from sqzlab.universe_dyn import Asset


def _asset(aid, start, n, qv, price=1.0):
    t = pd.date_range(start, periods=n, freq="1D")
    df = pd.DataFrame(dict(time_utc=t, open=price, high=price, low=price, close=price, volume=1.0,
                           qvol=np.asarray(qv, float) if np.ndim(qv) else np.full(n, float(qv)), filled=False))
    return Asset(aid, aid, df)


# ------------------------------------------------------------------------------------------------------------------
# 1. Universo sin lookahead
# ------------------------------------------------------------------------------------------------------------------
def test_universe_top_of_day_t_uses_only_data_before_t():
    n = 600
    rng = np.random.default_rng(0)
    assets = {f"C{i:02d}": _asset(f"C{i:02d}", "2020-01-01", n, rng.uniform(3e6, 9e6, n)) for i in range(30)}
    dates = pd.date_range("2020-01-01", periods=n, freq="1D")
    base = UD.build_universe(assets, dates)
    t0 = 450
    pert = {k: Asset(k, k, a.df.copy()) for k, a in assets.items()}
    for k in pert:                                   # mundo alternativo: del dia t0 en adelante el volumen es otro (x1000 y reordenado)
        pert[k].df.loc[t0:, "qvol"] = rng.uniform(1e9, 2e9, n - t0)
    alt = UD.build_universe(pert, dates)
    for key in ("top", "elig", "med"):
        a, b = base[key].iloc[: t0 + 1], alt[key].iloc[: t0 + 1]      # incluye el dia t0: su universo no puede ver el volumen del propio t0
        pd.testing.assert_frame_equal(a, b, check_exact=False)
    assert not base["top"].iloc[t0 + 1:].equals(alt["top"].iloc[t0 + 1:])   # y el cambio SI se nota despues (el test no es vacio)


def test_universe_needs_365_days_of_history_and_30d_median_of_2m_and_picks_top_n_with_alphabetical_ties():
    n = 420
    dates = pd.date_range("2020-01-01", periods=n, freq="1D")
    assets = {
        "AAA": _asset("AAA", "2020-01-01", n, 5e6),
        "BBB": _asset("BBB", "2020-01-01", n, 5e6),                    # empate con AAA: gana AAA en el ultimo lugar
        "CCC": _asset("CCC", "2020-01-01", n, 1.9e6),                  # volumen insuficiente
        "NEW": _asset("NEW", "2020-01-01", n, 9e6),
    }
    assets["NEW"] = _asset("NEW", "2020-02-01", n - 31, 9e6)            # arranca 31 dias despues
    u = UD.build_universe(assets, dates, top_n=1)
    first = assets["NEW"].first
    # 365 velas de historia: la primera vela es `first`; recien el dia first+365 hay 365 velas en t-1 (first..first+364)
    ok_day = first + pd.Timedelta(days=365)
    assert not u["elig"].loc[ok_day - pd.Timedelta(days=1), "NEW"]
    assert u["elig"].loc[ok_day, "NEW"]
    assert u["top"].loc[ok_day, "NEW"] and not u["top"].loc[ok_day, "AAA"]
    assert not u["elig"]["CCC"].any()
    day = pd.Timestamp("2021-01-15")                                    # NEW todavia no tiene 365 dias
    assert u["top"].loc[day, "AAA"] and not u["top"].loc[day, "BBB"]    # empate -> alfabetico


def test_universe_ends_when_data_ends_and_split_rule():
    n = 500
    dates = pd.date_range("2020-01-01", periods=n, freq="1D")
    short = _asset("DEAD", "2020-01-01", 420, 9e6)
    u = UD.build_universe({"DEAD": short, "LIVE": _asset("LIVE", "2020-01-01", n, 5e6)}, dates)
    assert u["elig"].loc[short.last, "DEAD"] and not u["elig"].loc[short.last + pd.Timedelta(days=1), "DEAD"]
    assert UD.split_points(np.array([1.0, 1.1, 30.0, 31.0, 1.0])) == [2, 4]    # x27 y /31: cortes
    assert UD.split_points(np.array([1.0, 19.0, 1.0])) == []                    # 19x y 1/19: dentro del umbral


def test_excluded_names_leveraged_needs_listed_stem_and_does_not_hit_jup():
    ex = UD.excluded_names(["BTC", "BTCUP", "BTCDOWN", "JUP", "SUP", "USDC", "WBTC", "PAXG", "ETH"])
    assert ex["BTCUP"] == "apalancado" and ex["BTCDOWN"] == "apalancado"
    assert "JUP" not in ex and "SUP" not in ex and "BTC" not in ex and "ETH" not in ex
    assert ex["USDC"] == "stable/fiat" and ex["WBTC"] == "envuelto/staked" and ex["PAXG"] == "respaldado por oro"
    assert UD.is_pegged(pd.Series(np.full(100, 1.0001))) and not UD.is_pegged(pd.Series(np.linspace(0.5, 2.0, 100)))


def test_fixed_params_match_between_json_and_universe_module():
    p = R.params()
    assert (p["top_n"], p["min_history_days"], p["min_median_volume_usd"], p["median_window_days"]) == (
        UD.TOP_N, UD.MIN_HIST, UD.MIN_MEDIAN_USD, UD.MED_WINDOW)
    assert p["lookbacks_days"] == [5, 10, 20, 30, 60, 90, 150, 250, 360] and p["gross_cap"] == 2.0 and p["coin_cap"] == 2.0
    assert R.lookbacks("h4") == [30, 60, 120, 180, 360, 540, 900, 1500, 2160] and R.lookbacks("d1") == p["lookbacks_days"]


# ------------------------------------------------------------------------------------------------------------------
# 2. Senal y trailing contra un calculo a mano
# ------------------------------------------------------------------------------------------------------------------
def test_donchian_state_and_trailing_stop_by_hand():
    c = np.array([10, 11, 12, 13, 14, 13, 12, 11, 10, 12, 15], float)
    on, stop, entry = R.donchian_state(c, 3)
    # t=3: previos 10,11,12 -> max 12, min 10, mid 11; 13>12 entra, stop 11
    # t=4: previos 11,12,13 -> mid 12 -> stop 12 (14>=12 sigue); t=5: previos 12,13,14 -> mid 13 -> stop 13 (13<13 es falso, sigue)
    # t=6: previos 13,14,13 -> mid 13,5 -> stop 13,5; 12<13,5 sale. t=7..9 sin entrada (cierre <= max previo); t=10: 15>12 entra, mid (12+10)/2=11
    assert on.tolist() == [False] * 3 + [True, True, True, False, False, False, False, True]
    assert entry.tolist() == [False] * 3 + [True] + [False] * 6 + [True]
    exp = [np.nan] * 3 + [11, 12, 13, 13.5] + [np.nan] * 3 + [11]
    np.testing.assert_allclose(stop, exp, equal_nan=True)


def test_stop_never_goes_down_while_in_position_and_entry_needs_strict_break():
    rng = np.random.default_rng(3)
    c = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, 800)))
    on, stop, entry = R.donchian_state(c, 20)
    hi, lo = R.prev_window(c, 20)
    for t in range(1, len(c)):
        if on[t - 1] and not entry[t] and not np.isnan(stop[t]) and not np.isnan(stop[t - 1]):
            assert stop[t] >= stop[t - 1] - 1e-12
        if entry[t]:
            assert c[t] > hi[t] and not on[t - 1]
    assert entry.sum() > 3
    c2 = np.r_[np.full(25, 100.0), 100.0]       # cierre igual al maximo previo: NO entra (estricto)
    assert not R.donchian_state(c2, 20)[2].any()


def test_signal_is_causal_truncating_the_future_does_not_change_the_past():
    rng = np.random.default_rng(5)
    c = 50 * np.exp(np.cumsum(rng.normal(0.0005, 0.04, 900)))
    full = R.ensemble(c, "d1")
    cut = R.ensemble(c[:600], "d1")
    np.testing.assert_array_equal(full["on"][:, :600], cut["on"])
    np.testing.assert_allclose(full["stop"][:, :600], cut["stop"], equal_nan=True)
    v1, v2 = R.vol_ann(c, "d1")[:600], R.vol_ann(c[:600], "d1")
    np.testing.assert_allclose(v1, v2, equal_nan=True)


# ------------------------------------------------------------------------------------------------------------------
# 3. Vol-target y tope
# ------------------------------------------------------------------------------------------------------------------
def test_vol_ann_hand_calc_and_multiplier_cap():
    a = 0.02
    lr = np.tile([a, -a], 100)                  # retornos log alternados: media 0 en cualquier ventana par
    c = 100 * np.exp(np.cumsum(lr))
    v = R.vol_ann(c, "d1")
    w = 90
    expected = a * math.sqrt(w / (w - 1)) * math.sqrt(365)       # desvio muestral (ddof=1) de w valores +-a con media 0
    assert np.isnan(v[:w]).all() and v[w + 5] == pytest.approx(expected, rel=1e-9)
    m = R.vol_multiplier(np.array([0.5, 0.1, 0.25, 0.0, np.nan]))
    np.testing.assert_allclose(m, [0.5, 2.0, 1.0, 0.0, 0.0])      # min(2, .25/vol); sin vol valida -> 0
    np.testing.assert_allclose(R.coin_weights(np.array([3, 9, 0]), np.array([0.5, 0.5, 0.5]), 9), [3 / 9 * 0.5, 0.5, 0.0])


def test_gross_cap_scales_all_weights_when_sum_exceeds_two():
    raw = np.array([[1.5, 1.0, 0.5], [0.4, 0.4, 0.4]])
    w, f = R.apply_gross_cap(raw)
    np.testing.assert_allclose(w[0], raw[0] * 2 / 3)
    assert w[0].sum() == pytest.approx(2.0) and f[0] == pytest.approx(2 / 3)
    np.testing.assert_allclose(w[1], raw[1])
    assert f[1] == 1.0


def test_target_weights_zero_when_out_of_top_no_price_or_forced_close():
    act = np.array([[9, 9, 9, 9]])
    vol = np.full((1, 4), 0.5)
    in_top = np.array([[True, False, True, True]])
    valid = np.array([[True, True, False, True]])
    fz = np.array([[False, False, False, True]])
    out = R.target_weights(act, vol, in_top, valid, fz, 9)
    np.testing.assert_allclose(out["w"][0], [0.5, 0, 0, 0])


# ------------------------------------------------------------------------------------------------------------------
# 4. Costos, marcado a mercado, banda, deslistadas, identidad contable
# ------------------------------------------------------------------------------------------------------------------
def test_costs_are_charged_on_each_weight_change_and_band_blocks_small_changes():
    prices = np.full((6, 1), 100.0)
    tg = np.array([[0.0], [0.5], [0.5], [0.55], [0.8], [0.0]])
    r = pf8.run_weights(prices, tg, cost=0.01, band=0.2)
    assert r["eq"][0] == 10_000
    assert r["traded"][1] == pytest.approx(5000.0) and r["costs"][1] == pytest.approx(50.0)     # entrada: 1% de 5000
    assert r["eq"][1] == pytest.approx(9950.0)
    assert r["traded"][2] == 0.0                                                                 # 0,5 -> 0,5: nada
    assert r["traded"][3] == 0.0                                                                 # objetivo 0,55 x 9950 = 5472,5 vs 5000: +9,5% < 20%: banda
    assert r["traded"][4] == pytest.approx(0.8 * 9950 - 5000)                                    # 0,8: +59% > 20%: opera la diferencia
    assert r["costs"][4] == pytest.approx(0.01 * (0.8 * 9950 - 5000))
    assert r["traded"][5] == pytest.approx(0.8 * 9950)                                           # salida total: siempre opera
    assert r["costs"].sum() == pytest.approx(0.01 * r["traded"].sum())
    assert r["eq"][5] == pytest.approx(10_000 - r["costs"].sum())                                # precio constante: solo perdemos costos
    assert len(r["episodes"]) == 1 and bool(r["episodes"]["closed"].iloc[0])


def test_mark_to_market_equity_in_a_synthetic_case_and_accounting_identity():
    p = np.array([100, 110, 121, 90, 90.0])[:, None]
    tg = np.array([[1.0], [1.0], [1.0], [1.0], [0.0]])
    r = pf8.run_weights(p, tg, cost=0.0, band=10.0)         # sin costos y sin rebalanceos: equity = precio/100 x 10000 mientras esta dentro
    np.testing.assert_allclose(r["eq"], [10_000, 11_000, 12_100, 9_000, 9_000])
    ep = r["episodes"].iloc[0]
    assert ep["pnl"] == pytest.approx(-1000.0) and ep["i0"] == 0 and ep["i1"] == 4
    rng = np.random.default_rng(1)
    T, M = 400, 5
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, (T, M)), axis=0))
    tg = rng.uniform(0, 0.6, (T, M)) * (rng.uniform(size=(T, M)) > 0.4)
    r = pf8.run_weights(prices, tg, cost=0.0015)
    d_eq = np.diff(np.r_[10_000.0, r["eq"]])
    np.testing.assert_allclose(r["pnl"].sum(axis=1), d_eq, atol=1e-6)                            # identidad: eq[t]-eq[t-1] = sum pnl
    assert r["episodes"]["pnl"].sum() == pytest.approx(r["pnl"].sum(), abs=1e-6)                 # los episodios suman todo el PnL
    assert (r["gross"] >= 0).all()


def test_delisted_coin_is_force_closed_on_its_last_candle(monkeypatch):
    times = pd.date_range("2020-01-01", periods=10, freq="1D")
    monkeypatch.setattr(pf8, "grid_for", lambda tf: times)
    monkeypatch.setattr(pf8, "END", {"1d": times[-1], "4h": times[-1]})
    n_alive, n_dead = 10, 6
    rng = np.random.default_rng(2)
    def mk(aid, n):
        t = pd.date_range("2020-01-01", periods=n, freq="1D")
        c = 100 + np.arange(n, dtype=float)
        return Asset(aid, aid, pd.DataFrame(dict(time_utc=t, open=c, high=c, low=c, close=c, volume=1.0, qvol=9e9, filled=False)))
    assets = {"ALIVE": mk("ALIVE", n_alive), "DEAD": mk("DEAD", n_dead)}
    top = pd.DataFrame(True, index=times, columns=["ALIVE", "DEAD"])
    p = pf8.build_panel(assets, top, "d1")
    j = p.ids.index("DEAD")
    assert p.force_zero[n_dead - 1, j] and p.force_zero[:, j].sum() == 1 and not p.valid[n_dead:, j].any()
    assert not p.force_zero[:, p.ids.index("ALIVE")].any()
    p.act[:] = 9
    p.vol[:] = 0.5
    tg = R.target_weights(p.act, p.vol, p.in_top, p.valid, p.force_zero, 9)["w"]
    assert tg[n_dead - 1, j] == 0 and tg[n_dead - 2, j] > 0 and (tg[n_dead:, j] == 0).all()
    r = pf8.run_weights(p.prices, tg, cost=0.0)
    assert r["q"][j] == 0.0                                                       # no queda posicion en la deslistada
    ep = r["episodes"]
    assert (ep[ep["m"] == j]["i1"] == n_dead - 1).all() and ep[ep["m"] == j]["closed"].all()


# ------------------------------------------------------------------------------------------------------------------
# 5. Anualizacion y metricas
# ------------------------------------------------------------------------------------------------------------------
def test_stats_annualization_cagr_sharpe_dd_and_best_month():
    idx = pd.date_range("2021-01-01", periods=366, freq="1D")
    g = 2.0 ** (1 / 365)
    s = pd.Series(1000.0 * g ** np.arange(366), index=idx)                    # duplica en 365 dias, sin volatilidad
    st = pf8.stats(s, "2021-01-02", "2022-01-01")
    assert st["days"] == 365 and st["cagr"] == pytest.approx(1.0, abs=1e-9) and st["dd"] == 0.0
    r = np.tile([0.02, -0.01], 100)
    eq = pd.Series(100.0 * np.cumprod(np.r_[1.0, 1 + r]), index=pd.date_range("2022-01-01", periods=201, freq="1D"))
    st = pf8.stats(eq, "2022-01-02", "2022-07-20")
    exp_sharpe = r.mean() / r.std(ddof=1) * math.sqrt(365)
    assert st["sharpe"] == pytest.approx(exp_sharpe, rel=1e-12)
    vals = np.r_[100.0, 100.0 * np.cumprod(1 + r)]
    assert st["dd"] == pytest.approx(((np.maximum.accumulate(vals) - vals) / np.maximum.accumulate(vals)).max())
    idx = pd.date_range("2022-12-31", periods=91, freq="1D")                  # base 31-dic, enero +50%, febrero 0%, marzo 0%
    v = np.full(91, 100.0)
    v[1:32] = np.linspace(100, 150, 31)
    v[32:] = 150.0
    s = pd.Series(v, index=idx)
    bm = pf8.cagr_without_best_month(s, "2023-01-01", "2023-03-31")
    assert bm["mejor_mes_ret"] == pytest.approx(0.5) and bm["cagr_sin_mejor_mes"] == pytest.approx(0.0, abs=1e-12)
    assert bm["meses"] == 3


# ------------------------------------------------------------------------------------------------------------------
# 6. Regresion del golden de `simulate` (esta fase no toca el motor SQZ+RSI)
# ------------------------------------------------------------------------------------------------------------------
def test_simulate_golden_regression_unchanged_by_fase8():
    from test_fase7 import test_defaults_regression_identical_to_pre_fase7 as golden
    golden()


# ------------------------------------------------------------------------------------------------------------------
# 7. signals --strategy r1fiel == pesos objetivo del backtest en la ultima vela (usa data/f8; se saltea si no esta)
# ------------------------------------------------------------------------------------------------------------------
def test_signals_r1fiel_targets_equal_the_backtest_weights_on_the_last_bar():
    from sqzlab import fase8
    from sqzlab.f8data import F8
    if not (F8 / "_manifest_1d.json").exists():
        pytest.skip("sin data/f8")
    from sqzlab.signals import r1fiel_signal
    out = r1fiel_signal("d1", fetch=False)
    w = fase8.load_world()
    p, _ = fase8.make_panel(w, "d1")
    tg = pf8.r1_targets(p)
    last = len(p.times) - 1
    assert out["bar_time_utc"].startswith(str(p.times[last].date()))
    got = {r["pair"].replace("USDT", ""): r["weight_pct_equity"] / 100 for r in out["targets"]}
    exp = {p.bases[j]: tg["w"][last, j] for j in range(len(p.ids)) if tg["w"][last, j] > 0}
    for k, v in exp.items():
        assert got.get(k, 0.0) == pytest.approx(v, abs=2e-6), k
    assert sum(got.values()) == pytest.approx(sum(exp.values()), abs=1e-4)
    assert out["gross"] <= R.params()["gross_cap"] + 1e-9


# ------------------------------------------------------------------------------------------------------------------
# 8. Tests agregados tras la revision independiente
# ------------------------------------------------------------------------------------------------------------------
def _s(cagr, sharpe, dd, share, nb=100, ex=0.1, coin="X"):
    return dict(cagr=cagr, sharpe=sharpe, dd=dd, top_share=share, top_coin=coin, cagr_sin_mejor_mes=ex, n_cerrados_salida=nb)


def test_verdict_precedence_and_thresholds():
    from sqzlab import fase8
    btc = dict(sharpe=1.0, dd=0.7)
    good = _s(0.5, 1.2, 0.5, 0.3)
    mk = lambda a, b: dict(strategy=dict(base=dict(A=a, B=b)), refs=dict(btc=dict(A=btc, B=btc)))
    assert fase8.verdict(mk(good, good))["veredicto"] == "SIRVE"
    bad_dd = _s(0.5, 1.2, 0.8, 0.3)
    assert fase8.verdict(mk(good, bad_dd))["veredicto"] == "NO SIRVE"
    assert fase8.verdict(mk(bad_dd, good))["veredicto"] == "NO SIRVE"
    # n_B < 30 => SIN MUESTRA EN B aunque fallen criterios
    assert fase8.verdict(mk(bad_dd, _s(-0.1, 0.1, 0.9, 0.9, nb=29)))["veredicto"] == "SIN MUESTRA EN B"
    assert fase8.verdict(mk(good, _s(0.5, 1.2, 0.5, 0.3, nb=30)))["veredicto"] == "SIRVE"
    # umbrales estrictos: Sharpe igual al de BTC no alcanza; concentracion justo 50% cumple; sin el mejor mes <= 0 falla en A (no se pide en B)
    assert not fase8.checks(_s(0.5, 1.0, 0.5, 0.3), btc, "B")[1][1]
    assert fase8.checks(_s(0.5, 1.2, 0.5, 0.5), btc, "B")[3][1] and not fase8.checks(_s(0.5, 1.2, 0.5, 0.51), btc, "B")[3][1]
    assert not fase8.checks(_s(0.5, 1.2, 0.5, 0.3, ex=0.0), btc, "A")[4][1] and len(fase8.checks(good, btc, "B")) == 4


def test_window_edges_base_is_previous_day_and_exit_on_boundary_counts():
    idx = pd.date_range("2025-03-28", periods=8, freq="1D")          # 28-mar .. 4-abr
    s = pd.Series([100, 101, 102, 103, 110, 121, 121, 121.0], index=idx)
    st = pf8.stats(s, "2025-04-01", "2025-04-04")
    assert st["days"] == 4 and st["total"] == pytest.approx(121 / 103 - 1)       # base = cierre del 31-mar (103)
    times = pd.date_range("2025-03-30", periods=5, freq="1D")
    p = pf8.Panel("d1", times, ["A"], ["A"], np.ones((5, 1)), np.zeros((5, 1), int), np.ones((5, 1)), np.ones((5, 1), bool), np.ones((5, 1), bool), np.zeros((5, 1), bool))
    ep = pd.DataFrame(dict(m=[0, 0, 0], i0=[0, 1, 3], i1=[1, 2, 4], pnl=[1.0, 1.0, 1.0], closed=[True, True, False]))   # salidas 31-mar y 1-abr; una abierta
    c = pf8.episode_counts(p, dict(episodes=ep), "2025-04-01", "2025-04-03")
    assert c == dict(n_cerrados_salida=1, n_cerrados_entrada=0, n_abiertos=1)    # la salida del 1-abr cuenta (entro el 31-mar: no cuenta por entrada); la del 31-mar no


def test_to_daily_h4_takes_the_20h_bar_of_each_utc_day():
    t = pd.date_range("2024-01-01", periods=12, freq="4h")
    s = pf8.to_daily(t, np.arange(12.0))
    assert s.tolist() == [5.0, 11.0] and list(s.index) == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")]


def test_to_df_handles_millisecond_and_microsecond_timestamps():
    from sqzlab import f8data
    row = lambda ms: [str(ms), "1", "2", "0.5", "1.5", "10", "0", "15", "3", "0", "0", "0"]
    df = f8data._to_df([row(1_735_689_600_000), row(1_735_776_000_000 * 1000)])   # 2025-01-01 en ms; 2025-01-02 en us
    assert list(df["time_utc"]) == [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-02")] and df["qvol"].tolist() == [15.0, 15.0]


def test_run_weights_bankruptcy_liquidates_and_stops_trading():
    p = np.array([100.0, 100.0, 10.0, 10.0, 10.0])[:, None]
    tg = np.full((5, 1), 3.0)                                   # 3x de apalancamiento: -90% => equity negativa
    r = pf8.run_weights(p, tg, cost=0.0, band=10.0)
    assert r["eq"][2] < 0 and r["q"][0] == 0.0 and (r["traded"][3:] == 0).all()


def test_load_assets_daily_splits_into_base_hash_2_with_history_from_scratch(monkeypatch):
    from sqzlab import universe_dyn
    t = pd.date_range("2020-01-01", periods=10, freq="1D")
    c = np.r_[np.full(5, 100.0), np.full(5, 1.0)]               # /100 el dia 5: corte
    raw = pd.DataFrame(dict(time_utc=t, open=c, high=c, low=c, close=c, volume=1.0, qvol=1e7))
    monkeypatch.setattr(universe_dyn, "load_f8", lambda b, tf, clip=True, live=False: raw)
    assets, excl, cuts = universe_dyn.load_assets_daily(["ZZZ"])
    assert sorted(assets) == ["ZZZ", "ZZZ#2"] and len(cuts) == 1
    assert assets["ZZZ"].last == t[4] and assets["ZZZ#2"].first == t[5] and assets["ZZZ"].split_to == t[5] and assets["ZZZ#2"].split_from == t[5]
