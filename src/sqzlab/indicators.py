"""Indicadores con la semantica de Pine Script v5 (ta.*). Solo numpy/pandas, sin atajos.

Convenciones Pine que se replican a proposito:
  - ta.ema arranca en el primer valor (sin semilla SMA); ta.rma semilla = SMA de los primeros n valores validos.
  - ta.stdev es poblacional (ddof=0).
  - ta.tr: en la primera vela vale high-low.
  - Las ventanas (sma/highest/lowest/linreg) devuelven NaN hasta tener n velas.
  - Los NaN se propagan; las comparaciones con NaN dan False (igual que `na` en una condicion de Pine).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view


def sma(x, n: int) -> np.ndarray:
    return pd.Series(x).rolling(n).mean().to_numpy()


def stdev(x, n: int) -> np.ndarray:
    return pd.Series(x).rolling(n).std(ddof=0).to_numpy()


def ema(x, n: int, seed: str = "first") -> np.ndarray:
    """ta.ema. seed='first': arranca en el primer valor. seed='sma': NaN hasta n velas, semilla = SMA(n)."""
    if seed == "first":
        return pd.Series(x).ewm(alpha=2.0 / (n + 1), adjust=False).mean().to_numpy()
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    a = 2.0 / (n + 1)
    out[n - 1] = x[:n].mean()
    for i in range(n, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def wma(x, n: int) -> np.ndarray:
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    w = np.arange(1, n + 1, dtype=float)
    out[n - 1:] = (sliding_window_view(x, n) * w).sum(axis=1) / w.sum()
    return out


def rma(x, n: int) -> np.ndarray:
    """ta.rma: semilla = SMA de los primeros n valores (ignorando los NaN iniciales)."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    valid = ~np.isnan(x)
    if not valid.any():
        return out
    first = int(np.argmax(valid))
    s = first + n - 1
    if s >= len(x):
        return out
    out[s] = x[first:s + 1].mean()
    a = 1.0 / n
    for i in range(s + 1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def rolling_max(x, n: int) -> np.ndarray:
    return pd.Series(x).rolling(n).max().to_numpy()


def rolling_min(x, n: int) -> np.ndarray:
    return pd.Series(x).rolling(n).min().to_numpy()


def linreg_end(x, n: int) -> np.ndarray:
    """ta.linreg(x, n, 0): valor de la recta de minimos cuadrados en la ultima vela de la ventana."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    t = np.arange(n, dtype=float)
    tm = t.mean()
    den = ((t - tm) ** 2).sum()
    w = sliding_window_view(x, n)
    wm = w.mean(axis=1)
    slope = ((t - tm) * (w - wm[:, None])).sum(axis=1) / den
    out[n - 1:] = wm + slope * (n - 1 - tm)
    return out


def fixnan(x) -> np.ndarray:
    return pd.Series(x).ffill().to_numpy()


def true_range(h, l, c) -> np.ndarray:
    pc = np.r_[np.nan, c[:-1]]
    tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    tr[0] = h[0] - l[0]
    return tr


def rsi(c, n: int) -> np.ndarray:
    ch = np.r_[np.nan, np.diff(c)]
    up = rma(np.where(np.isnan(ch), np.nan, np.maximum(ch, 0.0)), n)
    dn = rma(np.where(np.isnan(ch), np.nan, np.maximum(-ch, 0.0)), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        res = np.where(dn == 0, 100.0, np.where(up == 0, 0.0, 100.0 - 100.0 / (1.0 + up / dn)))
    return np.where(np.isnan(up) | np.isnan(dn), np.nan, res)


def dmi_adx(h, l, c, n: int) -> np.ndarray:
    """ta.dmi(n, n) -> adx (Pine: fixnan sobre +DI/-DI, adx = rma(|+DI - -DI| / (+DI + -DI))."""
    up = np.r_[np.nan, np.diff(h)]
    dn = -np.r_[np.nan, np.diff(l)]
    plus_dm = np.where(np.isnan(up), np.nan, np.where((up > dn) & (up > 0), up, 0.0))
    minus_dm = np.where(np.isnan(dn), np.nan, np.where((dn > up) & (dn > 0), dn, 0.0))
    trur = rma(true_range(h, l, c), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        plus = fixnan(100 * rma(plus_dm, n) / trur)
        minus = fixnan(100 * rma(minus_dm, n) / trur)
        s = plus + minus
        return 100 * rma(np.abs(plus - minus) / np.where(s == 0, 1.0, s), n)


def pivots(src, left: int, right: int, kind: str) -> np.ndarray:
    """Equivalente a ta.pivotlow / ta.pivothigh(src, left, right).

    Devuelve un array donde la posicion i trae el valor del pivote confirmado en la vela i (o sea el pivote
    esta en la vela i-right); NaN si no hay. Regla usada (a verificar contra TradingView en la fase D):
    el centro debe ser estrictamente menor (mayor) que las `left` velas de la izquierda y menor-o-igual
    (mayor-o-igual) que las `right` de la derecha, es decir un empate a la derecha no invalida el pivote.
    """
    assert kind in ("low", "high")
    x = np.asarray(src, float)
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(left + right, n):
        c = i - right
        mid = x[c]
        if np.isnan(mid):
            continue
        lw = x[c - left:c]
        rw = x[c + 1:i + 1]
        if np.isnan(lw).any() or np.isnan(rw).any():
            continue
        if kind == "low":
            ok = (mid < lw).all() and (mid <= rw).all()
        else:
            ok = (mid > lw).all() and (mid >= rw).all()
        if ok:
            out[i] = mid
    return out


def compute(df: pd.DataFrame, p: dict) -> dict:
    """Todos los indicadores que usa la strategy (A+B+C), a partir de un DataFrame OHLCV."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    d: dict = {"open": o, "high": h, "low": l, "close": c}
    tr = true_range(h, l, c)
    basis = sma(c, p["bbLen"])
    dev = p["bbMult"] * stdev(c, p["bbLen"])
    kc_ma = sma(c, p["kcLen"])
    rng = tr if p["useTrueRange"] else (h - l)
    rng_ma = sma(rng, p["kcLen"])
    up_kc, lo_kc = kc_ma + rng_ma * p["kcMult"], kc_ma - rng_ma * p["kcMult"]
    d["sqzOn"] = ((basis - dev) > lo_kc) & ((basis + dev) < up_kc)
    avg_hl = (rolling_max(h, p["kcLen"]) + rolling_min(l, p["kcLen"])) / 2
    d["mom"] = linreg_end(c - (avg_hl + sma(c, p["kcLen"])) / 2, p["kcLen"])
    d["rsi"] = rsi(c, p["rsiLen"])
    ma = p["maType"]
    d["rsiMa"] = {"SMA": sma, "EMA": ema, "WMA": wma, "RMA": rma}[ma](d["rsi"], p["maLen"])
    sd = p.get("emaSeed", "first")
    d["ema1"], d["ema2"], d["ema3"] = ema(c, p["emaFLen"], sd), ema(c, p["emaMLen"], sd), ema(c, p["emaSLen"], sd)
    d["adx"] = dmi_adx(h, l, c, p["adxLen"])
    d["atr"] = rma(tr, p["atrLen"])
    return d
