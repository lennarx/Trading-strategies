# Optimizacion W1 (generado por `python -m sqzlab.optimize`)

- **Pruebas (combinaciones evaluadas) hasta ahora: 1** (etapa 0: 1)
- Veredicto: SIN CANDIDATO: OOS n=12, exp=-0.128R, PF=0.64, baseline p95=0.388R, sin el mejor=-0.249R, recortada=-0.249R

## Etapa 0: referencia (defaults v2) en monedas train, entradas 2017-01-01..hoy

Monedas train: BTC, ETH, XRP, LTC, ADA, DOGE.

| n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 | k_ATR |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 43 | 0.939 | 4.621 | 0.326 | 7.002 | 40.364 | 0.266 | 0.266 | 0.161 | 0.003 | 0.680 | 2.410 |

Por senal y lado:

| kind | side | n | exp | pf | win | total |
|---|---|---|---|---|---|---|
| A | -1 | 1 | -0.195 | 0.000 | 0.000 | -0.195 |
| A | 1 | 11 | -0.296 | 0.350 | 0.182 | -3.259 |
| B | -1 | 6 | -0.407 | 0.000 | 0.000 | -2.443 |
| B | 1 | 5 | 0.136 | 1.485 | 0.400 | 0.682 |
| C | -1 | 11 | 0.040 | 1.325 | 0.455 | 0.438 |
| D | -1 | 1 | 0.193 | inf | 1.000 | 0.193 |
| D | 1 | 8 | 5.618 | 61.757 | 0.500 | 44.947 |

Por moneda:

| coin | n | exp | pf | win | total |
|---|---|---|---|---|---|
| ADA | 5 | 0.160 | 1.659 | 0.400 | 0.798 |
| BTC | 8 | 1.869 | 11.514 | 0.625 | 14.952 |
| DOGE | 9 | -0.228 | 0.004 | 0.111 | -2.054 |
| ETH | 7 | 4.013 | 18.118 | 0.571 | 28.092 |
| LTC | 6 | -0.453 | 0.000 | 0.000 | -2.719 |
| XRP | 8 | 0.162 | 1.619 | 0.250 | 1.294 |

**Sin muestra:** el agregado de W1 da 43 trades (< 100). Segun el protocolo, W1 hereda el set de D1.

## Etapa 5: fuera de muestra (se mira UNA sola vez)

W1 hereda el set final de D1 (sin muestra propia).

Set evaluado: `{"useA": true, "aLong": true, "aShort": false, "useB": true, "bLong": true, "bShort": true, "useC": false, "cLong": false, "cShort": false, "useD": true, "dLong": false, "dShort": true, "adxMin": 15, "pbBars": 3, "atrMult": 0.1, "minSqz": 8, "graceBars": 1, "needE200": true, "needMom": true, "invBars": 2, "dvL": 5, "dvR": 5, "dvMin": 5, "dvMax": 100, "dAtrMult": 0.5, "dMaxRisk": 5.0, "bbLen": 20, "bbMult": 2.5, "kcLen": 20, "kcMult": 2.0}`

| grupo | n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train (monedas train, todo 2017+) | 28 | 0.862 | 2.726 | 0.250 | 6.154 | 24.124 | -0.073 | -0.073 | -0.131 | 0.128 | 1.348 |
| holdout (monedas holdout, todo 2017+) | 12 | -0.128 | 0.642 | 0.333 | 2.072 | -1.533 | -0.249 | -0.249 | -0.170 | -0.069 | 0.388 |

Vara: defaults v2 sin optimizar (mismos grupos; es solo comparacion, no se elige nada con esto):

| grupo | n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train (monedas train, todo 2017+) | 43 | 0.939 | 4.621 | 0.326 | 7.002 | 40.364 | 0.266 | 0.266 | 0.161 | 0.011 | 0.736 |
| holdout (monedas holdout, todo 2017+) | 29 | -0.040 | 0.834 | 0.379 | 3.630 | -1.168 | -0.087 | -0.087 | -0.048 | -0.110 | 0.091 |

Criterios de escritura de `params/` (fijados antes): expectativa > 0,2R: NO; expectativa > p95 del baseline: NO; n >= 100: NO; sin el mejor trade > 0: NO; expectativa recortada (sin 2% mejores) > 0: NO; mediana por moneda > 0: NO. Entrenamiento factible: SI.
Criterios informativos (PROTOCOLO sec. 3): PF entre 1,5 y 2,5: NO; ganancia total >= 2x DD (en R): NO.

Por moneda (OOS):

| coin | n | exp | pf | win | total |
|---|---|---|---|---|---|
| BCH | 3 | -0.170 | 0.210 | 0.333 | -0.509 |
| BNB | 2 | 0.557 | 13.944 | 0.500 | 1.113 |
| LINK | 2 | -0.721 | 0.000 | 0.000 | -1.441 |
| SOL | 2 | -0.554 | 0.000 | 0.000 | -1.109 |
| XLM | 3 | 0.137 | 1.411 | 0.667 | 0.412 |

Por senal y lado (OOS):

| kind | side | n | exp | pf | win | total |
|---|---|---|---|---|---|---|
| A | 1 | 3 | -0.303 | 0.130 | 0.333 | -0.908 |
| B | -1 | 2 | -0.721 | 0.000 | 0.000 | -1.442 |
| B | 1 | 6 | 0.102 | 1.340 | 0.333 | 0.611 |
| D | -1 | 1 | 0.205 | inf | 1.000 | 0.205 |

Consistencia por anio (todas las monedas, set final):

| anio | n | exp | total |
|---|---|---|---|
| 2018 | 1 | -0.606 | -0.606 |
| 2020 | 2 | 12.762 | 25.524 |
| 2021 | 6 | -0.574 | -3.446 |
| 2022 | 1 | -0.483 | -0.483 |
| 2023 | 5 | 1.041 | 5.204 |
| 2024 | 13 | 0.275 | 3.579 |
| 2025 | 11 | -0.562 | -6.179 |
| 2026 | 1 | -1.003 | -1.003 |

