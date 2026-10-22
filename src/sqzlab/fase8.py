"""Fase 8: R1-fiel. Etapas (reglas en docs/PROTOCOLO.md, "Decisiones fijadas ANTES de la Fase 8"):

  python -m sqzlab.fase8 --stage data     informe de datos (deslistados, cortes, huecos, universo) -> results/fase8_data.md
  python -m sqzlab.fase8 --stage sanity   D1, costo base, SOLO 2018-01-01..2025-03-31 (no toca B): detecta bugs, no cambia reglas
  python -m sqzlab.fase8 --stage look     A y B (D1 y H4), 3 costos, referencias, veredicto. UNA SOLA VEZ (candado en el estado)

Cero optimizacion: una configuracion por TF; lo unico que varia es el costo.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import pf8
from . import r1fiel as R
from . import universe_dyn as UD
from .donchian import R1_DAYS, donchian_subtrades
from .donchian import vol_ann as vol_ann7
from .f8data import END, F8
from .pf7 import Rules, run_cartera
from .pf8 import A_START, B_START, PRE_B_END

ROOT = R.ROOT
RESULTS = ROOT / "results"
STATE = RESULTS / "fase8_state.json"
COSTS = R.params()["cost_per_side"]                       # base 0,15% (0,10 comision + 0,05 slippage); 0,10% solo comision; 0,25% estres
COST_ORDER = [("comision_sola", "0,10%"), ("base", "0,15% (base)"), ("estres", "0,25%")]
N_B_MIN = 30
END_DAY = END["1d"]


# ------------------------------------------------------------------------------------------------------------------
# Mundo: datos, universo, paneles
# ------------------------------------------------------------------------------------------------------------------
def load_world() -> dict:
    man = json.loads((F8 / "_manifest_1d.json").read_text(encoding="utf-8"))
    bases = [r["base"] for r in man["pares"] if r["ok"]]
    assets, excl, cuts = UD.load_assets_daily(bases)
    dates = pd.date_range("2017-08-01", END_DAY)
    uni = UD.build_universe(assets, dates)
    top = uni["top"]
    inwin = top.loc[A_START:END_DAY]
    ever = [i for i in top.columns if inwin[i].any()]
    first_day = inwin.index[inwin.any(axis=1)][0]
    return dict(man=man, bases=bases, assets=assets, excl=excl, cuts=cuts, uni=uni, top=top, ever=ever, first_day=first_day)


def make_panel(world: dict, tf: str, with_stops: bool = False) -> tuple[pf8.Panel, dict]:
    at = pf8.assets_for_tf(world["assets"], world["ever"], tf)
    return pf8.build_panel(at, world["top"], tf, with_stops), at


def slice_panel(p: pf8.Panel, end) -> pf8.Panel:
    m = p.times <= pd.Timestamp(end) + pd.Timedelta(hours=23, minutes=59)
    return pf8.Panel(p.tf, p.times[m], p.ids, p.bases, p.prices[m], p.act[m], p.vol[m], p.in_top[m], p.valid[m], p.force_zero[m],
                     None if p.stops is None else p.stops[:, m])


# ------------------------------------------------------------------------------------------------------------------
# Contraste: R1 de la Fase 7 sobre el mismo universo dinamico
# ------------------------------------------------------------------------------------------------------------------
def r1_fase7_curve(p: pf8.Panel, at: dict, cost_commission: float = 0.0010, slippage: float = 0.0005) -> dict:
    tf = p.tf
    end_bar = p.times[-1]
    rows, closes = [], {}
    for j, aid in enumerate(p.ids):
        a = at[aid]
        df = a.df
        t = pd.DatetimeIndex(df["time_utc"])
        c = df["close"].to_numpy(float)
        closes[aid] = (t.to_numpy(), c)
        sub = donchian_subtrades(df, tf, R1_DAYS, coin=aid)
        if sub.empty:
            continue
        v = vol_ann7(c, tf)
        dead = a.last < end_bar
        for r in sub.itertuples():
            pos = p.times.get_indexer([t[r.entry_i]])[0]
            if pos < 0 or not p.in_top[pos, j]:                      # solo se filtran las entradas al top 20 del dia
                continue
            is_open = bool(r.open) and not dead                      # deslistada: cierre forzado al ultimo cierre
            rows.append(dict(id=f"{aid}-{r.j}-{r.entry_i}", coin=aid, kind="E", side=1, entry_t=t[r.entry_i], exit_t=t[r.exit_i], entry_px=r.entry_px,
                             exit_px=r.exit_px, sd=max((r.entry_px - r.stop) / r.entry_px, 1e-6), w=r.w, vol=v[r.entry_i], open=is_open))
    tr = pd.DataFrame(rows)
    rules = Rules(mode="vol", max_pos=6, gross_cap=1.0, coin_cap=2.0, commission=cost_commission, slippage=slippage)
    res = run_cartera(tr, closes, p.times[0], p.times[-1], rules)
    tl = pd.DatetimeIndex(res["times"])
    return dict(daily=pf8.to_daily(tl, res["eq"]), n=int(res["trades"]["closed"].sum()), skipped=len(res["skipped"]))


# ------------------------------------------------------------------------------------------------------------------
# Corrida de una temporalidad: estrategia a 3 costos + referencias, metricas por ventana
# ------------------------------------------------------------------------------------------------------------------
def _clean(x):
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(float(x)) else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, pd.Timestamp):
        return str(x.date())
    return x


def window_metrics(p: pf8.Panel, res: dict, w0, w1) -> dict:
    daily = pf8.to_daily(p.times, res["eq"])
    st = pf8.stats(daily, w0, w1)
    if math.isfinite(st["cagr"]):
        st.update(pf8.cagr_without_best_month(daily, w0, w1))
    contrib = pf8.coin_contrib(p, res, w0, w1)
    tot = float(contrib.sum())
    top_coin = contrib.idxmax() if len(contrib) else ""
    d = p.times.normalize()
    m = (d >= pd.Timestamp(w0)) & (d <= pd.Timestamp(w1))
    years = max(st.get("days", 1), 1) / 365.0
    st.update(pf8.episode_counts(p, res, w0, w1))
    st.update(pf8.episode_detail(p, res, w0, w1))
    st.update(pnl_total=tot, top_coin=str(top_coin), top_share=float(contrib.max() / tot) if tot > 0 else float("nan"),
              gross_prom=float(res["gross"][m].mean()), gross_max=float(res["gross"][m].max()),
              turnover_anual=float(res["traded"][m].sum() / np.mean(res["eq"][m]) / years), costos_pct_equity=float(res["costs"][m].sum() / np.mean(res["eq"][m])))
    return st


def run_tf(world: dict, tf: str, end_cut=None, costs: list[str] | None = None, with_refs: bool = True) -> dict:
    p, at = make_panel(world, tf)
    if end_cut is not None:
        p = slice_panel(p, end_cut)
    last_day = p.times[-1].normalize()
    s0 = world["first_day"]
    wins = {"A": (s0, last_day)} if end_cut is not None else {"A": (s0, last_day), "B": (B_START, last_day)}
    tg = pf8.r1_targets(p)
    out = dict(tf=tf, windows={k: [str(v[0].date()), str(v[1].date())] for k, v in wins.items()}, strategy={}, refs={}, meta={})
    dm = (p.times.normalize() >= s0)
    chg = np.abs(np.diff(p.in_top[dm].astype(int), axis=0)).sum(axis=1) if dm.sum() > 1 else np.zeros(1)
    out["meta"] = dict(n_assets=len(p.ids), bars=len(p.times), universo_prom=float(p.in_top[dm].sum(axis=1).mean()),
                       universo_cambios_por_vela=float(chg.mean()),
                       escala_dias_con_tope=int(np.unique(p.times.normalize()[tg["scale"] < 1]).size), gross_raw_max=float(tg["raw"].sum(axis=1).max()))
    runs = {}
    for name in (costs or [c for c, _ in COST_ORDER]):
        res = pf8.run_weights(p.prices, tg["w"], COSTS[name])
        runs[name] = res
        out["strategy"][name] = {k: window_metrics(p, res, *w) for k, w in wins.items()}
        d_eq = np.diff(np.r_[pf8.INITIAL, res["eq"]])
        out["meta"][f"identidad_contable_{name}"] = float(np.abs(res["pnl"].sum(axis=1) - d_eq).max())
    ep = runs["base" if "base" in runs else next(iter(runs))]["episodes"]
    forced = ep[ep["closed"] & p.force_zero[ep["i1"].to_numpy(), ep["m"].to_numpy()]] if len(ep) else ep
    out["meta"]["cierres_forzados_con_posicion"] = [(p.ids[int(r.m)], str(p.times[int(r.i1)].date())) for r in forced.itertuples()]
    out["meta"]["n_deslistadas_o_cortadas_en_panel"] = int(p.force_zero.any(axis=0).sum())
    if with_refs:
        btc_j = p.ids.index("BTC")
        btc_daily = pf8.to_daily(p.times, np.where(np.isfinite(p.prices[:, btc_j]), p.prices[:, btc_j], np.nan))
        out["refs"]["btc"] = {k: pf8.stats(btc_daily, *w) for k, w in wins.items()}
        ew = pf8.run_weights(p.prices, pf8.ew_targets(p), COSTS["base"])
        out["refs"]["ew"] = {k: window_metrics(p, ew, *w) for k, w in wins.items()}
        if end_cut is None:
            r7 = r1_fase7_curve(p, at)
            out["refs"]["r1_fase7"] = {k: pf8.stats(r7["daily"], *w) for k, w in wins.items()}
            out["refs"]["r1_fase7"]["n_cerrados"] = r7["n"]
    return out


# ------------------------------------------------------------------------------------------------------------------
# Veredicto D1
# ------------------------------------------------------------------------------------------------------------------
def checks(strat: dict, btc: dict, window: str) -> list[tuple[str, bool, str]]:
    s, b = strat, btc
    fin = lambda x: x is not None and isinstance(x, float) and math.isfinite(x)
    c = [("1. CAGR neto > 0", fin(s["cagr"]) and s["cagr"] > 0, f"{s['cagr']:.2%}"),
         ("2. Sharpe > Sharpe buy&hold BTC", fin(s["sharpe"]) and s["sharpe"] > b["sharpe"], f"{s['sharpe']:.2f} vs {b['sharpe']:.2f}"),
         ("3. DD max < DD max buy&hold BTC", fin(s["dd"]) and s["dd"] < b["dd"], f"{s['dd']:.1%} vs {b['dd']:.1%}"),
         ("4. Ninguna moneda aporta > 50% de la ganancia", (not fin(s["top_share"])) or s["top_share"] <= 0.5,
          f"{s['top_coin']} {s['top_share']:.0%}" if fin(s["top_share"]) else f"ganancia total <= 0 ({s['top_coin']})")]
    if window == "A":
        c.append(("5. (solo A) CAGR > 0 sin el mejor mes", fin(s.get("cagr_sin_mejor_mes")) and s["cagr_sin_mejor_mes"] > 0, f"{s.get('cagr_sin_mejor_mes', float('nan')):.2%}"))
    return c


def verdict(d1: dict) -> dict:
    sb, btc = d1["strategy"]["base"], d1["refs"]["btc"]
    cA, cB = checks(sb["A"], btc["A"], "A"), checks(sb["B"], btc["B"], "B")
    nB = sb["B"]["n_cerrados_salida"]
    if nB < N_B_MIN:
        v = "SIN MUESTRA EN B"
    elif all(x[1] for x in cA) and all(x[1] for x in cB):
        v = "SIRVE"
    else:
        v = "NO SIRVE"
    return dict(veredicto=v, n_B=nB, A=cA, B=cB)


# ------------------------------------------------------------------------------------------------------------------
# Informes
# ------------------------------------------------------------------------------------------------------------------
def pct(x, d=1):
    return "-" if x is None or not math.isfinite(x) else f"{x*100:.{d}f}%"


def num(x, d=2):
    return "-" if x is None or not math.isfinite(x) else f"{x:.{d}f}"


def table(tf_res: dict, w: str) -> str:
    rows = ["| config | CAGR | Sharpe | DD max | Calmar | retorno total | n cerradas (salida en ventana) | mejor moneda (% de la ganancia) | CAGR sin mejor mes | exposicion bruta prom. | rotacion anual |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, lab in COST_ORDER:
        s = tf_res["strategy"][name][w]
        rows.append(f"| R1-fiel, costo {lab} por lado | {pct(s['cagr'])} | {num(s['sharpe'])} | {pct(s['dd'])} | {num(s['calmar'])} | {pct(s['total'])} | {s['n_cerrados_salida']} | "
                    f"{s['top_coin']} {pct(s['top_share'], 0)} | {pct(s.get('cagr_sin_mejor_mes'))} | {num(s['gross_prom'])}x | {num(s['turnover_anual'], 1)}x |")
    b = tf_res["refs"]["btc"][w]
    rows.append(f"| buy&hold BTC (sin costos) | {pct(b['cagr'])} | {num(b['sharpe'])} | {pct(b['dd'])} | {num(b['calmar'])} | {pct(b['total'])} | - | - | - | 1.00x | - |")
    e = tf_res["refs"]["ew"][w]
    rows.append(f"| equiponderado top 20 dinamico (costo base) | {pct(e['cagr'])} | {num(e['sharpe'])} | {pct(e['dd'])} | {num(e['calmar'])} | {pct(e['total'])} | - | "
                f"{e['top_coin']} {pct(e['top_share'], 0)} | {pct(e.get('cagr_sin_mejor_mes'))} | {num(e['gross_prom'])}x | {num(e['turnover_anual'], 1)}x |")
    r = tf_res["refs"]["r1_fase7"][w]
    rows.append(f"| R1 de la Fase 7 (cupo 6, bruto 1,0x, tamano fijo; costo base) | {pct(r['cagr'])} | {num(r['sharpe'])} | {pct(r['dd'])} | {num(r['calmar'])} | {pct(r['total'])} | "
                f"{tf_res['refs']['r1_fase7']['n_cerrados']} (toda la corrida) | - | - | - | - |")
    return "\n".join(rows)


RULES_MD = """## Reglas (fijadas ANTES en `docs/PROTOCOLO.md`, "Decisiones fijadas ANTES de la Fase 8")
- **Estrategia:** solo largo, ensamble de Donchian con N = 5, 10, 20, 30, 60, 90, 150, 250, 360 dias. Entra al cierre si `close` > maximo de los N cierres previos; trailing stop = max(stop de ayer, (max+min)/2 de los N cierres previos); sale al cierre si `close` < stop. Peso = (sub-senales abiertas/9) x min(2, 0,25/vol 90d anualizada); si el bruto pasa de 2,0 se escala todo a 2,0. Rebalanceo diario solo si el peso efectivo se aparta > 20% relativo del objetivo (entradas y salidas siempre).
- **Universo dinamico:** por dia t, con datos <= t-1: >= 365 dias de historia y mediana del volumen USD de 30 dias >= 2 M; top 20 por esa mediana (empates alfabeticos). Sale del top 20 -> se vende al cierre. Deslistada o cortada -> cierre forzado en su ultima vela.
- **Costos:** por lado sobre el nocional operado: 0,15% base (0,10 comision + 0,05 slippage); tambien 0,10% y 0,25%. El veredicto usa el base. **H4** = conversion declarada (N x 6, vol 540 velas, sqrt(6x365)), sin veredicto.
- **Ventanas:** A = 2018-01-01 a `END` (inicio efectivo = primer dia con una moneda elegible); B = 2025-04-01 a `END` (juez; tramo de la misma corrida continua, con la equity re-basada). SIRVE (D1) = en A y en B: CAGR > 0, Sharpe > BTC, DD < BTC, ninguna moneda > 50% de la ganancia; en A ademas CAGR > 0 sin el mejor mes. n_B < 30 operaciones cerradas (episodios por moneda con salida en B) = SIN MUESTRA EN B.
- **Cero optimizacion:** 1 configuracion por TF, 0 grillas. B se miro **una sola vez** (candado en `results/fase8_state.json`).
"""

DIFF_MD = """## Diferencias con el paper (Zarattini, Pagani, Barbon 2025) — TODO "no verificado": el texto del paper no se pudo bajar (SSRN 403, abarbon.com 502)
Las reglas salen del resumen de `docs/FASE8_PLAN.md` (CXO Advisory). Diferencias o supuestos nuestros que pueden no coincidir con el paper:
- **Tope bruto 2,0 de la cartera** (escalado de todos los pesos): el plan describe un tope de 200%; el paper puede aplicarlo por posicion. Supuesto nuestro.
- **Banda de rebalanceo de 20%**: supuesto nuestro anti-costos (el paper re-dimensiona a diario).
- **Ventana del stop = N cierres previos** (misma convencion que la entrada) y ejecucion **al cierre de la senal**: optimista; el paper puede ejecutar a la apertura siguiente.
- **Universo:** regla del plan (>= 365 dias, mediana 30d >= 2 M USD, top 20), sobre Binance spot USDT; el paper usa su propia fuente y definiciones.
- **Sin costo de financiamiento ni de prestamo** con bruto > 1 (optimista). Costos 0,15% por lado, mayores que muchos supuestos de la literatura.
- **Cortes de serie** (|salto| > 20x en un dia) y **cierre forzado de deslistadas al ultimo cierre**: ambos optimistas si hubo un crash real sin salida posible.
- **H4** es una conversion mecanica (N x 6), no algo probado por el paper.
"""


REVIEW_MD = """## Revision independiente previa a B (subagente que no vio el trabajo; hecha ANTES de `--stage look`)
Resultado: **sin hallazgos criticos**. Reimplemento por su cuenta el universo (coincide en 9 fechas), la senal Donchian/trailing, la vol, el motor de cartera (diferencia relativa de equity 7e-15), los costos (identidad contable 3,5e-10 USD), el CAGR/Sharpe/DD del buy&hold, y corrio todo el camino de `look` sobre un pseudo-B sin errores. Tests: 115 verdes antes de sus correcciones.

| # | Gravedad | Hallazgo | Que se hizo |
|---|---|---|---|
| 1 | MEDIO (solo bot) | si `update_all` falla para una moneda TRADING, sale del top y el bot leeria objetivo 0 (vender por un error de red) | `signals --strategy r1fiel` aborta con "DATOS INCOMPLETOS" si una moneda TRADING del top de ayer no tiene la vela de hoy |
| 2 | MENOR | `update_all` escribia en los mismos CSV que el backtest | el bot usa `data/f8_live/` (copia aparte) |
| 3 | MENOR | el criterio 4 agrupa por base: LUNA clasica y LUNA 2.0 (`LUNA#3`) cuentan como una sola moneda | anotado: en A casi no mueve nada y en B no hay cortes |
| 4 | INFO | el tope bruto 2,0 es sobre el objetivo; con la banda del 20% la exposicion efectiva llega a ~2,2x (antes de B: 2,23x) | anotado; `gross_max` se informa en cada tabla |
| 5-6 | MENOR | rotulo "dias con tope" contaba velas en H4; ventana hardcodeada en `sanity` | corregidos |
| 7-8 | MENOR | tests faltantes (precedencia del veredicto, bordes de ventana, `to_daily` H4, microsegundos, E<=0, BASE#2) | agregados |
| 9 | INFO | cortes de serie: efecto nulo en A (LUNA no tenia posicion al crash) y ningun corte cae en B; 5 cierres forzados con posicion antes de B son migraciones/renombres (BCHABC, NPXS, RNDR, MATIC, BNX#2) | anotado |
| 10 | INFO | renombres (MATIC>POL, EOS>A, MKR>SKY, FTM>S, RNDR>RENDER) se tratan como venta + moneda nueva que necesita 365 dias: sesga la cobertura del universo, no los precios | anotado (supuesto declarado) |
| 12 | INFO | n mide en parte el recambio del universo (30% de los episodios duran <= 2 velas, 18% salen por caer del top 20) | se informa al lado el n que sale por universo y la mediana de duracion |
| 15 | INFO | 2018-2019: solo 2 a 10 monedas elegibles (BTC/ETH/BNB sobre todo); recien en marzo 2020 hay 20 | anotado |

**No verificado:** compilacion del Pine (se prueba en TradingView mas abajo); texto del paper; pares que Binance haya borrado de ambas fuentes.
"""


def write_report(state: dict) -> None:
    L = state["look"]["results"]
    d1, h4 = L["d1"], L["h4"]
    v = state["look"]["veredicto"]
    wA, wB = d1["windows"]["A"], d1["windows"]["B"]
    out = [f"# Fase 8: R1-fiel (generado por `python -m sqzlab.fase8 --stage look`, {state['look']['when']})",
           f"> No es asesoria financiera. **Veredicto D1: {v['veredicto']}** (n_B = {v['n_B']} operaciones cerradas con salida en B; minimo {N_B_MIN}).",
           "", RULES_MD, DIFF_MD]
    data_md = RESULTS / "fase8_data.md"
    if data_md.exists():
        out.append("## Datos (resumen; detalle en `results/fase8_data.md`)\n" + "\n".join(data_md.read_text(encoding="utf-8").splitlines()[:12]) + "\n")
    for tf, lab, tfr in (("d1", "D1 (la estrategia)", d1), ("h4", "H4 (conversion declarada, secundaria)", h4)):
        out.append(f"## {lab}")
        for w, name in (("A", "A (informativa)"), ("B", "B (juez)")):
            a, b = tfr["windows"][w]
            sb = tfr["strategy"]["base"][w]
            det = (f"Detalle (R1-fiel, costo base): {sb['n_cerrados_salida']} operaciones cerradas con salida en la ventana, de las cuales **{sb['n_salida_por_universo']} salen porque la moneda cae del top 20** "
                   f"(o cierre forzado) y no por la senal; mediana de duracion {num(sb['dur_mediana_dias'], 1)} dias; n con entrada y salida en la ventana: {sb['n_cerrados_entrada']}; "
                   f"exposicion bruta maxima {num(sb['gross_max'])}x; costos pagados = {pct(sb['costos_pct_equity'], 0)} de la equity media.")
            out.append(f"### Ventana {name}: {a} a {b}\n\n{table(tfr, w)}\n\n{det}\n")
        m = tfr["meta"]
        out.append(f"- Monedas en el panel: {m['n_assets']}; tamano medio del universo: {m['universo_prom']:.1f}; dias con tope bruto activo (escala < 1): {m['escala_dias_con_tope']}; bruto crudo maximo: {m['gross_raw_max']:.2f}x; "
                   f"cambios de membresia del top 20 por vela: {m['universo_cambios_por_vela']:.2f}; monedas deslistadas/cortadas en el panel: {m['n_deslistadas_o_cortadas_en_panel']}; cierres forzados CON posicion: {len(m['cierres_forzados_con_posicion'])} "
                   f"{m['cierres_forzados_con_posicion'][:12]}.\n- Chequeo de identidad contable (max |sum pnl - delta equity|): {max(m[k] for k in m if k.startswith('identidad')):.2e} USD.\n")
    out.append("## Criterios SIRVE (D1, costo base)\n")
    for w, lst in (("A", v["A"]), ("B", v["B"])):
        out.append(f"**Ventana {w}**\n\n| criterio | cumple | valor |\n|---|---|---|")
        out += [f"| {n} | {'SI' if ok else 'NO'} | {val} |" for n, ok, val in lst]
        out.append("")
    out.append(f"**Veredicto D1: {v['veredicto']}.**\n")
    out.append(REVIEW_MD)
    out.append(state["look"].get("notes", ""))
    (RESULTS / "fase8.md").write_text("\n".join(out), encoding="utf-8")


def stage_data() -> None:
    w = load_world()
    man, ex = w["man"], None
    pares = pd.DataFrame(man["pares"])
    pares["last"] = pd.to_datetime(pares["last"])
    from .f8data import exchange_usdt
    ex = exchange_usdt()
    pares["status"] = pares["base"].map(ex).fillna("fuera de exchangeInfo")
    ended = pares[pares["last"] < END_DAY]
    miss = pares[pares["missing"] > 0]
    top = w["top"].loc[A_START:END_DAY]
    n = top.sum(axis=1)
    first20 = n.index[n >= 20][0]
    ever_bases = sorted({i.split("#")[0] for i in w["ever"]})
    delisted_in_top = sorted({i for i in w["ever"] if w["assets"][i].last < END_DAY})
    import collections
    lines = [
        "# Fase 8: datos (generado por `python -m sqzlab.fase8 --stage data`)",
        f"- Pares *USDT bajados (1d): **{man['descargados']}** (API: {int((pares.source == 'api').sum())}, data.binance.vision: {int((pares.source == 'vision').sum())}). `data.binance.vision` lista {man['n_vision']} simbolos USDT y `exchangeInfo` {man['n_exchange']}.",
        f"- **Deslistados incluidos: SI.** {int((pares.status == 'BREAK').sum())} pares con status BREAK (deslistados, historia completa por API) + {int((pares.status == 'fuera de exchangeInfo').sum())} fuera de exchangeInfo (NBT, via vision) = {len(ended)} pares con ultima vela anterior a END ({END_DAY.date()}). No se puede garantizar que falte alguno que Binance haya borrado de ambas fuentes: sesgo de supervivencia residual no medible.",
        f"- Velas diarias faltantes (rellenadas con el ultimo cierre y volumen 0): {int(pares['missing'].sum())} en {len(miss)} pares (maximo {int(pares['missing'].max())} en un par).",
        f"- Excluidos por nombre/peg: {len(w['excl'])} ({dict(collections.Counter(w['excl'].values()))}). Activos tras cortes: {len(w['assets'])}.",
        f"- Cortes de serie por salto > 20x en un dia (excluyendo apalancados): {[(c['base'], c['date'], round(c['ratio'], 6)) for c in w['cuts'] if c['base'] not in w['excl']]}.",
        f"- Universo dinamico: primer dia con al menos una moneda elegible **{w['first_day'].date()}**; primer dia con 20 elegibles {first20.date()}; tamano medio del universo {n[n > 0].mean():.1f}. Bases que alguna vez estuvieron en el top 20: {len(ever_bases)}; de ellas, activos deslistados o cortados antes de END: {len(delisted_in_top)} ({delisted_in_top[:40]}).",
        f"- H4: se bajaron los pares 4h de las {len(ever_bases)} bases que alguna vez estuvieron en el top 20 diario (regla mecanica sobre volumen).",
        "",
    ]
    (RESULTS / "fase8_data.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def stage_sanity() -> None:
    w = load_world()
    out = run_tf(w, "d1", end_cut=PRE_B_END, costs=["base"], with_refs=True)
    s = out["strategy"]["base"]["A"]
    print(json.dumps(_clean(out), indent=1, ensure_ascii=False))
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    st["sanity"] = dict(when=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), window=f"{w['first_day'].date()}..{PRE_B_END.date()} (no toca B)", result=_clean(out))
    STATE.write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf-8")


def stage_look() -> None:
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    if "look" in st:
        raise SystemExit("B ya se miro (results/fase8_state.json['look']): no se repite. No existe --force.")
    w = load_world()
    raw = {"d1": run_tf(w, "d1"), "h4": run_tf(w, "h4")}
    v = _clean(verdict(raw["d1"]))                    # el veredicto se calcula sobre los numeros crudos (antes de limpiar NaN)
    res = _clean(raw)
    st["look"] = dict(when=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), results=res, veredicto=v, notes="")
    STATE.write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf-8")
    write_report(st)
    print("veredicto D1:", v["veredicto"], "| n_B =", v["n_B"])


def stage_report() -> None:
    st = json.loads(STATE.read_text(encoding="utf-8"))
    write_report(st)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["data", "sanity", "look", "report"], required=True)
    a = ap.parse_args()
    {"data": stage_data, "sanity": stage_sanity, "look": stage_look, "report": stage_report}[a.stage]()


if __name__ == "__main__":
    main()
