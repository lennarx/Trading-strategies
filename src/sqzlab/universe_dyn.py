"""Fase 8: universo DINAMICO diario (top 20 por liquidez), sin lookahead. Reglas en docs/PROTOCOLO.md (Fase 8, secciones 2 y 3).

Para el dia t se usan SOLO datos <= t-1:
  elegible = >= 365 velas diarias de historia (calendario, de la primera vela a t-1)
             y mediana del volumen en USD de los 30 dias t-30..t-1 (dia faltante = 0) >= 2.000.000
  universo(t) = las 20 elegibles de mayor mediana (empates por id alfabetico); si hay menos de 20, todas.
Ademas una moneda cuyos datos terminaron antes de t no es elegible. Los datos de una moneda se cortan donde el cierre salta
mas de 20x (o menos de 1/20) en un dia (reemplazo de ticker / redenominacion): el tramo posterior es una moneda nueva `BASE#2`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .f8data import load_f8

TOP_N = 20
MIN_HIST = 365
MIN_MEDIAN_USD = 2_000_000.0
MED_WINDOW = 30
SPLIT_RATIO = 20.0

STABLE_FIAT = {"USDC", "USDP", "TUSD", "BUSD", "FDUSD", "DAI", "USDD", "PYUSD", "AEUR", "EUR", "UST", "USTC", "USDT", "GBP", "TRY", "BRL",
               "ARS", "AUD", "RUB", "UAH", "NGN", "IDRT", "BIDR", "BVND", "EURI", "USD1", "USDE", "XUSD", "RLUSD", "USDS", "ZAR", "PLN",
               "RON", "CZK", "JPY", "MXN", "COP", "VAI", "SUSD", "LUSD", "GUSD", "HUSD", "PAX", "USDSB", "BKRW"}
WRAPPED = {"WBTC", "WBETH", "WBNB", "BETH", "STETH", "WETH", "WAVAX", "WSTETH", "RETH", "CBETH", "SBTC", "RENBTC", "HBTC", "TBTC"}
GOLD = {"PAXG", "XAUT"}
LEVERAGED_SUFFIX = ("UP", "DOWN", "BULL", "BEAR")


def excluded_names(bases) -> dict[str, str]:
    """{base: motivo} por NOMBRE: stable/fiat, envueltos, oro, apalancados (base = otra base listada + sufijo UP/DOWN/BULL/BEAR)."""
    bs = set(bases)
    out = {}
    for b in sorted(bs):
        if b in STABLE_FIAT:
            out[b] = "stable/fiat"
        elif b in WRAPPED:
            out[b] = "envuelto/staked"
        elif b in GOLD:
            out[b] = "respaldado por oro"
        else:
            for suf in LEVERAGED_SUFFIX:
                if b.endswith(suf) and b[:-len(suf)] in bs and len(b) > len(suf):
                    out[b] = "apalancado"
                    break
    return out


def is_pegged(close: pd.Series) -> bool:
    """Regla de peg: mediana del cierre en [0,97; 1,03] y percentil 99 - percentil 1 < 0,10 en toda la vida."""
    c = close.dropna()
    if len(c) < 30:
        return False
    return bool(0.97 <= c.median() <= 1.03 and (c.quantile(0.99) - c.quantile(0.01)) < 0.10)


def split_points(close: np.ndarray, ratio: float = SPLIT_RATIO) -> list[int]:
    """Indices i donde el cierre salta mas de `ratio`x (o menos de 1/ratio) respecto del cierre previo: el tramo nuevo empieza en i."""
    c = np.asarray(close, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = c[1:] / c[:-1]
    bad = np.where((r > ratio) | (r < 1.0 / ratio))[0] + 1
    return [int(i) for i in bad]


def fill_calendar(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Reindexa a la grilla completa de la vida de la moneda: velas faltantes = ultimo cierre (o=h=l=c), volumen 0, `filled`=True."""
    d = df.set_index("time_utc")
    idx = pd.date_range(d.index[0], d.index[-1], freq=freq)
    out = d.reindex(idx)
    filled = out["close"].isna()
    out["close"] = out["close"].ffill()
    for c in ("open", "high", "low"):
        out[c] = out[c].fillna(out["close"])
    out["volume"] = out["volume"].fillna(0.0)
    out["qvol"] = out["qvol"].fillna(0.0)
    out["filled"] = filled
    out.index.name = "time_utc"
    return out.reset_index()


@dataclass
class Asset:
    id: str
    base: str
    df: pd.DataFrame                 # grilla completa (diaria o 4h), columnas time_utc, open, high, low, close, volume, qvol, filled
    split_from: pd.Timestamp | None = None   # fecha de inicio del tramo (si viene de un corte)
    split_to: pd.Timestamp | None = None     # fecha (exclusiva) donde el tramo termina por un corte
    meta: dict = field(default_factory=dict)

    @property
    def first(self) -> pd.Timestamp:
        return self.df["time_utc"].iloc[0]

    @property
    def last(self) -> pd.Timestamp:
        return self.df["time_utc"].iloc[-1]


def load_assets_daily(bases, clip: bool = True, live: bool = False) -> tuple[dict[str, Asset], dict[str, str], list[dict]]:
    """Carga los CSV diarios de data/f8/1d, descarta por nombre y por peg, corta en saltos y rellena huecos.
    Devuelve (assets, excluidos {base: motivo}, cortes [dict])."""
    bases = list(bases)
    excl = excluded_names(bases)
    assets: dict[str, Asset] = {}
    cuts: list[dict] = []
    for b in sorted(bases):
        if b in excl:
            continue
        raw = load_f8(b, "1d", clip, live)
        if is_pegged(raw["close"]):
            excl[b] = "peg (regla mecanica)"
            continue
        pts = split_points(raw["close"].to_numpy())
        bounds = [0] + pts + [len(raw)]
        for k in range(len(bounds) - 1):
            seg = raw.iloc[bounds[k]:bounds[k + 1]]
            if len(seg) == 0:
                continue
            aid = b if k == 0 else f"{b}#{k + 1}"
            a = Asset(aid, b, fill_calendar(seg.reset_index(drop=True), "1D"),
                      split_from=seg["time_utc"].iloc[0] if k > 0 else None,
                      split_to=raw["time_utc"].iloc[bounds[k + 1]] if k < len(bounds) - 2 else None)
            assets[aid] = a
        for i in pts:
            cuts.append(dict(base=b, date=str(raw["time_utc"].iloc[i].date()), ratio=float(raw["close"].iloc[i] / raw["close"].iloc[i - 1])))
    return assets, excl, cuts


def build_universe(assets: dict[str, Asset], dates: pd.DatetimeIndex, top_n: int = TOP_N, min_hist: int = MIN_HIST,
                   min_med: float = MIN_MEDIAN_USD, win: int = MED_WINDOW) -> dict[str, pd.DataFrame]:
    """Panel (fechas x ids) con: `med` (mediana 30d del volumen USD usando solo datos <= t-1), `elig` (bool) y `top` (bool).
    `dates` es la grilla diaria sobre la que se evalua (debe cubrir desde antes de la primera moneda)."""
    ids = sorted(assets)
    full = pd.date_range(min(a.first for a in assets.values()), dates[-1], freq="1D")
    vol = pd.DataFrame(0.0, index=full, columns=ids)
    first = {}
    last = {}
    for i in ids:
        a = assets[i]
        s = a.df.set_index("time_utc")["qvol"]
        vol.loc[s.index.intersection(full), i] = s.loc[s.index.intersection(full)].to_numpy()
        first[i], last[i] = a.first, a.last
    med = vol.rolling(win, min_periods=win).median().shift(1)               # dia t -> t-win..t-1
    t = full.to_numpy("datetime64[ns]")[:, None]
    fst = np.array([np.datetime64(first[i]) for i in ids])[None, :]
    lst = np.array([np.datetime64(last[i]) for i in ids])[None, :]
    hist_ok = (t - np.timedelta64(1, "D") - fst) >= np.timedelta64(min_hist - 1, "D")   # velas de t-1 hacia atras desde la primera: >= min_hist
    alive = t <= lst
    elig = hist_ok & alive & (med.to_numpy() >= min_med)
    score = np.where(elig, med.to_numpy(), -np.inf)
    top = np.zeros_like(elig)
    for k in range(len(full)):
        row = score[k]
        n_ok = int(np.isfinite(row).sum())
        if n_ok == 0:
            continue
        order = np.argsort(-row, kind="stable")[: min(top_n, n_ok)]           # estable sobre ids alfabeticos: empate -> alfabetico
        top[k, order] = True
    idx = full
    res = dict(med=med, elig=pd.DataFrame(elig, idx, ids), top=pd.DataFrame(top, idx, ids))
    return {k: v.loc[v.index.isin(dates)] if k != "med" else v.loc[v.index.isin(dates)] for k, v in res.items()}
