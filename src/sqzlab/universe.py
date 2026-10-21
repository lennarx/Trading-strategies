"""Universo de monedas, cortes temporales y carga de datos para la optimizacion (Fase 4).

Todo esto esta fijado en docs/PROTOCOLO.md ("Decisiones fijadas ANTES de la primera corrida del optimizador").
Una sola fuente por moneda (la de historia mas larga); nunca la misma moneda de dos fuentes.
"""
from __future__ import annotations

import pandas as pd

from .data import load

TRAIN = {"BTC": "bitstamp", "ETH": "bitstamp", "XRP": "bitstamp", "LTC": "bitstamp", "ADA": "binance", "DOGE": "binance"}
HOLDOUT = {"SOL": "binance", "LINK": "binance", "BNB": "binance", "BCH": "bitstamp", "XLM": "bitstamp"}
SOURCES = {**TRAIN, **HOLDOUT}

ENTRY_FROM = pd.Timestamp("2017-01-01")          # solo cuentan trades con entrada desde aca
TRAIN_END = pd.Timestamp("2023-12-31 23:59:59")  # D1/H4: train = 2017-01-01..2023-12-31, test = 2024-01-01..hoy
TEST_FROM = pd.Timestamp("2024-01-01")
DATA_END = {"1d": "2026-10-20", "1w": "2026-10-19", "4h": "2026-10-20 20:00"}   # ultima vela cerrada del dia fijado
WARMUP_FROM = "2016-01-01"                       # D1/H4; W1 usa todo el historial (EMA200 semanal = 200 semanas)

# walk-forward informativo de H4: (train desde, train hasta, test desde, test hasta)
WALK_FORWARD = [
    ("2017-01-01", "2019-12-31", "2020-01-01", "2020-12-31"),
    ("2018-01-01", "2020-12-31", "2021-01-01", "2021-12-31"),
    ("2019-01-01", "2021-12-31", "2022-01-01", "2022-12-31"),
    ("2020-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
]

TF_CODE = {"h4": "4h", "d1": "1d", "w1": "1w"}


def load_coin(sym: str, tf: str) -> pd.DataFrame:
    """tf en codigo de data ('4h', '1d', '1w'). Warm-up completo, cortado en la ultima vela cerrada fijada."""
    start = None if tf == "1w" else WARMUP_FROM
    return load(SOURCES[sym], sym, tf, start=start, end=DATA_END[tf])


def load_universe(tf: str, group: str = "all") -> dict[str, pd.DataFrame]:
    coins = {"train": TRAIN, "holdout": HOLDOUT, "all": SOURCES}[group]
    return {s: load_coin(s, tf) for s in coins}
