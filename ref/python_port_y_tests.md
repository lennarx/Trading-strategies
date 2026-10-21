"""Port a Python del indicador SQZ+RSI+SIG v4 (Pine v5). Bar-by-bar, mismo orden de evaluacion que el Pine."""
import numpy as np
import pandas as pd

UP = '/root/.claude/uploads/f50443a5-be15-50dc-aa4c-c106bf5a1b81/'
FILES = {
    ('SOL', '1d'): '5bfa3435-SOL-USDT_1d.csv', ('BTC', '1d'): 'a1b643e1-BTC-USDT_1d.csv',
    ('ETH', '1d'): '1cfbb398-ETH-USDT_1d.csv', ('XRP', '1d'): '8f0c0ef3-XRP-USDT_1d.csv',
    ('DOGE', '1d'): 'a45dae69-DOGE-USDT_1d.csv', ('LINK', '1d'): '23dcb69c-LINK-USDT_1d.csv',
    ('SOL', '4h'): '8aa66720-SOL-USDT_4h.csv', ('BTC', '4h'): 'd34a76b0-BTC-USDT_4h.csv',
    ('ETH', '4h'): '2ce0bb18-ETH-USDT_4h.csv',
}


def load(sym, tf):
    df = pd.read_csv(UP + FILES[(sym, tf)], parse_dates=['time_utc'])
    return df.reset_index(drop=True)


def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def stdev(x, n):  # Pine: poblacional
    return pd.Series(x).rolling(n).std(ddof=0).to_numpy()


def ema(x, n):  # Pine ta.ema: arranca en el primer valor
    return pd.Series(x).ewm(alpha=2.0 / (n + 1), adjust=False).mean().to_numpy()


def rma(x, n):  # Pine ta.rma: semilla = sma de los primeros n (ignorando na iniciales)
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    first = np.argmax(~np.isnan(x)) if (~np.isnan(x)).any() else None
    if first is None:
        return out
    s = first + n - 1
    if s >= len(x):
        return out
    out[s] = np.mean(x[first:s + 1])
    a = 1.0 / n
    for i in range(s + 1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def linreg_end(x, n):  # ta.linreg(x, n, 0)
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    t = np.arange(n)
    tm = t.mean()
    den = ((t - tm) ** 2).sum()
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        if np.isnan(w).any():
            continue
        slope = ((t - tm) * (w - w.mean())).sum() / den
        out[i] = w.mean() + slope * (n - 1 - tm)
    return out


def rolling_max(x, n):
    return pd.Series(x).rolling(n).max().to_numpy()


def rolling_min(x, n):
    return pd.Series(x).rolling(n).min().to_numpy()


DEFAULT = dict(
    bbLen=20, bbMult=2.0, kcLen=20, kcMult=1.5, normLen=100,
    rsiLen=14, maLen=14, emaF=20, emaM=55, emaS=200, adxLen=14, adxMin=20.0,
    pbBars=5, atrLen=14, atrMult=0.25, useRsiF=True,
    useA=True, useB=True, minSqz=6, graceBars=2, needMom=True, needE200=True, stopModeB='mid', invBars=3,
    useC=True, cHot=65.0, cCold=35.0, cLook=10, cWin=3, cNeedMom=True, cNeedEma=True,
    cStopBars=7, cAtrMult=0.25, cMaxRisk=3.0,
    allowLong=True, allowShort=True,
)


def indicators(df, p):
    o, h, l, c = (df[k].to_numpy(float) for k in ['open', 'high', 'low', 'close'])
    n = len(c)
    d = {}
    prev_c = np.r_[np.nan, c[:-1]]
    tr = np.maximum.reduce([h - l, np.abs(h - prev_c), np.abs(l - prev_c)])
    tr[0] = h[0] - l[0]
    basis = sma(c, p['bbLen'])
    dev = p['bbMult'] * stdev(c, p['bbLen'])
    upBB, loBB = basis + dev, basis - dev
    kcMa = sma(c, p['kcLen'])
    rngMa = sma(tr, p['kcLen'])
    upKC, loKC = kcMa + rngMa * p['kcMult'], kcMa - rngMa * p['kcMult']
    d['sqzOn'] = (loBB > loKC) & (upBB < upKC)
    avgHL = (rolling_max(h, p['kcLen']) + rolling_min(l, p['kcLen'])) / 2
    d['mom'] = linreg_end(c - (avgHL + sma(c, p['kcLen'])) / 2, p['kcLen'])
    # RSI (Pine: rma de ganancias/perdidas)
    ch = np.r_[np.nan, np.diff(c)]
    gain = np.where(np.isnan(ch), np.nan, np.maximum(ch, 0))
    loss = np.where(np.isnan(ch), np.nan, np.maximum(-ch, 0))
    ag, al = rma(gain, p['rsiLen']), rma(loss, p['rsiLen'])
    with np.errstate(divide='ignore', invalid='ignore'):
        rsi = np.where(al == 0, 100.0, 100 - 100 / (1 + ag / al))
    rsi = np.where(np.isnan(ag), np.nan, rsi)
    d['rsi'] = rsi
    d['rsiMa'] = sma(rsi, p['maLen'])
    d['ema1'], d['ema2'], d['ema3'] = ema(c, p['emaF']), ema(c, p['emaM']), ema(c, p['emaS'])
    # DMI / ADX (Pine)
    up = np.r_[np.nan, np.diff(h)]
    down = -np.r_[np.nan, np.diff(l)]
    plusDM = np.where(np.isnan(up), np.nan, np.where((up > down) & (up > 0), up, 0.0))
    minusDM = np.where(np.isnan(down), np.nan, np.where((down > up) & (down > 0), down, 0.0))
    trur = rma(tr, p['adxLen'])
    plus = 100 * rma(plusDM, p['adxLen']) / trur
    minus = 100 * rma(minusDM, p['adxLen']) / trur
    s = plus + minus
    d['adx'] = 100 * rma(np.abs(plus - minus) / np.where(s == 0, 1, s), p['adxLen'])
    d['atr'] = rma(tr, p['atrLen'])
    d['tr'] = tr
    return d


def run(df, **over):
    p = dict(DEFAULT)
    p.update(over)
    o, h, l, c = (df[k].to_numpy(float) for k in ['open', 'high', 'low', 'close'])
    n = len(c)
    d = indicators(df, p)
    mom, rsi, rsiMa = d['mom'], d['rsi'], d['rsiMa']
    ema1, ema2, ema3, adx, atr, sqzOn = d['ema1'], d['ema2'], d['ema3'], d['adx'], d['atr'], d['sqzOn']
    pb = p['pbBars']
    touchUp = (l <= ema1).astype(float)
    breakUp = (c < ema2).astype(float)
    touchDn = (h >= ema1).astype(float)
    breakDn = (c > ema2).astype(float)
    setupLong = (rolling_max(touchUp, pb) == 1) & (rolling_max(breakUp, pb) == 0)
    setupShort = (rolling_max(touchDn, pb) == 1) & (rolling_max(breakDn, pb) == 0)
    pbLow, pbHigh = rolling_min(l, pb), rolling_max(h, pb)
    rsiHotRecent = rolling_max(rsi, p['cLook']) >= p['cHot']
    rsiColdRecent = rolling_min(rsi, p['cLook']) <= p['cCold']
    stopCS_a = rolling_max(h, p['cStopBars']) + p['cAtrMult'] * atr
    stopCL_a = rolling_min(l, p['cStopBars']) - p['cAtrMult'] * atr

    lastLong = lastShort = None
    runLen, sinceOn, sqHi, sqLo = 0, 999, np.nan, np.nan
    pos = posType = 0
    stopLvl = tgtLvl = np.nan
    entryBar = None
    entHi = entLo = np.nan
    cArmS = cArmL = None
    trades, sigs = [], []
    cur = None
    overwritten = 0

    def nz(x, v=0.0):
        return v if (x is None or (isinstance(x, float) and np.isnan(x))) else x

    for i in range(n):
        if i == 0 or any(np.isnan(v) for v in (ema3[i], adx[i], atr[i], rsiMa[i], mom[i])):
            # indicadores sin calentar: solo actualizo estado del squeeze
            if sqzOn[i]:
                if sinceOn > 0:
                    runLen, sqHi, sqLo = 1, h[i], l[i]
                else:
                    runLen += 1
                    sqHi, sqLo = max(nz(sqHi, h[i]), h[i]), min(nz(sqLo, l[i]), l[i])
                sinceOn = 0
            else:
                sinceOn = min(sinceOn + 1, 999)
            continue
        momPrev = nz(mom[i - 1])
        adxPrev = nz(adx[i - 1])
        upTrend = ema1[i] > ema2[i] > ema3[i]
        downTrend = ema1[i] < ema2[i] < ema3[i]
        adxOk = adx[i] >= p['adxMin'] and adx[i] > adxPrev
        trigLong = c[i] > ema1[i] and c[i] > h[i - 1]
        trigShort = c[i] < ema1[i] and c[i] < l[i - 1]
        rsiLongOk = (not p['useRsiF']) or rsi[i] > rsiMa[i]
        rsiShortOk = (not p['useRsiF']) or rsi[i] < rsiMa[i]
        longRawA = p['useA'] and p['allowLong'] and upTrend and adxOk and setupLong[i] and trigLong and rsiLongOk
        shortRawA = p['useA'] and p['allowShort'] and downTrend and adxOk and setupShort[i] and trigShort and rsiShortOk
        longSigA = shortSigA = False
        if longRawA and (lastLong is None or i - lastLong > pb):
            longSigA, lastLong = True, i
        if shortRawA and (lastShort is None or i - lastShort > pb):
            shortSigA, lastShort = True, i
        # B
        rHiPrev, rLoPrev = sqHi, sqLo
        armedPrev = runLen >= p['minSqz'] and sinceOn <= p['graceBars']
        momUp = mom[i] > 0 and mom[i] > momPrev
        momDown = mom[i] < 0 and mom[i] < momPrev
        bLong = p['useB'] and armedPrev and c[i] > rHiPrev and ((not p['needE200']) or c[i] > ema3[i]) and ((not p['needMom']) or momUp)
        bShort = p['useB'] and armedPrev and c[i] < rLoPrev and ((not p['needE200']) or c[i] < ema3[i]) and ((not p['needMom']) or momDown)
        longSigB = p['allowLong'] and bLong
        shortSigB = p['allowShort'] and bShort
        if sqzOn[i]:
            if sinceOn > 0:
                runLen, sqHi, sqLo = 1, h[i], l[i]
            else:
                runLen += 1
                sqHi, sqLo = max(nz(sqHi, h[i]), h[i]), min(nz(sqLo, l[i]), l[i])
            sinceOn = 0
        else:
            sinceOn = min(sinceOn + 1, 999)
        if longSigB or shortSigB:
            runLen, sinceOn = 0, 999
        # C
        rsiXDown = rsi[i - 1] >= rsiMa[i - 1] and rsi[i] < rsiMa[i] if not np.isnan(rsiMa[i - 1]) else False
        rsiXUp = rsi[i - 1] <= rsiMa[i - 1] and rsi[i] > rsiMa[i] if not np.isnan(rsiMa[i - 1]) else False
        if rsiXDown and rsiHotRecent[i]:
            cArmS = i
        if rsiXUp and rsiColdRecent[i]:
            cArmL = i
        stopCS, stopCL = stopCS_a[i], stopCL_a[i]
        riskOkS = p['cMaxRisk'] == 0 or stopCS - c[i] <= p['cMaxRisk'] * atr[i]
        riskOkL = p['cMaxRisk'] == 0 or c[i] - stopCL <= p['cMaxRisk'] * atr[i]
        cShort = (p['useC'] and cArmS is not None and i - cArmS <= p['cWin'] and rsi[i] < rsiMa[i]
                  and ((not p['cNeedMom']) or mom[i] < momPrev) and ((not p['cNeedEma']) or c[i] < ema1[i]) and riskOkS and pos != -1)
        cLong = (p['useC'] and cArmL is not None and i - cArmL <= p['cWin'] and rsi[i] > rsiMa[i]
                 and ((not p['cNeedMom']) or mom[i] > momPrev) and ((not p['cNeedEma']) or c[i] > ema1[i]) and riskOkL and pos != 1)
        shortSigC = p['allowShort'] and cShort
        longSigC = p['allowLong'] and cLong
        if shortSigC:
            cArmS = None
        if longSigC:
            cArmL = None
        # salidas
        exitL = exitS = False
        exit_px = None
        if pos == 1 and (l[i] <= stopLvl or c[i] < ema1[i] or (posType == 2 and i - entryBar <= p['invBars'] and c[i] < entHi)):
            exitL = True
            exit_px = min(o[i], stopLvl) if l[i] <= stopLvl else c[i]
        if pos == -1 and (h[i] >= stopLvl or c[i] > ema1[i] or (posType == 2 and i - entryBar <= p['invBars'] and c[i] > entLo)):
            exitS = True
            exit_px = max(o[i], stopLvl) if h[i] >= stopLvl else c[i]
        if exitL or exitS:
            cur.update(exit_i=i, exit_px=exit_px)
            risk = abs(cur['entry'] - cur['stop'])
            cur['R'] = cur['dir'] * (exit_px - cur['entry']) / risk
            trades.append(cur)
            cur = None
            pos = posType = 0

        def enter(direction, ptype, stop, tgt=np.nan):
            nonlocal pos, posType, stopLvl, tgtLvl, cur, overwritten
            if pos == direction and cur is not None:
                overwritten += 1
                if not p.get('pyramid_ignore', True):
                    pass
                else:
                    return
            if cur is not None and pos == -direction:  # reversa: cierra la posicion opuesta al cierre de la vela
                risk0 = abs(cur['entry'] - cur['stop'])
                cur.update(exit_i=i, exit_px=c[i], rev=True)
                cur['R'] = cur['dir'] * (c[i] - cur['entry']) / risk0
                trades.append(cur)
                cur = None
            pos, posType, stopLvl, tgtLvl = direction, ptype, stop, tgt
            cur = dict(entry_i=i, entry=c[i], stop=stop, dir=direction, type='ABC'[ptype - 1] if ptype <= 3 else '?', t=df['time_utc'][i])
            if ptype == 2:
                cur['type'] = 'B'
            if ptype == 1:
                cur['type'] = 'A'
            if ptype == 3:
                cur['type'] = 'C'

        if longSigB:
            if not (pos == 1 and cur is not None):
                entryBar, entHi, entLo = i, rHiPrev, rLoPrev
            enter(1, 2, (rHiPrev + rLoPrev) / 2 if p['stopModeB'] == 'mid' else rLoPrev)
        elif shortSigB:
            if not (pos == -1 and cur is not None):
                entryBar, entHi, entLo = i, rHiPrev, rLoPrev
            enter(-1, 2, (rHiPrev + rLoPrev) / 2 if p['stopModeB'] == 'mid' else rHiPrev)
        elif longSigA:
            enter(1, 1, pbLow[i] - p['atrMult'] * atr[i])
        elif shortSigA:
            enter(-1, 1, pbHigh[i] + p['atrMult'] * atr[i])
        elif longSigC:
            enter(1, 3, stopCL)
        elif shortSigC:
            enter(-1, 3, stopCS)
        # registro de senales (como las veria el usuario: las que alguna vez disparan)
        for flag, kind, dr in ((longSigA, 'A', 1), (shortSigA, 'A', -1), (longSigB, 'B', 1), (shortSigB, 'B', -1), (longSigC, 'C', 1), (shortSigC, 'C', -1)):
            if flag:
                sigs.append(dict(i=i, t=df['time_utc'][i], kind=kind, dir=dr, close=c[i]))
    if cur is not None:  # abierto al final: marco a mercado
        risk = abs(cur['entry'] - cur['stop'])
        cur.update(exit_i=n - 1, exit_px=c[-1], open=True, R=cur['dir'] * (c[-1] - cur['entry']) / risk)
        trades.append(cur)
    d['overwritten'] = overwritten
    return pd.DataFrame(trades), pd.DataFrame(sigs), d