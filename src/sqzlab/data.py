"""Carga de velas desde data/ y construccion de 1W por resampleo de 1d."""
from __future__ import annotations

import pandas as pd

from .fetch import path_for


def load(source: str, sym: str, tf: str, start=None, end=None) -> pd.DataFrame:
    """tf: '1d', '4h' o '1w' (la semanal se arma desde 1d). start/end filtran por time_utc (end inclusive)."""
    if tf == "1w":
        df = to_weekly(load(source, sym, "1d"))
    else:
        df = pd.read_csv(path_for(source, sym, tf), parse_dates=["time_utc"])
    if start is not None:
        df = df[df["time_utc"] >= pd.Timestamp(start)]
    if end is not None:
        df = df[df["time_utc"] <= pd.Timestamp(end)]
    return df.reset_index(drop=True)


def to_weekly(d1: pd.DataFrame, week_start: str = "W-MON") -> pd.DataFrame:
    """Semanas que abren el lunes 00:00 UTC (hipotesis a confirmar calibrando contra la base semanal de TV)."""
    x = d1.set_index("time_utc")
    w = x.resample(week_start, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    w = w.dropna(subset=["open"]).reset_index()
    return w
