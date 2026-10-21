# Optimizacion H4 (generado por `python -m sqzlab.optimize`)

- **Pruebas (combinaciones evaluadas) hasta ahora: 356** (etapa 0: 1, etapa 1: 8, etapa 2: 240, etapa 3: 81, etapa 4: 26)
- Veredicto: CANDIDATO: OOS n=556, exp=0.389R, PF=1.98, baseline p95=0.191R, sin el mejor=0.328R, recortada=0.095R

## Etapa 0: referencia (defaults v2) en monedas train, entradas 2017-01-01..2023-12-31

Monedas train: BTC, ETH, XRP, LTC, ADA, DOGE.

| n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 | k_ATR |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2029 | 0.320 | 2.004 | 0.293 | 30.981 | 649.089 | 0.281 | 0.004 | 0.304 | -0.025 | 0.010 | 2.207 |

Por senal y lado:

| kind | side | n | exp | pf | win | total |
|---|---|---|---|---|---|---|
| A | -1 | 293 | 0.142 | 1.375 | 0.311 | 41.574 |
| A | 1 | 242 | 0.829 | 3.426 | 0.376 | 200.562 |
| B | -1 | 353 | 0.325 | 1.941 | 0.329 | 114.727 |
| B | 1 | 369 | 0.814 | 2.977 | 0.314 | 300.289 |
| C | -1 | 389 | -0.069 | 0.669 | 0.195 | -26.773 |
| D | -1 | 156 | 0.082 | 1.300 | 0.282 | 12.818 |
| D | 1 | 227 | 0.026 | 1.106 | 0.269 | 5.891 |

Por moneda:

| coin | n | exp | pf | win | total |
|---|---|---|---|---|---|
| ADA | 312 | 0.170 | 1.570 | 0.292 | 52.915 |
| BTC | 370 | 0.511 | 2.561 | 0.311 | 189.251 |
| DOGE | 261 | 0.601 | 2.798 | 0.287 | 156.886 |
| ETH | 332 | 0.282 | 1.919 | 0.292 | 93.506 |
| LTC | 358 | 0.076 | 1.249 | 0.282 | 27.318 |
| XRP | 396 | 0.326 | 1.967 | 0.293 | 129.213 |

## Etapa 1: piernas aisladas (defaults v2, una pierna encendida a la vez)

| senal | lado | n | exp | pf | win | base_p50 | base_p95 | viva | debil |
|---|---|---|---|---|---|---|---|---|---|
| A | largo | 333 | 0.802 | 3.250 | 0.375 | 0.078 | 0.237 | True | True |
| A | corto | 382 | 0.090 | 1.228 | 0.301 | -0.008 | 0.091 | False | True |
| B | largo | 432 | 0.949 | 3.364 | 0.322 | 0.105 | 0.266 | True | True |
| B | corto | 423 | 0.235 | 1.661 | 0.303 | -0.010 | 0.091 | True | True |
| C | largo | 378 | -0.006 | 0.971 | 0.190 | 0.083 | 0.222 | False | False |
| C | corto | 389 | -0.069 | 0.669 | 0.195 | -0.009 | 0.069 | False | False |
| D | largo | 235 | 0.027 | 1.110 | 0.277 | 0.079 | 0.271 | False | False |
| D | corto | 225 | 0.031 | 1.116 | 0.271 | -0.006 | 0.107 | False | True |

Piernas vivas (exp > p95 del baseline aleatorio). Se llevan a la etapa 2: A+, B+, B-.

## Etapa 2: grilla por senal (solo piernas llevadas; el resto de las senales apagado)

### Senal A (48 combinaciones, 48 factibles)

Elegida (mejor score suavizado de meseta, no el pico): {"adxMin": 30, "pbBars": 3, "atrMult": 0.1}

Top 8 por score suavizado:

| adxMin | pbBars | atrMult | n | exp | exp_trim | pf | smooth |
|---|---|---|---|---|---|---|---|
| 30 | 3 | 0.100 | 60 | 2.195 | 0.504 | 6.613 | 0.432 |
| 30 | 3 | 0.250 | 60 | 1.983 | 0.462 | 6.455 | 0.419 |
| 30 | 5 | 0.100 | 105 | 1.448 | 0.361 | 5.358 | 0.404 |
| 25 | 3 | 0.100 | 134 | 1.253 | 0.402 | 4.236 | 0.390 |
| 30 | 8 | 0.100 | 157 | 0.970 | 0.407 | 4.575 | 0.380 |
| 30 | 5 | 0.250 | 105 | 1.319 | 0.342 | 5.277 | 0.375 |
| 30 | 3 | 0.500 | 60 | 1.715 | 0.410 | 6.323 | 0.371 |
| 30 | 8 | 0.250 | 157 | 0.914 | 0.392 | 4.651 | 0.367 |

Pico crudo (no se usa): exp=2.195R con n=60, score suavizado 0.432.

### Senal B (192 combinaciones, 114 factibles)

Elegida (mejor score suavizado de meseta, no el pico): {"minSqz": 12, "graceBars": 2, "needE200": true, "needMom": true, "invBars": 0}

Top 8 por score suavizado:

| minSqz | graceBars | needE200 | needMom | invBars | n | exp | exp_trim | pf | smooth |
|---|---|---|---|---|---|---|---|---|---|
| 12 | 2 | True | True | 0 | 397 | 0.846 | 0.300 | 3.200 | 0.217 |
| 12 | 1 | True | True | 0 | 369 | 0.877 | 0.289 | 3.227 | 0.211 |
| 12 | 4 | True | True | 0 | 429 | 0.827 | 0.272 | 3.154 | 0.194 |
| 12 | 4 | True | False | 0 | 453 | 0.832 | 0.258 | 3.094 | 0.193 |
| 12 | 1 | True | True | 2 | 370 | 0.776 | 0.188 | 3.332 | 0.173 |
| 12 | 2 | True | True | 2 | 398 | 0.745 | 0.199 | 3.274 | 0.172 |
| 12 | 4 | True | False | 2 | 454 | 0.773 | 0.200 | 3.308 | 0.164 |
| 12 | 4 | True | True | 2 | 430 | 0.733 | 0.178 | 3.215 | 0.158 |

Pico crudo (no se usa): exp=0.877R con n=369, score suavizado 0.211.

## Etapa 3: squeeze comun (bb/kc) con lo elegido en la etapa 2 (81 combinaciones)

Elegido: {"bbLen": 26, "bbMult": 2.0, "kcLen": 16, "kcMult": 2.0} (score suavizado 0.306, n=377, exp=0.874R).

Top 8:

| bbLen | bbMult | kcLen | kcMult | n | exp | exp_trim | pf | smooth |
|---|---|---|---|---|---|---|---|---|
| 26 | 2.000 | 16 | 2.000 | 377 | 0.874 | 0.316 | 3.250 | 0.306 |
| 26 | 2.500 | 26 | 2.000 | 366 | 0.763 | 0.198 | 3.037 | 0.263 |
| 16 | 2.000 | 16 | 1.500 | 643 | 0.609 | 0.157 | 2.461 | 0.259 |
| 16 | 1.500 | 16 | 1.000 | 434 | 0.770 | 0.230 | 2.856 | 0.257 |
| 20 | 2.500 | 16 | 2.000 | 356 | 0.883 | 0.280 | 3.344 | 0.255 |
| 16 | 2.500 | 16 | 2.000 | 784 | 0.605 | 0.207 | 2.500 | 0.252 |
| 26 | 2.000 | 20 | 2.000 | 473 | 0.706 | 0.224 | 2.852 | 0.244 |
| 16 | 2.500 | 20 | 2.000 | 612 | 0.640 | 0.164 | 2.554 | 0.236 |

## Etapa 4: chequeo de meseta +-20% sobre el set final (train)

Centro: n=377, exp=0.874R, exp recortada=0.316R, PF=3.25. Criterio: la expectativa recortada del vecino sigue > 0 y >= 50% de la central.

| param | vecino | valor | n | exp | exp_trim | pf | ok |
|---|---|---|---|---|---|---|---|
| adxMin | -20% | 24.000 | 455 | 0.795 | 0.295 | 3.036 | True |
| adxMin | +20% | 36.000 | 348 | 0.885 | 0.320 | 3.293 | True |
| pbBars | -20% | 2.000 | 364 | 0.909 | 0.324 | 3.332 | True |
| pbBars | +20% | 4.000 | 394 | 0.841 | 0.307 | 3.197 | True |
| atrMult | -20% | 0.080 | 377 | 0.879 | 0.316 | 3.261 | True |
| atrMult | +20% | 0.120 | 377 | 0.869 | 0.316 | 3.239 | True |
| minSqz | -20% | 10.000 | 466 | 0.815 | 0.315 | 3.015 | True |
| minSqz | +20% | 14.000 | 302 | 0.763 | 0.170 | 2.964 | True |
| graceBars | -20% | 1.000 | 365 | 0.887 | 0.310 | 3.254 | True |
| graceBars | +20% | 3.000 | 390 | 0.859 | 0.320 | 3.256 | True |
| bbLen | -20% | 21.000 | 637 | 0.655 | 0.222 | 2.694 | True |
| bbLen | +20% | 31.000 | 260 | 0.885 | 0.232 | 3.287 | True |
| bbMult | -20% | 1.600 | 673 | 0.602 | 0.209 | 2.566 | True |
| bbMult | +20% | 2.400 | 192 | 1.008 | 0.328 | 3.584 | True |
| kcLen | -20% | 13.000 | 306 | 0.795 | 0.206 | 3.002 | True |
| kcLen | +20% | 19.000 | 453 | 0.740 | 0.240 | 2.922 | True |
| kcMult | -20% | 1.600 | 155 | 1.196 | 0.354 | 4.342 | True |
| kcMult | +20% | 2.400 | 674 | 0.592 | 0.198 | 2.527 | True |

Ningun parametro es un pico aislado.

## Etapa 5: fuera de muestra (se mira UNA sola vez)

Set evaluado: `{"useA": true, "aLong": true, "aShort": false, "useB": true, "bLong": true, "bShort": true, "useC": false, "cLong": false, "cShort": false, "useD": false, "dLong": false, "dShort": false, "adxMin": 30, "pbBars": 3, "atrMult": 0.1, "minSqz": 12, "graceBars": 2, "needE200": true, "needMom": true, "invBars": 0, "bbLen": 26, "bbMult": 2.0, "kcLen": 16, "kcMult": 2.0}`

| grupo | n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train (monedas train, 2017-2023) | 377 | 0.874 | 3.250 | 0.419 | 10.820 | 329.531 | 0.641 | 0.316 | 0.697 | 0.044 | 0.182 |
| test (monedas train, 2024-hoy) | 166 | 0.410 | 2.097 | 0.392 | 12.232 | 68.059 | 0.242 | 0.090 | 0.251 | -0.020 | 0.203 |
| holdout (monedas holdout, 2017-hoy) | 390 | 0.380 | 1.934 | 0.372 | 15.325 | 148.061 | 0.293 | 0.100 | 0.347 | 0.025 | 0.259 |
| OOS agregado (test + holdout) | 556 | 0.389 | 1.980 | 0.378 | 23.935 | 216.120 | 0.328 | 0.095 | 0.290 | 0.019 | 0.191 |

Vara: defaults v2 sin optimizar (mismos grupos; es solo comparacion, no se elige nada con esto):

| grupo | n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train (monedas train, 2017-2023) | 2029 | 0.320 | 2.004 | 0.293 | 30.981 | 649.089 | 0.281 | 0.004 | 0.304 | -0.025 | 0.015 |
| test (monedas train, 2024-hoy) | 998 | 0.113 | 1.338 | 0.275 | 38.872 | 112.711 | 0.077 | -0.078 | 0.113 | -0.068 | -0.015 |
| holdout (monedas holdout, 2017-hoy) | 2179 | 0.056 | 1.179 | 0.273 | 56.978 | 122.633 | 0.045 | -0.096 | 0.029 | -0.042 | 0.012 |
| OOS agregado (test + holdout) | 3177 | 0.074 | 1.231 | 0.274 | 65.287 | 235.344 | 0.063 | -0.091 | 0.078 | -0.050 | -0.008 |

Criterios de escritura de `params/` (fijados antes): expectativa > 0,2R: SI; expectativa > p95 del baseline: SI; n >= 100: SI; sin el mejor trade > 0: SI; expectativa recortada (sin 2% mejores) > 0: SI; mediana por moneda > 0: SI. Entrenamiento factible: SI.
Criterios informativos (PROTOCOLO sec. 3): PF entre 1,5 y 2,5: SI; ganancia total >= 2x DD (en R): SI.

Por moneda (OOS):

| coin | n | exp | pf | win | total |
|---|---|---|---|---|---|
| ADA | 30 | 0.290 | 1.789 | 0.333 | 8.709 |
| BCH | 73 | 0.157 | 1.348 | 0.356 | 11.483 |
| BNB | 99 | 0.689 | 2.767 | 0.404 | 68.185 |
| BTC | 26 | 0.137 | 1.298 | 0.346 | 3.553 |
| DOGE | 36 | 0.322 | 1.734 | 0.333 | 11.589 |
| ETH | 25 | 0.211 | 1.533 | 0.400 | 5.271 |
| LINK | 89 | 0.347 | 1.764 | 0.326 | 30.846 |
| LTC | 26 | 0.115 | 1.492 | 0.538 | 2.997 |
| SOL | 70 | 0.771 | 3.640 | 0.529 | 53.942 |
| XLM | 59 | -0.278 | 0.374 | 0.220 | -16.394 |
| XRP | 23 | 1.563 | 5.901 | 0.435 | 35.940 |

Por senal y lado (OOS):

| kind | side | n | exp | pf | win | total |
|---|---|---|---|---|---|---|
| A | 1 | 97 | 0.661 | 2.741 | 0.340 | 64.070 |
| B | -1 | 208 | 0.020 | 1.049 | 0.346 | 4.195 |
| B | 1 | 251 | 0.589 | 2.493 | 0.418 | 147.855 |

Consistencia por anio (todas las monedas, set final):

| anio | n | exp | total |
|---|---|---|---|
| 2017 | 24 | 1.750 | 41.997 |
| 2018 | 39 | 0.882 | 34.413 |
| 2019 | 97 | 0.674 | 65.412 |
| 2020 | 104 | 0.692 | 71.920 |
| 2021 | 121 | 1.399 | 169.319 |
| 2022 | 97 | 0.219 | 21.252 |
| 2023 | 128 | 0.478 | 61.131 |
| 2024 | 124 | 0.329 | 40.828 |
| 2025 | 108 | 0.201 | 21.671 |
| 2026 | 91 | 0.195 | 17.709 |

Walk-forward informativo (train 3 anios -> test 1 anio, re-eligiendo el squeeze en cada fold):

| train | test | n_test | exp_test | elegido |
|---|---|---|---|---|
| 2017-2019 | 2020 | 71 | 0.332 | {"bbLen": 16, "bbMult": 1.5, "kcLen": 16, "kcMult": 1.0} |
| 2018-2020 | 2021 | 96 | 1.520 | {"bbLen": 16, "bbMult": 2.0, "kcLen": 20, "kcMult": 1.5} |
| 2019-2021 | 2022 | 19 | 1.323 | {"bbLen": 26, "bbMult": 1.5, "kcLen": 26, "kcMult": 1.0} |
| 2020-2022 | 2023 | 49 | -0.003 | {"bbLen": 20, "bbMult": 1.5, "kcLen": 20, "kcMult": 1.0} |

