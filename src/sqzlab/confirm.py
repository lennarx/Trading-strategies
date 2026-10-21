"""Fase 6.1: confirmacion de los sets actuales en monedas que el optimizador nunca vio (grupo Z1; Z2 esta reservado).

Uso:  python -m sqzlab.confirm --tf h4|d1|w1 --group z1 [--workers 16] [--reps 1000] [--force]
Corre `params/<tf>.json` (set vigente) y la vara (v2 sin optimizar) en las monedas del grupo, mide en R neto con los
mismos criterios que la etapa 5 del optimizador y los compara con el baseline aleatorio. NO toca ningun parametro:
el veredicto es "CONFIRMA", "NO CONFIRMA" o "SIN MUESTRA". Se mira UNA sola vez por (tf, grupo): el estado queda en
results/confirm_<tf>_<grupo>_state.json y repetirlo exige --force (queda anotado). Las decisiones estan fijadas en
docs/PROTOCOLO.md ("Decisiones fijadas ANTES de la Fase 6").
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from . import universe as U
from .genpine import load_params, pine_defaults, read_ref
from .metrics import breakdown, summarize, window
from .optimize import MIN_N_FINAL, OOS_MIN_EXP, RESULTS, Evaluator, _py, diff_vs_v2, md_table, random_baseline_for

SUMMARY_KEYS = ("n", "exp", "pf", "win", "dd", "total", "exp_ex_best", "exp_trim", "med_coin")


def criteria(sm: dict, base_p95: float) -> dict[str, bool]:
    """Mismos criterios de escritura de `params/` (PROTOCOLO, 'Se escribe params solo si'), sobre el agregado del grupo."""
    return {"expectativa > 0,2R": sm["exp"] > OOS_MIN_EXP, "expectativa > p95 del baseline": sm["exp"] > base_p95,
            f"n >= {MIN_N_FINAL}": sm["n"] >= MIN_N_FINAL, "sin el mejor trade > 0": sm["exp_ex_best"] > 0,
            "expectativa recortada (sin 2% mejores) > 0": sm["exp_trim"] > 0}


def verdict(sm: dict, crit: dict[str, bool]) -> str:
    if sm["n"] < MIN_N_FINAL:
        return f"SIN MUESTRA (n={sm['n']} < {MIN_N_FINAL}): ni confirma ni desmiente"
    return "CONFIRMA" if all(crit.values()) else "NO CONFIRMA"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", required=True, choices=["h4", "d1", "w1"])
    ap.add_argument("--group", required=True, choices=["z1", "z2"])
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--force", action="store_true", help="repetir la mirada (queda anotado)")
    ap.add_argument("--dry-run", nargs="*", metavar="MONEDA", default=None,
                    help="prueba de humo con esas monedas (ej. BTC ETH): imprime, no escribe informe ni estado, no gasta la mirada")
    a = ap.parse_args()
    if a.group == "z2":
        raise SystemExit("Z2 esta reservado para el veredicto final de las variantes de la 6.4 (PROTOCOLO): no se usa con confirm.")
    state_path = RESULTS / f"confirm_{a.tf}_{a.group}_state.json"
    st = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else dict(looks=0)
    dry = a.dry_run is not None
    if st["looks"] >= 1 and not a.force and not dry:
        raise SystemExit(f"{a.tf.upper()} {a.group.upper()} ya se miro una vez ({state_path.name}). Repetirlo invalida la prueba; "
                         "si igual hace falta, --force (queda anotado).")
    st["looks"] += 1

    coins = list(a.dry_run) if dry else list(U.fresh_group(a.group))
    params = load_params(a.tf)
    wins = {s: (U.ENTRY_FROM, None) for s in coins}
    ev = Evaluator(a.tf, coins, a.workers)
    try:
        cur, ref = ev.run([params, {}], coins)
    finally:
        ev.close()

    def groups(allt: pd.DataFrame) -> dict[str, pd.DataFrame]:
        full = window(allt, U.ENTRY_FROM)
        return {f"{a.group.upper()} todo el historial": full, f"{a.group.upper()} 2024-hoy": window(full, U.TEST_FROM)}

    def table(allt: pd.DataFrame, tag: str) -> tuple[pd.DataFrame, dict]:
        rows, out = [], {}
        for name, tr in groups(allt).items():
            sm = summarize(tr)
            bl = random_baseline_for(a.tf, tr, wins, f"confirm{tag}:{name}", a.reps)
            rows.append(dict(grupo=name, **{k: sm[k] for k in SUMMARY_KEYS}, base_p50=bl["p50"], base_p95=bl["p95"]))
            out[name] = (sm, bl)
        return pd.DataFrame(rows), out

    df, res = table(cur, "")
    dfr, _ = table(ref, "ref")
    main_name = f"{a.group.upper()} todo el historial"
    sm, bl = res[main_name]
    crit = criteria(sm, bl["p95"])
    v = verdict(sm, crit)
    cur_full = groups(cur)[main_name]
    yr = cur_full.assign(anio=cur_full["entry_t"].dt.year).groupby("anio")["R"].agg(n="count", exp="mean", total="sum").reset_index()
    txt = (f"# Confirmacion {a.tf.upper()} en {a.group.upper()} (generado por `python -m sqzlab.confirm`)\n\n"
           f"- **Veredicto: {v}.** Sin tocar ningun parametro: es solo \"confirma / no confirma\".\n"
           f"- Monedas ({len(coins)}): {', '.join(coins)}. Datos hasta {U.DATA_END[U.TF_CODE[a.tf]]}.\n"
           f"- Set evaluado: `params/{a.tf}.json`; difiere de la v2 en: "
           f"{', '.join(f'{k}={v}' for k, _, v in diff_vs_v2(params, pine_defaults(read_ref()))) or 'nada (= v2)'}\n"
           "- Salvedad: monedas nuevas pero **en el mismo periodo** que las de train; no es un OOS en el tiempo (eso es `forward`).\n"
           f"- Criterios (PROTOCOLO): " + "; ".join(f"{k}: {'SI' if x else 'NO'}" for k, x in crit.items()) + ".\n\n"
           "## Set vigente\n\n" + md_table(df) +
           "\n## Vara: v2 sin optimizar (mismas monedas; solo comparacion)\n\n" + md_table(dfr) +
           "\n## Por moneda (set vigente)\n\n" + md_table(breakdown(cur_full, "coin")) +
           "\n## Por senal y lado (set vigente)\n\n" + md_table(breakdown(cur_full, ["kind", "side"])) +
           "\n## Por anio (set vigente)\n\n" + md_table(yr))
    if dry:
        print(txt)
        return
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"confirm_{a.tf}_{a.group}.md").write_text(txt + "\n", encoding="utf-8")
    st.update(verdict=v, n=sm["n"], exp=sm["exp"], exp_trim=sm["exp_trim"], pf=sm["pf"], coins=coins, crit=crit)
    state_path.write_text(json.dumps(_py(st), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"[{a.tf} {a.group}] {v}: n={sm['n']}, exp={sm['exp']:.3f}R, PF={sm['pf']:.2f}, recortada={sm['exp_trim']:.3f}R, "
          f"baseline p95={bl['p95']:.3f}R")


if __name__ == "__main__":
    main()
