"""Fase 6.4: variantes estructurales de stop/salida/regimen, una por una, declaradas ANTES en docs/PROTOCOLO.md.

Uso:  python -m sqzlab.varsearch --tf h4|d1 --stage train      # seleccion, solo train (monedas train, 2017-2023)
      python -m sqzlab.varsearch --tf h4|d1 --stage z2         # veredicto, UNA sola mirada por variante sobreviviente
Las variantes se aplican encima del set vigente (`params/<tf>.json`); todas estan apagadas por defecto en `simulate`.
Seleccion (PROTOCOLO): un punto pasa a Z2 si es factible, mejora la expectativa recortada de train en >= 0,02R respecto del
mismo set sin variante, su score suavizado de meseta tambien supera al del set sin variante y, solo en H4, mejora la
expectativa media en >= 3 de los 4 anios 2020-2023. El OOS de la Fase 4/5 y Z1 NO se usan. Veredicto en Z2: gana si cumple
los criterios absolutos de confirmacion Y supera al set sin variante en expectativa y en recortada. Estado en
results/varsearch_<tf>_state.json; informe en results/varsearch_<tf>.md.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from . import universe as U
from .confirm import criteria
from .genpine import load_params
from .metrics import summarize, window
from .optimize import (MIN_N_FINAL, RESULTS, Evaluator, Grid, _py, best_row, md_table, random_baseline_for, score_grid)

VARIANTS: dict[str, tuple[str, dict]] = {
    "V1": ("trailing por ATR", {"trailK": [2.0, 3.0, 4.0, 6.0]}),
    "V2": ("break-even a +beR x riesgo", {"beR": [1.0, 1.5, 2.0]}),
    "V3": ("salida contra la EMA55", {"exitMid": [True]}),
    "V4": ("largos solo con BTC D1 sobre su EMA200", {"regimeFilter": [True]}),
}
MIN_GAIN = 0.02            # mejora minima de la expectativa recortada en train, en R
WF_YEARS = [2020, 2021, 2022, 2023]
WF_MIN_WINS = 3


def year_exp(tr: pd.DataFrame, y: int) -> float:
    w = window(tr, pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31 23:59:59"))
    return float(w["R"].mean()) if len(w) else 0.0


def train(tf: str, workers: int | None) -> None:
    path = RESULTS / f"varsearch_{tf}_state.json"
    if path.exists():
        raise SystemExit(f"{path.name} ya existe: la seleccion en train de {tf.upper()} ya se corrio (para repetirla, borrar el estado a mano y anotar la razon).")
    base = load_params(tf)
    win = (U.ENTRY_FROM, U.TRAIN_END)
    ev = Evaluator(tf, list(U.TRAIN), workers)
    tests, report, survivors = 0, [], {}
    try:
        ctrl_tr = window(ev.run([base], list(U.TRAIN))[0], *win)
        tests += 1
        c = summarize(ctrl_tr)
        report.append(f"Control (set vigente sin variante), train: n={c['n']}, exp={c['exp']:.3f}R, recortada={c['exp_trim']:.3f}R, PF={c['pf']:.2f}.\n")
        for vid, (name, dims) in VARIANTS.items():
            grid = Grid(dims, dict(base))
            frames = ev.run(grid.combos(), list(U.TRAIN))
            tests += len(frames)
            df = score_grid(grid, frames, win, MIN_N_FINAL)
            df["gana_recortada"] = df["exp_trim"] - c["exp_trim"]
            bi = best_row(df)
            why = []
            if bi is None:
                why.append("ningun punto factible")
            else:
                row = df.loc[bi]
                if row["gana_recortada"] < MIN_GAIN:
                    why.append(f"recortada mejora {row['gana_recortada']:+.3f}R < {MIN_GAIN}R")
                if row["smooth"] <= c["exp_trim"]:
                    why.append(f"meseta suavizada {row['smooth']:.3f} <= control {c['exp_trim']:.3f}")
                if tf == "h4":
                    var_tr = window(frames[bi], *win)
                    wins = sum(year_exp(var_tr, y) > year_exp(ctrl_tr, y) for y in WF_YEARS)
                    if wins < WF_MIN_WINS:
                        why.append(f"mejora la expectativa en {wins} de {len(WF_YEARS)} anios (< {WF_MIN_WINS})")
            cols = [k for k in dims] + ["n", "exp", "exp_trim", "pf", "smooth", "feasible", "gana_recortada"]
            report.append(f"\n### {vid}: {name}\n\n" + md_table(df[cols]) +
                          f"\n**{'PASA a Z2' if not why else 'NO pasa'}**{'' if not why else ': ' + '; '.join(why)}.\n")
            if not why:
                survivors[vid] = {k: _py(df.loc[bi, k]) for k in dims}
    finally:
        ev.close()
    st = dict(tf=tf, tests=tests, control=_py(c), survivors=survivors, z2_looks={})
    path.write_text(json.dumps(_py(st), indent=1, ensure_ascii=False), encoding="utf-8")
    txt = (f"# Variantes {tf.upper()}: seleccion en train (generado por `python -m sqzlab.varsearch`)\n\n"
           f"Set base: `params/{tf}.json`. Train: monedas {', '.join(U.TRAIN)}, entradas {win[0].date()}..{win[1].date()}. "
           f"**Pruebas: {tests}** (1 control + puntos de grilla). Criterios fijados antes en PROTOCOLO.\n\n" + "".join(report) +
           f"\n**Pasan a Z2:** {', '.join(f'{v} {p}' for v, p in survivors.items()) or 'ninguna'}.\n")
    (RESULTS / f"varsearch_{tf}.md").write_text(txt, encoding="utf-8")
    print(txt)


def z2(tf: str, workers: int | None, reps: int) -> None:
    path = RESULTS / f"varsearch_{tf}_state.json"
    st = json.loads(path.read_text(encoding="utf-8"))
    todo = [v for v in st["survivors"] if str(v) not in st["z2_looks"]]
    if not todo:
        raise SystemExit("No hay variantes sobrevivientes sin mirar en Z2 (o ya se miraron todas: cada una se mira UNA sola vez).")
    base = load_params(tf)
    coins = list(U.fresh_group("z2"))
    wins = {s: (U.ENTRY_FROM, None) for s in coins}
    ev = Evaluator(tf, coins, workers)
    out = []
    try:
        for vid in todo:
            pt = st["survivors"][vid]
            ctrl, var = ev.run([base, {**base, **pt}], coins)
            ctrl, var = window(ctrl, U.ENTRY_FROM), window(var, U.ENTRY_FROM)
            sc, sv = summarize(ctrl), summarize(var)
            bl = random_baseline_for(tf, var, wins, f"z2:{vid}", reps)
            crit = criteria(sv, bl["p95"])
            beats = sv["exp"] > sc["exp"] and sv["exp_trim"] > sc["exp_trim"]
            wins_ = all(crit.values()) and beats
            st["z2_looks"][vid] = dict(wins=bool(wins_), n=sv["n"], exp=sv["exp"], exp_trim=sv["exp_trim"], control_exp=sc["exp"],
                                       control_exp_trim=sc["exp_trim"], point=pt)
            rows = pd.DataFrame([dict(set="control (sin variante)", **{k: sc[k] for k in ("n", "exp", "pf", "exp_ex_best", "exp_trim", "dd")}),
                                 dict(set=f"{vid} {pt}", **{k: sv[k] for k in ("n", "exp", "pf", "exp_ex_best", "exp_trim", "dd")})])
            out.append(f"\n### {vid} {pt} en Z2 ({', '.join(coins)})\n\n" + md_table(rows) +
                       f"\nBaseline aleatorio p95 = {bl['p95']:.3f}R. Criterios absolutos: " + "; ".join(f"{k}: {'SI' if x else 'NO'}" for k, x in crit.items()) +
                       f". Supera al control en exp y en recortada: {'SI' if beats else 'NO'}.\n**{'GANA' if wins_ else 'DESCARTADA'}.**\n")
    finally:
        ev.close()
        path.write_text(json.dumps(_py(st), indent=1, ensure_ascii=False), encoding="utf-8")
    head = (f"\n\n## Veredicto en Z2 (una sola mirada por variante; miradas de esta corrida: {len(todo)})\n\n"
            "Si se miran varias variantes en el mismo Z2 hay comparaciones multiples: una que gana por poco entre varias vale menos.\n")
    rp = RESULTS / f"varsearch_{tf}.md"
    rp.write_text(rp.read_text(encoding="utf-8") + head + "".join(out), encoding="utf-8")
    print(head + "".join(out))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", required=True, choices=["h4", "d1"])
    ap.add_argument("--stage", required=True, choices=["train", "z2"])
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--reps", type=int, default=1000)
    a = ap.parse_args()
    train(a.tf, a.workers) if a.stage == "train" else z2(a.tf, a.workers, a.reps)


if __name__ == "__main__":
    main()
