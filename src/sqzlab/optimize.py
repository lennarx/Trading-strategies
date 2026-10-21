"""Fase 4: optimizador por temporalidad (un set por temporalidad, agregado entre monedas, nunca por moneda).

Uso:  python -m sqzlab.optimize --tf d1 [--stage all|0..5] [--workers 16] [--reps 500]

Etapas (cada una suma al contador de pruebas; las decisiones estan fijadas en docs/PROTOCOLO.md):
  0 referencia (defaults v2) + baseline aleatorio     3 squeeze comun (bb/kc) con lo mejor de la etapa 2
  1 piernas aisladas (A/B/C/D x largo/corto)          4 chequeo de meseta +-20% sobre el set final
  2 grilla por senal (solo piernas vivas)             5 fuera de muestra, UNA sola vez (test, holdout, WF)
Estado en results/opt_<tf>_state.json, CSV por etapa en results/opt_<tf>_stage<N>.csv e informe en results/opt_<tf>.md.
Semillas fijas: dos corridas dan los mismos CSV.
"""
from __future__ import annotations

import argparse
import itertools
import json
import multiprocessing as mp
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import universe as U
from .baseline import CoinSeries, random_baseline, side_counts
from .indicators import compute
from .metrics import breakdown, summarize, trade_frame, window
from .strategy import DEFAULTS, simulate, v2_params

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
BASE = v2_params()
IND_KEYS = ("bbLen", "bbMult", "kcLen", "kcMult", "useTrueRange", "rsiLen", "maType", "maLen", "emaFLen", "emaMLen",
            "emaSLen", "emaSeed", "adxLen", "atrLen", "volLen")
SIGNALS = {"A": ("useA", "aLong", "aShort"), "B": ("useB", "bLong", "bShort"),
           "C": ("useC", "cLong", "cShort"), "D": ("useD", "dLong", "dShort")}
LEGS = [(s, side) for s in SIGNALS for side in (1, -1)]
GRIDS = {
    "A": {"adxMin": [15, 20, 25, 30], "pbBars": [3, 5, 8], "atrMult": [0.1, 0.25, 0.5, 1.0]},
    "B": {"minSqz": [4, 6, 8, 12], "graceBars": [1, 2, 4], "needE200": [False, True], "needMom": [False, True],
          "invBars": [0, 2, 3, 5]},
    "C": {"cHot+cCold": [(60, 40), (65, 35), (70, 30), (75, 25)], "cLook": [6, 10, 15], "cWin": [2, 3, 5],
          "cStopBars": [5, 7, 10], "cAtrMult": [0.25, 0.5, 1.0], "cMaxRisk": [2.0, 3.0, 5.0, 0.0]},
    "D": {"dvL+dvR": [(3, 3), (5, 5), (8, 8)], "dvMin": [3, 5, 8], "dvMax": [30, 60, 100], "dAtrMult": [0.25, 0.5, 1.0],
          "dMaxRisk": [0.0, 3.0, 5.0]},
}
GRID_SQZ = {"bbLen": [16, 20, 26], "bbMult": [1.5, 2.0, 2.5], "kcLen": [16, 20, 26], "kcMult": [1.0, 1.5, 2.0]}
MIN_N_ISOLATED = {"d1": 30, "h4": 40, "w1": 15}
MIN_N_FINAL = 100
MIN_N_LEG = 15
OOS_MIN_EXP = 0.2


# ----------------------------------------------------------------------------------------------------------------
# Evaluador: simula (combinacion x moneda) en un Pool; cachea indicadores por set de parametros de indicadores
# ----------------------------------------------------------------------------------------------------------------
_W: dict = {}


def ind_key(p: dict) -> tuple:
    return tuple(p[k] for k in IND_KEYS)


def _init_worker(tf: str, coins: tuple[str, ...]) -> None:
    _W["tf"], _W["df"], _W["cache"] = tf, {s: U.load_coin(s, tf) for s in coins}, {}


def _eval_task(task):
    cid, coin, over = task
    p = {**BASE, **over}
    full = {**DEFAULTS, **p}
    key = (coin, ind_key(full))
    cache = _W["cache"]
    if key not in cache:
        if len(cache) >= 48:
            cache.pop(next(iter(cache)))
        cache[key] = compute(_W["df"][coin], full)
    ind = cache[key]
    res = simulate(_W["df"][coin], ind=ind, **p)
    return cid, coin, trade_frame(res, coin, ind["atr"])


class Evaluator:
    def __init__(self, tf: str, coins: list[str], workers: int | None = None):
        self.tf, self.coins = tf, list(coins)
        self.workers = workers if workers is not None else min(16, os.cpu_count() or 1)
        self.pool = None
        if self.workers > 1:
            self.pool = mp.get_context("spawn").Pool(self.workers, _init_worker, (U.TF_CODE[tf], tuple(self.coins)))
        else:
            _init_worker(U.TF_CODE[tf], tuple(self.coins))

    def close(self) -> None:
        if self.pool:
            self.pool.close()
            self.pool.join()

    def run(self, combos: list[dict], coins: list[str] | None = None) -> list[pd.DataFrame]:
        """Un DataFrame de trades (todas las monedas pedidas, sin filtrar ventana) por combinacion, en orden."""
        coins = coins or self.coins
        tasks = [(i, c, o) for i, o in enumerate(combos) for c in coins]
        it = self.pool.imap_unordered(_eval_task, tasks, chunksize=2) if self.pool else map(_eval_task, tasks)
        parts: dict[int, dict[str, pd.DataFrame]] = {i: {} for i in range(len(combos))}
        for cid, coin, tf_ in it:
            parts[cid][coin] = tf_
        return [pd.concat([parts[i][c] for c in coins], ignore_index=True) for i in range(len(combos))]


# ----------------------------------------------------------------------------------------------------------------
# Grillas y score suavizado de meseta
# ----------------------------------------------------------------------------------------------------------------
@dataclass
class Grid:
    dims: dict[str, list]
    fixed: dict

    def shape(self) -> tuple[int, ...]:
        return tuple(len(v) for v in self.dims.values())

    def combos(self) -> list[dict]:
        out = []
        for idx in itertools.product(*[range(n) for n in self.shape()]):
            over = dict(self.fixed)
            for (name, vals), i in zip(self.dims.items(), idx):
                if "+" in name:
                    over.update(zip(name.split("+"), vals[i]))
                else:
                    over[name] = vals[i]
            out.append(over)
        return out


def plateau_smooth(s: np.ndarray) -> np.ndarray:
    """Promedio del punto y sus vecinos a +-1 paso sobre cada eje de la grilla (s con la forma de la grilla)."""
    stack = [s]
    for ax in range(s.ndim):
        for sh in (1, -1):
            x = np.full_like(s, np.nan)
            src = [slice(None)] * s.ndim
            dst = [slice(None)] * s.ndim
            if sh == 1:
                src[ax], dst[ax] = slice(0, -1), slice(1, None)
            else:
                src[ax], dst[ax] = slice(1, None), slice(0, -1)
            x[tuple(dst)] = s[tuple(src)]
            stack.append(x)
    return np.nanmean(np.stack(stack), axis=0)


def score_grid(grid: Grid, frames: list[pd.DataFrame], win: tuple, min_n: int) -> pd.DataFrame:
    """Una fila por combinacion: metricas en la ventana, factibilidad, score crudo y suavizado de meseta."""
    combos = grid.combos()
    rows = []
    for over, tr in zip(combos, frames):
        s = summarize(window(tr, *win))
        feas = s["n"] >= min_n and s["exp_trim"] > 0 and s["med_coin"] > 0
        rows.append({**{k: v for k, v in over.items() if k in _grid_keys(grid)}, **s, "feasible": bool(feas)})
    df = pd.DataFrame(rows)
    raw = np.where(df["feasible"], np.clip(df["exp_trim"], -2, 2), -1.0).reshape(grid.shape())
    df["smooth"] = plateau_smooth(raw).reshape(-1)
    return df


def _grid_keys(grid: Grid) -> list[str]:
    return [k for name in grid.dims for k in name.split("+")]


def best_row(df: pd.DataFrame) -> int | None:
    ok = df[df["feasible"]]
    if ok.empty:
        return None
    return int(ok.sort_values(["smooth", "n"], ascending=[False, False]).index[0])


def md_table(df: pd.DataFrame, nd: int = 3) -> str:
    if df.empty:
        return "(vacio)\n"
    f = df.copy()
    for c in f.columns:
        if f[c].dtype.kind == "f":
            f[c] = f[c].map(lambda x: "inf" if np.isinf(x) else f"{x:.{nd}f}")
    head = "| " + " | ".join(map(str, f.columns)) + " |\n|" + "---|" * len(f.columns) + "\n"
    return head + "".join("| " + " | ".join(map(str, r)) + " |\n" for r in f.itertuples(index=False))


def _py(x):
    if isinstance(x, dict):
        return {k: _py(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_py(v) for v in x]
    if isinstance(x, np.generic):
        return x.item()
    return x


def switches(legs: set) -> dict:
    """Casillas de Que probar para un conjunto de piernas {(senal, lado)}."""
    out = {}
    for sig, (use, lng, sht) in SIGNALS.items():
        out[use] = (sig, 1) in legs or (sig, -1) in legs
        out[lng] = (sig, 1) in legs
        out[sht] = (sig, -1) in legs
    return out


# ----------------------------------------------------------------------------------------------------------------
# Corrida por etapas
# ----------------------------------------------------------------------------------------------------------------
class Run:
    def __init__(self, tf: str, workers: int | None, reps: int):
        self.tf, self.reps = tf, reps
        self.code = U.TF_CODE[tf]
        self.train = list(U.TRAIN)
        self.holdout = list(U.HOLDOUT)
        self.win = (U.ENTRY_FROM, None if tf == "w1" else U.TRAIN_END)
        self.state_path = RESULTS / f"opt_{tf}_state.json"
        self.st = json.loads(self.state_path.read_text(encoding="utf-8")) if self.state_path.exists() else dict(
            tests=0, tests_by_stage={}, alive={}, legs=[], chosen={}, sqz={}, final={}, oos_looks=0, no_sample=False,
            reports={}, verdict="")
        self.ev = Evaluator(tf, self.train + self.holdout, workers)
        self._series: dict = {}

    # -- utilidades ------------------------------------------------------------------------------------------
    def save(self) -> None:
        RESULTS.mkdir(exist_ok=True)
        self.state_path.write_text(json.dumps(_py(self.st), indent=1, ensure_ascii=False), encoding="utf-8")
        head = (f"# Optimizacion {self.tf.upper()} (generado por `python -m sqzlab.optimize`)\n\n"
                f"- **Pruebas (combinaciones evaluadas) hasta ahora: {self.st['tests']}** "
                f"({', '.join(f'etapa {k}: {v}' for k, v in sorted(self.st['tests_by_stage'].items()))})\n"
                f"- Veredicto: {self.st['verdict'] or '(pendiente)'}\n\n")
        body = "".join(self.st["reports"][k] for k in sorted(self.st["reports"]))
        (RESULTS / f"opt_{self.tf}.md").write_text(head + body, encoding="utf-8")

    def count(self, stage: int, n: int) -> None:
        self.st["tests"] += n
        self.st["tests_by_stage"][str(stage)] = self.st["tests_by_stage"].get(str(stage), 0) + n

    def report(self, stage: int, text: str) -> None:
        self.st["reports"][str(stage)] = text

    def series(self, sym: str, win: tuple) -> CoinSeries:
        key = (sym, str(win))
        if key not in self._series:
            df = U.load_coin(sym, self.code)
            self._series[key] = CoinSeries(compute(df, {**DEFAULTS, **BASE}), df["time_utc"].to_numpy(), *win)
        return self._series[key]

    def baseline(self, tr: pd.DataFrame, wins: dict[str, tuple], tag: str, reps: int | None = None) -> dict:
        """Baseline aleatorio con las cantidades/lados de `tr`; `wins` = ventana de entrada por moneda."""
        if len(tr) == 0:
            return dict(p50=0.0, p95=0.0, mean=0.0, std=0.0, reps=0, kd=0.0)
        kd = float(np.nanmedian(tr["sd"]))
        coins = {s: self.series(s, w) for s, w in wins.items() if s in set(tr["coin"])}
        return random_baseline(coins, side_counts(tr), kd, reps or self.reps, seed_tag=f"{self.tf}:{tag}")

    def train_wins(self) -> dict:
        return {s: self.win for s in self.train}

    def eval_train(self, combos: list[dict]) -> list[pd.DataFrame]:
        return self.ev.run(combos, self.train)

    def full_params(self) -> dict:
        """Set final acumulado: casillas de las piernas + parametros elegidos por senal + squeeze."""
        p = switches({tuple(x) for x in self.st["legs"]})
        for ch in self.st["chosen"].values():
            p.update(ch)
        p.update(self.st["sqz"])
        return p

    # -- etapa 0 ---------------------------------------------------------------------------------------------
    def stage0(self) -> None:
        tr = window(self.eval_train([{}])[0], *self.win)
        self.count(0, 1)
        s = summarize(tr)
        bl = self.baseline(tr, self.train_wins(), "s0")
        self.st["no_sample"] = bool(self.tf == "w1" and s["n"] < MIN_N_FINAL)
        txt = (f"## Etapa 0: referencia (defaults v2) en monedas train, entradas {self.win[0].date()}..{self.win[1].date() if self.win[1] else 'hoy'}\n\n"
               f"Monedas train: {', '.join(self.train)}.\n\n"
               + md_table(pd.DataFrame([{**s, "base_p50": bl["p50"], "base_p95": bl["p95"], "k_ATR": bl["kd"]}]))
               + "\nPor senal y lado:\n\n" + md_table(breakdown(tr, ["kind", "side"]))
               + "\nPor moneda:\n\n" + md_table(breakdown(tr, "coin")))
        if self.st["no_sample"]:
            txt += (f"\n**Sin muestra:** el agregado de W1 da {s['n']} trades (< {MIN_N_FINAL}). Segun el protocolo, W1 hereda "
                    f"el set de D1.\n")
        self.report(0, txt + "\n")
        print(f"[{self.tf}] etapa 0: n={s['n']} exp={s['exp']:.3f}R pf={s['pf']:.2f} baseline p50={bl['p50']:.3f} p95={bl['p95']:.3f}")

    # -- etapa 1 ---------------------------------------------------------------------------------------------
    def stage1(self) -> None:
        combos = [switches({leg}) for leg in LEGS]
        frames = self.eval_train(combos)
        self.count(1, len(combos))
        rows = []
        for leg, tr in zip(LEGS, frames):
            tr = window(tr, *self.win)
            s = summarize(tr)
            bl = self.baseline(tr, self.train_wins(), f"s1:{leg[0]}{leg[1]}")
            rows.append(dict(senal=leg[0], lado="largo" if leg[1] > 0 else "corto", n=s["n"], exp=s["exp"], pf=s["pf"],
                             win=s["win"], base_p50=bl["p50"], base_p95=bl["p95"],
                             viva=bool(s["n"] >= MIN_N_LEG and s["exp"] > bl["p95"]),
                             debil=bool(s["n"] >= MIN_N_LEG and s["exp"] > bl["p50"])))
        df = pd.DataFrame(rows)
        alive = [(r.senal, 1 if r.lado == "largo" else -1) for r in df.itertuples() if r.viva]
        weak = [(r.senal, 1 if r.lado == "largo" else -1) for r in df.itertuples() if r.debil]
        used, note = alive, "Piernas vivas (exp > p95 del baseline aleatorio)."
        if not alive and weak:
            used, note = weak, "Ninguna pierna viva: se siguen las debiles (exp > p50 del baseline); el veredicto lo da el fuera de muestra."
        elif not alive:
            note = "Ninguna pierna supera siquiera al p50 del baseline aleatorio: no hay ventaja en esta temporalidad con estas senales."
        self.st["legs"], self.st["alive"] = [list(x) for x in used], dict(vivas=[list(x) for x in alive], debiles=[list(x) for x in weak])
        df.to_csv(RESULTS / f"opt_{self.tf}_stage1.csv", index=False)
        self.report(1, "## Etapa 1: piernas aisladas (defaults v2, una pierna encendida a la vez)\n\n" + md_table(df)
                    + f"\n{note} Se llevan a la etapa 2: {', '.join(f'{s}{'+' if d > 0 else '-'}' for s, d in used) or 'ninguna'}.\n\n")
        print(f"[{self.tf}] etapa 1: {note} -> {used}")

    # -- etapa 2 ---------------------------------------------------------------------------------------------
    def stage2(self) -> None:
        legs = {tuple(x) for x in self.st["legs"]}
        self.st["chosen"] = {}
        out, csv = "## Etapa 2: grilla por senal (solo piernas llevadas; el resto de las senales apagado)\n\n", []
        min_n = MIN_N_ISOLATED[self.tf]
        for sig in SIGNALS:
            sl = {x for x in legs if x[0] == sig}
            if not sl:
                continue
            grid = Grid(GRIDS[sig], switches(sl))
            frames = self.eval_train(grid.combos())
            self.count(2, len(frames))
            df = score_grid(grid, frames, self.win, min_n)
            df.insert(0, "senal", sig)
            csv.append(df)
            b = best_row(df)
            keys = _grid_keys(grid)
            if b is None:
                out += f"### Senal {sig}\n\nNingun punto de la grilla ({len(df)} combinaciones) cumple las restricciones (n>={min_n}, exp recortada>0, mediana por moneda>0). Se deja con defaults.\n\n"
                self.st["chosen"][sig] = {}
                continue
            ch = {k: df.loc[b, k] for k in keys}
            self.st["chosen"][sig] = _py({k: (bool(v) if isinstance(v, (np.bool_, bool)) else v) for k, v in ch.items()})
            top = df[df["feasible"]].sort_values(["smooth", "n"], ascending=False).head(8)
            out += (f"### Senal {sig} ({len(df)} combinaciones, {int(df['feasible'].sum())} factibles)\n\nElegida (mejor score suavizado de meseta, no el pico): "
                    f"{json.dumps(_py(self.st['chosen'][sig]))}\n\nTop 8 por score suavizado:\n\n" + md_table(top[keys + ['n', 'exp', 'exp_trim', 'pf', 'smooth']]))
            peak = df[df["feasible"]].sort_values("exp", ascending=False).head(1)
            if len(peak):
                out += f"\nPico crudo (no se usa): exp={peak['exp'].iloc[0]:.3f}R con n={int(peak['n'].iloc[0])}, score suavizado {peak['smooth'].iloc[0]:.3f}.\n\n"
        if csv:
            pd.concat(csv, ignore_index=True).to_csv(RESULTS / f"opt_{self.tf}_stage2.csv", index=False)
        self.report(2, out)
        print(f"[{self.tf}] etapa 2: elegido {self.st['chosen']}")

    # -- etapa 3 ---------------------------------------------------------------------------------------------
    def stage3(self) -> None:
        self.st["sqz"] = {}
        base = {**switches({tuple(x) for x in self.st["legs"]})}
        for ch in self.st["chosen"].values():
            base.update(ch)
        grid = Grid(GRID_SQZ, base)
        frames = self.eval_train(grid.combos())
        self.count(3, len(frames))
        df = score_grid(grid, frames, self.win, MIN_N_FINAL)
        df.to_csv(RESULTS / f"opt_{self.tf}_stage3.csv", index=False)
        b = best_row(df)
        keys = _grid_keys(grid)
        txt = f"## Etapa 3: squeeze comun (bb/kc) con lo elegido en la etapa 2 ({len(df)} combinaciones)\n\n"
        if b is None:
            txt += f"Ningun punto cumple n>={MIN_N_FINAL} + exp recortada>0 + mediana por moneda>0. Se deja el squeeze por defecto; el set queda marcado como NO APTO.\n\n"
            self.st["final_feasible"] = False
        else:
            self.st["sqz"] = _py({k: df.loc[b, k] for k in keys})
            self.st["final_feasible"] = True
            txt += (f"Elegido: {json.dumps(_py(self.st['sqz']))} (score suavizado {df.loc[b, 'smooth']:.3f}, n={int(df.loc[b, 'n'])}, exp={df.loc[b, 'exp']:.3f}R).\n\nTop 8:\n\n"
                    + md_table(df[df['feasible']].sort_values(['smooth', 'n'], ascending=False).head(8)[keys + ['n', 'exp', 'exp_trim', 'pf', 'smooth']]))
        self.report(3, txt + "\n")
        print(f"[{self.tf}] etapa 3: {self.st['sqz']}")

    # -- etapa 4 ---------------------------------------------------------------------------------------------
    def stage4(self) -> None:
        final = self.full_params()
        tuned = {}
        for ch in list(self.st["chosen"].values()) + [self.st["sqz"]]:
            tuned.update(ch)
        probes = plateau_probes(tuned)   # (param, signo, valor)
        combos = [final] + [{**final, k: v} for k, _, v in probes]
        frames = self.eval_train(combos)
        self.count(4, len(combos))
        s0 = summarize(window(frames[0], *self.win))
        rows, fail = [], []
        for (k, sg, v), fr in zip(probes, frames[1:]):
            s = summarize(window(fr, *self.win))
            ok = s["exp_trim"] > 0 and (s0["exp_trim"] <= 0 or s["exp_trim"] >= 0.5 * s0["exp_trim"])
            rows.append(dict(param=k, vecino=sg, valor=v, n=s["n"], exp=s["exp"], exp_trim=s["exp_trim"], pf=s["pf"], ok=ok))
            if not ok and k not in fail:
                fail.append(k)
        txt = (f"## Etapa 4: chequeo de meseta +-20% sobre el set final (train)\n\nCentro: n={s0['n']}, exp={s0['exp']:.3f}R, exp recortada={s0['exp_trim']:.3f}R, PF={s0['pf']:.2f}. "
               f"Criterio: la expectativa recortada del vecino sigue > 0 y >= 50% de la central.\n\n" + md_table(pd.DataFrame(rows)))
        if fail:
            txt += f"\n**Picos (se revierten al default v2):** {', '.join(fail)}.\n"
            for k in fail:
                for d in self.st["chosen"].values():
                    if k in d:
                        d[k] = BASE[k]
                if k in self.st["sqz"]:
                    self.st["sqz"][k] = BASE[k]
            fr2 = self.eval_train([self.full_params()])[0]
            self.count(4, 1)
            s2 = summarize(window(fr2, *self.win))
            txt += f"Tras revertir: n={s2['n']}, exp={s2['exp']:.3f}R, PF={s2['pf']:.2f}.\n"
            if s2["n"] < MIN_N_FINAL or s2["exp_trim"] <= 0:
                self.st["final_feasible"] = False
        else:
            txt += "\nNingun parametro es un pico aislado.\n"
        self.st["final"] = self.full_params()
        self.report(4, txt + "\n")
        print(f"[{self.tf}] etapa 4: picos {fail}")

    # -- etapa 5 ---------------------------------------------------------------------------------------------
    def stage5(self, force: bool) -> None:
        if self.st["oos_looks"] >= 1 and not force:
            raise SystemExit("El fuera de muestra (test/holdout) ya se miro una vez para esta temporalidad. "
                             "Repetirlo invalida la prueba; si igual hace falta, usar --force-oos (queda anotado).")
        self.st["oos_looks"] += 1
        final = self.st["final"] or self.full_params()
        if self.st["no_sample"]:
            d1 = json.loads((RESULTS / "opt_d1_state.json").read_text(encoding="utf-8")) if (RESULTS / "opt_d1_state.json").exists() else {}
            final = d1.get("final", {}) if d1.get("final_feasible", False) else {}
        tr_all, ref_all = self.ev.run([final, {}], self.train + self.holdout)

        def make_groups(allt: pd.DataFrame):
            if self.tf == "w1":
                ho = window(allt[allt["coin"].isin(self.holdout)], U.ENTRY_FROM)
                ho_w = {s: (U.ENTRY_FROM, None) for s in self.holdout}
                return {"train (monedas train, todo 2017+)": (window(allt[allt["coin"].isin(self.train)], *self.win), self.train_wins()),
                        "holdout (monedas holdout, todo 2017+)": (ho, ho_w)}, ho, ho_w
            te = window(allt[allt["coin"].isin(self.train)], U.TEST_FROM)
            ho = window(allt[allt["coin"].isin(self.holdout)], U.ENTRY_FROM)
            te_w = {s: (U.TEST_FROM, None) for s in self.train}
            ho_w = {s: (U.ENTRY_FROM, None) for s in self.holdout}
            o, ow = pd.concat([te, ho], ignore_index=True), {**te_w, **ho_w}
            return {"train (monedas train, 2017-2023)": (window(allt[allt["coin"].isin(self.train)], *self.win), self.train_wins()),
                    "test (monedas train, 2024-hoy)": (te, te_w), "holdout (monedas holdout, 2017-hoy)": (ho, ho_w),
                    "OOS agregado (test + holdout)": (o, ow)}, o, ow

        txt = "## Etapa 5: fuera de muestra (se mira UNA sola vez)\n\n"
        if self.st["no_sample"]:
            txt += "W1 hereda el set final de D1 (sin muestra propia).\n\n"
        txt += f"Set evaluado: `{json.dumps(_py({k: v for k, v in final.items()}))}`\n\n"
        reps = max(self.reps, 1000)

        def table(allt: pd.DataFrame, tag: str):
            groups, oos_, _ = make_groups(allt)
            rows = []
            for name, (tr, wins) in groups.items():
                sm = summarize(tr)
                bl = self.baseline(tr, wins, f"s5{tag}:{name}", reps)
                rows.append(dict(grupo=name, **{k: sm[k] for k in ("n", "exp", "pf", "win", "dd", "total", "exp_ex_best", "exp_trim", "med_coin")},
                                 base_p50=bl["p50"], base_p95=bl["p95"]))
            return pd.DataFrame(rows), oos_

        df, oos = table(tr_all, "")
        txt += md_table(df)
        if len(ref_all):
            dfr, _ = table(ref_all, "ref")
            txt += ("\nVara: defaults v2 sin optimizar (mismos grupos; es solo comparacion, no se elige nada con esto):\n\n" + md_table(dfr))
        so = summarize(oos)
        o = df.iloc[-1]
        crit = {"expectativa > 0,2R": so["exp"] > OOS_MIN_EXP, "expectativa > p95 del baseline": so["exp"] > o["base_p95"],
                f"n >= {MIN_N_FINAL}": so["n"] >= MIN_N_FINAL, "sin el mejor trade > 0": so["exp_ex_best"] > 0, "expectativa recortada (sin 2% mejores) > 0": so["exp_trim"] > 0,
                "mediana por moneda > 0": so["med_coin"] > 0}
        info = {"PF entre 1,5 y 2,5": 1.5 <= so["pf"] <= 2.5, "ganancia total >= 2x DD (en R)": so["total"] >= 2 * so["dd"]}
        passes = all(crit.values()) and bool(final) and self.st.get("final_feasible", False)
        txt += ("\nCriterios de escritura de `params/` (fijados antes): " + "; ".join(f"{k}: {'SI' if v else 'NO'}" for k, v in crit.items())
                + f". Entrenamiento factible: {'SI' if self.st.get('final_feasible', False) else 'NO'}.\n"
                + "Criterios informativos (PROTOCOLO sec. 3): " + "; ".join(f"{k}: {'SI' if v else 'NO'}" for k, v in info.items()) + ".\n\n")
        txt += "Por moneda (OOS):\n\n" + md_table(breakdown(oos, "coin")) + "\nPor senal y lado (OOS):\n\n" + md_table(breakdown(oos, ["kind", "side"]))
        yr = tr_all.assign(anio=tr_all["entry_t"].dt.year)
        yr = yr[yr["entry_t"] >= U.ENTRY_FROM]
        ytab = yr.groupby("anio")["R"].agg(n="count", exp="mean", total="sum").reset_index()
        txt += "\nConsistencia por anio (todas las monedas, set final):\n\n" + md_table(ytab)
        if self.tf != "w1" and not self.st["no_sample"]:
            txt += "\n" + self._walk_forward()
        self.st["oos"] = dict(passes=bool(passes), exp=so["exp"], n=so["n"], pf=so["pf"], crit=crit)
        self.st["verdict"] = (f"{'CANDIDATO' if passes else 'SIN CANDIDATO'}: OOS n={so['n']}, exp={so['exp']:.3f}R, PF={so['pf']:.2f}, "
                              f"baseline p95={o['base_p95']:.3f}R, sin el mejor={so['exp_ex_best']:.3f}R, recortada={so['exp_trim']:.3f}R")
        self.report(5, txt + "\n")
        print(f"[{self.tf}] etapa 5: {self.st['verdict']}")

    def _walk_forward(self) -> str:
        """Walk-forward informativo: en cada fold se re-elige sobre la grilla de squeeze (con las piernas ya fijadas)
        usando solo la ventana de train del fold, y se mide en el anio siguiente. No agrega pruebas nuevas (misma grilla)."""
        base = {**switches({tuple(x) for x in self.st["legs"]})}
        for ch in self.st["chosen"].values():
            base.update(ch)
        grid = Grid(GRID_SQZ, base)
        frames = self.eval_train(grid.combos())
        rows = []
        for a, b, c, d in U.WALK_FORWARD:
            df = score_grid(grid, frames, (pd.Timestamp(a), pd.Timestamp(b) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)), 40)
            i = best_row(df)
            if i is None:
                rows.append(dict(train=f"{a[:4]}-{b[:4]}", test=c[:4], n_test=0, exp_test=0.0, elegido="(sin factible)"))
                continue
            s = summarize(window(frames[i], pd.Timestamp(c), pd.Timestamp(d) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)))
            rows.append(dict(train=f"{a[:4]}-{b[:4]}", test=c[:4], n_test=s["n"], exp_test=s["exp"],
                             elegido=json.dumps(_py({k: df.loc[i, k] for k in _grid_keys(grid)}))))
        return "Walk-forward informativo (train 3 anios -> test 1 anio, re-eligiendo el squeeze en cada fold):\n\n" + md_table(pd.DataFrame(rows))


def plateau_probes(tuned: dict) -> list[tuple]:
    """Vecinos a -20%/+20% de cada parametro numerico elegido: (param, '-20%'|'+20%', valor). Los enteros se mueven al
    menos 1 paso; bool y 0 (= apagado) no se mueven. Acepta tipos numpy (los valores salen de DataFrames)."""
    out = []
    for k, v in tuned.items():
        if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)) or v == 0:
            continue
        v = v.item() if isinstance(v, np.generic) else v
        lo, hi = v * 0.8, v * 1.2
        if isinstance(v, int):
            lo, hi = int(round(lo)), int(round(hi))
            lo, hi = (lo if lo != v else v - 1), (hi if hi != v else v + 1)
        else:
            lo, hi = round(lo, 4), round(hi, 4)
        out += [(k, "-20%", _clamp(k, lo)), (k, "+20%", _clamp(k, hi))]
    return out


def _clamp(k: str, v):
    lim = {"cHot": (50, 100), "cCold": (0, 50), "minSqz": (2, 10**6), "dvMax": (5, 10**6), "adxMin": (1, 10**6)}
    lo, hi = lim.get(k, (1 if isinstance(v, int) else 0, 10**6))
    return type(v)(min(max(v, lo), hi))


# ----------------------------------------------------------------------------------------------------------------
# Entregables: params/<tf>.json, Pine regenerados, candidates/<tf>.md
# ----------------------------------------------------------------------------------------------------------------
def write_entregables(run: Run) -> None:
    from . import genpine
    from .calibrate import stats

    tf = run.tf
    final = _py(run.st["final"] or run.full_params())
    if run.st["no_sample"]:
        d1 = json.loads((RESULTS / "opt_d1_state.json").read_text(encoding="utf-8")) if (RESULTS / "opt_d1_state.json").exists() else {}
        final = d1.get("final", {}) if d1.get("oos", {}).get("passes") else {}
    passes = bool(run.st["oos"]["passes"]) if not run.st["no_sample"] else bool(final)
    cand = ROOT / "candidates" / f"{tf}.md"
    cand.parent.mkdir(exist_ok=True)
    ref = (ROOT / "ref" / "sqz_rsi_strategy_v2.pine").read_text(encoding="utf-8").splitlines()
    labels = {}
    for ln in ref:
        m = genpine.INPUT_RE.match(ln)
        if m:
            lab = __import__("re").search(r'"([^"]*)"', m["rest"])
            grp = __import__("re").search(r'group="([^"]*)"', m["rest"])
            labels[m["name"]] = (lab.group(1) if lab else m["name"], grp.group(1) if grp else "")
    if not passes:
        cand.write_text(f"# Candidato {tf.upper()}: SIN CANDIDATO\n\n{run.st['verdict']}\n\n`params/{tf}.json` queda en los defaults v2 "
                        f"(SIN OPTIMIZAR). Ver `results/opt_{tf}.md` para el detalle, el conteo de pruebas y la tabla 'Vara' (la v2 sin optimizar medida en los mismos grupos). "
                        f"Mejor set encontrado en train (NO apto, solo referencia):\n\n```json\n{json.dumps(_py(run.st['final']), indent=1)}\n```\n",
                        encoding="utf-8")
        print(f"[{tf}] sin candidato: params intactos; escrito {cand.relative_to(ROOT)}")
        return
    path = ROOT / "params" / f"{tf}.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    changed = []
    for k, v in final.items():
        if k in doc and not k.startswith("_") and doc[k] != v:
            old = doc[k]
            doc[k] = float(v) if isinstance(old, float) else v
            changed.append((k, old, doc[k]))
    note = "HEREDADO de D1 (sin muestra propia), " if run.st["no_sample"] else ""
    doc["_meta"]["status"] = f"OPTIMIZADO {pd.Timestamp.today().date()}, {note}{run.st['tests']} pruebas (ver results/opt_{tf}.md)"
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    genpine.generate()
    # resultado esperado del port en el tramo que muestra TV (BTC/ETH/SOL; 4h desde 2024-01-01)
    exp_rows = []
    for sym in ("BTC", "ETH", "SOL"):
        df = U.load_coin(sym, run.code)
        if tf == "h4":
            df = df[df["time_utc"] >= pd.Timestamp("2024-01-01")].reset_index(drop=True)
        elif tf == "d1":
            pass
        r = simulate(df, **{**BASE, **{k: v for k, v in doc.items() if not k.startswith("_")}})
        s = stats(r, df)
        exp_rows.append(dict(simbolo=f"{sym} ({U.SOURCES[sym]})", desde=str(df.time_utc.iloc[0])[:10], trades=s["trades"],
                             ganadoras=s["wins"], pnl_usd=round(s["pnl"], 2), pf=round(s["pf"], 3), dd_usd=round(s["dd"], 2)))
    lines = [f"# Candidato {tf.upper()} (el Pine se probo en TradingView: ver results/tv_log.md)\n\n",
             f"{run.st['verdict']}\n\n", f"Estado de params: `{doc['_meta']['status']}`. Script: `pine/{tf}/sqz_rsi_strategy_{tf}.pine` y el unificado.\n\n",
             "## Parametros que cambian respecto de los defaults v2 (nombres EXACTOS de la pestana Entradas)\n\n",
             "| Grupo | Casilla/campo | v2 | candidato |\n|---|---|---|---|\n"]
    for k, old, new in changed:
        lab, grp = labels.get(k, (k, ""))
        lines.append(f"| {grp} | {lab} (`{k}`) | {old} | {new} |\n")
    lines += ["\nTodo lo demas queda en el default de la v2.\n", "\n## Resultado esperado del port (USD, capital 10.000, riesgo 1%, comision 0,05%/lado)\n\n",
              md_table(pd.DataFrame(exp_rows)), "\nSe compara 1 a 1 contra Estadisticas clave de TradingView (sin garantia: el port no es TV).\n"]
    cand.write_text("".join(lines), encoding="utf-8")
    print(f"[{tf}] params escritos, Pine regenerados, {cand.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", required=True, choices=["h4", "d1", "w1"])
    ap.add_argument("--stage", default="all", help="all | 0..5 | write (solo escribir params/candidates desde el estado)")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--reps", type=int, default=500)
    ap.add_argument("--force-oos", action="store_true", help="repetir el fuera de muestra (queda anotado)")
    ap.add_argument("--no-write", action="store_true", help="no escribir params/ ni candidates/")
    a = ap.parse_args()
    run = Run(a.tf, a.workers, a.reps)
    try:
        stages = range(6) if a.stage == "all" else ([] if a.stage == "write" else [int(a.stage)])
        if a.stage == "all":                  # una corrida completa arranca de cero (el conteo de pruebas tambien)
            run.st.update(tests=0, tests_by_stage={}, alive={}, legs=[], chosen={}, sqz={}, final={}, no_sample=False,
                          reports={}, verdict="", final_feasible=True)
            if run.st.get("oos_looks", 0) and not a.force_oos:
                raise SystemExit("Ya se miro el fuera de muestra de esta temporalidad: no se re-corre 'all' sin --force-oos.")
        for st in stages:
            if st == 0:
                run.stage0()
            elif st == 1:
                if run.st["no_sample"]:
                    print("W1 sin muestra: se saltan las etapas 1-4 (hereda D1)")
                    continue
                run.stage1()
            elif st in (2, 3, 4):
                if run.st["no_sample"]:
                    continue
                [run.stage2, run.stage3, run.stage4][st - 2]()
            else:
                if not run.st["no_sample"] and not run.st["legs"]:
                    run.st.update(final={}, final_feasible=False)
                run.stage5(a.force_oos)
            run.save()
        if (a.stage in ("all", "5", "write")) and not a.no_write:
            write_entregables(run)
    finally:
        run.ev.close()


if __name__ == "__main__":
    main()
