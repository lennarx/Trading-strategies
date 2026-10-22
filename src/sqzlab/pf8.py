"""Fase 8: motor de cartera con pesos objetivo diarios, equity MARCADA A MERCADO, banda de rebalanceo y costos por lado.

Reglas en docs/PROTOCOLO.md ("Decisiones fijadas ANTES de la Fase 8", secciones 1, 4 y 5). En cada cierre:
  1. se marcan las posiciones; equity E = efectivo + sum(q x precio);
  2. objetivo de cada moneda = peso x E; se opera solo si: sale (objetivo 0 con posicion), entra (objetivo > 0 sin posicion) o
     |objetivo - actual| > banda x actual (actual = q x precio);
  3. cada cambio paga `cost` (por lado) sobre el nocional operado (comision + slippage juntos); el efectivo puede quedar negativo
     (apalancamiento sin costo de financiamiento: supuesto optimista, declarado).
Identidad contable (testeada): eq[t] - eq[t-1] = sum_m pnl[t, m]  con pnl = q_{t-1} x (p_t - p_{t-1}) - costo.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import r1fiel as R
from .f8data import END, load_f8
from .universe_dyn import Asset, fill_calendar

INITIAL = 10_000.0
A_START = pd.Timestamp("2018-01-01")
B_START = pd.Timestamp("2025-04-01")
PRE_B_END = pd.Timestamp("2025-03-31")


# ------------------------------------------------------------------------------------------------------------------
# Panel de una temporalidad
# ------------------------------------------------------------------------------------------------------------------
@dataclass
class Panel:
    tf: str
    times: pd.DatetimeIndex
    ids: list[str]
    bases: list[str]
    prices: np.ndarray       # (T, M) NaN fuera de la vida de la moneda
    act: np.ndarray          # (T, M) sub-senales abiertas
    vol: np.ndarray          # (T, M) vol anualizada
    in_top: np.ndarray       # (T, M) bool: top 20 del dia (datos <= t-1)
    valid: np.ndarray        # (T, M) bool: hay vela en t
    force_zero: np.ndarray   # (T, M) bool: ultima vela de una moneda deslistada/cortada (cierre forzado)
    stops: np.ndarray | None = None   # (K, T, M) opcional (validacion Pine)


def grid_for(tf: str) -> pd.DatetimeIndex:
    return pd.date_range(A_START, END["1d" if tf == "d1" else "4h"], freq="1D" if tf == "d1" else "4h")


def assets_for_tf(daily_assets: dict[str, Asset], ids: list[str], tf: str) -> dict[str, Asset]:
    """D1: los mismos activos. H4: se cargan los CSV de 4h y se cortan en las mismas fechas que el activo diario."""
    if tf == "d1":
        return {i: daily_assets[i] for i in ids}
    out = {}
    for i in ids:
        a = daily_assets[i]
        raw = load_f8(a.base, "4h")   # corta en END
        if a.split_from is not None:
            raw = raw[raw["time_utc"] >= a.split_from]
        if a.split_to is not None:
            raw = raw[raw["time_utc"] < a.split_to]
        if len(raw) == 0:
            continue
        out[i] = Asset(i, a.base, fill_calendar(raw.reset_index(drop=True), "4h"), a.split_from, a.split_to)
    return out


def build_panel(assets: dict[str, Asset], top_daily: pd.DataFrame, tf: str, with_stops: bool = False) -> Panel:
    times = grid_for(tf)
    ids = sorted(assets)
    T, M = len(times), len(ids)
    end_bar = times[-1]
    k = len(R.params()["lookbacks_days"])
    prices = np.full((T, M), np.nan)
    act = np.zeros((T, M), int)
    vol = np.full((T, M), np.nan)
    valid = np.zeros((T, M), bool)
    force_zero = np.zeros((T, M), bool)
    stops = np.full((k, T, M), np.nan) if with_stops else None
    for j, i in enumerate(ids):
        a = assets[i]
        d = a.df
        t = pd.DatetimeIndex(d["time_utc"])
        sel = t.isin(times)
        c = d["close"].to_numpy(float)
        e = R.ensemble(c, tf)
        v = R.vol_ann(c, tf)
        pos = times.get_indexer(t[sel])
        prices[pos, j] = c[sel]
        act[pos, j] = e["act"][sel]
        vol[pos, j] = v[sel]
        valid[pos, j] = True
        if with_stops:
            stops[:, pos, j] = e["stop"][:, sel]
        if a.last < end_bar and a.last in times:
            force_zero[times.get_loc(a.last), j] = True
    day = times.normalize()
    top = top_daily.reindex(columns=ids, fill_value=False)
    rows = top.index.get_indexer(day)
    in_top = np.zeros((T, M), bool)
    ok = rows >= 0
    in_top[ok] = top.to_numpy()[rows[ok]]
    return Panel(tf, times, ids, [assets[i].base for i in ids], prices, act, vol, in_top, valid, force_zero, stops)


def r1_targets(p: Panel) -> dict:
    return R.target_weights(p.act, p.vol, p.in_top, p.valid, p.force_zero, len(R.params()["lookbacks_days"]))


def ew_targets(p: Panel) -> np.ndarray:
    """Pesos 1/|U| para los miembros del top 20 del dia (con precio y sin cierre forzado); suma 1."""
    mem = p.in_top & p.valid & ~p.force_zero
    n = mem.sum(axis=1, keepdims=True)
    return np.where(mem, 1.0 / np.maximum(n, 1), 0.0)


# ------------------------------------------------------------------------------------------------------------------
# Motor
# ------------------------------------------------------------------------------------------------------------------
def run_weights(prices: np.ndarray, targets: np.ndarray, cost: float, band: float | None = None, initial: float = INITIAL) -> dict:
    band = R.params()["rebalance_band"] if band is None else band
    T, M = prices.shape
    q = np.zeros(M)
    cash = float(initial)
    last_p = np.zeros(M)
    eq = np.empty(T)
    pnl = np.zeros((T, M))
    gross = np.zeros(T)
    npos = np.zeros(T, int)
    traded = np.zeros(T)
    costs = np.zeros(T)
    ep_pnl = np.zeros(M)
    ep_start = np.full(M, -1)
    episodes: list[tuple] = []
    dead = False
    for t in range(T):
        p = prices[t]
        pv = np.where(np.isfinite(p), p, last_p)
        move = q * (pv - last_p)
        E = cash + float((q * pv).sum())
        tgt = targets[t]
        if dead or E <= 0:                                  # quiebra: se liquida todo y no se vuelve a operar
            dead = True
            tgt = np.zeros(M)
        q_old = q.copy()
        cur = q * pv
        want = tgt * E
        sell = (tgt <= 0) & (q > 0)
        buy = (tgt > 0) & (q <= 0) & (pv > 0)
        reb = (tgt > 0) & (q > 0) & (np.abs(want - cur) > band * cur)
        delta = np.where(sell, -cur, np.where(buy, want, np.where(reb, want - cur, 0.0)))
        cv = cost * np.abs(delta)
        cash -= float(delta.sum() + cv.sum())
        pos = pv > 0
        q = q + np.where(pos, delta / np.where(pos, pv, 1.0), 0.0)
        q[sell] = 0.0
        pnl[t] = move - cv
        act_b = (q_old > 0) | buy
        ep_pnl[act_b] += pnl[t][act_b]
        ep_start[buy] = t
        for m in np.where(sell)[0]:
            episodes.append((int(m), int(ep_start[m]), t, float(ep_pnl[m]), True))
            ep_pnl[m] = 0.0
            ep_start[m] = -1
        eq[t] = cash + float((q * pv).sum())
        gross[t] = float((q * pv).sum()) / eq[t] if eq[t] > 0 else 0.0
        npos[t] = int((q > 0).sum())
        traded[t] = float(np.abs(delta).sum())
        costs[t] = float(cv.sum())
        last_p = pv
    for m in np.where(q > 0)[0]:
        episodes.append((int(m), int(ep_start[m]), T - 1, float(ep_pnl[m]), False))
    ep = pd.DataFrame(episodes, columns=["m", "i0", "i1", "pnl", "closed"])
    return dict(eq=eq, pnl=pnl, gross=gross, npos=npos, traded=traded, costs=costs, episodes=ep, q=q, initial=initial)


# ------------------------------------------------------------------------------------------------------------------
# Metricas
# ------------------------------------------------------------------------------------------------------------------
def to_daily(times: pd.DatetimeIndex, x: np.ndarray) -> pd.Series:
    """Serie diaria con el ultimo valor de cada dia UTC (D1: tal cual; H4: el cierre de la vela 20:00)."""
    s = pd.Series(np.asarray(x, float), index=times)
    return s.groupby(s.index.normalize()).last()


def stats(daily: pd.Series, start, end, base_date=None) -> dict:
    """CAGR, Sharpe, DD maximo y Calmar sobre los dias [start, end]; la base es el valor del dia anterior a `start`."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    base_date = start - pd.Timedelta(days=1) if base_date is None else pd.Timestamp(base_date)
    s = daily[(daily.index >= start) & (daily.index <= end)]
    if base_date not in daily.index or len(s) < 2:
        return dict(cagr=np.nan, sharpe=np.nan, dd=np.nan, calmar=np.nan, days=len(s), total=np.nan)
    base = float(daily.loc[base_date])
    vals = np.r_[base, s.to_numpy(float)]
    n = len(vals) - 1
    r = vals[1:] / vals[:-1] - 1.0
    cagr = (vals[-1] / base) ** (365.0 / n) - 1.0 if vals[-1] > 0 else -1.0
    sd = r.std(ddof=1)
    sharpe = float(r.mean() / sd * np.sqrt(365.0)) if sd > 0 else float("nan")
    peak = np.maximum.accumulate(vals)
    dd = float(((peak - vals) / peak).max())
    return dict(cagr=float(cagr), sharpe=sharpe, dd=dd, calmar=float(cagr / dd) if dd > 1e-12 else float("nan"), days=n,
                total=float(vals[-1] / base - 1.0))


def cagr_without_best_month(daily: pd.Series, start, end) -> dict:
    """CAGR re-anualizado quitando el retorno del mejor mes calendario (los meses parciales de los bordes cuentan como meses)."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    base_date = start - pd.Timedelta(days=1)
    s = daily[(daily.index >= start) & (daily.index <= end)]
    base = float(daily.loc[base_date])
    me = s.groupby([s.index.year, s.index.month]).last().to_numpy(float)
    prev = np.r_[base, me[:-1]]
    r = me / prev - 1.0
    k = int(np.argmax(r))
    n = len(s)
    g = np.prod(1.0 + np.delete(r, k))
    return dict(cagr_sin_mejor_mes=float(g ** (365.0 / n) - 1.0) if g > 0 else -1.0, mejor_mes_ret=float(r[k]), meses=len(r))


def coin_contrib(p: Panel, res: dict, start, end) -> pd.Series:
    """PnL marcado a mercado por MONEDA BASE (suma de ids de la misma base) en las velas con fecha en [start, end]."""
    d = p.times.normalize()
    m = (d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end))
    s = pd.Series(res["pnl"][m].sum(axis=0), index=p.bases)
    return s.groupby(level=0).sum()


def episode_counts(p: Panel, res: dict, start, end) -> dict:
    ep = res["episodes"]
    if len(ep) == 0:
        return dict(n_cerrados_salida=0, n_cerrados_entrada=0, n_abiertos=0)
    t0, t1 = pd.Timestamp(start), pd.Timestamp(end)
    di = p.times.normalize()[ep["i0"].to_numpy()]
    do = p.times.normalize()[ep["i1"].to_numpy()]
    closed = ep["closed"].to_numpy()
    return dict(n_cerrados_salida=int((closed & (do >= t0) & (do <= t1)).sum()),
                n_cerrados_entrada=int((closed & (di >= t0) & (di <= t1) & (do <= t1)).sum()),
                n_abiertos=int((~closed).sum()))


def episode_detail(p: Panel, res: dict, start, end) -> dict:
    """Detalle de los episodios cerrados con salida en [start, end]: cuantos salen porque la moneda cayo del top 20 (o cierre forzado) y no por la
    senal, y la mediana de duracion en dias (hallazgo #12 de la revision previa: n mide en parte el recambio del universo)."""
    ep = res["episodes"]
    t0, t1 = pd.Timestamp(start), pd.Timestamp(end)
    if len(ep) == 0:
        return dict(n_salida_por_universo=0, dur_mediana_dias=float("nan"))
    do = p.times.normalize()[ep["i1"].to_numpy()]
    m = ep["closed"].to_numpy() & (do >= t0) & (do <= t1)
    e = ep[m]
    if len(e) == 0:
        return dict(n_salida_por_universo=0, dur_mediana_dias=float("nan"))
    by_uni = ~p.in_top[e["i1"].to_numpy(), e["m"].to_numpy()] | p.force_zero[e["i1"].to_numpy(), e["m"].to_numpy()]
    bars_per_day = 1.0 if p.tf == "d1" else 6.0
    return dict(n_salida_por_universo=int(by_uni.sum()), dur_mediana_dias=float(np.median((e["i1"] - e["i0"]).to_numpy()) / bars_per_day))
