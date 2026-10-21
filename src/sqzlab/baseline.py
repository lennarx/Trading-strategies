"""Baseline aleatorio: entradas al azar con el mismo manejo de stops y salidas que la strategy.

Para cada moneda: la misma cantidad de entradas largas y cortas que la estrategia real, en barras al azar de la
misma ventana, sin superponerse (una posicion a la vez, como pyramiding=0). Stop = entrada -/+ k*ATR, con k = mediana
de la distancia real de los stops en ATR. Salidas iguales: stop tocado intravela (desde la vela siguiente, con gap al
open) o cierre contra la EMA rapida. R neto = (PnL - comision por lado sobre el valor) / riesgo.
Semilla fija: misma entrada -> mismo resultado.
"""
from __future__ import annotations

import zlib

import numpy as np
import pandas as pd


def _next_true(cond: np.ndarray) -> np.ndarray:
    """nxt[j] = primer indice k >= j con cond[k]; n si no hay."""
    n = len(cond)
    idx = np.where(cond, np.arange(n), n)
    return np.minimum.accumulate(idx[::-1])[::-1]


class CoinSeries:
    """Arrays de una moneda listos para el baseline. i0/i1 = rango de barras de entrada permitido (la ventana)."""

    def __init__(self, ind: dict, time, start, end):
        self.o, self.h, self.l, self.c = ind["open"], ind["high"], ind["low"], ind["close"]
        self.atr, self.e1 = ind["atr"], ind["ema1"]
        self.n = len(self.c)
        with np.errstate(invalid="ignore"):
            self.nxt_long = _next_true(self.c < self.e1)     # salida larga: cierre bajo la EMA rapida
            self.nxt_short = _next_true(self.c > self.e1)
        t = pd.to_datetime(time)
        ok = ~np.isnan(self.atr) & ~np.isnan(self.e1) & ~np.isnan(ind["ema3"])
        ok &= (t >= pd.Timestamp(start)) if start is not None else True
        ok &= (t <= pd.Timestamp(end)) if end is not None else True
        ok[-1] = False                                       # una entrada en la ultima vela nunca cierra
        self.eligible = np.flatnonzero(ok)

    def trade(self, side: int, i: int, kd: float, rate: float):
        """(indice de salida, R neto) del trade que entra al cierre de i, o None si queda abierto al final."""
        entry = self.c[i]
        dist = kd * self.atr[i]
        if dist <= 0:
            return None
        stop = entry - side * dist
        nxt = self.nxt_long if side > 0 else self.nxt_short
        j_e = nxt[i + 1] if i + 1 < self.n else self.n
        end = min(j_e + 1, self.n)
        seg = self.l[i + 1:end] <= stop if side > 0 else self.h[i + 1:end] >= stop
        hit = np.flatnonzero(seg)
        if hit.size:
            j = i + 1 + int(hit[0])
            px = min(self.o[j], stop) if side > 0 else max(self.o[j], stop)
        elif j_e < self.n:
            j, px = int(j_e), self.c[j_e]
        else:
            return None
        return j, (side * (px - entry) - rate * (entry + px)) / dist


def random_baseline(coins: dict[str, CoinSeries], counts: dict[str, tuple[int, int]], kd: float, reps: int = 500,
                    seed_tag: str = "base", commission_pct: float = 0.05, seed: int = 20261021) -> dict:
    """Distribucion de la expectativa (R medio por trade, agregado entre monedas) de `reps` replicas aleatorias.
    counts[moneda] = (largas, cortas) de la estrategia real. Devuelve p50, p95, media y desvio de esa expectativa."""
    rate = commission_pct / 100.0
    rng = np.random.default_rng(seed + zlib.crc32(seed_tag.encode()))
    exps = np.empty(reps)
    for r in range(reps):
        tot, cnt = 0.0, 0
        for sym, cs in coins.items():
            nl, ns = counts.get(sym, (0, 0))
            if (nl + ns) == 0 or cs.eligible.size == 0:
                continue
            occ = np.zeros(cs.n, bool)
            for side, want in ((1, nl), (-1, ns)):
                got = 0
                if want == 0:
                    continue
                for i in rng.permutation(cs.eligible)[: want * 6]:
                    if occ[i]:
                        continue
                    res = cs.trade(side, int(i), kd, rate)
                    if res is None:
                        continue
                    j, rr = res
                    if occ[i:j + 1].any():
                        continue
                    occ[i:j + 1] = True
                    tot += rr
                    cnt += 1
                    got += 1
                    if got == want:
                        break
        exps[r] = tot / cnt if cnt else 0.0
    return dict(p50=float(np.percentile(exps, 50)), p95=float(np.percentile(exps, 95)), mean=float(exps.mean()),
                std=float(exps.std()), reps=reps, kd=float(kd))


def side_counts(tr: pd.DataFrame) -> dict[str, tuple[int, int]]:
    """(largas, cortas) por moneda a partir del DataFrame de trades reales."""
    out = {}
    for sym, g in tr.groupby("coin"):
        out[sym] = (int((g["side"] > 0).sum()), int((g["side"] < 0).sum()))
    return out
