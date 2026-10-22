"""Fase 7, P2 y P5: senal E (ensamble de canales de Donchian, solo largo) y volatilidad objetivo.

Reglas fijadas en docs/PROTOCOLO.md ("Decisiones fijadas ANTES de la Fase 7"). Resumen:
  - entrada: cierre > maximo de los N cierres PREVIOS (la vela actual no entra en la ventana); salida: cierre < minimo de
    los max(N//2, 2) cierres previos; todo al cierre de la vela (process_orders_on_close). Cada N es una sub-senal;
    la exposicion es el promedio del ensamble (peso 1/K por sub-senal).
  - lookbacks en dias -> velas: H4 x6, D1 x1, W1 floor(d/7 + 0,5) con minimo 4.
  - vol anual = desvio (ddof=1) de los retornos log cierre a cierre de 90 dias, por sqrt(velas por anio).
Las reglas del paper (Zarattini, Pagani, Barbon 2025) vienen de un resumen del plan, NO verificadas contra el texto.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .strategy import prev_close_max, prev_close_min

E_DAYS = [20, 60, 150, 250]                       # P2: subconjunto fijo del paper
R1_DAYS = [5, 10, 20, 30, 60, 90, 150, 250, 360]  # R1: ensamble completo
BARS_PER_DAY = {"h4": 6.0, "d1": 1.0, "w1": 1.0 / 7.0}
BARS_PER_YEAR = {"h4": 365.0 * 6, "d1": 365.0, "w1": 365.0 / 7.0}
VOL_DAYS = 90
VOL_TARGET = 0.25
VOL_CAP = 2.0


def days_to_bars(d: int, tf: str) -> int:
    if tf == "w1":
        return max(4, int(math.floor(d / 7 + 0.5)))
    return int(d * BARS_PER_DAY[tf])


def half(n: int) -> int:
    return max(n // 2, 2)


def vol_window(tf: str) -> int:
    return days_to_bars(VOL_DAYS, tf) if tf != "w1" else 13


def vol_ann(close, tf: str) -> np.ndarray:
    """Vol anualizada en cada vela, con datos hasta el cierre de esa vela (NaN hasta tener la ventana completa)."""
    c = np.asarray(close, float)
    lr = np.r_[np.nan, np.diff(np.log(c))]
    sd = pd.Series(lr).rolling(vol_window(tf)).std(ddof=1).to_numpy()
    return sd * math.sqrt(BARS_PER_YEAR[tf])


def vol_weight(vol: float) -> float:
    """Nocional como multiplo de la equity: min(0,25 / vol, 2); NaN si no hay vol."""
    if not vol or np.isnan(vol) or vol <= 0:
        return float("nan")
    return min(VOL_TARGET / vol, VOL_CAP)


def donchian_subtrades(df: pd.DataFrame, tf: str, days: list[int], coin: str = "") -> pd.DataFrame:
    """Sub-trades largos de la senal E: una fila por entrada de cada sub-senal. Columnas: coin, kind='E', side=1, entry_i,
    exit_i, entry_px, exit_px, stop (minimo de salida al entrar), w (=1/K), lb (lookback en velas), open (sigue abierto al final)."""
    c = df["close"].to_numpy(float)
    n = len(c)
    rows = []
    k = len(days)
    for j, d in enumerate(days):
        nb = days_to_bars(d, tf)
        hi = prev_close_max(c, nb)
        lo = prev_close_min(c, half(nb))
        inpos, ei, lvl = False, -1, np.nan
        for i in range(n):
            if not inpos:
                if c[i] > hi[i] and not np.isnan(lo[i]):    # NaN en hi -> la comparacion da False
                    inpos, ei, lvl = True, i, lo[i]
            elif c[i] < lo[i]:
                rows.append((coin, "E", 1, ei, i, c[ei], c[i], lvl, 1.0 / k, nb, False, j))
                inpos = False
        if inpos:
            rows.append((coin, "E", 1, ei, n - 1, c[ei], c[-1], lvl, 1.0 / k, nb, True, j))
    cols = ["coin", "kind", "side", "entry_i", "exit_i", "entry_px", "exit_px", "stop", "w", "lb", "open", "j"]
    return pd.DataFrame(rows, columns=cols)
