"""Fase 7: cartera con equity MARCADA A MERCADO, evento por evento en la grilla de velas del TF.

Reglas en docs/PROTOCOLO.md ("Decisiones fijadas ANTES de la Fase 7", seccion 3). Entrada: una tabla de trades (de `simulate` y/o
de la senal E) con precios del port SIN slippage; el motor aplica comision y slippage por lado y dimensiona con la equity de
ese momento. Orden dentro de una vela: salidas -> equity para dimensionar -> entradas (al cierre) -> marca a mercado.

Columnas de `trades`: id (unico), coin, kind, side, entry_t, exit_t, entry_px, exit_px, sd (distancia del stop inicial en
fraccion del precio de entrada), w (peso: 1 o 1/K), vol (vol anual al entrar, para el modo 'vol'), open (sigue abierto al
fin de los datos). Un trade con exit_t posterior al fin del tramo (o abierto) se marca al ultimo cierre y se corta ahi.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .donchian import vol_weight


@dataclass
class Rules:
    mode: str = "risk"                  # 'risk' = riesgo fijo por trade (6.3), 'vol' = volatilidad objetivo (paper)
    risk_pct: float = 1.0
    max_lev: float = 1.0                # tope de nocional por trade, multiplo de la equity (modo risk)
    open_risk_cap: float | None = 5.0   # % de la equity, suma de nocional x sd (modo risk)
    max_pos: int | None = 6             # monedas con posicion abierta
    gross_cap: float | None = 1.0       # exposicion bruta marcada / equity (modo vol)
    coin_cap: float | None = 2.0        # nocional marcado de una moneda / equity (modo vol)
    commission: float = 0.0005          # por lado
    slippage: float = 0.0005            # por lado, en contra
    initial: float = 10000.0


def aligned_closes(closes: dict, timeline: np.ndarray) -> np.ndarray:
    """closes: {coin: (times, close)} -> matriz [coin, k] con ffill; NaN antes de la primera vela de la moneda."""
    out = np.full((len(closes), len(timeline)), np.nan)
    for ci, (_, (t, c)) in enumerate(closes.items()):
        s = pd.Series(np.asarray(c, float), index=pd.DatetimeIndex(t))
        s = s[~s.index.duplicated(keep="last")]
        out[ci] = s.reindex(pd.DatetimeIndex(timeline), method="ffill").to_numpy()
    return out


def make_timeline(closes: dict, t0, t1) -> np.ndarray:
    allt = np.unique(np.concatenate([np.asarray(t, dtype="datetime64[ns]") for t, _ in closes.values()]))
    return allt[(allt >= np.datetime64(pd.Timestamp(t0))) & (allt <= np.datetime64(pd.Timestamp(t1)))]


def run_cartera(trades: pd.DataFrame, closes: dict, t0, t1, rules: Rules, drop_id=None, priority: dict | None = None) -> dict:
    """`priority`: {moneda: rango}; entre entradas de la MISMA vela entra primero el de menor rango (default: orden alfabetico)."""
    if not trades["id"].is_unique:
        raise ValueError("ids de trades duplicados: el motor colapsaria posiciones")
    tl = make_timeline(closes, t0, t1)
    T = len(tl)
    cidx = {c: i for i, c in enumerate(closes)}
    C = aligned_closes(closes, tl)
    tr = trades[(trades["entry_t"] >= pd.Timestamp(t0)) & (trades["entry_t"] <= pd.Timestamp(t1))]
    if drop_id is not None:
        tr = tr[tr["id"] != drop_id]
    tr = tr.assign(_rk=tr["coin"].map(priority) if priority else 0)
    tr = tr.sort_values(["entry_t", "_rk", "coin", "id"], kind="stable")
    ent_at, ex_at, info = defaultdict(list), defaultdict(list), {}
    ent_idx = np.searchsorted(tl, tr["entry_t"].to_numpy("datetime64[ns]"))
    ex_idx = np.searchsorted(tl, tr["exit_t"].to_numpy("datetime64[ns]"))
    for (_, r), ke, kx in zip(tr.iterrows(), ent_idx, ex_idx):
        if ke >= T or tl[ke] != np.datetime64(r.entry_t):
            continue                                  # la vela de entrada no esta en la grilla (no deberia pasar)
        info[r.id] = r
        ent_at[ke].append(r.id)
        if not r.open and kx < T and tl[kx] == np.datetime64(r.exit_t):
            ex_at[kx].append(r.id)

    sl, cm = rules.slippage, rules.commission
    cash = rules.initial
    book: dict = {}                                   # id -> dict(coin, ci, qty, efill, notional, risk, fee_in)
    eq = np.empty(T)
    eq_closed = np.empty(T)
    done, skipped = [], []
    risk_open = 0.0

    def mtm(k: int) -> float:
        return sum(b["qty"] * (C[b["ci"], k] - b["efill"]) for b in book.values())

    for k in range(T):
        for tid in ex_at.get(k, ()):
            b = book.pop(tid, None)
            if b is None:
                continue
            r = info[tid]
            fill = r.exit_px * (1.0 - r.side * sl)
            pnl = b["qty"] * (fill - b["efill"])
            fee = abs(b["qty"]) * fill * cm
            cash += pnl - fee
            risk_open -= b["risk"]
            done.append(dict(id=tid, coin=r.coin, kind=r.kind, side=r.side, entry_t=r.entry_t, exit_t=r.exit_t,
                             notional=b["notional"], pnl=pnl - fee - b["fee_in"], risk=b["notional"] * r.sd, closed=True))
        if ent_at.get(k):
            e_now = cash + mtm(k)
            gross = sum(abs(b["qty"]) * C[b["ci"], k] for b in book.values())
            coin_n: dict = defaultdict(float)
            for b in book.values():
                coin_n[b["coin"]] += abs(b["qty"]) * C[b["ci"], k]
            for tid in ent_at[k]:
                r = info[tid]
                held = {b["coin"] for b in book.values()}
                if rules.max_pos is not None and r.coin not in held and len(held) >= rules.max_pos:
                    skipped.append((tid, "cupo")); continue
                if rules.mode == "risk":
                    if not r.sd > 0:
                        skipped.append((tid, "sd")); continue
                    notional = min(e_now * rules.risk_pct / 100.0 * r.w / r.sd, e_now * rules.max_lev * r.w)
                    if rules.open_risk_cap is not None and risk_open + notional * r.sd > e_now * rules.open_risk_cap / 100.0 + 1e-9:
                        skipped.append((tid, "riesgo")); continue
                else:
                    wv = vol_weight(r.vol)
                    if np.isnan(wv):
                        skipped.append((tid, "sin_vol")); continue
                    notional = e_now * wv * r.w
                    if rules.gross_cap is not None:
                        notional = min(notional, e_now * rules.gross_cap - gross)
                    if rules.coin_cap is not None:
                        notional = min(notional, e_now * rules.coin_cap - coin_n[r.coin])
                if not notional > 1e-9 * e_now:
                    skipped.append((tid, "tope")); continue
                efill = r.entry_px * (1.0 + r.side * sl)
                qty = r.side * notional / efill
                fee = abs(qty) * efill * cm
                cash -= fee
                book[tid] = dict(coin=r.coin, ci=cidx[r.coin], qty=qty, efill=efill, notional=notional, risk=notional * r.sd, fee_in=fee)
                risk_open += notional * r.sd
                gross += notional
                coin_n[r.coin] += notional
        eq[k] = cash + mtm(k)
        eq_closed[k] = cash
    for tid, b in book.items():                        # abiertos al fin del tramo: marca a mercado, no cuentan en n
        r = info[tid]
        done.append(dict(id=tid, coin=r.coin, kind=r.kind, side=r.side, entry_t=r.entry_t, exit_t=pd.NaT, notional=b["notional"],
                         pnl=b["qty"] * (C[b["ci"], T - 1] - b["efill"]) - b["fee_in"], risk=b["notional"] * r.sd, closed=False))
    ex = pd.DataFrame(done, columns=["id", "coin", "kind", "side", "entry_t", "exit_t", "notional", "pnl", "risk", "closed"])
    ex["R"] = np.where(ex["risk"] > 0, ex["pnl"] / ex["risk"].where(ex["risk"] > 0, 1.0), np.nan)
    return dict(times=tl, eq=eq, eq_closed=eq_closed, trades=ex, skipped=skipped, initial=rules.initial, coins=list(closes))


def curve_metrics(times: np.ndarray, eq: np.ndarray, initial: float) -> dict:
    """CAGR, DD maximo (sobre la curva con el capital inicial adelante) y Calmar."""
    if len(eq) == 0:
        return dict(cagr=0.0, dd=0.0, calmar=0.0, final=initial, years=0.0)
    step = np.median(np.diff(times)) if len(times) > 1 else np.timedelta64(0, "D")   # hasta el CIERRE de la ultima vela
    years = max((times[-1] - times[0] + step) / np.timedelta64(1, "D") / 365.25, 1e-9)
    full = np.r_[initial, eq]
    cagr = (eq[-1] / initial) ** (1.0 / years) - 1.0 if eq[-1] > 0 else -1.0
    dd = float(((np.maximum.accumulate(full) - full) / np.maximum.accumulate(full)).max())
    calmar = cagr / dd if dd > 1e-12 else (float("inf") if cagr > 0 else 0.0)
    return dict(cagr=float(cagr), dd=dd, calmar=float(calmar), final=float(eq[-1]), years=float(years))


def buyhold_btc(btc: tuple, timeline: np.ndarray, initial: float = 10000.0) -> np.ndarray:
    c = aligned_closes({"BTC": btc}, timeline)[0]
    return initial * c / c[0]


def buyhold_ew(closes: dict, timeline: np.ndarray, initial: float = 10000.0) -> np.ndarray:
    """1/N por moneda, entra en su primera vela dentro del tramo, sin rebalancear; antes de listarse queda en efectivo."""
    C = aligned_closes(closes, timeline)
    n = len(closes)
    tot = np.zeros(len(timeline))
    for row in C:
        valid = ~np.isnan(row)
        if not valid.any():
            tot += initial / n
            continue
        first = int(np.argmax(valid))
        ratio = np.where(valid, row / row[first], 1.0)
        tot += initial / n * ratio
    return tot


def e_episodes(cl: pd.DataFrame) -> int:
    """Episodios de la senal E: sub-trades de E de una misma moneda que se solapan en el tiempo cuentan como 1."""
    n = 0
    for _, g in cl[cl["kind"] == "E"].groupby("coin"):
        end = None
        for r in g.sort_values("entry_t").itertuples():
            if end is None or r.entry_t >= end:
                n += 1
                end = r.exit_t
            else:
                end = max(end, r.exit_t)
    return n


def group_report(res: dict) -> dict:
    """n (cerrados), PnL por moneda, mediana por moneda, concentracion maxima, R medio, curva cerrada y marcada."""
    t = res["trades"]
    cl = t[t["closed"]]
    pc = t.groupby("coin")["pnl"].sum().reindex(res["coins"], fill_value=0.0)   # monedas sin trades cuentan 0
    total = float(pc.sum())
    conc = float(pc.max() / total) if total > 0 else float("nan")
    m = curve_metrics(res["times"], res["eq"], res["initial"])
    mc = curve_metrics(res["times"], res["eq_closed"], res["initial"])
    n_sub = int(len(cl))
    return dict(n=int((cl["kind"] != "E").sum()) + e_episodes(cl), n_sub=n_sub, n_abiertos=int((~t["closed"]).sum()), skipped=len(res["skipped"]), pnl_total=total,
                pnl_mediana_moneda=float(pc.median()) if len(pc) else 0.0, conc_max=conc,
                R_medio=float(cl["R"].mean()) if len(cl) else 0.0, **m,
                cagr_cerrada=mc["cagr"], dd_cerrada=mc["dd"], calmar_cerrada=mc["calmar"])
