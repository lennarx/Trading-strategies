"""Metricas en R neto de comision a partir de los trades de `strategy.simulate`.

1R = riesgo en USD del trade (|entrada - stop| * cantidad); R neto = PnL neto de comision / 1R.
Las metricas se calculan sobre trades CERRADOS cuya entrada cae dentro de una ventana.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRIM_FRAC = 0.02
COLS = ["coin", "kind", "side", "entry_t", "exit_t", "R", "sd", "spct"]


def trade_frame(res, coin: str, atr=None) -> pd.DataFrame:
    """Trades cerrados de un SimResult como DataFrame. `sd` = distancia del stop en ATR de la vela de entrada
    (hace falta `atr`; lo usa el baseline aleatorio). `spct` = distancia del stop en fraccion del precio de entrada
    (la usa la cartera para respetar el tope maxLev)."""
    t = res.time
    rows = [(coin, tr.kind, tr.side, t[tr.entry_i], t[tr.exit_i], tr.r_net,
             abs(tr.entry_px - tr.stop) / atr[tr.entry_i] if atr is not None else np.nan,
             abs(tr.entry_px - tr.stop) / tr.entry_px) for tr in res.trades]
    df = pd.DataFrame(rows, columns=COLS)
    df["entry_t"] = pd.to_datetime(df["entry_t"])
    df["exit_t"] = pd.to_datetime(df["exit_t"])
    return df.dropna(subset=["R"]).reset_index(drop=True)


def window(tr: pd.DataFrame, start=None, end=None) -> pd.DataFrame:
    """Trades con entrada en [start, end]."""
    m = np.ones(len(tr), bool)
    if start is not None:
        m &= (tr["entry_t"] >= pd.Timestamp(start)).to_numpy()
    if end is not None:
        m &= (tr["entry_t"] <= pd.Timestamp(end)).to_numpy()
    return tr[m]


def max_drawdown_r(tr: pd.DataFrame) -> float:
    """Caida maxima de la curva acumulada de R (ordenada por fecha de salida), en R."""
    if len(tr) == 0:
        return 0.0
    r = tr.sort_values("exit_t", kind="stable")["R"].to_numpy(float)
    eq = np.r_[0.0, np.cumsum(r)]
    return float((np.maximum.accumulate(eq) - eq).max())


def summarize(tr: pd.DataFrame) -> dict:
    """n, expectativa (R medio), PF en R, % ganadores, DD en R, R total, expectativa sin el mejor trade, expectativa recortada (sin el 2% de mejores),
    mediana de la expectativa por moneda."""
    n = len(tr)
    if n == 0:
        return dict(n=0, exp=0.0, pf=0.0, win=0.0, dd=0.0, total=0.0, exp_ex_best=0.0, exp_trim=0.0, med_coin=0.0)
    r = tr["R"].to_numpy(float)
    gp, gl = r[r > 0].sum(), -r[r < 0].sum()
    ex_best = (r.sum() - r.max()) / (n - 1) if n > 1 else 0.0
    k = int(np.ceil(TRIM_FRAC * n))                 # recorte: sin el 2% de mejores trades (al menos 1)
    trim = np.sort(r)[: n - k].mean() if n > k else 0.0
    per_coin = tr.groupby("coin")["R"].mean()
    return dict(n=n, exp=float(r.mean()), pf=float(gp / gl) if gl > 0 else float("inf"), win=float((r > 0).mean()),
                dd=max_drawdown_r(tr), total=float(r.sum()), exp_ex_best=float(ex_best), exp_trim=float(trim),
                med_coin=float(per_coin.median()))


def breakdown(tr: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    """Desglose por senal/lado/moneda: n, expectativa, PF en R, % ganadores, R total."""
    rows = []
    for key, g in tr.groupby(by):
        s = summarize(g)
        rows.append({**(dict(zip(by, key)) if isinstance(by, list) else {by: key}),
                     **{k: s[k] for k in ("n", "exp", "pf", "win", "total")}})
    return pd.DataFrame(rows)
