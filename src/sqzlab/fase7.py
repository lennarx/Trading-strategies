"""Fase 7: "que la estrategia SIRVA". Palancas P1-P5, referencias R0/R1, grilla de train con score de meseta y mirada unica a Z2/Z3.

Todas las reglas estan fijadas en docs/PROTOCOLO.md ("Decisiones fijadas ANTES de la Fase 7"). Este modulo es la libreria; el CLI
(`python -m sqzlab.fase7 --stage train|look|report`) esta al final.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import universe as U
from .donchian import E_DAYS, R1_DAYS, donchian_subtrades, vol_ann
from .genpine import load_params
from .htf import HTF_OF, P1_DEFAULT_N, P4_N, htf_flags
from .indicators import compute
from .optimize import BASE
from .pf7 import Rules, buyhold_btc, buyhold_ew, curve_metrics, group_report, run_cartera
from .strategy import DEFAULTS, simulate

TRAIN_END = U.TRAIN_END
STEP = {"h4": pd.Timedelta(hours=4), "d1": pd.Timedelta(days=1), "w1": pd.Timedelta(days=7)}
MIN_N = 100
MAX_CONC = 0.40
CALMAR_CAP = 10.0
N_SEEDS = 9                  # prioridades de monedas sorteadas para el cupo (PROTOCOLO 5 ter); toda metrica = mediana de las 9


@dataclass(frozen=True)
class Cfg:
    p1: str = "normal"      # normal (cortos del set vigente) | off | bear
    p2: bool = False        # sub-senales E sumadas
    p3: int = 0             # 0 = salida EMA20; M = Donchian de M cierres previos para A y B
    p4: int = 0             # 0 = sin filtro; N = EMA(N) del TF mayor para largos
    p5: str = "risk"        # risk | vol

    def label(self) -> str:
        return f"P1={self.p1} P2={'E' if self.p2 else '-'} P3={self.p3 or 'EMA20'} P4={self.p4 or '-'} P5={self.p5}"


R0 = Cfg()
SHORT_KEYS = ("aShort", "bShort", "cShort", "dShort")


# ----------------------------------------------------------------------------------------------- datos por moneda
_COIN: dict = {}


def coin_data(tf: str, sym: str) -> dict:
    key = (tf, sym)
    if key not in _COIN:
        code = U.TF_CODE[tf]
        df = U.load_coin(sym, code)
        params = {**BASE, **load_params(tf)}
        ind = compute(df, {**DEFAULTS, **params})
        _COIN[key] = dict(df=df, params=params, ind=ind, vol=vol_ann(df["close"].to_numpy(float), tf), htf={}, sqz={}, e={})
    return _COIN[key]


def htf_for(tf: str, sym: str, n: int) -> dict:
    cd = coin_data(tf, sym)
    if n not in cd["htf"]:
        hdf = U.load_htf(sym, HTF_OF[tf])
        cd["htf"][n] = htf_flags(cd["df"]["time_utc"].to_numpy(), hdf, n)
    return cd["htf"][n]


def _rows(cd: dict, sym: str, trs: list, tf: str) -> pd.DataFrame:
    df, vol = cd["df"], cd["vol"]
    t = df["time_utc"].to_numpy()
    rows = []
    for tr in trs:
        rows.append((f"{sym}-{tr.kind}-{tr.entry_i}-{tr.exit_i}-{tr.side}", sym, tr.kind, tr.side, pd.Timestamp(t[tr.entry_i]),
                     pd.Timestamp(t[tr.exit_i]), tr.entry_px, tr.exit_px, abs(tr.entry_px - tr.stop) / tr.entry_px, 1.0,
                     vol[tr.entry_i], tr.exit_reason == "abierto"))
    return pd.DataFrame(rows, columns=TRADE_COLS)


TRADE_COLS = ["id", "coin", "kind", "side", "entry_t", "exit_t", "entry_px", "exit_px", "sd", "w", "vol", "open"]


def sqz_trades(tf: str, sym: str, cfg: Cfg) -> pd.DataFrame:
    """Trades A/B/C/D del set vigente con las palancas P1, P3 y P4 de `cfg` (P2 y P5 no cambian estos trades)."""
    cd = coin_data(tf, sym)
    key = (cfg.p1, cfg.p3, cfg.p4)
    if key in cd["sqz"]:
        return cd["sqz"][key]
    over = dict(cd["params"])
    if cfg.p1 == "off":
        over.update({k: False for k in SHORT_KEYS})
    htf = None
    n_bear = cfg.p4 or P1_DEFAULT_N.get(tf, 0)
    if cfg.p1 == "bear":
        over["shortHtf"] = True
    if cfg.p4:
        over["longHtf"] = True
    if cfg.p3:
        over["donchExit"] = cfg.p3
    if over.get("longHtf") or over.get("shortHtf"):
        zeros = np.zeros(len(cd["df"]), bool)
        htf = dict(bull=htf_for(tf, sym, cfg.p4)["bull"] if cfg.p4 else zeros,
                   bear=htf_for(tf, sym, n_bear)["bear"] if cfg.p1 == "bear" else zeros)
    res = simulate(cd["df"], ind=cd["ind"], htf=htf, **over)
    trs = list(res.trades) + ([res.open_trade] if res.open_trade is not None else [])
    cd["sqz"][key] = _rows(cd, sym, trs, tf)
    return cd["sqz"][key]


def e_trades(tf: str, sym: str, days: list[int]) -> pd.DataFrame:
    cd = coin_data(tf, sym)
    key = tuple(days)
    if key not in cd["e"]:
        sub = donchian_subtrades(cd["df"], tf, days, sym)
        t = cd["df"]["time_utc"].to_numpy()
        out = pd.DataFrame({
            "id": [f"{sym}-E{r.j}-{r.lb}-{r.entry_i}" for r in sub.itertuples()], "coin": sym, "kind": "E", "side": 1,
            "entry_t": [pd.Timestamp(t[i]) for i in sub["entry_i"]], "exit_t": [pd.Timestamp(t[i]) for i in sub["exit_i"]],
            "entry_px": sub["entry_px"].to_numpy(), "exit_px": sub["exit_px"].to_numpy(),
            "sd": ((sub["entry_px"] - sub["stop"]) / sub["entry_px"]).to_numpy(), "w": sub["w"].to_numpy(),
            "vol": cd["vol"][sub["entry_i"].to_numpy(int)] if len(sub) else np.array([]), "open": sub["open"].to_numpy()})
        cd["e"][key] = out[TRADE_COLS]
    return cd["e"][key]


def trades_for(tf: str, coins, cfg: Cfg | str) -> pd.DataFrame:
    """cfg: un Cfg (candidato o R0) o 'R1' (ensamble completo de 9 lookbacks, solo largo)."""
    parts = []
    for sym in coins:
        if cfg == "R1":
            parts.append(e_trades(tf, sym, R1_DAYS))
        else:
            parts.append(sqz_trades(tf, sym, cfg))
            if cfg.p2:
                parts.append(e_trades(tf, sym, E_DAYS))
    return pd.concat(parts, ignore_index=True)


def rules_for(cfg: Cfg | str, informative_r1: bool = False) -> Rules:
    if cfg == "R1":
        if informative_r1:
            return Rules(mode="vol", max_pos=None, gross_cap=None, coin_cap=2.0, open_risk_cap=None)
        return Rules(mode="vol")
    return Rules(mode="vol") if cfg.p5 == "vol" else Rules(mode="risk")


# ----------------------------------------------------------------------------------------------- grupos y tramos
def group_closes(tf: str, coins) -> dict:
    out = {}
    for sym in coins:
        df = coin_data(tf, sym)["df"]
        out[sym] = (df["time_utc"].to_numpy(), df["close"].to_numpy(float))
    return out


def btc_closes(tf: str) -> tuple:
    df = U.load_coin("BTC", U.TF_CODE[tf])
    return df["time_utc"].to_numpy(), df["close"].to_numpy(float)


def group_window(tf: str, coins, t1=None, t0_min=None) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Tramo comun: desde max(2017-01-01, primera vela del grupo + 200 velas) hasta DATA_END (o `t1`)."""
    first = min(coin_data(tf, s)["df"]["time_utc"].iloc[0] for s in coins)
    t0 = max(U.ENTRY_FROM, first + 200 * STEP[tf])
    if t0_min is not None:
        t0 = max(t0, pd.Timestamp(t0_min))
    return t0, pd.Timestamp(t1) if t1 is not None else pd.Timestamp(U.DATA_END[U.TF_CODE[tf]])


def priorities(coins) -> list[dict]:
    """N_SEEDS prioridades de monedas (semillas fijas 0..8) para desempatar entradas de la misma vela cuando el cupo o un tope aprieta."""
    cs = sorted(coins)
    return [{c: int(r) for c, r in zip(cs, np.random.default_rng(sd).permutation(len(cs)))} for sd in range(N_SEEDS)]


MEDIAN_KEYS = ("n", "n_sub", "n_abiertos", "skipped", "pnl_total", "pnl_mediana_moneda", "conc_max", "R_medio", "cagr", "dd", "calmar", "final",
               "cagr_cerrada", "dd_cerrada", "calmar_cerrada", "cagr_sin_mejor")


def _nanmedian(v):
    v = np.asarray(v, float)
    return float("nan") if np.isnan(v).sum() * 2 >= len(v) else float(np.nanmedian(v))


def evaluate(tf: str, coins, t0, t1, cfg: Cfg | str, informative_r1: bool = False, extras: bool = True) -> dict:
    """Corre la cartera de `cfg` en el grupo y el tramo con N_SEEDS prioridades de monedas y devuelve la MEDIANA de cada metrica
    (si la corrida con semilla 0 no saltea ninguna entrada, el orden no importa y no se repite). Con `extras`: 'sin el mejor trade'
    (se quita el de mayor PnL en USD) y los buy&hold."""
    coins = list(coins)
    trades = trades_for(tf, coins, cfg)
    closes = group_closes(tf, coins)
    rules = rules_for(cfg, informative_r1)
    reps, res0 = [], None
    for k, pr in enumerate(priorities(coins)):
        res = run_cartera(trades, closes, t0, t1, rules, priority=pr)
        rep = group_report(res)
        if extras:
            cl = res["trades"][res["trades"]["closed"]]
            if len(cl):
                r2 = run_cartera(trades, closes, t0, t1, rules, drop_id=cl.loc[cl["pnl"].idxmax(), "id"], priority=pr)
                rep["cagr_sin_mejor"] = curve_metrics(r2["times"], r2["eq"], r2["initial"])["cagr"]
            else:
                rep["cagr_sin_mejor"] = float("nan")
        reps.append(rep)
        if k == 0:
            res0 = res
            if not res["skipped"]:
                break                                  # nada compitio por cupo: el orden no cambia nada
    out = dict(reps[0])
    for key in MEDIAN_KEYS:
        if key in reps[0]:
            out[key] = _nanmedian([r[key] for r in reps])
    out["n"] = int(out["n"])
    out["_res"] = res0
    out["seeds"] = len(reps)
    if extras:
        out.update(benchmarks(tf, coins, res0["times"]))
    return out


def benchmarks(tf: str, coins, times) -> dict:
    ini = 10000.0
    b = curve_metrics(times, buyhold_btc(btc_closes(tf), times, ini), ini)
    e = curve_metrics(times, buyhold_ew(group_closes(tf, coins), times, ini), ini)
    return dict(bh_btc_cagr=b["cagr"], bh_btc_dd=b["dd"], bh_btc_calmar=b["calmar"],
                bh_ew_cagr=e["cagr"], bh_ew_dd=e["dd"], bh_ew_calmar=e["calmar"])


def sirve_criteria(r: dict) -> dict[str, bool]:
    """Los criterios (1)-(4) de PROTOCOLO, seccion 1, sobre un `evaluate` con extras."""
    return {
        "CAGR > 0": r["cagr"] > 0,
        "Calmar > BTC buy&hold": r["calmar"] > r["bh_btc_calmar"],
        "Calmar > equiponderado buy&hold": r["calmar"] > r["bh_ew_calmar"],
        "DD <= 50% del DD de BTC buy&hold": r["dd"] <= 0.5 * r["bh_btc_dd"],
        f"n >= {MIN_N}": r["n"] >= MIN_N,
        "CAGR > 0 sin el mejor trade": r.get("cagr_sin_mejor", float("nan")) > 0,
        "mediana por moneda del PnL > 0": r["pnl_mediana_moneda"] > 0,
        f"ninguna moneda > {MAX_CONC:.0%} de la ganancia": (r["conc_max"] <= MAX_CONC) if not np.isnan(r["conc_max"]) else False,
    }


def verdict_group(r: dict) -> str:
    if r["n"] < MIN_N:
        return "SIN MUESTRA"
    return "CUMPLE" if all(sirve_criteria(r).values()) else "NO CUMPLE"


def feasible_train(r: dict) -> bool:
    """Condiciones 3.1.3 + CAGR > 0 en train (no mira los buy&hold)."""
    return (r["n"] >= MIN_N and r["cagr"] > 0 and r.get("cagr_sin_mejor", -1) > 0 and r["pnl_mediana_moneda"] > 0
            and not np.isnan(r["conc_max"]) and r["conc_max"] <= MAX_CONC)


# ----------------------------------------------------------------------------------------------- grilla y meseta
def axes(tf: str) -> dict[str, list]:
    p4 = [0] + P4_N.get(tf, [])
    return dict(p1=["off", "bear"] if tf in HTF_OF else ["off"], p2=[False, True], p3=[0, 10, 20, 40], p4=p4, p5=["risk", "vol"])


def grid(tf: str) -> list[Cfg]:
    a = axes(tf)
    return [Cfg(*v) for v in itertools.product(a["p1"], a["p2"], a["p3"], a["p4"], a["p5"])]


def neighbors(tf: str, c: Cfg) -> list[Cfg]:
    a = axes(tf)
    out = []
    for name, opts in a.items():
        i = opts.index(getattr(c, name))
        for j in (i - 1, i + 1):
            if 0 <= j < len(opts):
                out.append(Cfg(**{**c.__dict__, name: opts[j]}))
    return out


def plateau_scores(tf: str, calmar: dict, feasible: dict) -> dict:
    """score de meseta = promedio del Calmar del punto y de sus vecinos +-1 paso; vecino infactible = -1; solo puntos factibles."""
    sc = {}
    for c in grid(tf):
        if not feasible[c]:
            continue
        vals = [min(calmar[c], CALMAR_CAP)] + [min(calmar[n], CALMAR_CAP) if feasible[n] else -1.0 for n in neighbors(tf, c)]
        sc[c] = float(np.mean(vals))
    return sc


def choose(tf: str, calmar: dict, feasible: dict) -> Cfg | None:
    sc = plateau_scores(tf, calmar, feasible)
    if not sc:
        return None
    order = {c: i for i, c in enumerate(grid(tf))}
    return max(sc, key=lambda c: (round(sc[c], 12), -order[c]))


# ----------------------------------------------------------------------------------------------- CLI
def _row(label: str, r: dict, with_crit: bool = True) -> dict:
    out = dict(config=label, n=r["n"], n_sub=r["n_sub"], R_medio=r["R_medio"], CAGR=r["cagr"], DD=r["dd"], Calmar=r["calmar"], CAGR_cerrada=r["cagr_cerrada"],
               DD_cerrada=r["dd_cerrada"], CAGR_sin_mejor=r.get("cagr_sin_mejor", float("nan")), mediana_PnL_moneda=r["pnl_mediana_moneda"],
               conc_max=r["conc_max"], BTC_CAGR=r["bh_btc_cagr"], BTC_DD=r["bh_btc_dd"], BTC_Calmar=r["bh_btc_calmar"],
               EW_CAGR=r["bh_ew_cagr"], EW_DD=r["bh_ew_dd"], EW_Calmar=r["bh_ew_calmar"], saltados=r["skipped"])
    if with_crit:
        c = sirve_criteria(r)
        out["criterios"] = f"{sum(c.values())}/{len(c)}"
        out["veredicto_grupo"] = verdict_group(r)
        out["fallan"] = "; ".join(k for k, v in c.items() if not v) or "-"
    return out


def _state_path():
    from .optimize import RESULTS
    return RESULTS / "fase7_state.json"


def _load_state() -> dict:
    import json
    p = _state_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save_state(st: dict) -> None:
    import json
    from .optimize import _py
    _state_path().write_text(json.dumps(_py(st), indent=1, ensure_ascii=False), encoding="utf-8")


def stage_train(tf: str) -> None:
    from .optimize import RESULTS, md_table
    coins = list(U.TRAIN)
    t0, t1 = group_window(tf, coins, t1=TRAIN_END)
    pts = grid(tf)
    rows, calmar, feas = [], {}, {}
    for c in pts:
        r = evaluate(tf, coins, t0, t1, c)
        calmar[c], feas[c] = r["calmar"], feasible_train(r)
        rows.append(dict(config=c.label(), p1=c.p1, p2=c.p2, p3=c.p3, p4=c.p4, p5=c.p5, n=r["n"], R_medio=r["R_medio"], CAGR=r["cagr"], DD=r["dd"],
                         Calmar=r["calmar"], CAGR_sin_mejor=r["cagr_sin_mejor"], mediana_PnL_moneda=r["pnl_mediana_moneda"],
                         conc_max=r["conc_max"], factible=feas[c], saltados=r["skipped"]))
    sc = plateau_scores(tf, calmar, feas)
    best = choose(tf, calmar, feas)
    df = pd.DataFrame(rows)
    df["meseta"] = [sc.get(c, float("nan")) for c in pts]
    df["elegido"] = [c == best for c in pts]
    refs = []
    for name, cfg in (("R0", R0), ("R1", "R1")):
        r = evaluate(tf, coins, t0, t1, cfg)
        refs.append(_row(name, r, with_crit=False))
    RESULTS.mkdir(exist_ok=True)
    df.to_csv(RESULTS / f"fase7_{tf}_grid.csv", index=False)
    st = _load_state()
    t = st.setdefault(tf, {})
    if t.get("looks"):
        raise SystemExit("Ya hubo miradas a Z2/Z3: no se puede re-correr el train (cambiaria el candidato despues de mirar).")
    prev = t.get("train")
    pasadas = (prev.get("pasadas", 1) if prev else 0) + 1       # cada corrida de train se cuenta (la 1.a, pre-revision, esta archivada)
    t["train"] = dict(window=[str(t0), str(t1)], coins=coins, puntos=len(pts), referencias=2, pasadas=pasadas,
                      pruebas=(len(pts) + 2) * pasadas, factibles=int(sum(feas.values())),
                      max_n=int(df["n"].max()), candidato=None if best is None else dict(best.__dict__), meseta=None if best is None else sc[best])
    _save_state(st)
    print(f"[{tf}] train {t0.date()}..{t1.date()}: {len(pts)} puntos, {sum(feas.values())} factibles, candidato: {best.label() if best else None}")
    top = df.sort_values("meseta", ascending=False).head(12)
    print(md_table(top.drop(columns=["p1", "p2", "p3", "p4", "p5"])))
    print(md_table(pd.DataFrame(refs)))


def _group_coins(tf: str, group: str) -> list[str]:
    if group == "pool":
        return list({**U.HOLDOUT, **U.FRESH_Z1, **U.FRESH_Z2, **U.FRESH_Z3})
    return list(U.fresh_group(group))


def stage_look(tf: str, group: str) -> None:
    """UNA sola mirada por (tf, grupo): queda trabada en el estado. No existe --force (PROTOCOLO)."""
    import json
    from .optimize import RESULTS, md_table
    st = _load_state()
    t = st.setdefault(tf, {})
    if "train" not in t:
        raise SystemExit("Falta correr --stage train antes de mirar.")
    if (tf == "w1") != (group == "pool"):
        raise SystemExit("W1 se valida con --group pool (pooling de todas las monedas no-train); H4 y D1 con z2 / z3.")
    if group in t.get("looks", {}):
        raise SystemExit(f"{tf.upper()} {group.upper()} ya se miro una vez: repetirlo invalida la prueba (no hay --force).")
    cand_d = t["train"]["candidato"]
    cand = Cfg(**cand_d) if cand_d else None
    coins = _group_coins(tf, group)
    if t.get("looks") and any(l.get("candidato") != cand_d for l in t["looks"].values()):
        raise SystemExit("El candidato cambio entre miradas: no se mira.")
    t0, t1 = group_window(tf, coins)
    wins = {"todo el historial": (t0, t1), "2024-hoy": (max(t0, U.TEST_FROM), t1)}
    configs = ([("candidato", cand)] if cand else []) + [("R0", R0), ("R1", "R1")]
    out_rows, verdicts = [], {}
    for wname, (a, b) in wins.items():
        for name, cfg in configs:
            r = evaluate(tf, coins, a, b, cfg)
            label = f"{name} [{cfg.label()}]" if isinstance(cfg, Cfg) else name
            out_rows.append(dict(tramo=wname, **_row(label, r)))
            if wname == "todo el historial":
                verdicts[name] = dict(veredicto=verdict_group(r), criterios=sirve_criteria(r), n=r["n"], calmar=r["calmar"], cagr=r["cagr"], dd=r["dd"])
        ri = evaluate(tf, coins, a, b, "R1", informative_r1=True)
        out_rows.append(dict(tramo=wname, **_row("R1 informativa (sin cupo ni tope bruto)", ri, with_crit=False)))
    df = pd.DataFrame(out_rows)
    t.setdefault("looks", {})[group] = dict(coins=coins, window=[str(t0), str(t1)], veredictos=verdicts, mirada=1, candidato=cand_d)
    _save_state(st)
    df.to_csv(RESULTS / f"fase7_{tf}_{group}.csv", index=False)
    (RESULTS / f"fase7_{tf}_{group}.md").write_text(f"# Fase 7 {tf.upper()} en {group.upper()} (una sola mirada)\n\nMonedas: {', '.join(coins)}. Tramo: {t0} a {t1}.\n\n"
                                                    + md_table(df) + "\n", encoding="utf-8")
    print(f"[{tf}] {group}: {len(coins)} monedas, tramo {t0.date()}..{t1.date()}")
    print(md_table(df))


def stage_allcoins(tf: str) -> None:
    """Tabla informativa 2024-hoy en todas las monedas (contaminada: incluye train/holdout/Z1/Z2/Z3)."""
    from .optimize import RESULTS, md_table
    st = _load_state()
    t = st[tf]
    need = {"w1": ["pool"]}.get(tf, ["z2", "z3"])
    if any(g not in t.get("looks", {}) for g in need):
        raise SystemExit(f"Falta la mirada a {need}: allcoins va DESPUES de las miradas.")
    if "allcoins_2024" in t:
        raise SystemExit("allcoins ya se corrio una vez.")
    cand_d = t["train"]["candidato"]
    coins = list({**U.TRAIN, **U.HOLDOUT, **U.FRESH_Z1, **U.FRESH_Z2, **U.FRESH_Z3})
    a, b = group_window(tf, coins, t0_min=U.TEST_FROM)
    configs = ([("candidato", Cfg(**cand_d))] if cand_d else []) + [("R0", R0), ("R1", "R1")]
    rows = []
    for name, cfg in configs:
        rows.append(_row(name, evaluate(tf, coins, a, b, cfg), with_crit=False))
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / f"fase7_{tf}_allcoins.csv", index=False)
    t["allcoins_2024"] = dict(coins=len(coins), window=[str(a), str(b)])
    _save_state(st)
    print(f"[{tf}] 2024-hoy todas las monedas ({len(coins)}), {a.date()}..{b.date()} (informativa, contaminada)")
    print(md_table(df))


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["train", "look", "allcoins"])
    ap.add_argument("--tf", required=True, choices=["h4", "d1", "w1"])
    ap.add_argument("--group", choices=["z2", "z3", "pool"])
    a = ap.parse_args()
    if a.stage == "train":
        stage_train(a.tf)
    elif a.stage == "look":
        if not a.group:
            raise SystemExit("--group z2|z3 (H4/D1) o pool (W1)")
        stage_look(a.tf, a.group)
    else:
        stage_allcoins(a.tf)


if __name__ == "__main__":
    main()
