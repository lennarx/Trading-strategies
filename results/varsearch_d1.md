# Variantes D1: seleccion en train (generado por `python -m sqzlab.varsearch`)

Set base: `params/d1.json`. Train: monedas BTC, ETH, XRP, LTC, ADA, DOGE, entradas 2017-01-01..2023-12-31. **Pruebas: 10** (1 control + puntos de grilla). Criterios fijados antes en PROTOCOLO.

Control (set vigente sin variante), train: n=293, exp=0.571R, recortada=0.184R, PF=3.07.

### V1: trailing por ATR

| trailK | n | exp | exp_trim | pf | smooth | feasible | gana_recortada |
|---|---|---|---|---|---|---|---|
| 2.000 | 316 | 0.209 | 0.081 | 1.878 | 0.101 | True | -0.103 |
| 3.000 | 299 | 0.468 | 0.121 | 2.752 | 0.103 | True | -0.063 |
| 4.000 | 295 | 0.448 | 0.106 | 2.604 | 0.135 | True | -0.078 |
| 6.000 | 293 | 0.494 | 0.179 | 2.787 | 0.143 | True | -0.006 |

**NO pasa**: recortada mejora -0.006R < 0.02R; meseta suavizada 0.143 <= control 0.184.

### V2: break-even a +beR x riesgo

| beR | n | exp | exp_trim | pf | smooth | feasible | gana_recortada |
|---|---|---|---|---|---|---|---|
| 1.000 | 295 | 0.535 | 0.151 | 2.981 | 0.151 | True | -0.034 |
| 1.500 | 294 | 0.536 | 0.151 | 2.965 | 0.163 | True | -0.034 |
| 2.000 | 293 | 0.573 | 0.187 | 3.103 | 0.169 | True | 0.002 |

**NO pasa**: recortada mejora +0.002R < 0.02R; meseta suavizada 0.169 <= control 0.184.

### V3: salida contra la EMA55

| exitMid | n | exp | exp_trim | pf | smooth | feasible | gana_recortada |
|---|---|---|---|---|---|---|---|
| True | 268 | 2.475 | 0.059 | 9.555 | 0.059 | True | -0.126 |

**NO pasa**: recortada mejora -0.126R < 0.02R; meseta suavizada 0.059 <= control 0.184.

### V4: largos solo con BTC D1 sobre su EMA200

| regimeFilter | n | exp | exp_trim | pf | smooth | feasible | gana_recortada |
|---|---|---|---|---|---|---|---|
| True | 266 | 0.577 | 0.151 | 3.014 | 0.151 | True | -0.033 |

**NO pasa**: recortada mejora -0.033R < 0.02R; meseta suavizada 0.151 <= control 0.184.

**Pasan a Z2:** ninguna.
