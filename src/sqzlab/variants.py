"""Fase 6.4: soporte de las variantes estructurales (ver docs/PROTOCOLO.md, "Variantes estructurales (6.4)").

V4 (filtro de regimen): bandera por vela de si el cierre diario de BTC (Bitstamp) de AYER esta sobre su EMA200 diaria
(semilla SMA). En Pine seria request.security con [1] y lookahead_on: el valor del dia anterior, ya cerrado.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from .data import load
from .indicators import ema


@lru_cache(maxsize=1)
def _btc_bull() -> pd.Series:
    df = load("bitstamp", "BTC", "1d")
    c = df["close"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        bull = c > ema(c, 200, "sma")          # NaN (primeras 199 velas) compara False
    return pd.Series(bull, index=df["time_utc"].dt.normalize())


def regime_flags(times) -> np.ndarray:
    """bool por vela: True si BTC D1 cerro AYER (dia anterior al de la apertura de la vela) sobre su EMA200 diaria."""
    day = pd.DatetimeIndex(times).normalize() - pd.Timedelta(days=1)
    return _btc_bull().reindex(day).fillna(False).to_numpy(bool)
