"""Simulador bar-by-bar de la strategy SQZ+RSI (A+B+C) con la semantica de strategy() de TradingView.

Fuente de verdad: ref/sqz_rsi_strategy_v2.pine (con useD apagado y cLong encendida = lo que parece correr hoy
en TradingView, la "v1"). La senal D (divergencia del momentum) esta portada desde la Fase 3 y viene APAGADA en DEFAULTS (useD=False) para no
alterar la calibracion A+B+C; los empates de pivotes y la senal D no estan verificados contra TradingView.

Semantica replicada (ver docs/TV_BASELINES.md):
  - process_orders_on_close=true: las ordenes de mercado generadas al cierre de la vela i se llenan al cierre de i.
  - El stop (strategy.exit) se activa desde la vela siguiente; se llena al precio del stop o al open si hay gap.
  - posNow se lee al inicio de la corrida de la vela (ya refleja los stops tocados dentro de esa vela).
  - Tamano: min(equity*riesgo%/|close-stop|, equity*maxLev/close), equity = cash + PnL abierto a mercado,
    calculada ANTES de ejecutar las ordenes de esa vela (incluye el PnL abierto de la posicion que se va a revertir).
  - Cadena de entradas else-if con prioridad B largo, B corto, A largo, A corto, C largo, C corto, D largo, D corto.
  - Comision: porcentaje del valor de la orden, por lado.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .indicators import compute, pivots, rolling_max, rolling_min

DEFAULTS: dict = dict(
    # Que probar (v1 = A+B+C con C compras encendida; la v2 de ref/ trae cLong=False)
    useA=True, useB=True, useC=True, aLong=True, aShort=True, bLong=True, bShort=True, cLong=True, cShort=True,
    # Backtest
    initial_capital=10000.0, commission_pct=0.05, riskPct=1.0, maxLev=1.0,
    # Squeeze
    bbLen=20, bbMult=2.0, kcLen=20, kcMult=1.5, useTrueRange=True,
    # RSI
    emaSeed="sma",
    # Redondeo a mintick (hipotesis de calibracion): mintick=None lo apaga. tick_stop redondea el nivel de stop de
    # strategy.exit; tick_fill redondea los precios de fill (entrada, cierre y stop).
    mintick=None, tick_stop=False, tick_fill=False,
    rsiLen=14, maType="SMA", maLen=14,
    # Senal A y base
    emaFLen=20, emaMLen=55, emaSLen=200, adxLen=14, adxMin=20.0, pbBars=5, atrLen=14, atrMult=0.25, useRsiF=True,
    # Senal B
    minSqz=6, graceBars=2, needMom=True, needE200=True, stopModeB="Punto medio del rango", invBars=3,
    # Senal C
    cHot=65.0, cCold=35.0, cLook=10, cWin=3, cNeedMom=True, cNeedEma=True, cStopBars=7, cAtrMult=0.25, cMaxRisk=3.0,
    # Senal D (divergencia del momentum). Apagada aca (calibracion A+B+C); la v2 de ref/ la trae encendida.
    useD=False, dLong=True, dShort=True, dvL=5, dvR=5, dvMin=5, dvMax=60, dvZero=True, dNeedEma=True,
    dAtrMult=0.25, dMaxRisk=0.0,
    # Volumen (opcional)
    useVol=False, volLen=20, volMult=1.5,
)


def v2_params(over: dict | None = None) -> dict:
    """Defaults de la strategy v2 de ref/ (cLong apagada, D encendida): lo que traen params/*.json sin optimizar."""
    return {**DEFAULTS, "cLong": False, "useD": True, **(over or {})}


@dataclass
class Trade:
    side: int            # +1 largo, -1 corto
    kind: str            # A / B / C / D
    entry_i: int
    entry_px: float
    qty: float
    stop: float
    exit_i: int = -1
    exit_px: float = np.nan
    exit_reason: str = ""   # stop / ema / inval / reversa / abierto
    comm: float = 0.0       # comision total (entrada + salida)
    pnl_gross: float = 0.0
    risk_cash: float = 0.0  # |entry-stop|*qty: es 1R en USD

    @property
    def pnl_net(self) -> float:
        return self.pnl_gross - self.comm

    @property
    def r_net(self) -> float:
        return self.pnl_net / self.risk_cash if self.risk_cash > 0 else np.nan


@dataclass
class SimResult:
    trades: list[Trade] = field(default_factory=list)
    equity: np.ndarray | None = None      # equity al cierre de cada vela (cash + PnL abierto)
    time: np.ndarray | None = None
    open_trade: Trade | None = None
    final_equity: float = np.nan

    def table(self) -> pd.DataFrame:
        rows = []
        for t in self.trades + ([self.open_trade] if self.open_trade else []):
            rows.append(dict(side=t.side, kind=t.kind, entry_i=t.entry_i, entry_px=t.entry_px, qty=t.qty, stop=t.stop,
                             exit_i=t.exit_i, exit_px=t.exit_px, reason=t.exit_reason, pnl_gross=t.pnl_gross,
                             comm=t.comm, pnl_net=t.pnl_net, R=t.r_net))
        return pd.DataFrame(rows)


def simulate(df: pd.DataFrame, **over) -> SimResult:
    p = dict(DEFAULTS)
    p.update(over)
    d = compute(df, p)
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    n = len(c)
    mom, rsi, rsiMa = d["mom"], d["rsi"], d["rsiMa"]
    ema1, ema2, ema3, adx, atr, sqzOn = d["ema1"], d["ema2"], d["ema3"], d["adx"], d["atr"], d["sqzOn"]

    volume, hasVol, volAvg = d["volume"], d["hasVol"], d["volAvg"]
    pivL = pivots(mom, p["dvL"], p["dvR"], "low")
    pivH = pivots(mom, p["dvL"], p["dvR"], "high")
    pb = p["pbBars"]
    touchUp, breakUp = (l <= ema1).astype(float), (c < ema2).astype(float)
    touchDn, breakDn = (h >= ema1).astype(float), (c > ema2).astype(float)
    # Pine: ta.highest(...) == 1 con NaN -> False; un NaN en las series bool de arriba no existe (comparan a False)
    setupLong = (rolling_max(touchUp, pb) == 1) & (rolling_max(breakUp, pb) == 0)
    setupShort = (rolling_max(touchDn, pb) == 1) & (rolling_max(breakDn, pb) == 0)
    pbLow, pbHigh = rolling_min(l, pb), rolling_max(h, pb)
    rsiHot = rolling_max(rsi, p["cLook"]) >= p["cHot"]
    rsiCold = rolling_min(rsi, p["cLook"]) <= p["cCold"]
    stopCS_a = rolling_max(h, p["cStopBars"]) + p["cAtrMult"] * atr
    stopCL_a = rolling_min(l, p["cStopBars"]) - p["cAtrMult"] * atr

    mt = p["mintick"]

    def rt(x: float) -> float:
        return round(x / mt) * mt

    r_stop = (lambda x: rt(x)) if (mt and p["tick_stop"]) else (lambda x: x)
    r_fill = (lambda x: rt(x)) if (mt and p["tick_fill"]) else (lambda x: x)
    comm_rate = p["commission_pct"] / 100.0
    riskPct, maxLev = p["riskPct"], p["maxLev"]
    invBars = p["invBars"]
    mid_stop = p["stopModeB"] == "Punto medio del rango"

    cash = float(p["initial_capital"])   # capital + PnL realizado - comisiones pagadas
    pos = 0.0                            # cantidad con signo
    avg = np.nan
    stop_px = np.nan
    stop_live_from = 0
    cur: Trade | None = None

    posType = 0
    entryBar = None
    entHi = entLo = np.nan
    lastLong = lastShort = None
    runLen, sinceOn = 0, 999
    sqHi = sqLo = np.nan
    cArmS = cArmL = None
    pLBar = pHBar = None
    pLPx = pLMom = pHPx = pHMom = np.nan
    dvR = p["dvR"]

    trades: list[Trade] = []
    eq_curve = np.full(n, np.nan)

    def close_pos(i: int, px: float, reason: str):
        nonlocal cash, pos, avg, cur, stop_px
        pnl = pos * (px - avg)
        fee = abs(pos) * px * comm_rate
        cash += pnl - fee
        cur.exit_i, cur.exit_px, cur.exit_reason = i, px, reason
        cur.pnl_gross += pnl
        cur.comm += fee
        trades.append(cur)
        cur = None
        pos = 0.0
        avg = np.nan
        stop_px = np.nan

    def open_pos(i: int, side: int, kind: str, q: float, px: float, stop: float):
        nonlocal cash, pos, avg, cur, stop_px, stop_live_from
        fee = q * px * comm_rate
        cash -= fee
        pos = side * q
        avg = px
        stop = r_stop(stop)
        stop_px = stop
        stop_live_from = i + 1
        cur = Trade(side=side, kind=kind, entry_i=i, entry_px=px, qty=q, stop=stop, comm=fee,
                    risk_cash=abs(px - stop) * q)

    for i in range(n):
        # 1) broker emulator: el stop colocado en una vela anterior se toca dentro de esta vela
        if pos != 0 and not np.isnan(stop_px) and stop_live_from <= i:
            if pos > 0 and l[i] <= stop_px:
                close_pos(i, r_fill(min(o[i], stop_px)), "stop")
            elif pos < 0 and h[i] >= stop_px:
                close_pos(i, r_fill(max(o[i], stop_px)), "stop")
        posNow = 1 if pos > 0 else (-1 if pos < 0 else 0)
        eq_now = cash + (pos * (c[i] - avg) if pos != 0 else 0.0)   # strategy.equity al cierre, antes de las ordenes
        eq_curve[i] = eq_now

        ip = i - 1
        e1, e2, e3 = ema1[i], ema2[i], ema3[i]
        volOk = (not p["useVol"]) or (not hasVol[i]) or volume[i] > volAvg[i] * p["volMult"]

        # 2) senal A
        upTrend = e1 > e2 and e2 > e3
        downTrend = e1 < e2 and e2 < e3
        adxPrev = adx[ip] if ip >= 0 and not np.isnan(adx[ip]) else 0.0
        adxOk = adx[i] >= p["adxMin"] and adx[i] > adxPrev
        hPrev = h[ip] if ip >= 0 else np.nan
        lPrev = l[ip] if ip >= 0 else np.nan
        trigLong = c[i] > e1 and c[i] > hPrev
        trigShort = c[i] < e1 and c[i] < lPrev
        rsiLongOk = (not p["useRsiF"]) or rsi[i] > rsiMa[i]
        rsiShortOk = (not p["useRsiF"]) or rsi[i] < rsiMa[i]
        longRawA = p["useA"] and p["aLong"] and upTrend and adxOk and setupLong[i] and trigLong and rsiLongOk and volOk
        shortRawA = p["useA"] and p["aShort"] and downTrend and adxOk and setupShort[i] and trigShort and rsiShortOk and volOk
        longSigA = shortSigA = False
        if longRawA and (lastLong is None or i - lastLong > pb):
            longSigA, lastLong = True, i
        if shortRawA and (lastShort is None or i - lastShort > pb):
            shortSigA, lastShort = True, i

        # 3) senal B (estado del squeeze HASTA la vela anterior)
        rHiPrev, rLoPrev = sqHi, sqLo
        armedPrev = runLen >= p["minSqz"] and sinceOn <= p["graceBars"]
        momPrev = mom[ip] if ip >= 0 and not np.isnan(mom[ip]) else 0.0
        momUp = mom[i] > 0 and mom[i] > momPrev
        momDown = mom[i] < 0 and mom[i] < momPrev
        longSigB = (p["useB"] and p["bLong"] and armedPrev and c[i] > rHiPrev and ((not p["needE200"]) or c[i] > e3)
                    and ((not p["needMom"]) or momUp) and volOk)
        shortSigB = (p["useB"] and p["bShort"] and armedPrev and c[i] < rLoPrev and ((not p["needE200"]) or c[i] < e3)
                     and ((not p["needMom"]) or momDown) and volOk)
        if sqzOn[i]:
            if sinceOn > 0:
                runLen, sqHi, sqLo = 1, h[i], l[i]
            else:
                runLen += 1
                sqHi = max(h[i] if np.isnan(sqHi) else sqHi, h[i])
                sqLo = min(l[i] if np.isnan(sqLo) else sqLo, l[i])
            sinceOn = 0
        else:
            sinceOn = min(sinceOn + 1, 999)
        if longSigB or shortSigB:
            runLen, sinceOn = 0, 999

        # 4) senal C
        rsiPrev, maPrev = (rsi[ip], rsiMa[ip]) if ip >= 0 else (np.nan, np.nan)
        rsiXDown = rsi[i] < rsiMa[i] and rsiPrev >= maPrev
        rsiXUp = rsi[i] > rsiMa[i] and rsiPrev <= maPrev
        if rsiXDown and rsiHot[i]:
            cArmS = i
        if rsiXUp and rsiCold[i]:
            cArmL = i
        stopCS, stopCL = stopCS_a[i], stopCL_a[i]
        riskOkS = p["cMaxRisk"] == 0 or stopCS - c[i] <= p["cMaxRisk"] * atr[i]
        riskOkL = p["cMaxRisk"] == 0 or c[i] - stopCL <= p["cMaxRisk"] * atr[i]
        shortSigC = (p["useC"] and p["cShort"] and cArmS is not None and i - cArmS <= p["cWin"] and rsi[i] < rsiMa[i]
                     and ((not p["cNeedMom"]) or mom[i] < momPrev) and ((not p["cNeedEma"]) or c[i] < e1)
                     and riskOkS and posNow != -1)
        longSigC = (p["useC"] and p["cLong"] and cArmL is not None and i - cArmL <= p["cWin"] and rsi[i] > rsiMa[i]
                    and ((not p["cNeedMom"]) or mom[i] > momPrev) and ((not p["cNeedEma"]) or c[i] > e1)
                    and riskOkL and posNow != 1)
        if shortSigC:
            cArmS = None
        if longSigC:
            cArmL = None

        # 4b) senal D: divergencia del momentum (pivotes sobre el momentum crudo; la senal llega dvR velas tarde)
        bullDiv = bearDiv = False
        if not np.isnan(pivL[i]):
            nBar = i - dvR
            nPx = l[nBar]
            okRange = pLBar is not None and p["dvMin"] <= nBar - pLBar <= p["dvMax"]
            okSide = (not p["dvZero"]) or (pivL[i] < 0 and (0.0 if np.isnan(pLMom) else pLMom) < 0)
            if okRange and okSide and nPx < pLPx and pivL[i] > pLMom:
                bullDiv = True
            pLBar, pLPx, pLMom = nBar, nPx, pivL[i]
        if not np.isnan(pivH[i]):
            nBarH = i - dvR
            nPxH = h[nBarH]
            okRangeH = pHBar is not None and p["dvMin"] <= nBarH - pHBar <= p["dvMax"]
            okSideH = (not p["dvZero"]) or (pivH[i] > 0 and (0.0 if np.isnan(pHMom) else pHMom) > 0)
            if okRangeH and okSideH and nPxH > pHPx and pivH[i] < pHMom:
                bearDiv = True
            pHBar, pHPx, pHMom = nBarH, nPxH, pivH[i]
        stopDL = pLPx - p["dAtrMult"] * atr[i]
        stopDS = pHPx + p["dAtrMult"] * atr[i]
        riskOkDL = p["dMaxRisk"] == 0 or c[i] - stopDL <= p["dMaxRisk"] * atr[i]
        riskOkDS = p["dMaxRisk"] == 0 or stopDS - c[i] <= p["dMaxRisk"] * atr[i]
        longSigD = (p["useD"] and p["dLong"] and bullDiv and c[i] > stopDL and ((not p["dNeedEma"]) or c[i] > e1)
                    and riskOkDL and posNow != 1)
        shortSigD = (p["useD"] and p["dShort"] and bearDiv and c[i] < stopDS and ((not p["dNeedEma"]) or c[i] < e1)
                     and riskOkDS and posNow != -1)

        # 5) salidas por condicion (strategy.close al cierre)
        eb = entryBar if entryBar is not None else -999
        if posNow == 1 and (c[i] < e1 or (posType == 2 and i - eb <= invBars and c[i] < entHi)):
            reason = "ema" if c[i] < e1 else "inval"
            close_pos(i, r_fill(c[i]), reason)
        elif posNow == -1 and (c[i] > e1 or (posType == 2 and i - eb <= invBars and c[i] > entLo)):
            reason = "ema" if c[i] > e1 else "inval"
            close_pos(i, r_fill(c[i]), reason)

        # 6) entradas (cadena else-if con prioridad B, A, C)
        def calc_qty(stop_level: float) -> float:
            risk_pu = abs(c[i] - stop_level)
            q_risk = (eq_now * riskPct / 100.0) / risk_pu if risk_pu > 0 else 0.0
            return min(q_risk, eq_now * maxLev / c[i])

        def enter(side: int, kind: str, q: float, stop: float):
            if pos != 0 and np.sign(pos) == -side:     # reversa: cierra y abre en el mismo cierre
                close_pos(i, r_fill(c[i]), "reversa")
            open_pos(i, side, kind, q, r_fill(c[i]), stop)

        if longSigB:
            if posNow != 1:
                stopB = (rHiPrev + rLoPrev) / 2 if mid_stop else rLoPrev
                q = calc_qty(stopB)
                if q > 0:
                    posType, entryBar, entHi, entLo = 2, i, rHiPrev, rLoPrev
                    enter(1, "B", q, stopB)
        elif shortSigB:
            if posNow != -1:
                stopB = (rHiPrev + rLoPrev) / 2 if mid_stop else rHiPrev
                q = calc_qty(stopB)
                if q > 0:
                    posType, entryBar, entHi, entLo = 2, i, rHiPrev, rLoPrev
                    enter(-1, "B", q, stopB)
        elif longSigA:
            if posNow != 1:
                stopA = pbLow[i] - p["atrMult"] * atr[i]
                q = calc_qty(stopA)
                if q > 0:
                    posType = 1
                    enter(1, "A", q, stopA)
        elif shortSigA:
            if posNow != -1:
                stopA = pbHigh[i] + p["atrMult"] * atr[i]
                q = calc_qty(stopA)
                if q > 0:
                    posType = 1
                    enter(-1, "A", q, stopA)
        elif longSigC:
            q = calc_qty(stopCL)
            if q > 0:
                posType = 3
                enter(1, "C", q, stopCL)
        elif shortSigC:
            q = calc_qty(stopCS)
            if q > 0:
                posType = 3
                enter(-1, "C", q, stopCS)
        elif longSigD:
            q = calc_qty(stopDL)
            if q > 0:
                posType = 4
                enter(1, "D", q, stopDL)
        elif shortSigD:
            q = calc_qty(stopDS)
            if q > 0:
                posType = 4
                enter(-1, "D", q, stopDS)

    res = SimResult(trades=trades, equity=eq_curve, time=df["time_utc"].to_numpy())
    if cur is not None:   # posicion abierta al final: marca a mercado (TradingView la cuenta aparte)
        cur.exit_i, cur.exit_px, cur.exit_reason = n - 1, c[-1], "abierto"
        cur.pnl_gross = pos * (c[-1] - avg)
        res.open_trade = cur
    res.final_equity = cash + (pos * (c[-1] - avg) if pos != 0 else 0.0)
    return res
