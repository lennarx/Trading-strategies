"""Fase 7, P4 y P1: filtro de tendencia del TF mayor de la MISMA moneda, sin lookahead.

Semantica Pine replicada: request.security(tickerid, tfMayor, close[1] > ta.ema(close, N)[1], lookahead=barmerge.lookahead_on).
Una vela del TF chico usa SIEMPRE la ultima vela CERRADA del TF mayor que ya existia antes de que abriera la vela mayor
que la contiene: una H4 del dia D usa D-1; una D1 de la semana W usa W-1 (semanas que abren el lunes 00:00 UTC).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import ema

HTF_OF = {"h4": "1d", "d1": "1w"}                 # TF mayor (codigo de data) de cada temporalidad; W1 no tiene
P4_N = {"h4": [50, 100], "d1": [10, 20, 40]}      # grillas de P4 (PROTOCOLO, Fase 7)
P1_DEFAULT_N = {"h4": 100, "d1": 20}              # N de P1 cuando P4 esta apagado


def htf_flags(ltf_times, htf_df: pd.DataFrame, n: int) -> dict:
    """{'bull': close>EMA(n), 'bear': close<EMA(n)} de la ultima vela CERRADA del TF mayor, alineado a `ltf_times`.
    Las velas sin TF mayor previo o con EMA todavia NaN dan False en ambos."""
    c = htf_df["close"].to_numpy(float)
    e = ema(c, n, "sma")
    bull_h, bear_h = c > e, c < e                        # NaN -> False
    ht = htf_df["time_utc"].to_numpy("datetime64[ns]")
    lt = np.asarray(ltf_times, dtype="datetime64[ns]")
    k = np.searchsorted(ht, lt, side="right") - 1 - 1   # vela mayor que contiene a la vela chica, menos una = ya cerrada
    ok = k >= 0
    kk = np.where(ok, k, 0)
    return dict(bull=np.where(ok, bull_h[kk], False), bear=np.where(ok, bear_h[kk], False))
