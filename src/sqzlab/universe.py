"""Universo de monedas, cortes temporales y carga de datos para la optimizacion (Fase 4).

Todo esto esta fijado en docs/PROTOCOLO.md ("Decisiones fijadas ANTES de la primera corrida del optimizador").
Una sola fuente por moneda (la de historia mas larga); nunca la misma moneda de dos fuentes.
"""
from __future__ import annotations

import pandas as pd

from .data import load

TRAIN = {"BTC": "bitstamp", "ETH": "bitstamp", "XRP": "bitstamp", "LTC": "bitstamp", "ADA": "binance", "DOGE": "binance"}
HOLDOUT = {"SOL": "binance", "LINK": "binance", "BNB": "binance", "BCH": "bitstamp", "XLM": "bitstamp"}
# Fase 6.1: monedas que el optimizador NUNCA vio (todas Binance spot USDT). Lista candidata, criterios de descarte y regla
# de particion fijados en docs/PROTOCOLO.md ("Decisiones fijadas ANTES de la Fase 6"). Z1 = confirmacion de los sets
# actuales; Z2 = reservado para el veredicto final de las variantes de la 6.4 (no se usa antes).
FRESH_CANDIDATES = ["AAVE", "ALGO", "ATOM", "AVAX", "DOT", "ETC", "FIL", "ICP", "NEAR", "TRX", "UNI", "VET"]   # alfabetico
FRESH_MIN_FIRST_1D = pd.Timestamp("2023-10-20")   # primera vela 1D posterior a esto = menos de 3 anios -> se descarta
FRESH_MAX_MISSING_4H = 10                         # mas velas 4h faltantes que esto, o un hueco > 2 dias -> se descarta
# Resultado de screen_fresh() + partition_fresh() corrido el 2026-10-21 sobre los CSV bajados: sobrevivieron las 12 (ninguna
# descartada); alfabetico alternado. tests/test_universe.py verifica que esto siga siendo igual a la regla.
FRESH_Z1: dict[str, str] = {s: "binance" for s in ("AAVE", "ATOM", "DOT", "FIL", "NEAR", "UNI")}
FRESH_Z2: dict[str, str] = {s: "binance" for s in ("ALGO", "AVAX", "ETC", "ICP", "TRX", "VET")}
# Fase 7: Z3 = 24 monedas Binance spot USDT nunca usadas, elegidas por la regla de docs/PROTOCOLO.md (Fase 7, seccion 5) con
# `python -m sqzlab.z3` el 2026-10-21 (results/z3_universe.json/.md: 106 recorridas en orden alfabetico, 82 descartes por antiguedad).
FRESH_Z3: dict[str, str] = {s: "binance" for s in (
    "1INCH", "ACM", "AGLD", "ALICE", "ANKR", "AR", "ARPA", "ASR", "ATM", "AUDIO", "AVA", "AXS",
    "BAND", "BAR", "BAT", "BEL", "BNT", "C98", "CAKE", "CELO", "CELR", "CFX", "CHR", "CHZ")}
SOURCES = {**TRAIN, **HOLDOUT, **FRESH_Z1, **FRESH_Z2, **FRESH_Z3}

ENTRY_FROM = pd.Timestamp("2017-01-01")          # solo cuentan trades con entrada desde aca
TRAIN_END = pd.Timestamp("2023-12-31 23:59:59")  # D1/H4: train = 2017-01-01..2023-12-31, test = 2024-01-01..hoy
TEST_FROM = pd.Timestamp("2024-01-01")
DATA_END = {"1d": "2026-10-20", "1w": "2026-10-12", "4h": "2026-10-20 20:00"}   # ultima vela cerrada del dia fijado (1w: ultima SEMANA COMPLETA; la del 10-19 traia el cierre parcial del 21-oct)
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


def load_htf(sym: str, tf: str) -> pd.DataFrame:
    """TF mayor para los filtros P4/P1 (Fase 7). La semanal NO se corta en DATA_END['1w']: la semana en curso hace falta como
    indice (una D1 usa la semana W-1); su cierre parcial nunca se usa."""
    if tf == "1w":
        return load(SOURCES[sym], sym, "1w")
    return load_coin(sym, tf)


def screen_fresh(candidates: list[str] | None = None) -> tuple[list[str], dict[str, str]]:
    """Aplica los criterios mecanicos de descarte (PROTOCOLO, Fase 6) a los CSV de data/. Devuelve (sobrevivientes
    ordenados alfabeticamente, {moneda: motivo del descarte}). No mira ningun resultado de la estrategia."""
    from .fetch import path_for
    ok, out = [], {}
    for sym in sorted(candidates or FRESH_CANDIDATES):
        p1, p4 = path_for("binance", sym, "1d"), path_for("binance", sym, "4h")
        if not (p1.exists() and p4.exists()):
            out[sym] = "no bajo (listado/red)"
            continue
        d1 = pd.read_csv(p1, parse_dates=["time_utc"])["time_utc"]
        d4 = pd.read_csv(p4, parse_dates=["time_utc"])["time_utc"]
        if d1.iloc[0] > FRESH_MIN_FIRST_1D:
            out[sym] = f"menos de 3 anios (primera vela 1D {d1.iloc[0].date()})"
            continue
        expected = int((d4.iloc[-1] - d4.iloc[0]) / pd.Timedelta(hours=4)) + 1
        missing, biggest = expected - len(d4), d4.diff().max()
        if missing > FRESH_MAX_MISSING_4H or biggest > pd.Timedelta(days=2):
            out[sym] = f"huecos en 4h ({missing} velas faltantes, hueco max {biggest})"
            continue
        ok.append(sym)
    return ok, out


def partition_fresh(survivors: list[str]) -> tuple[list[str], list[str]]:
    """Alfabetico alternado sobre los sobrevivientes: 1.a, 3.a, 5.a... -> Z1; 2.a, 4.a... -> Z2."""
    s = sorted(survivors)
    return s[0::2], s[1::2]


def fresh_group(group: str) -> dict[str, str]:
    return {"z1": FRESH_Z1, "z2": FRESH_Z2, "z3": FRESH_Z3}[group]


def load_universe(tf: str, group: str = "all") -> dict[str, pd.DataFrame]:
    """'all' = train + holdout de la Fase 4 (no incluye las monedas frescas); 'z1' / 'z2' = monedas nuevas de la Fase 6."""
    coins = {"train": TRAIN, "holdout": HOLDOUT, "all": {**TRAIN, **HOLDOUT}, "z1": FRESH_Z1, "z2": FRESH_Z2, "z3": FRESH_Z3}[group]
    return {s: load_coin(s, tf) for s in coins}
