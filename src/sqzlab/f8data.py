"""Fase 8: datos de Binance spot de TODOS los pares *USDT (incluidos los deslistados) a data/f8/<TF>/<BASE>.csv.

Fuentes (docs/PROTOCOLO.md, "Decisiones fijadas ANTES de la Fase 8", seccion 2):
  - pares presentes hoy en `exchangeInfo` (cualquier status): API publica api.binance.com/api/v3/klines (historia completa);
  - pares que ya no estan en `exchangeInfo` (deslistados): data.binance.vision (zips mensuales + zips diarios del mes final).
Columnas: time_utc,open,high,low,close,volume,qvol  (qvol = volumen en USDT ~ USD). UTC. Se corta en END (ultima vela CERRADA fijada).
Si algo se bloquea NO se esquiva: queda en el manifiesto como fallo y se informa.

Uso:  python -m sqzlab.f8data --tf 1d              (todos los pares USDT)
      python -m sqzlab.f8data --tf 4h --bases BTC ETH ...
"""
from __future__ import annotations

import argparse
import io
import json
import re
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from .fetch import DATA, TF_SECONDS

F8 = DATA / "f8"
F8_LIVE = DATA / "f8_live"   # uso en vivo (bot): copia aparte para no mezclar con los datos del backtest
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
VISION = "https://data.binance.vision"
API = "https://api.binance.com/api/v3"
END = {"1d": pd.Timestamp("2026-10-21"), "4h": pd.Timestamp("2026-10-21 20:00")}   # ultima vela CERRADA fijada (PROTOCOLO Fase 8, seccion 2)
COLS = ["time_utc", "open", "high", "low", "close", "volume", "qvol"]
_SESSION = requests.Session()


def _get(url: str, params: dict | None = None, raw: bool = False, tries: int = 6):
    last = None
    for a in range(tries):
        try:
            r = _SESSION.get(url, params=params, timeout=40)
            if r.status_code in (429, 418, 500, 502, 503, 504):
                time.sleep(2 * (a + 1))
                continue
            r.raise_for_status()
            return r.content if raw else r.json()
        except requests.RequestException as e:      # reintenta; si persiste, el llamador lo anota como fallo
            last = e
            time.sleep(1 + a)
    raise RuntimeError(f"fallo persistente en {url} {params}: {last!r}")


def s3_list(prefix: str, delimiter: str | None = "/") -> tuple[list[str], list[str]]:
    """(keys, common_prefixes) del bucket data.binance.vision bajo `prefix`, con paginacion por marker."""
    keys, prefixes, marker = [], [], ""
    while True:
        params = {"prefix": prefix, "marker": marker}
        if delimiter:
            params["delimiter"] = delimiter
        xml = _get(S3, params, raw=True).decode("utf-8")
        keys += re.findall(r"<Key>([^<]+)</Key>", xml)
        prefixes += re.findall(r"<CommonPrefixes><Prefix>([^<]+)</Prefix></CommonPrefixes>", xml)
        if "<IsTruncated>true</IsTruncated>" not in xml:
            break
        m = re.search(r"<NextMarker>([^<]+)</NextMarker>", xml)
        marker = m.group(1) if m else (keys[-1] if keys else prefixes[-1])
    return keys, prefixes


def vision_symbols() -> list[str]:
    """Todos los simbolos *USDT con klines mensuales en data.binance.vision (incluye los deslistados)."""
    _, pre = s3_list("data/spot/monthly/klines/")
    return sorted(p.rstrip("/").split("/")[-1] for p in pre if p.rstrip("/").endswith("USDT"))


def exchange_usdt() -> dict[str, str]:
    """{base: status} de los pares <BASE>USDT que HOY existen en exchangeInfo (cualquier status)."""
    info = _get(f"{API}/exchangeInfo")
    return {s["baseAsset"]: s["status"] for s in info["symbols"] if s.get("quoteAsset") == "USDT"}


def _to_df(rows: list[list]) -> pd.DataFrame:
    df = pd.DataFrame([[r[0], r[1], r[2], r[3], r[4], r[5], r[7]] for r in rows], columns=["ms", "open", "high", "low", "close", "volume", "qvol"])
    ms = pd.to_numeric(df["ms"]).astype("int64")
    ms = ms.where(ms < 10**14, ms // 1000)           # desde 2025 los zips de spot traen microsegundos
    df["time_utc"] = pd.to_datetime(ms, unit="ms")
    for c in ["open", "high", "low", "close", "volume", "qvol"]:
        df[c] = df[c].astype(float)
    return df[COLS]


def fetch_api(symbol: str, tf: str, start_ms: int = 0) -> pd.DataFrame:
    step = TF_SECONDS[tf] * 1000
    rows, start = [], start_ms
    while True:
        page = _get(f"{API}/klines", {"symbol": symbol, "interval": tf, "limit": 1000, "startTime": start})
        if not page:
            break
        rows += page
        nxt = int(page[-1][0]) + step
        if len(page) < 1000 or nxt <= start:
            break
        start = nxt
    return _to_df(rows) if rows else pd.DataFrame(columns=COLS)


def _zip_rows(content: bytes) -> list[list]:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        txt = z.read(z.namelist()[0]).decode("utf-8")
    rows = []
    for ln in txt.splitlines():
        p = ln.split(",")
        if len(p) >= 8 and p[0].strip().isdigit():
            rows.append(p)
    return rows


def fetch_vision(symbol: str, tf: str) -> pd.DataFrame:
    """Zips mensuales y, para el mes final (sin zip mensual todavia), los zips diarios."""
    mk, _ = s3_list(f"data/spot/monthly/klines/{symbol}/{tf}/")
    mk = [k for k in mk if k.endswith(".zip")]
    rows: list[list] = []
    for k in mk:
        rows += _zip_rows(_get(f"{VISION}/{k}", raw=True))
    last_month = max((re.search(r"-(\d{4}-\d{2})\.zip", k).group(1) for k in mk), default="")
    dk, _ = s3_list(f"data/spot/daily/klines/{symbol}/{tf}/")
    for k in dk:
        if not k.endswith(".zip"):
            continue
        d = re.search(r"-(\d{4}-\d{2})-\d{2}\.zip", k).group(1)
        if d > last_month:
            rows += _zip_rows(_get(f"{VISION}/{k}", raw=True))
    return _to_df(rows) if rows else pd.DataFrame(columns=COLS)


def path_f8(base: str, tf: str, live: bool = False) -> Path:
    return (F8_LIVE if live else F8) / tf / f"{base}.csv"


def load_f8(base: str, tf: str, clip: bool = True, live: bool = False) -> pd.DataFrame:
    """clip=True (backtest): corta en END; clip=False (uso en vivo): todas las velas cerradas bajadas. live=True prefiere data/f8_live/ si existe."""
    p = path_f8(base, tf, True) if live and path_f8(base, tf, True).exists() else path_f8(base, tf)
    df = pd.read_csv(p, parse_dates=["time_utc"])
    return df[df["time_utc"] <= END[tf]].reset_index(drop=True) if clip else df


def _clean(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    df = df.drop_duplicates("time_utc").sort_values("time_utc")
    df = df[df["time_utc"] <= END[tf]]
    return df.reset_index(drop=True)


def download_one(base: str, tf: str, listed: bool) -> dict:
    sym = f"{base}USDT"
    out = dict(base=base, source="api" if listed else "vision", ok=False)
    try:
        df = _clean(fetch_api(sym, tf), tf) if listed else pd.DataFrame(columns=COLS)
        if df.empty:                                   # no esta en exchangeInfo, o la API no devuelve nada: data.binance.vision
            out["source"] = "vision"
            df = _clean(fetch_vision(sym, tf), tf)
        if df.empty:
            out["error"] = "vacio"
            return out
        path_f8(base, tf).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path_f8(base, tf), index=False, date_format="%Y-%m-%d %H:%M:%S")
        step = pd.Timedelta(seconds=TF_SECONDS[tf])
        expected = int((df["time_utc"].iloc[-1] - df["time_utc"].iloc[0]) / step) + 1
        out.update(ok=True, n=len(df), first=str(df["time_utc"].iloc[0]), last=str(df["time_utc"].iloc[-1]), missing=expected - len(df))
    except Exception as e:      # no esquivar: anotar el fallo
        out["error"] = repr(e)
    return out


def download(tf: str, bases: list[str] | None = None, workers: int = 8) -> dict:
    ex = exchange_usdt()
    vis = [s[:-4] for s in vision_symbols()]
    universe = sorted(set(ex) | set(vis)) if bases is None else sorted(bases)
    jobs = [(b, tf, b in ex) for b in universe]
    with ThreadPoolExecutor(workers) as pool:
        res = list(pool.map(lambda j: download_one(*j), jobs))
    man = dict(tf=tf, end=str(END[tf]), n_exchange=len(ex), n_vision=len(vis), n_vision_not_in_exchange=len(set(vis) - set(ex)),
               n_exchange_not_in_vision=len(set(ex) - set(vis)), descargados=sum(r["ok"] for r in res),
               fallos={r["base"]: r.get("error") for r in res if not r["ok"]}, pares=res)
    F8.mkdir(parents=True, exist_ok=True)
    (F8 / f"_manifest_{tf}.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    return man


def update_all(tf: str = "1d", now: pd.Timestamp | None = None, workers: int = 8) -> dict:
    """Uso en vivo (signals --strategy r1fiel): actualiza data/f8/<tf>/ de los pares que HOY tienen status TRADING bajando desde unas velas antes de la
    ultima conocida; pares nuevos se bajan completos. Guarda SOLO velas cerradas (apertura + paso <= ahora UTC). No recorta en END."""
    now = now if now is not None else pd.Timestamp.now(tz="UTC").tz_localize(None)
    step = pd.Timedelta(seconds=TF_SECONDS[tf])
    ex = exchange_usdt()
    live = sorted(b for b, st in ex.items() if st == "TRADING")

    def one(base: str) -> str:
        try:
            p = path_f8(base, tf, True)
            src = p if p.exists() else path_f8(base, tf)             # la 1.a vez se parte de la copia del backtest
            old = pd.read_csv(src, parse_dates=["time_utc"]) if src.exists() else None
            start = 0 if old is None else int((old["time_utc"].iloc[-1] - 5 * step).timestamp() * 1000)
            new = fetch_api(f"{base}USDT", tf, start)
            df = new if old is None else pd.concat([old, new])
            df = df.drop_duplicates("time_utc", keep="last").sort_values("time_utc")
            df = df[df["time_utc"] + step <= now].reset_index(drop=True)
            if df.empty:
                return "vacio"
            p.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(p, index=False, date_format="%Y-%m-%d %H:%M:%S")
            return "ok"
        except Exception as e:      # no esquivar: anotar
            return repr(e)

    with ThreadPoolExecutor(workers) as pool:
        res = dict(zip(live, pool.map(one, live)))
    return dict(actualizados=sum(v == "ok" for v in res.values()), fallos={k: v for k, v in res.items() if v != "ok"})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", choices=["1d", "4h"], required=True)
    ap.add_argument("--bases", nargs="*", default=None)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    m = download(a.tf, a.bases, a.workers)
    print({k: v for k, v in m.items() if k not in ("pares", "fallos")})
    print("fallos:", m["fallos"])


if __name__ == "__main__":
    main()
