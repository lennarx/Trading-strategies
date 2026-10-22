"""Senales de la ULTIMA VELA CERRADA para el bot del usuario (no depende de alertas de TradingView).

Uso:  python -m sqzlab.signals --tf h4|d1|w1 --symbols BTC ETH SOL [--source bingx|binance|bitstamp] [--no-fetch]
                               [--donchian 20 60 150 250] [--out archivo.json]
      python -m sqzlab.signals --strategy r1fiel [--tf d1|h4] [--no-fetch] [--out archivo.json]   (Fase 8: PESOS OBJETIVO de la cartera)
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


def r1fiel_signal(tf: str = "d1", fetch: bool = True, now: pd.Timestamp | None = None) -> dict:
    """Fase 8: pesos objetivo (% de la equity) de la cartera R1-fiel para la ULTIMA vela diaria CERRADA. Mismo codigo que el backtest
    (universe_dyn + r1fiel): el universo del dia usa datos <= t-1, las senales usan cierres <= t. Contrato en docs/BOT.md."""
    import hashlib

    from . import r1fiel as R
    from . import universe_dyn as UD
    from .f8data import F8, F8_LIVE, exchange_usdt, update_all
    if tf != "d1":
        raise SystemExit("signals --strategy r1fiel solo implementado para d1 (la estrategia); h4 es una conversion sin veredicto")
    upd = update_all("1d", now=now) if fetch else None
    bases = sorted({p.stem for d in (F8, F8_LIVE) for p in (d / "1d").glob("*.csv")})
    assets, excl, cuts = UD.load_assets_daily(bases, clip=False, live=True)
    last_day = max(a.last for a in assets.values())
    dates = pd.date_range("2017-08-01", last_day)
    uni = UD.build_universe(assets, dates)
    top = uni["top"].iloc[-1]
    prev_top = uni["top"].iloc[-2]
    try:
        trading = {b for b, st in exchange_usdt().items() if st == "TRADING"}
    except Exception:           # sin red: no se puede distinguir deslistada de dato faltante
        trading = None
    stale = sorted(assets[i].base for i in prev_top.index if bool(prev_top[i]) and assets[i].last < last_day and (trading is None or assets[i].base in trading))
    if stale:                   # no devolver pesos: el bot vendería por un dato faltante (hallazgo #1 de la revision previa)
        raise SystemExit(f"DATOS INCOMPLETOS: monedas del top 20 de ayer, hoy TRADING, sin la vela {last_day.date()}: {stale}. No se emiten pesos; reintentar la descarga.")
    ids = [i for i in top.index if bool(top[i])]
    day = {i: assets[i] for i in ids if assets[i].last == last_day}      # una moneda cuya ultima vela no es la de hoy (deslistada) no tiene objetivo
    res = R.last_bar_targets(day, top, "d1")
    ps = R.params()
    rows = []
    for aid in sorted(res["targets"], key=lambda k: -res["targets"][k]["weight"]):
        t = res["targets"][aid]
        base = assets[aid].base
        rows.append(dict(symbol=base, pair=f"{base}USDT", weight_pct_equity=round(t["weight"] * 100.0, 4), weight_raw_pct_equity=round(t["weight_raw"] * 100.0, 4),
                         active_subsignals=t["active"], total_subsignals=t["total"], vol_ann=t["vol_ann"], close=t["close"],
                         stop_by_lookback_days=dict(zip(ps["lookbacks_days"], t["stops"]))))
    return dict(strategy="r1fiel", tf=tf, bar_time_utc=_iso(last_day), params_hash=hashlib.sha256(json.dumps(ps, sort_keys=True).encode()).hexdigest()[:16],
                universe=[assets[i].base for i in ids], gross_raw=round(res["gross_raw"], 6), gross_scale=round(res["scale"], 6), gross=round(res["gross"], 6),
                rebalance_band=ps["rebalance_band"], targets=rows, data_update=upd,
                note="Monedas que no figuran en `targets` tienen objetivo 0. Peso = % de la equity (nocional). No es asesoria financiera.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="sqzrsi", choices=["sqzrsi", "r1fiel"])
    ap.add_argument("--tf", default="d1", choices=["h4", "d1", "w1"])
    ap.add_argument("--symbols", nargs="+", default=None)
    ap.add_argument("--source", default="binance", choices=["bingx", "binance", "bitstamp"])
    ap.add_argument("--no-fetch", action="store_true", help="no baja velas: usa lo que hay en data/")
    ap.add_argument("--donchian", nargs="*", type=int, default=None, metavar="DIAS",
                    help="agrega el estado de la senal E (sin argumentos: 20 60 150 250). Apagado por defecto.")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.strategy == "r1fiel":
        res = r1fiel_signal(a.tf, not a.no_fetch)
    else:
        if not a.symbols:
            ap.error("--symbols es obligatorio con --strategy sqzrsi")
        e_days = None if a.donchian is None else (a.donchian or E_DAYS)
        res = build(a.tf, a.symbols, a.source, not a.no_fetch, e_days)
    txt = json.dumps(res, indent=1, ensure_ascii=False)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
