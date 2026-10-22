"""Fase 8: R1-fiel. Ensamble de Donchian (solo largo) con trailing stop, vol objetivo y pesos de cartera.

Reglas fijadas en docs/PROTOCOLO.md ("Decisiones fijadas ANTES de la Fase 8", seccion 1) y parametros en params/r1fiel.json:
  - por moneda y por N: entra al cierre si close[t] > max de los N cierres previos; stop inicial = (max+min)/2 de esos N cierres previos;
    luego stop = max(stop de ayer, (max+min)/2 de los N cierres previos de esa vela); sale al cierre si close[t] < stop.
  - peso moneda = (sub-senales abiertas / K) x min(coin_cap, vol_target / vol); vol = desvio (ddof=1) de retornos log de 90 dias x sqrt(365).
  - si el bruto de la cartera supera gross_cap (2,0) se escalan todos los pesos por gross_cap / bruto.
Todo es causal: la decision de la vela t usa solo cierres <= t.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BARS_PER_DAY = {"d1": 1, "h4": 6}
BARS_PER_YEAR = {"d1": 365.0, "h4": 365.0 * 6}


@lru_cache(maxsize=1)
def params() -> dict:
    d = json.loads((ROOT / "params" / "r1fiel.json").read_text(encoding="utf-8"))
    return {k: v for k, v in d.items() if not k.startswith("_")}


def n_bars(days: int, tf: str) -> int:
    """Lookback en velas: D1 = dias; H4 = dias x 6 (conversion declarada)."""
    return int(days * BARS_PER_DAY[tf])


def lookbacks(tf: str) -> list[int]:
    return [n_bars(d, tf) for d in params()["lookbacks_days"]]


def prev_window(c: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """(max, min) de los n cierres PREVIOS (la vela actual no entra); NaN hasta tener n cierres previos."""
    s = pd.Series(np.asarray(c, float))
    return s.rolling(n).max().shift(1).to_numpy(), s.rolling(n).min().shift(1).to_numpy()


def donchian_state(c: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Maquina de estados de UNA sub-senal. Devuelve (on, stop, entry): on[t] = posicion abierta DESPUES de operar al cierre t;
    stop[t] = nivel del trailing stop vigente en t (NaN si no hay posicion; en la vela de salida queda el stop que se perforo);
    entry[t] = True en la vela donde se entra."""
    c = np.asarray(c, float)
    hi, lo = prev_window(c, n)
    mid = (hi + lo) / 2.0
    T = len(c)
    on = np.zeros(T, bool)
    stop = np.full(T, np.nan)
    entry = np.zeros(T, bool)
    pos, st = False, -np.inf
    for t in range(T):
        if pos:
            st = max(st, mid[t])
            stop[t] = st
            if c[t] < st:
                pos = False
        elif c[t] > hi[t]:                       # NaN en hi -> False
            pos, st = True, mid[t]
            stop[t] = st
            entry[t] = True
        on[t] = pos
    return on, stop, entry


def ensemble(c: np.ndarray, tf: str) -> dict:
    """K sub-senales de la moneda: `on` (K, T), `stop` (K, T), `entry` (K, T), `act` (T,) = cuantas abiertas."""
    ns = lookbacks(tf)
    res = [donchian_state(c, n) for n in ns]
    on = np.array([r[0] for r in res])
    return dict(on=on, stop=np.array([r[1] for r in res]), entry=np.array([r[2] for r in res]), act=on.sum(axis=0).astype(int), ns=ns)


def vol_ann(c: np.ndarray, tf: str) -> np.ndarray:
    """Vol anualizada con datos hasta el cierre de cada vela: desvio (ddof=1) de retornos log de `vol_window_days` x sqrt(velas/anio).
    NaN hasta tener la ventana completa de retornos."""
    c = np.asarray(c, float)
    w = n_bars(params()["vol_window_days"], tf)
    with np.errstate(divide="ignore", invalid="ignore"):
        lr = np.r_[np.nan, np.diff(np.log(c))]
    return pd.Series(lr).rolling(w).std(ddof=1).to_numpy() * math.sqrt(BARS_PER_YEAR[tf])


def vol_multiplier(vol: np.ndarray) -> np.ndarray:
    """min(coin_cap, vol_target / vol); 0 donde no hay vol valida (>0)."""
    p = params()
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.minimum(p["coin_cap"], p["vol_target"] / vol)
    return np.where(np.isfinite(m) & (vol > 0), m, 0.0)


def coin_weights(act: np.ndarray, vol: np.ndarray, k: int) -> np.ndarray:
    """peso sin escalar = act / K x min(coin_cap, vol_target / vol). Sin vol -> 0."""
    return act / float(k) * vol_multiplier(vol)


def apply_gross_cap(raw: np.ndarray, gross_cap: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """raw: (T, M) pesos objetivo por moneda. Si la suma de una fila supera gross_cap, la fila se escala por gross_cap / suma.
    Devuelve (pesos escalados, factor por fila)."""
    g = params()["gross_cap"] if gross_cap is None else gross_cap
    tot = raw.sum(axis=1)
    f = np.where(tot > g, g / np.where(tot > 0, tot, 1.0), 1.0)
    return raw * f[:, None], f


def target_weights(act: np.ndarray, vol: np.ndarray, in_top: np.ndarray, valid: np.ndarray, force_zero: np.ndarray, k: int) -> dict:
    """act, vol, in_top, valid, force_zero: matrices (T, M). Pesos objetivo del cierre de cada vela:
    cero si la moneda no esta en el top 20 del dia, no tiene precio, o es su ultima vela de una moneda deslistada/cortada."""
    raw = coin_weights(act, vol, k)
    raw = np.where(in_top & valid & ~force_zero, raw, 0.0)
    raw = np.nan_to_num(raw, nan=0.0)
    w, f = apply_gross_cap(raw)
    return dict(raw=raw, w=w, scale=f)


# ------------------------------------------------------------------------------------------------------------------
# Senales para el bot (python -m sqzlab.signals --strategy r1fiel)
# ------------------------------------------------------------------------------------------------------------------
def last_bar_targets(assets: dict, top_row: pd.Series, tf: str = "d1") -> dict:
    """Pesos objetivo de la ULTIMA vela de `assets` (todas con datos hasta la misma vela cerrada). `top_row`: bool por id del universo del
    dia de esa vela. Devuelve {id: dict(active, total, vol, weight_raw, weight)} y el factor de escala."""
    ps = params()
    k = len(ps["lookbacks_days"])
    rows, raw = {}, {}
    for aid, a in assets.items():
        c = a.df["close"].to_numpy(float)
        if len(c) < 2 or not bool(top_row.get(aid, False)):
            continue
        e = ensemble(c, tf)
        v = vol_ann(c, tf)[-1]
        act = int(e["act"][-1])
        w = float(coin_weights(np.array([act]), np.array([v]), k)[0]) if np.isfinite(v) else 0.0
        raw[aid] = w
        rows[aid] = dict(active=act, total=k, vol_ann=None if not np.isfinite(v) else round(float(v), 4), weight_raw=w,
                         stops=[None if not np.isfinite(x) else float(x) for x in e["stop"][:, -1]], close=float(c[-1]))
    tot = sum(raw.values())
    f = ps["gross_cap"] / tot if tot > ps["gross_cap"] else 1.0
    for aid in rows:
        rows[aid]["weight"] = rows[aid]["weight_raw"] * f
    return dict(targets=rows, scale=f, gross_raw=tot, gross=tot * f)
