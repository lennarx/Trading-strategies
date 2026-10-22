"""Fase 7: arma el grupo Z3 (monedas Binance spot USDT nunca usadas) con la regla fijada en docs/PROTOCOLO.md (seccion 5).

Regla: exchangeInfo spot de Binance -> pares <BASE>USDT con status TRADING; fuera las bases ya usadas, stablecoins y fiat,
envueltos/staked, apalancados (UP/DOWN/BULL/BEAR) y respaldados por oro; orden alfabetico por base; recorrer y quedarse con las
que tienen primera vela 1D <= 2021-10-20 y pasan los descartes de huecos de la 6.1 (4h: <= 10 velas faltantes y ningun hueco
> 2 dias; error de descarga = descarte), hasta 24. Se registran los descartes. Sin red -> falla y se reporta (no se esquiva).

Uso:  python -m sqzlab.z3        (escribe results/z3_universe.json y .md; baja los CSV a data/)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from . import universe as U
from .fetch import _get, fetch_binance, path_for
from .optimize import RESULTS

FIRST_1D_MAX = pd.Timestamp("2021-10-20")
MAX_Z3 = 24
STABLE_FIAT = {"USDC", "USDP", "TUSD", "BUSD", "FDUSD", "DAI", "USDD", "PYUSD", "AEUR", "EUR", "UST", "USTC", "USDT", "GBP", "TRY",
               "BRL", "ARS", "AUD", "RUB", "UAH", "NGN", "IDRT", "BIDR", "BVND", "EURI", "USD1", "USDE", "XUSD", "RLUSD", "USDS"}
WRAPPED = {"WBTC", "WBETH", "WBNB", "BETH", "STETH", "WETH", "WAVAX", "WSTETH", "RETH", "CBETH", "SBTC", "RENBTC", "HBTC", "TBTC"}
GOLD = {"PAXG", "XAUT"}
LEVERAGED_SUFFIX = ("UP", "DOWN", "BULL", "BEAR")


def used_bases() -> set[str]:
    return set(U.TRAIN) | set(U.HOLDOUT) | set(U.FRESH_Z1) | set(U.FRESH_Z2)


def eligible_bases() -> list[str]:
    info = _get("https://api.binance.com/api/v3/exchangeInfo", {})
    bases = set()
    for s in info["symbols"]:
        if s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING" and s.get("isSpotTradingAllowed", True):
            bases.add(s["baseAsset"])
    out = []
    for b in sorted(bases):
        if b in used_bases() or b in STABLE_FIAT or b in WRAPPED or b in GOLD or b.endswith(LEVERAGED_SUFFIX):
            continue
        out.append(b)
    return out


def first_1d(sym: str) -> pd.Timestamp | None:
    page = _get("https://api.binance.com/api/v3/klines", {"symbol": f"{sym}USDT", "interval": "1d", "limit": 1, "startTime": 0})
    return pd.to_datetime(int(page[0][0]), unit="ms") if page else None


def screen(sym: str) -> tuple[bool, str]:
    """(pasa, motivo). Baja 1d y 4h a data/ solo si la primera vela 1D es suficientemente vieja."""
    f = first_1d(sym)
    if f is None:
        return False, "sin velas 1D"
    if f > FIRST_1D_MAX:
        return False, f"primera vela 1D {f.date()} (> 2021-10-20)"
    for tf in ("1d", "4h"):
        try:
            df = fetch_binance(sym, tf)
        except Exception as e:  # no esquivar: descartar y anotar
            return False, f"fallo de descarga {tf}: {e!r}"
        if df.empty:
            return False, f"vacio {tf}"
        df.to_csv(path_for("binance", sym, tf), index=False, date_format="%Y-%m-%d %H:%M:%S")
        if tf == "4h":
            t = df["time_utc"]
            expected = int((t.iloc[-1] - t.iloc[0]) / pd.Timedelta(hours=4)) + 1
            missing, biggest = expected - len(t), t.diff().max()
            if missing > U.FRESH_MAX_MISSING_4H or biggest > pd.Timedelta(days=2):
                return False, f"huecos en 4h ({missing} velas faltantes, hueco max {biggest})"
    return True, f"ok (primera vela 1D {f.date()})"


def main() -> None:
    cands = eligible_bases()
    print(f"{len(cands)} bases elegibles tras los filtros de nombre")
    ok, disc = [], {}
    scanned = 0
    for sym in cands:
        if len(ok) >= MAX_Z3:
            break
        scanned += 1
        passed, why = screen(sym)
        print(f"{sym}: {'OK' if passed else 'DESCARTE'} - {why}")
        if passed:
            ok.append(sym)
        else:
            disc[sym] = why
    res = dict(fecha=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), elegibles=len(cands), recorridas=scanned,
               sobrevivientes=ok, descartes=disc)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "z3_universe.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    md = (f"# Z3: universo (generado por `python -m sqzlab.z3`, {res['fecha']})\n\nRegla en `docs/PROTOCOLO.md` (Fase 7, seccion 5). "
          f"{len(cands)} bases elegibles tras filtros de nombre; se recorrieron {scanned} en orden alfabetico.\n\n"
          f"**Sobrevivientes ({len(ok)}):** {', '.join(ok)}\n\n**Descartes ({len(disc)}):**\n\n"
          + "\n".join(f"- {k}: {v}" for k, v in disc.items()) + "\n")
    (RESULTS / "z3_universe.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
