"""Fase 6.2: forward test con los params CONGELADOS. Es el unico OOS de verdad en el tiempo.

Uso:  python -m sqzlab.forward [--tf h4 d1 w1] [--no-fetch]
Re-baja (incremental) las velas del universo completo, simula con `params/<tf>.json` tal como estan hoy y guarda en
`results/forward/<tf>.csv` los trades CERRADOS con entrada >= FORWARD_FROM. Idempotente: correrlo dos veces no duplica
(los trades ya guardados no se reescriben; si una vela vieja fue revisada por el exchange y el trade cambia, avisa).
Si el contenido de params/<tf>.json cambia (se guarda el hash, sin `_meta`) arranca una SERIE NUEVA y la anterior queda
archivada. Resumen en `results/forward.md`.

Regla fijada ANTES (docs/PROTOCOLO.md): se evalua UNA sola vez, al llegar a n >= 100 trades en H4 (en D1 cuando de);
mientras tanto solo se mira para cuidar que los datos esten bien, nunca para tocar parametros.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone

import pandas as pd

from . import universe as U
from .fetch import TF_SECONDS, update_csv
from .genpine import load_params
from .metrics import breakdown, summarize, trade_frame, window
from .optimize import BASE, ROOT, md_table
from .data import load
from .indicators import compute
from .strategy import DEFAULTS, simulate

FORWARD_FROM = pd.Timestamp("2026-10-22")
OUT = ROOT / "results" / "forward"
KEY = ["coin", "kind", "side", "entry_t"]
STEP = {"4h": pd.Timedelta(hours=4), "1d": pd.Timedelta(days=1), "1w": pd.Timedelta(days=7)}


def universe() -> dict[str, str]:
    """Todas las monedas conocidas (train, holdout, Z1, Z2): en el forward ninguna esta 'quemada', todas son tiempo nuevo."""
    return {**U.TRAIN, **U.HOLDOUT, **U.FRESH_Z1, **U.FRESH_Z2}


def params_hash(tf: str) -> str:
    return hashlib.sha256(json.dumps(load_params(tf), sort_keys=True).encode()).hexdigest()[:16]


def closed_only(df: pd.DataFrame, tf: str, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Saca la vela en curso: una vela esta cerrada si su apertura + paso <= ahora (UTC)."""
    now = now if now is not None else pd.Timestamp(datetime.now(timezone.utc).replace(tzinfo=None))
    return df[df["time_utc"] + STEP[tf] <= now].reset_index(drop=True)


def simulate_tf(tf: str, fetch: bool = True, now: pd.Timestamp | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(trades cerrados con entrada >= FORWARD_FROM, trades abiertos) del universo completo con los params vigentes."""
    code = U.TF_CODE[tf]
    params = {**BASE, **load_params(tf)}
    closed, opened = [], []
    for sym, src in universe().items():
        if fetch:
            try:
                update_csv(src, sym, "1d" if code == "1w" else code)
            except Exception as e:  # no esquivar bloqueos: reportar y seguir con lo que hay
                print(f"FALLO {src} {sym}: {e!r}")
        start = None if code == "1w" else U.WARMUP_FROM
        df = closed_only(load(src, sym, code, start=start), code, now)
        ind = compute(df, {**DEFAULTS, **params})
        res = simulate(df, ind=ind, **params)
        closed.append(trade_frame(res, sym, ind["atr"]))
        if res.open_trade is not None and df["time_utc"].iloc[res.open_trade.entry_i] >= FORWARD_FROM:
            t = res.open_trade
            opened.append(dict(coin=sym, kind=t.kind, side=t.side, entry_t=df["time_utc"].iloc[t.entry_i], stop=t.stop,
                               R_abierto=t.r_net))
    tr = window(pd.concat(closed, ignore_index=True), FORWARD_FROM)
    return tr, pd.DataFrame(opened, columns=["coin", "kind", "side", "entry_t", "stop", "R_abierto"])


def merge_saved(saved: pd.DataFrame, fresh: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Los trades guardados no se tocan; se agregan los nuevos. Devuelve (tabla, avisos de trades guardados que hoy dan distinto)."""
    if saved.empty:
        return fresh, []
    m = saved.merge(fresh[KEY + ["R"]], on=KEY, how="left", suffixes=("", "_hoy"))
    warns = [f"{r.coin} {r.kind} {r.side:+d} {r.entry_t}: R guardado {r.R:.4f} vs hoy {r.R_hoy:.4f}"
             for r in m.itertuples() if pd.notna(r.R_hoy) and abs(r.R - r.R_hoy) > 1e-6]
    new = fresh.merge(saved[KEY], on=KEY, how="left", indicator=True).query("_merge == 'left_only'").drop(columns="_merge")
    out = pd.concat([saved, new], ignore_index=True).sort_values("entry_t", kind="stable").reset_index(drop=True)
    return out, warns


def update_series(tf: str, fresh: pd.DataFrame) -> tuple[pd.DataFrame, list[str], str]:
    """Aplica la regla de congelado: hash igual -> mezcla; hash distinto -> archiva la serie vieja y empieza otra."""
    OUT.mkdir(parents=True, exist_ok=True)
    meta_p, csv_p = OUT / f"{tf}_meta.json", OUT / f"{tf}.csv"
    h = params_hash(tf)
    note = ""
    meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
    if meta and meta.get("hash") != h:
        k = meta.get("series", 1)
        if csv_p.exists():
            csv_p.rename(OUT / f"{tf}_serie{k}_{meta['hash']}.csv")
        note = f"params/{tf}.json cambio (hash {meta['hash']} -> {h}): la serie {k} se archivo y arranca la {k + 1}."
        meta = dict(series=k + 1)
    saved = pd.read_csv(csv_p, parse_dates=["entry_t", "exit_t"]) if csv_p.exists() else pd.DataFrame(columns=fresh.columns)
    out, warns = merge_saved(saved, fresh)
    out.to_csv(csv_p, index=False, date_format="%Y-%m-%d %H:%M:%S")
    meta.update(hash=h, series=meta.get("series", 1), started=meta.get("started", str(FORWARD_FROM.date())),
                updated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    meta_p.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return out, warns, note


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", nargs="+", default=["h4", "d1", "w1"], choices=["h4", "d1", "w1"])
    ap.add_argument("--no-fetch", action="store_true", help="no re-bajar velas (usa lo que hay en data/)")
    a = ap.parse_args()
    sections = [f"# Forward test (generado por `python -m sqzlab.forward`)\n\nEntradas desde {FORWARD_FROM.date()}, params congelados "
                "(hash en `results/forward/<tf>_meta.json`). **Regla fijada antes:** se evalua UNA sola vez al llegar a n >= 100 trades "
                "en H4 (D1 cuando de); mientras tanto esto es solo para cuidar los datos, no para tocar parametros.\n"]
    for tf in a.tf:
        fresh, opened = simulate_tf(tf, fetch=not a.no_fetch)
        tr, warns, note = update_series(tf, fresh)
        sm = summarize(tr)
        meta = json.loads((OUT / f"{tf}_meta.json").read_text(encoding="utf-8"))
        txt = (f"\n## {tf.upper()} (serie {meta['series']}, hash `{meta['hash']}`, actualizado {meta['updated']})\n\n"
               f"- Cerrados: n={sm['n']}, R medio={sm['exp']:.3f}, PF={sm['pf']:.2f}, sin el mejor={sm['exp_ex_best']:.3f}R, "
               f"recortada={sm['exp_trim']:.3f}R, R total={sm['total']:.2f}. Abiertos: {len(opened)}.\n")
        if note:
            txt += f"- **{note}**\n"
        for w in warns:
            txt += f"- AVISO (dato revisado): {w}\n"
        if sm["n"]:
            txt += "\nPor moneda:\n\n" + md_table(breakdown(tr, "coin")) + "\nPor senal y lado:\n\n" + md_table(breakdown(tr, ["kind", "side"]))
        if len(opened):
            txt += "\nAbiertos (marca a mercado, no cuentan en las metricas):\n\n" + md_table(opened)
        sections.append(txt)
        print(f"[{tf}] cerrados={sm['n']} abiertos={len(opened)} {note}")
    (ROOT / "results" / "forward.md").write_text("".join(sections) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
