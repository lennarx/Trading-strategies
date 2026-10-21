# Variantes H4: seleccion en train (generado por `python -m sqzlab.varsearch`)

Set base: `params/h4.json`. Train: monedas BTC, ETH, XRP, LTC, ADA, DOGE, entradas 2017-01-01..2023-12-31. **Pruebas: 10** (1 control + puntos de grilla). Criterios fijados antes en PROTOCOLO.

Control (set vigente sin variante), train: n=377, exp=0.874R, recortada=0.316R, PF=3.25.

### V1: trailing por ATR

| trailK | n | exp | exp_trim | pf | smooth | feasible | gana_recortada |
|---|---|---|---|---|---|---|---|
| 2.000 | 390 | 0.363 | 0.230 | 2.374 | 0.226 | True | -0.086 |
| 3.000 | 384 | 0.395 | 0.223 | 2.189 | 0.247 | True | -0.093 |
| 4.000 | 379 | 0.731 | 0.287 | 2.979 | 0.274 | True | -0.029 |
| 6.000 | 377 | 0.854 | 0.311 | 3.221 | 0.299 | True | -0.005 |

**NO pasa**: recortada mejora -0.005R < 0.02R; meseta suavizada 0.299 <= control 0.316; mejora la expectativa en 0 de 4 anios (< 3).

### V2: break-even a +beR x riesgo

| beR | n | exp | exp_trim | pf | smooth | feasible | gana_recortada |
|---|---|---|---|---|---|---|---|
| 1.000 | 379 | 0.840 | 0.297 | 3.335 | 0.298 | True | -0.019 |
| 1.500 | 378 | 0.844 | 0.299 | 3.281 | 0.303 | True | -0.017 |
| 2.000 | 378 | 0.857 | 0.313 | 3.257 | 0.306 | True | -0.003 |

**NO pasa**: recortada mejora -0.003R < 0.02R; meseta suavizada 0.306 <= control 0.316; mejora la expectativa en 0 de 4 anios (< 3).

### V3: salida contra la EMA55

| exitMid | n | exp | exp_trim | pf | smooth | feasible | gana_recortada |
|---|---|---|---|---|---|---|---|
| True | 358 | 0.999 | 0.346 | 2.917 | 0.346 | True | 0.030 |

**NO pasa**: mejora la expectativa en 1 de 4 anios (< 3).

### V4: largos solo con BTC D1 sobre su EMA200

| regimeFilter | n | exp | exp_trim | pf | smooth | feasible | gana_recortada |
|---|---|---|---|---|---|---|---|
| True | 329 | 0.799 | 0.268 | 2.980 | 0.268 | True | -0.048 |

**NO pasa**: recortada mejora -0.048R < 0.02R; meseta suavizada 0.268 <= control 0.316; mejora la expectativa en 1 de 4 anios (< 3).

**Pasan a Z2:** ninguna.
