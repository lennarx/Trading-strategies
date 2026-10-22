"""Arma results/fase7.md a partir del estado y los CSV que dejan las etapas de `sqzlab.fase7` (solo formato: no calcula nada nuevo).

Uso:  python -m sqzlab.fase7_report
Los hallazgos de la revision independiente van en results/fase7_review.md (si existe se incluye textual).
"""
from __future__ import annotations

import json

import pandas as pd

from .optimize import RESULTS, md_table

TFS = ["h4", "d1", "w1"]
GROUPS = {"h4": ["z2", "z3"], "d1": ["z2", "z3"], "w1": ["pool"]}
PRIOR_TESTS = {"h4": 366, "d1": 627, "w1": 1}      # HANDOFF: Fase 4 + 6.4 (H4 356+10, D1 617+10, W1 1)
SHOW = ["config", "n", "n_sub", "R_medio", "CAGR", "DD", "Calmar", "CAGR_cerrada", "DD_cerrada", "CAGR_sin_mejor", "mediana_PnL_moneda", "conc_max",
        "BTC_CAGR", "BTC_DD", "BTC_Calmar", "EW_Calmar", "saltados", "criterios", "veredicto_grupo"]


NOTES = """
## Cómo leer esto (limitaciones, sin maquillaje)

- **Entregable:** como ningún candidato SQZ+RSI ni R1 cumplen, `params/{h4,d1,w1}.json` NO se tocaron (`git diff --stat params/` vacío) y el forward test sigue con su serie 1. El entregable es el set vigente y las herramientas nuevas (`sqzlab.signals`, `docs/BOT.md`); el Pine no cambia.
- **Z2 y Z3 se miraron una sola vez por TF** (H4 y D1: Z2 y Z3; W1: un pool de las 41 monedas no-train). Todas las pruebas de la Fase 7 y las miradas están contadas arriba (la grilla de train se corrió 2 veces: la 1.ª pasada archivada se descartó tras la revisión).
- **n** = trades A/B/C/D cerrados + episodios de E; `n_sub` cuenta cada sub-señal de E por separado.
- **Sesgo de supervivencia:** todos los grupos son monedas que HOY siguen listadas; eso favorece a la estrategia y al buy&hold por igual. Z3 incluye fan tokens de poco volumen donde 0,05% de slippage es optimista.
- **R1 no es una réplica exacta del paper:** el tamaño se fija en la entrada (no se re-dimensiona a diario) y se aplican cupo de 6 monedas y tope bruto 1,0x; el paper no se pudo bajar (SSRN 403, abarbon.com 502) y sus reglas están **no verificadas**. La "R1 informativa" sin cupo ni tope bruto apalanca hasta 2x por moneda con 24 a 41 monedas a la vez y por eso llega a −100%: es solo informativa y no decide nada.
- **Modo riesgo vs modo vol:** el modo riesgo no tiene tope bruto agregado y el modo vol sí (1,0x); CAGR y DD no son comparables entre modos, el Calmar es casi invariante a la escala.
- **Concentración por moneda:** con 6 monedas el criterio "ninguna moneda > 40% de la ganancia" es muy exigente y falla incluso en referencias razonables; se mantuvo tal cual estaba fijado (prohibido aflojarlo después de mirar).
- **2024-hoy** es el tramo donde las altcoins perdieron en general (buy&hold equiponderado negativo en todas las tablas): ahí ningún enfoque de esta fase gana plata de forma consistente.
"""


def tf_verdict(tf: str, st: dict) -> tuple[str, str]:
    """(veredicto del candidato SQZ+RSI, nota). SIRVE = CUMPLE en todos los grupos de validacion."""
    t = st.get(tf, {})
    looks = t.get("looks", {})
    if not looks:
        return "SIN MIRAR", "no se hizo la mirada a Z2/Z3"
    cand = t["train"]["candidato"]
    if cand is None:
        r0 = [looks[g]["veredictos"]["R0"]["veredicto"] for g in GROUPS[tf] if g in looks]
        if t["train"]["max_n"] < 100 or "SIN MUESTRA" in r0:
            return "SIN MUESTRA", ("sin candidato: el set vigente (R0) tiene n < 100 en la validacion y los puntos con E que llegan a n >= 100 "
                                   "fallan la concentracion por moneda en train")
        return "NO SIRVE", "ningun punto de la grilla cumplio las condiciones 3.1.3 en train"
    vs = [looks[g]["veredictos"]["candidato"]["veredicto"] for g in GROUPS[tf] if g in looks]
    if any(v == "SIN MUESTRA" for v in vs):
        return "SIN MUESTRA", "n < 100 trades en algun grupo de validacion"
    return ("SIRVE", "cumple los criterios en todos los grupos") if all(v == "CUMPLE" for v in vs) else ("NO SIRVE", "falla algun criterio en algun grupo")


def r1_ok(tf: str, st: dict) -> bool:
    looks = st.get(tf, {}).get("looks", {})
    return bool(looks) and all(looks[g]["veredictos"]["R1"]["veredicto"] == "CUMPLE" for g in GROUPS[tf] if g in looks)


def main() -> None:
    st = json.loads((RESULTS / "fase7_state.json").read_text(encoding="utf-8"))
    out = ["# Fase 7: que la estrategia SIRVA (generado por `python -m sqzlab.fase7_report`)\n",
           "Reglas fijadas ANTES en `docs/PROTOCOLO.md` (\"Decisiones fijadas ANTES de la Fase 7\"). No es asesoria financiera. "
           "Las reglas del ensamble de Donchian salen del resumen del plan: el paper (Zarattini, Pagani, Barbon 2025) **no se pudo bajar** "
           "(SSRN 403, abarbon.com 502) y por eso esta **no verificado** contra el texto.\n"]
    rows, total_new = [], 0
    for tf in TFS:
        v, note = tf_verdict(tf, st)
        t = st.get(tf, {})
        pruebas = t.get("train", {}).get("pruebas", 0)
        total_new += pruebas
        cand = t.get("train", {}).get("candidato")
        rows.append(dict(TF=tf.upper(), veredicto=v, nota=note, candidato=("sin candidato" if not cand else
                                                                          f"P1={cand['p1']} P2={'E' if cand['p2'] else '-'} P3={cand['p3'] or 'EMA20'} P4={cand['p4'] or '-'} P5={cand['p5']}"),
                         R1_cumple_Z2_y_Z3=r1_ok(tf, st), pruebas_nuevas=pruebas, pruebas_acumuladas=PRIOR_TESTS[tf] + pruebas))
    out.append("## Veredicto por temporalidad\n\n" + md_table(pd.DataFrame(rows)) + "\n")
    out.append(f"Pruebas nuevas de la Fase 7: **{total_new}** (grilla + R0/R1 por TF; cada mirada a un grupo se cuenta aparte: "
               f"{sum(len(st.get(tf, {}).get('looks', {})) for tf in TFS)} miradas en total, maximo 1 por TF y grupo).\n")
    for tf in TFS:
        t = st.get(tf, {})
        if "train" not in t:
            continue
        out.append(f"\n## {tf.upper()}\n")
        tr = t["train"]
        out.append(f"- Train: monedas {', '.join(tr['coins'])}, tramo {tr['window'][0][:10]} a {tr['window'][1][:10]}. {tr['puntos']} puntos de grilla + 2 referencias = "
                   f"{tr['pruebas']} pruebas; factibles: {tr['factibles']}. Candidato elegido por meseta: "
                   f"{'ninguno' if not tr['candidato'] else tr['candidato']}.\n")
        from . import fase7 as F
        t0, t1 = pd.Timestamp(tr["window"][0]), pd.Timestamp(tr["window"][1])
        cf = [("candidato", F.Cfg(**tr["candidato"]))] if tr["candidato"] else []
        trows = [F._row(n + (f" [{c.label()}]" if n == "candidato" else ""), F.evaluate(tf, tr["coins"], t0, t1, c), with_crit=False)
                 for n, c in cf + [("R0", F.R0), ("R1", "R1")]]
        out.append("\nTrain (referencias recalculadas con el mismo codigo; buy&hold en el mismo tramo):\n\n"
                   + md_table(pd.DataFrame(trows)[["config", "n", "n_sub", "R_medio", "CAGR", "DD", "Calmar", "CAGR_sin_mejor", "mediana_PnL_moneda", "conc_max",
                                                    "BTC_CAGR", "BTC_DD", "BTC_Calmar", "EW_Calmar"]]) + "\n")
        g = pd.read_csv(RESULTS / f"fase7_{tf}_grid.csv")
        cols = ["config", "n", "R_medio", "CAGR", "DD", "Calmar", "CAGR_sin_mejor", "mediana_PnL_moneda", "conc_max", "factible", "meseta", "elegido"]
        out.append("\nTrain, top 10 por score de meseta (todas las filas en `results/fase7_%s_grid.csv`):\n\n" % tf
                   + md_table(g[g["meseta"].notna()].sort_values("meseta", ascending=False).head(10)[cols]) + "\n")
        for grp in GROUPS[tf]:
            p = RESULTS / f"fase7_{tf}_{grp}.csv"
            if not p.exists():
                continue
            d = pd.read_csv(p)
            lk = t["looks"][grp]
            out.append(f"\n### {grp.upper()} (una mirada; monedas: {', '.join(lk['coins'])}; tramo {lk['window'][0][:10]} a {lk['window'][1][:10]})\n")
            for tramo, dd in d.groupby("tramo", sort=False):
                cols_ok = [c for c in SHOW if c in dd.columns]
                out.append(f"\n**{tramo}**\n\n" + md_table(dd[cols_ok]) + "\n")
            ver = lk["veredictos"]
            if "candidato" in ver and "R1" in ver:
                out.append(f"\n- Candidato vs R1 (Calmar, todo el historial): {ver['candidato']['calmar']:.2f} vs {ver['R1']['calmar']:.2f} "
                           f"-> {'el candidato supera a R1' if ver['candidato']['calmar'] > ver['R1']['calmar'] else 'el candidato NO supera a R1'}.\n")
        pa = RESULTS / f"fase7_{tf}_allcoins.csv"
        if pa.exists():
            out.append("\n### 2024-hoy en todas las monedas (informativa; contaminada: incluye train, holdout, Z1, Z2 y Z3)\n\n" + md_table(pd.read_csv(pa)[
                [c for c in SHOW if c in pd.read_csv(pa).columns]]) + "\n")
    out.append(NOTES)
    bb = [tf.upper() for tf in TFS if tf_verdict(tf, st)[0] != "SIRVE" and r1_ok(tf, st)]
    out.append("\n## Plan B\n\n" + (f"R1 (Donchian ensamble) cumple los criterios en Z2 y Z3 en: {', '.join(bb)}. Segun lo fijado, el entregable seria el unificado "
                                    "con la senal E como motor principal.\n" if bb else "Ningun TF tiene R1 cumpliendo los criterios en todos sus grupos: no hay plan B que "
                                                                                      "entregar; se dice con numeros y se espera al usuario.\n"))
    rv = RESULTS / "fase7_review.md"
    if rv.exists():
        out.append("\n" + rv.read_text(encoding="utf-8"))
    (RESULTS / "fase7.md").write_text("".join(out), encoding="utf-8")
    print("".join(out)[:3000])


if __name__ == "__main__":
    main()
