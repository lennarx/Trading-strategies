"""Fase 6.0: prueba de estres de costos (slippage por lado) sobre los sets YA elegidos (params/h4.json, params/d1.json).

Es una MEDICION, no una seleccion: no se elige nada con esto. Cada corrida (set x slippage) cuenta como una prueba.
Uso:  python -m sqzlab.stress [--tf h4 d1] [--slips 0 0.02 0.05 0.10] [--workers 16]
Sale en results/stress_costs.md. La comision de 0,05% por lado ya esta en todos los casos; el slippage se suma encima.
"""
from __future__ import annotations

import argparse

import pandas as pd

from . import universe as U
from .genpine import load_params
from .metrics import summarize, window
from .optimize import RESULTS, Evaluator, md_table

SLIPS = [0.0, 0.02, 0.05, 0.10]


def groups(allt: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """OOS agregado como en optimize.stage5 (test de monedas train + holdout) y todo el historial 2017+."""
    te = window(allt[allt["coin"].isin(list(U.TRAIN))], U.TEST_FROM)
    ho = window(allt[allt["coin"].isin(list(U.HOLDOUT))], U.ENTRY_FROM)
    return {"OOS agregado (test 2024-hoy + holdout)": pd.concat([te, ho], ignore_index=True),
            "todo 2017-hoy, todas las monedas": window(allt, U.ENTRY_FROM)}


def run_tf(tf: str, slips: list[float], workers: int | None) -> tuple[pd.DataFrame, int]:
    params = load_params(tf)
    coins = list(U.TRAIN) + list(U.HOLDOUT)
    ev = Evaluator(tf, coins, workers)
    try:
        frames = ev.run([{**params, "slip_pct": s} for s in slips], coins)
    finally:
        ev.close()
    rows = []
    for s, fr in zip(slips, frames):
        for name, tr in groups(fr).items():
            sm = summarize(tr)
            rows.append(dict(tf=tf.upper(), slip_por_lado=f"{s:.2f}%", grupo=name,
                             **{k: sm[k] for k in ("n", "exp", "pf", "exp_ex_best", "exp_trim", "dd", "total")}))
    return pd.DataFrame(rows), len(slips)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", nargs="+", default=["h4", "d1"], choices=["h4", "d1", "w1"])
    ap.add_argument("--slips", nargs="+", type=float, default=SLIPS)
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    parts, tests = [], 0
    for tf in a.tf:
        df, n = run_tf(tf, a.slips, a.workers)
        parts.append(df)
        tests += n
    out = pd.concat(parts, ignore_index=True)
    txt = ("# Prueba de estres de costos (Fase 6.0)\n\n"
           "Medicion de los sets YA elegidos (`params/h4.json` optimizado, `params/d1.json` = v2): no se selecciona nada con esto. "
           f"Comision 0,05% por lado en todos los casos; `slip_pct` se suma por lado, en contra del trade, en entrada, cierre y stop. "
           f"**Pruebas de esta corrida: {tests}** (una por set x slippage; el conteo de optimizacion no cambia).\n\n"
           "Lectura: R neto por trade. Si la expectativa recortada (`exp_trim`) se va a cero o negativo con 0,05%, la ventaja no sobrevive costos realistas "
           "de perpetuos/alts en H4.\n\n" + md_table(out))
    (RESULTS / "stress_costs.md").write_text(txt + "\n", encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
