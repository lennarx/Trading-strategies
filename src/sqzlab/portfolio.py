"""Fase 6.3: cartera con equity compartida. Responde "cuanto puedo perder de verdad operando todo junto?".

Uso:  python -m sqzlab.portfolio --tf h4|d1|w1 [--risks 0.5 1 2] [--cap 5] [--max-pos 6] [--max-lev 1]
Toma los trades (R neto de comision, entrada y salida) del set vigente `params/<tf>.json` en las monedas de train+holdout
(las de Z1/Z2 no se tocan aca), desde 2017, y los reproduce en orden cronologico con una sola equity:
  - cada trade arriesga riesgo% de la equity realizada al entrar (compuesto), con el tope de apalancamiento por trade
    de la strategy (valor nocional <= maxLev x equity => riesgo <= maxLev x distancia del stop en % del precio);
  - tope de riesgo abierto total (`--cap`, % de la equity) y maximo de posiciones (`--max-pos`): si no entra, se saltea;
  - al salir, la equity suma riesgo_usd * R.
Aproximaciones DECLARADAS: la equity es la realizada (cierra trades; no marca a mercado lo abierto), asi que el DD sale
algo mas suave que el de TradingView; no modela margen ni liquidez. El tramo largo incluye los anios donde se eligio el
set (sesgo optimista): el tramo 2024-hoy es el que vale. Barrido de riesgo solo informativo.
Sale en results/portfolio_<tf>.md.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from . import universe as U
from .genpine import load_params
from .indicators import compute
from .metrics import summarize, trade_frame, window
from .optimize import BASE, RESULTS, md_table
from .strategy import DEFAULTS, simulate


def coin_trades(tf: str) -> pd.DataFrame:
    """Trades cerrados del set vigente en train+holdout, entradas >= 2017-01-01."""
    code = U.TF_CODE[tf]
    params = {**BASE, **load_params(tf)}
    parts = []
    for sym in {**U.TRAIN, **U.HOLDOUT}:
        df = U.load_coin(sym, code)
        ind = compute(df, {**DEFAULTS, **params})
        parts.append(trade_frame(simulate(df, ind=ind, **params), sym, ind["atr"]))
    return window(pd.concat(parts, ignore_index=True), U.ENTRY_FROM).reset_index(drop=True)


def run_portfolio(tr: pd.DataFrame, risk_pct: float, cap_pct: float | None = None, max_pos: int | None = None,
                  initial: float = 10000.0, compound: bool = True, max_lev: float | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(curva de equity en cada salida, trades tomados con su riesgo en USD). `compound=False`: riesgo fijo sobre el
    capital inicial (sirve para chequear que la suma coincide con la suma de R). `max_lev`: tope de apalancamiento por
    trade como en la strategy (necesita la columna `spct`); None lo ignora."""
    ev = sorted([(r.entry_t, 1, i) for i, r in tr.iterrows()] + [(r.exit_t, 0, i) for i, r in tr.iterrows()],
                key=lambda e: (e[0], e[1], tr.at[e[2], "coin"]))   # a igual hora salen antes de entrar
    equity, open_risk, taken = initial, {}, {}
    curve = [(tr["entry_t"].min(), initial)]
    for t, kind, i in ev:
        if kind == 1:
            base = equity if compound else initial
            frac = risk_pct / 100.0
            if max_lev and "spct" in tr.columns:
                frac = min(frac, max_lev * float(tr.at[i, "spct"]))
            ra = base * frac
            if max_pos is not None and len(open_risk) >= max_pos:
                continue
            if cap_pct is not None and sum(open_risk.values()) + ra > base * cap_pct / 100.0 + 1e-9:
                continue
            open_risk[i] = ra
        elif i in open_risk:
            ra = open_risk.pop(i)
            equity += ra * tr.at[i, "R"]
            taken[i] = ra
            curve.append((t, equity))
    cv = pd.DataFrame(curve, columns=["t", "equity"])
    tk = tr.loc[list(taken)].assign(risk_usd=pd.Series(taken))
    return cv, tk


def curve_stats(cv: pd.DataFrame, initial: float = 10000.0) -> dict:
    eq = cv["equity"].to_numpy(float)
    years = max((cv["t"].iloc[-1] - cv["t"].iloc[0]).days / 365.25, 1e-9)
    cagr = (eq[-1] / initial) ** (1 / years) - 1 if eq[-1] > 0 else -1.0
    dd = float(((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq)).max())
    m = cv.set_index("t")["equity"].resample("ME").last().ffill()
    mret = m.pct_change().dropna()
    return dict(final=float(eq[-1]), cagr=float(cagr), dd=dd, mar=float(cagr / dd) if dd > 0 else float("inf"),
                meses=len(mret), meses_neg=float((mret < 0).mean()) if len(mret) else 0.0,
                peor_mes=float(mret.min()) if len(mret) else 0.0, anios=float(years))


def concurrency(tk: pd.DataFrame) -> dict:
    """Maximo de posiciones abiertas a la vez y que parte de las perdedoras coincide con otra perdedora abierta."""
    ev = sorted([(r.entry_t, 1) for r in tk.itertuples()] + [(r.exit_t, -1) for r in tk.itertuples()], key=lambda e: (e[0], e[1]))
    cur = mx = 0
    for _, d in ev:
        cur += d
        mx = max(mx, cur)
    los = tk[tk["R"] < 0]
    overlap = 0
    for r in los.itertuples():
        o = los[(los["coin"] != r.coin) & (los["entry_t"] < r.exit_t) & (los["exit_t"] > r.entry_t)]
        overlap += len(o) > 0
    return dict(max_abiertas=mx, perdedoras=len(los), perdedoras_con_otra_perdedora=overlap / len(los) if len(los) else 0.0)


def buy_hold_btc(start: pd.Timestamp, end: pd.Timestamp) -> dict:
    df = U.load_coin("BTC", "1d")
    df = df[(df["time_utc"] >= start) & (df["time_utc"] <= end)]
    c = df["close"].to_numpy(float)
    years = (df["time_utc"].iloc[-1] - df["time_utc"].iloc[0]).days / 365.25
    return dict(cagr=float((c[-1] / c[0]) ** (1 / years) - 1), dd=float(((np.maximum.accumulate(c) - c) / np.maximum.accumulate(c)).max()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", required=True, choices=["h4", "d1", "w1"])
    ap.add_argument("--risks", nargs="+", type=float, default=[0.5, 1.0, 2.0])
    ap.add_argument("--cap", type=float, default=5.0, help="tope de riesgo abierto total, %% de la equity (0 = sin tope)")
    ap.add_argument("--max-pos", type=int, default=6, help="maximo de posiciones abiertas (0 = sin limite)")
    ap.add_argument("--max-lev", type=float, default=1.0, help="tope de apalancamiento por trade como en la strategy (0 = ignorarlo)")
    a = ap.parse_args()
    all_tr = coin_trades(a.tf)
    cap, mp, ml = (a.cap or None), (a.max_pos or None), (a.max_lev or None)
    long_name = f"{U.ENTRY_FROM.year}-hoy (incluye el tramo donde se eligio el set)"
    periods = {long_name: all_tr,
               f"{U.TEST_FROM.year}-hoy (despues del corte de train)": window(all_tr, U.TEST_FROM).reset_index(drop=True)}
    blocks, extra = "", ""
    for pname, tr in periods.items():
        rows = []
        for rk in a.risks:
            for label, c_, m_ in (("con topes", cap, mp), ("sin topes de cartera", None, None)):
                cv, tk = run_portfolio(tr, rk, c_, m_, max_lev=ml)
                s = curve_stats(cv)
                rows.append(dict(riesgo=f"{rk:g}%", topes=label, trades=len(tk), salteados=len(tr) - len(tk), equity_final=s["final"],
                                 CAGR=s["cagr"], DD_max=s["dd"], MAR=s["mar"], meses_neg=s["meses_neg"], peor_mes=s["peor_mes"]))
                if rk == 1.0 and label == "con topes" and pname == long_name:
                    cc = concurrency(tk)
                    extra = (f"\n## Concurrencia (riesgo 1%, con topes, {U.ENTRY_FROM.year}-hoy)\n\n"
                             f"- Maximo de posiciones abiertas a la vez: {cc['max_abiertas']}.\n"
                             f"- Trades perdedores: {cc['perdedoras']}; el {cc['perdedoras_con_otra_perdedora']:.0%} coincide en el tiempo con una "
                             "perdedora de OTRA moneda (las cripto pierden juntas: la diversificacion entre monedas ayuda poco).\n")
        sm_p = summarize(tr)
        bh = buy_hold_btc(tr["entry_t"].min(), tr["exit_t"].max())
        blocks += (f"\n## {pname}\n\nn={sm_p['n']} trades, {sm_p['exp']:.3f}R por trade, suma {sm_p['total']:.1f}R. "
                   f"Comprar y mantener BTC en el mismo tramo: CAGR {bh['cagr']:.1%}, DD maximo {bh['dd']:.1%} (cierres diarios).\n\n"
                   + md_table(pd.DataFrame(rows)))
    txt = (f"# Cartera {a.tf.upper()} (generado por `python -m sqzlab.portfolio`)\n\n"
           f"Set: `params/{a.tf}.json`. Monedas: {', '.join({**U.TRAIN, **U.HOLDOUT})}. Entradas hasta {U.DATA_END[U.TF_CODE[a.tf]]}. "
           "Capital inicial 10.000; riesgo % sobre la equity realizada, compuesto.\n"
           f"Topes: riesgo abierto total {a.cap:g}% de la equity y maximo {a.max_pos} posiciones (\"sin topes de cartera\" = cada trade entra siempre); "
           f"tope de apalancamiento por trade como la strategy (maxLev {a.max_lev:g}). "
           "**Aproximaciones:** equity realizada (no marca a mercado lo abierto, el DD real puede ser peor), sin margen ni liquidez. "
           "**Leer con cuidado:** el tramo largo incluye los anios donde se ELIGIO el set (sesgo optimista); el tramo 2024-hoy es el que vale. "
           "No es asesoria financiera.\n" + blocks + extra)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"portfolio_{a.tf}.md").write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
