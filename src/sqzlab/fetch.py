"""Descarga de velas OHLCV a data/<fuente>_<SIMBOLO>_<tf>.csv (columnas time_utc,open,high,low,close,volume; UTC).

Fuentes:
  bitstamp: lo que mira TradingView en las bases (BTCUSD). Pagina hacia atras con `end`.
  binance:  spot <SIM>USDT (api.binance.com, publico; 1d y 4h alineados a 00:00 UTC), historia desde 2017-2020 segun moneda.
  bingx:    perpetuo USDT-M (swap v3), para BTC/ETH/SOL (y mas monedas). Pagina hacia atras por ventanas.

Uso:  python -m sqzlab.fetch --source bitstamp --symbols BTC ETH --tf 1d 4h
Si hay bloqueo de red NO se esquiva: el script falla con el error y hay que pedir el archivo.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import requests

DATA = Path(__file__).resolve().parents[2] / "data"
BITSTAMP_STEP = {"1d": 86400, "4h": 14400}
BINGX_INT = {"1d": "1d", "4h": "4h"}
TF_SECONDS = {"1d": 86400, "4h": 14400}
COLS = ["time_utc", "open", "high", "low", "close", "volume"]


def _get(url: str, params: dict) -> dict | list:
    for attempt in range(5):
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"rate limit persistente en {url}")


def fetch_bitstamp(sym: str, tf: str, since_ms: int | None = None) -> pd.DataFrame:
    pair = f"{sym.lower()}usd"
    step = BITSTAMP_STEP[tf]
    url = f"https://www.bitstamp.net/api/v2/ohlc/{pair}/"
    end = int(time.time())
    rows: list[dict] = []
    while True:
        js = _get(url, {"step": step, "limit": 1000, "end": end})
        page = js["data"]["ohlc"]
        if not page:
            break
        rows.extend(page)
        first = min(int(x["timestamp"]) for x in page)
        end = first - 1
        if since_ms is not None and first * 1000 <= since_ms:   # actualizacion incremental: ya cubrimos lo conocido
            break
        time.sleep(0.15)
    df = pd.DataFrame(rows)
    df["time_utc"] = pd.to_datetime(df["timestamp"].astype("int64"), unit="s")
    return _clean(df)


def fetch_bingx(sym: str, tf: str, since_ms: int | None = None) -> pd.DataFrame:
    """Perpetuo USDT-M (swap v3): velas diarias alineadas a 00:00 UTC y historia desde ~mayo-2021 (BTC/ETH).
    El spot de BingX NO sirve: limita la consulta a 380 dias y su vela diaria abre a las 16:00 UTC (UTC+8)."""
    url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"
    step_ms = TF_SECONDS[tf] * 1000
    end_ms = int(time.time() * 1000)
    rows: list[dict] = []
    empty_in_a_row = 0
    floor_ms = since_ms if since_ms is not None else 1_500_000_000_000
    while end_ms > floor_ms and empty_in_a_row < 3:  # no hay datos antes de 2017
        js = _get(url, {"symbol": f"{sym}-USDT", "interval": BINGX_INT[tf], "limit": 1000,
                        "startTime": end_ms - 1000 * step_ms, "endTime": end_ms})
        page = js.get("data") or []
        if page:
            rows.extend(page)
            empty_in_a_row = 0
        elif rows:
            empty_in_a_row += 1
        end_ms -= 1000 * step_ms
        if not rows and end_ms < 1_550_000_000_000:
            break
        time.sleep(0.2)
    df = pd.DataFrame(rows)
    df["time_utc"] = pd.to_datetime(df["time"].astype("int64"), unit="ms")
    return _clean(df)


def fetch_binance(sym: str, tf: str, since_ms: int | None = None) -> pd.DataFrame:
    """Spot SIMUSDT. Pagina hacia adelante con startTime (1000 velas por llamada). Sin workarounds de red."""
    url = "https://api.binance.com/api/v3/klines"
    step_ms = TF_SECONDS[tf] * 1000
    start = since_ms if since_ms is not None else 1_500_000_000_000   # 2017-07-14, antes del primer par de Binance
    rows: list[list] = []
    while True:
        page = _get(url, {"symbol": f"{sym}USDT", "interval": tf, "limit": 1000, "startTime": start})
        if not page:
            break
        rows.extend(page)
        nxt = int(page[-1][0]) + step_ms
        if nxt <= start or len(page) < 2:
            break
        start = nxt
        time.sleep(0.1)
    df = pd.DataFrame([r[:6] for r in rows], columns=["ms", "open", "high", "low", "close", "volume"])
    df["time_utc"] = pd.to_datetime(df["ms"].astype("int64"), unit="ms")
    return _clean(df)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df = df[COLS].drop_duplicates("time_utc").sort_values("time_utc").reset_index(drop=True)
    return df


def fetch(source: str, sym: str, tf: str, since_ms: int | None = None) -> pd.DataFrame:
    return {"bitstamp": fetch_bitstamp, "bingx": fetch_bingx, "binance": fetch_binance}[source](sym, tf, since_ms)


def update_csv(source: str, sym: str, tf: str, overlap: int = 10) -> pd.DataFrame:
    """Actualizacion incremental de data/<fuente>_<SIM>_<tf>.csv: baja solo desde `overlap` velas antes de la ultima
    conocida y mezcla (lo nuevo pisa lo viejo en las velas repetidas). Sin CSV previo hace la descarga completa."""
    p = path_for(source, sym, tf)
    if not p.exists():
        df = fetch(source, sym, tf)
    else:
        old = pd.read_csv(p, parse_dates=["time_utc"])
        since = int((old["time_utc"].iloc[-1] - pd.Timedelta(seconds=overlap * TF_SECONDS[tf])).timestamp() * 1000)
        new = fetch(source, sym, tf, since)
        df = _clean(pd.concat([old, new]).drop_duplicates("time_utc", keep="last")) if len(new) else old
    DATA.mkdir(exist_ok=True)
    df.to_csv(p, index=False, date_format="%Y-%m-%d %H:%M:%S")
    return df


def path_for(source: str, sym: str, tf: str) -> Path:
    return DATA / f"{source}_{sym.upper()}_{tf}.csv"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["bitstamp", "bingx", "binance"], required=True)
    ap.add_argument("--symbols", nargs="+", required=True)
    ap.add_argument("--tf", nargs="+", default=["1d", "4h"])
    a = ap.parse_args()
    DATA.mkdir(exist_ok=True)
    for sym in a.symbols:
        for tf in a.tf:
            try:
                df = fetch(a.source, sym, tf)
            except Exception as e:  # no esquivar bloqueos: reportar
                print(f"FALLO {a.source} {sym} {tf}: {e!r}")
                continue
            if df.empty:
                print(f"VACIO {a.source} {sym} {tf}")
                continue
            p = path_for(a.source, sym, tf)
            df.to_csv(p, index=False, date_format="%Y-%m-%d %H:%M:%S")
            print(f"{p.name}: {len(df)} velas, {df.time_utc.iloc[0]} -> {df.time_utc.iloc[-1]}")


if __name__ == "__main__":
    main()
