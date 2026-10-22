"""Senales de la ULTIMA VELA CERRADA para el bot del usuario (no depende de alertas de TradingView).

Uso:  python -m sqzlab.signals --tf h4|d1|w1 --symbols BTC ETH SOL [--source bingx|binance|bitstamp] [--no-fetch]
                               [--donchian 20 60 150 250] [--out archivo.json]
Un solo motor: es `strategy.simulate` con `params/<tf>.json` (la misma logica del backtest y del Pine). Baja velas con
`fetch.update_csv`, descarta la vela en curso (`forward.closed_only`) y devuelve un JSON por moneda con la senal de la vela
cerrada mas reciente. Contrato en docs/BOT.md.

Sin repintado por diseno: `simulate` es causal (cada decision de la vela i usa solo velas <= i), asi que una senal emitida para
una vela cerrada no cambia cuando llegan velas nuevas (tests/test_signals.py lo verifica contra la corrida con 50+ velas mas).
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from . import universe as U
from .data import load
from .donchian import E_DAYS, days_to_bars, half, vol_ann, vol_weight
from .fetch import update_csv
from .forward import closed_only, params_hash
from .genpine import load_params
from .indicators import compute
from .optimize import BASE
from .strategy import DEFAULTS, prev_close_max, prev_close_min, simulate

SIDE = {1: "long", -1: "short"}


def _iso(t) -> str:
    return pd.Timestamp(t).strftime("%Y-%m-%dT%H:%M:%SZ")


def bar_events(df: pd.DataFrame, params: dict) -> dict[int, dict]:
    """{indice de vela: evento} de la corrida completa: entradas y salidas de `simulate`. Una vela puede traer una salida
    y una entrada (reversa)."""
    ind = compute(df, {**DEFAULTS, **params})
    res = simulate(df, ind=ind, **params)
    ev: dict[int, dict] = {}
    for t in res.trades:
        ev.setdefault(t.exit_i, {})["exit"] = dict(kind=t.kind, side=t.side, reason=t.exit_reason)
        ev.setdefault(t.entry_i, {})["entry"] = dict(kind=t.kind, side=t.side, entry_px=t.entry_px, stop=t.stop)
    if res.open_trade is not None:
        t = res.open_trade
        ev.setdefault(t.entry_i, {})["entry"] = dict(kind=t.kind, side=t.side, entry_px=t.entry_px, stop=t.stop)
    ev["_open"] = res.open_trade
    return ev


def size_pct(entry: float, stop: float, params: dict) -> float:
    """% de la equity en nocional con el sizing de la strategy: min(riesgo% / distancia del stop, maxLev)."""
    d = abs(entry - stop) / entry
    return float(min(params["riskPct"] / 100.0 / d, params["maxLev"]) * 100.0) if d > 0 else 0.0


def last_signal(df: pd.DataFrame, tf: str, symbol: str, params: dict | None = None) -> dict:
    """Senal de la ultima vela de `df` (que debe traer SOLO velas cerradas)."""
    p = {**BASE, **load_params(tf)} if params is None else params
    ev = bar_events(df, p)
    i = len(df) - 1
    e = ev.get(i, {})
    base = dict(symbol=symbol, tf=tf, bar_time_utc=_iso(df["time_utc"].iloc[i]), params_hash=params_hash(tf))
    op = ev["_open"]
    position = None if op is None else dict(side=SIDE[op.side], kind=op.kind, since_bar_time_utc=_iso(df["time_utc"].iloc[op.entry_i]),
                                            entry_ref=float(op.entry_px), stop=float(op.stop))
    if "entry" in e:
        x = e["entry"]
        out = dict(action=SIDE[x["side"]], kind=x["kind"], entry_ref=float(x["entry_px"]), stop=float(x["stop"]),
                   size_pct_equity=round(size_pct(x["entry_px"], x["stop"], p), 4))
        if "exit" in e:
            out["closes_previous"] = dict(kind=e["exit"]["kind"], reason=e["exit"]["reason"])
    elif "exit" in e:
        x = e["exit"]
        out = dict(action="exit", kind=x["kind"], entry_ref=None, stop=None, size_pct_equity=0.0, reason=x["reason"])
    else:
        out = dict(action="none", kind=None, entry_ref=None, stop=None, size_pct_equity=0.0)
    return {**base, **out, "position": position}


def e_state(df: pd.DataFrame, tf: str, symbol: str, days: list[int]) -> dict:
    """Estado de la senal E (ensamble de Donchian, solo largo) en la ultima vela cerrada: cuantas sub-senales estan activas,
    cuales entran/salen en esta vela y el tamano objetivo (activas/K x min(0,25/vol, 2))."""
    c = df["close"].to_numpy(float)
    n = len(c)
    vol = vol_ann(c, tf)[-1]
    active, entering, exiting = 0, [], []
    for d in days:
        nb = days_to_bars(d, tf)
        hi, lo = prev_close_max(c, nb), prev_close_min(c, half(nb))
        inpos = False
        for i in range(n):
            if not inpos:
                if c[i] > hi[i] and not np.isnan(lo[i]):
                    inpos = True
                    if i == n - 1:
                        entering.append(d)
            elif c[i] < lo[i]:
                inpos = False
                if i == n - 1:
                    exiting.append(d)
        active += inpos
    wv = vol_weight(vol)
    k = len(days)
    action = "long" if entering else (("exit" if active == 0 else "reduce") if exiting else "none")
    return dict(symbol=symbol, tf=tf, bar_time_utc=_iso(df["time_utc"].iloc[-1]), action=action, kind="E", entry_ref=float(c[-1]) if entering else None,
                stop=None, size_pct_equity=None if np.isnan(wv) else round(active / k * wv * 100.0, 4),
                active_subsignals=int(active), total_subsignals=k, entering_days=entering, exiting_days=exiting,
                vol_ann=None if np.isnan(vol) else round(float(vol), 4), e_days=list(days), params_hash=params_hash(tf))


def build(tf: str, symbols: list[str], source: str, fetch: bool, e_days: list[int] | None) -> list[dict]:
    code = U.TF_CODE[tf]
    out = []
    for sym in symbols:
        if fetch:
            update_csv(source, sym, "1d" if code == "1w" else code)
        df = closed_only(load(source, sym, code, start=None if code == "1w" else U.WARMUP_FROM), code)
        out.append(last_signal(df, tf, sym))
        if e_days:
            out.append(e_state(df, tf, sym, e_days))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", required=True, choices=["h4", "d1", "w1"])
    ap.add_argument("--symbols", nargs="+", required=True)
    ap.add_argument("--source", default="binance", choices=["bingx", "binance", "bitstamp"])
    ap.add_argument("--no-fetch", action="store_true", help="no baja velas: usa lo que hay en data/")
    ap.add_argument("--donchian", nargs="*", type=int, default=None, metavar="DIAS",
                    help="agrega el estado de la senal E (sin argumentos: 20 60 150 250). Apagado por defecto.")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    e_days = None if a.donchian is None else (a.donchian or E_DAYS)
    res = build(a.tf, a.symbols, a.source, not a.no_fetch, e_days)
    txt = json.dumps(res, indent=1, ensure_ascii=False)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
