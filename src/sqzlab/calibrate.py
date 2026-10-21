"""Fase 2: calibracion del port contra las bases de TradingView (docs/TV_BASELINES.md). A+B+C, C compras encendida.

Uso:  python -m sqzlab.calibrate            (imprime la tabla y escribe results/calibration.md)

Convencion de tiempos de TV (deducida de los spot-checks, ver HANDOFF): la hora de la lista de trades es la de
APERTURA de la vela. 4h se muestra en UTC-3 (sumar 3h para pasar a UTC). 1D/1W se muestran como fecha UTC.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .data import load
from .strategy import simulate

# Base de TV: (fuente, simbolo, tf, desde, hasta, trades, ganadoras, pnl_usd, pf, dd_usd)
BASELINES = {
    "BTC 1D": dict(sym="BTC", tf="1d", start=None, end="2026-10-20", trades=119, wins=39, pnl=105963.62, pf=4.751, dd=4790.17),
    "BTC 4h": dict(sym="BTC", tf="4h", start="2024-01-01 00:00", end="2026-10-20 00:00", trades=153, wins=43, pnl=2086.75, pf=1.376, dd=1002.29),
    "BTC 1W": dict(sym="BTC", tf="1w", start=None, end="2026-10-19", trades=12, wins=7, pnl=10467.53, pf=34.191, dd=164.71),
    "ETH 1D": dict(sym="ETH", tf="1d", start=None, end="2026-10-20", trades=83, wins=31, pnl=8863.10, pf=3.426, dd=899.46),
    "ETH 4h": dict(sym="ETH", tf="4h", start="2024-01-01 00:00", end="2026-10-20 00:00", trades=151, wins=35, pnl=844.86, pf=1.147, dd=1144.33),
    "ETH 1W": dict(sym="ETH", tf="1w", start=None, end="2026-10-19", trades=7, wins=2, pnl=-181.64, pf=0.16, dd=200.12),
}

# Spot-checks de TV: (lado, entrada, salida, px_entrada, px_salida, pnl_usd). 1D: fecha UTC. 4h: hora local UTC-3.
SPOT_1D = [
    (-1, "2026-10-07", "2026-10-11", 83275, 83679, -126.04), (1, "2026-09-18", "2026-10-07", 80879, 83275, 408.56),
    (1, "2026-08-20", "2026-09-10", 73008, 76529, 470.47), (-1, "2026-07-13", "2026-07-14", 62257, 64976, -1118.11),
    (1, "2026-07-03", "2026-07-08", 62522, 62238, -75.24), (-1, "2026-05-15", "2026-07-03", 79062, 62522, 4663.42),
    (-1, "2026-01-29", "2026-03-02", 84530, 68821, 2599.39), (-1, "2025-12-15", "2025-12-30", 86412, 88390, -281.12),
    (-1, "2025-11-04", "2025-12-03", 101466, 93472, 1068.05), (1, "2025-10-26", "2025-10-29", 114551, 110038, -537.66),
]
SPOT_4H_LOCAL = [
    (1, "2026-10-18 21:00", "2026-10-19 09:00", 82425, 81833, -78.66), (-1, "2026-10-14 09:00", "2026-10-16 05:00", 81549, 82533, -67.79),
    (1, "2026-10-04 05:00", "2026-10-05 09:00", 85293, 85259, -16.07), (1, "2026-10-01 21:00", "2026-10-02 13:00", 85487, 84297, -60.99),
]


def stats(res, df) -> dict:
    pn = np.array([t.pnl_net for t in res.trades])
    gp, gl = pn[pn > 0].sum(), -pn[pn < 0].sum()
    # TV "Max equity drawdown" se parece mas a la caida de la curva de trades CERRADOS (991,8 vs 1.002,3 en BTC 4h)
    # que a la equity a mercado vela a vela (1.445): se usa la primera, aproximacion no exacta.
    eq = np.r_[float(10000.0), 10000.0 + np.cumsum(pn)]
    peak = np.maximum.accumulate(eq)
    return dict(trades=len(pn), wins=int((pn > 0).sum()), pnl=res.final_equity - 10000.0,
                pf=gp / gl if gl > 0 else np.inf, dd=float((peak - eq).max()))


def match_spot(res, df, spots, tf) -> list[dict]:
    """Busca para cada spot-check el trade del port con mismo lado, fecha de entrada y precios (+-1 USD)."""
    out = []
    tt = pd.to_datetime(df["time_utc"].to_numpy())
    for side, ent, ext, pe, px, pnl in spots:
        e_utc = pd.Timestamp(ent) + (pd.Timedelta(hours=3) if tf == "4h" else pd.Timedelta(0))
        hit = None
        for t in res.trades:
            if t.side == side and tt[t.entry_i] == e_utc and abs(t.entry_px - pe) <= 1.0 and abs(t.exit_px - px) <= 1.0:
                hit = t
        out.append(dict(tv_pnl=pnl, port_pnl=None if hit is None else round(hit.pnl_net, 2),
                        ok=hit is not None, ratio=None if hit is None else round(pnl / hit.pnl_net, 4)))
    return out


def run_all(source: str = "bitstamp", **over) -> tuple[pd.DataFrame, dict]:
    rows, spots = [], {}
    for name, b in BASELINES.items():
        df = load(source, b["sym"], b["tf"], start=b["start"], end=b["end"])
        res = simulate(df, **over)
        s = stats(res, df)
        rows.append(dict(base=name, desde_port=str(df.time_utc.iloc[0])[:10], tv_trades=b["trades"], port_trades=s["trades"],
                         tv_wins=b["wins"], port_wins=s["wins"], tv_pnl=b["pnl"], port_pnl=round(s["pnl"], 2),
                         tv_pf=b["pf"], port_pf=round(s["pf"], 3), tv_dd=b["dd"], port_dd=round(s["dd"], 2)))
        if name == "BTC 1D":
            spots[name] = match_spot(res, df, SPOT_1D, "1d")
        if name == "BTC 4h":
            spots[name] = match_spot(res, df, SPOT_4H_LOCAL, "4h")
    return pd.DataFrame(rows), spots


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    tab, spots = run_all()
    print(tab.to_string(index=False))
    for k, v in spots.items():
        print(f"\nSpot-checks {k}: {sum(x['ok'] for x in v)}/{len(v)} coinciden en lado, fecha y precios")
        print(pd.DataFrame(v).to_string(index=False))
    out = Path(__file__).resolve().parents[2] / "results" / "calibration.md"
    out.write_text("Calibracion (generado por `python -m sqzlab.calibrate`)\n\n" + tab.to_string(index=False) + "\n",
                   encoding="utf-8")


if __name__ == "__main__":
    main()
