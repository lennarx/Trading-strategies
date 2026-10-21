# Optimizacion D1 (generado por `python -m sqzlab.optimize`)

- **Pruebas (combinaciones evaluadas) hasta ahora: 617** (etapa 0: 1, etapa 1: 8, etapa 2: 483, etapa 3: 81, etapa 4: 44)
- Veredicto: SIN CANDIDATO: OOS n=278, exp=0.336R, PF=1.87, baseline p95=0.174R, sin el mejor=0.189R, recortada=-0.029R

## Etapa 0: referencia (defaults v2) en monedas train, entradas 2017-01-01..2023-12-31

Monedas train: BTC, ETH, XRP, LTC, ADA, DOGE.

| n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 | k_ATR |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 293 | 0.571 | 3.066 | 0.338 | 12.614 | 167.224 | 0.425 | 0.184 | 0.557 | 0.004 | 0.105 | 2.298 |

Por senal y lado:

| kind | side | n | exp | pf | win | total |
|---|---|---|---|---|---|---|
| A | -1 | 45 | -0.021 | 0.945 | 0.289 | -0.962 |
| A | 1 | 34 | 2.235 | 9.811 | 0.529 | 75.976 |
| B | -1 | 48 | 0.330 | 1.853 | 0.333 | 15.836 |
| B | 1 | 46 | 1.295 | 5.401 | 0.435 | 59.587 |
| C | -1 | 63 | -0.043 | 0.751 | 0.222 | -2.699 |
| D | -1 | 20 | 0.142 | 1.788 | 0.350 | 2.842 |
| D | 1 | 37 | 0.450 | 2.973 | 0.297 | 16.644 |

Por moneda:

| coin | n | exp | pf | win | total |
|---|---|---|---|---|---|
| ADA | 42 | 0.493 | 2.969 | 0.381 | 20.715 |
| BTC | 55 | 1.075 | 5.065 | 0.382 | 59.148 |
| DOGE | 32 | 1.556 | 6.726 | 0.375 | 49.781 |
| ETH | 48 | 0.049 | 1.140 | 0.312 | 2.370 |
| LTC | 57 | -0.025 | 0.894 | 0.263 | -1.431 |
| XRP | 59 | 0.621 | 3.189 | 0.339 | 36.641 |

## Etapa 1: piernas aisladas (defaults v2, una pierna encendida a la vez)

| senal | lado | n | exp | pf | win | base_p50 | base_p95 | viva | debil |
|---|---|---|---|---|---|---|---|---|---|
| A | largo | 48 | 1.780 | 7.938 | 0.542 | 0.140 | 0.540 | True | True |
| A | corto | 54 | 0.008 | 1.022 | 0.296 | -0.021 | 0.145 | False | True |
| B | largo | 55 | 1.331 | 5.282 | 0.400 | 0.155 | 0.671 | True | True |
| B | corto | 65 | 0.241 | 1.663 | 0.323 | -0.024 | 0.145 | True | True |
| C | largo | 65 | 0.184 | 1.989 | 0.231 | 0.166 | 0.558 | False | True |
| C | corto | 63 | -0.043 | 0.751 | 0.222 | -0.023 | 0.107 | False | False |
| D | largo | 37 | 0.450 | 2.973 | 0.297 | 0.115 | 0.600 | False | True |
| D | corto | 32 | 0.389 | 3.149 | 0.344 | -0.033 | 0.167 | True | True |

Piernas vivas (exp > p95 del baseline aleatorio). Se llevan a la etapa 2: A+, B+, B-, D-.

## Etapa 2: grilla por senal (solo piernas llevadas; el resto de las senales apagado)

### Senal A (48 combinaciones, 32 factibles)

Elegida (mejor score suavizado de meseta, no el pico): {"adxMin": 15, "pbBars": 3, "atrMult": 0.1}

Top 8 por score suavizado:

| adxMin | pbBars | atrMult | n | exp | exp_trim | pf | smooth |
|---|---|---|---|---|---|---|---|
| 15 | 3 | 0.100 | 57 | 2.068 | 0.834 | 6.297 | 0.812 |
| 15 | 3 | 0.250 | 55 | 1.989 | 0.860 | 6.985 | 0.806 |
| 15 | 3 | 0.500 | 55 | 1.736 | 0.787 | 6.901 | 0.751 |
| 15 | 5 | 0.100 | 75 | 0.935 | 0.661 | 4.011 | 0.718 |
| 15 | 5 | 0.250 | 75 | 0.874 | 0.620 | 3.952 | 0.684 |
| 15 | 3 | 1.000 | 55 | 1.399 | 0.681 | 6.981 | 0.680 |
| 15 | 5 | 0.500 | 75 | 0.795 | 0.569 | 3.952 | 0.628 |
| 20 | 3 | 0.250 | 31 | 2.645 | 0.928 | 10.455 | 0.574 |

Pico crudo (no se usa): exp=2.782R con n=32, score suavizado 0.522.

### Senal B (192 combinaciones, 192 factibles)

Elegida (mejor score suavizado de meseta, no el pico): {"minSqz": 8, "graceBars": 1, "needE200": true, "needMom": true, "invBars": 2}

Top 8 por score suavizado:

| minSqz | graceBars | needE200 | needMom | invBars | n | exp | exp_trim | pf | smooth |
|---|---|---|---|---|---|---|---|---|---|
| 8 | 1 | True | True | 2 | 90 | 1.098 | 0.706 | 4.529 | 0.549 |
| 8 | 1 | True | True | 0 | 90 | 1.057 | 0.665 | 3.801 | 0.538 |
| 8 | 1 | True | True | 3 | 90 | 1.058 | 0.666 | 4.360 | 0.521 |
| 8 | 1 | True | False | 2 | 96 | 1.041 | 0.673 | 4.079 | 0.519 |
| 8 | 2 | True | True | 2 | 95 | 1.051 | 0.679 | 4.446 | 0.518 |
| 8 | 1 | True | False | 0 | 96 | 1.025 | 0.657 | 3.570 | 0.516 |
| 8 | 2 | True | True | 0 | 95 | 1.021 | 0.649 | 3.843 | 0.505 |
| 8 | 1 | True | False | 3 | 96 | 1.013 | 0.644 | 4.046 | 0.497 |

Pico crudo (no se usa): exp=1.098R con n=90, score suavizado 0.549.

### Senal D (243 combinaciones, 36 factibles)

Elegida (mejor score suavizado de meseta, no el pico): {"dvL": 5, "dvR": 5, "dvMin": 5, "dvMax": 100, "dAtrMult": 0.5, "dMaxRisk": 5.0}

Top 8 por score suavizado:

| dvL | dvR | dvMin | dvMax | dAtrMult | dMaxRisk | n | exp | exp_trim | pf | smooth |
|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 5 | 5 | 100 | 0.500 | 5.000 | 32 | 0.356 | 0.091 | 3.183 | -0.272 |
| 5 | 5 | 5 | 100 | 0.500 | 0.000 | 32 | 0.356 | 0.091 | 3.183 | -0.273 |
| 5 | 5 | 5 | 100 | 0.250 | 0.000 | 32 | 0.389 | 0.099 | 3.149 | -0.314 |
| 5 | 5 | 5 | 100 | 0.250 | 5.000 | 32 | 0.389 | 0.099 | 3.149 | -0.314 |
| 5 | 5 | 3 | 100 | 0.500 | 5.000 | 32 | 0.356 | 0.091 | 3.183 | -0.318 |
| 5 | 5 | 8 | 100 | 0.500 | 5.000 | 32 | 0.356 | 0.091 | 3.183 | -0.318 |
| 5 | 5 | 3 | 100 | 0.500 | 0.000 | 32 | 0.356 | 0.091 | 3.183 | -0.319 |
| 5 | 5 | 8 | 100 | 0.500 | 0.000 | 32 | 0.356 | 0.091 | 3.183 | -0.319 |

Pico crudo (no se usa): exp=0.389R con n=32, score suavizado -0.451.

## Etapa 3: squeeze comun (bb/kc) con lo elegido en la etapa 2 (81 combinaciones)

Elegido: {"bbLen": 20, "bbMult": 2.5, "kcLen": 20, "kcMult": 2.0} (score suavizado 0.427, n=181, exp=0.927R).

Top 8:

| bbLen | bbMult | kcLen | kcMult | n | exp | exp_trim | pf | smooth |
|---|---|---|---|---|---|---|---|---|
| 20 | 2.500 | 20 | 2.000 | 181 | 0.927 | 0.374 | 3.866 | 0.427 |
| 26 | 2.000 | 16 | 2.000 | 143 | 1.092 | 0.449 | 4.509 | 0.419 |
| 20 | 2.500 | 16 | 2.000 | 144 | 1.155 | 0.518 | 4.462 | 0.406 |
| 26 | 2.000 | 26 | 2.000 | 185 | 0.911 | 0.356 | 4.215 | 0.388 |
| 20 | 2.000 | 26 | 2.000 | 193 | 0.840 | 0.324 | 3.719 | 0.358 |
| 20 | 1.500 | 20 | 1.500 | 238 | 0.723 | 0.292 | 3.329 | 0.353 |
| 26 | 1.500 | 16 | 2.000 | 208 | 0.771 | 0.236 | 3.435 | 0.351 |
| 20 | 2.000 | 16 | 2.000 | 227 | 0.726 | 0.244 | 3.291 | 0.341 |

## Etapa 4: chequeo de meseta +-20% sobre el set final (train)

Centro: n=181, exp=0.927R, exp recortada=0.374R, PF=3.87. Criterio: la expectativa recortada del vecino sigue > 0 y >= 50% de la central.

| param | vecino | valor | n | exp | exp_trim | pf | ok |
|---|---|---|---|---|---|---|---|
| adxMin | -20% | 12.000 | 186 | 0.901 | 0.363 | 3.677 | True |
| adxMin | +20% | 18.000 | 168 | 0.993 | 0.398 | 4.336 | True |
| pbBars | -20% | 2.000 | 172 | 0.994 | 0.413 | 4.279 | True |
| pbBars | +20% | 4.000 | 183 | 0.741 | 0.348 | 3.269 | True |
| atrMult | -20% | 0.080 | 181 | 0.935 | 0.376 | 3.887 | True |
| atrMult | +20% | 0.120 | 179 | 0.945 | 0.392 | 4.040 | True |
| minSqz | -20% | 6.000 | 196 | 0.824 | 0.312 | 3.407 | True |
| minSqz | +20% | 10.000 | 164 | 0.987 | 0.377 | 4.037 | True |
| graceBars | -20% | 1.000 | 181 | 0.927 | 0.374 | 3.866 | True |
| graceBars | +20% | 2.000 | 185 | 0.919 | 0.379 | 3.912 | True |
| invBars | -20% | 1.000 | 181 | 0.926 | 0.373 | 3.792 | True |
| invBars | +20% | 3.000 | 181 | 0.912 | 0.359 | 3.848 | True |
| dvL | -20% | 4.000 | 180 | 0.935 | 0.380 | 3.905 | True |
| dvL | +20% | 6.000 | 181 | 0.927 | 0.374 | 3.866 | True |
| dvR | -20% | 4.000 | 174 | 0.980 | 0.406 | 4.022 | True |
| dvR | +20% | 6.000 | 180 | 0.890 | 0.333 | 3.711 | True |
| dvMin | -20% | 4.000 | 181 | 0.927 | 0.374 | 3.866 | True |
| dvMin | +20% | 6.000 | 181 | 0.927 | 0.374 | 3.866 | True |
| dvMax | -20% | 80.000 | 181 | 0.927 | 0.374 | 3.866 | True |
| dvMax | +20% | 120.000 | 181 | 0.927 | 0.374 | 3.866 | True |
| dAtrMult | -20% | 0.400 | 181 | 0.929 | 0.376 | 3.862 | True |
| dAtrMult | +20% | 0.600 | 181 | 0.925 | 0.372 | 3.869 | True |
| dMaxRisk | -20% | 4.000 | 181 | 0.926 | 0.373 | 3.856 | True |
| dMaxRisk | +20% | 6.000 | 181 | 0.927 | 0.374 | 3.866 | True |
| bbLen | -20% | 16.000 | 184 | 0.771 | 0.255 | 3.256 | True |
| bbLen | +20% | 24.000 | 126 | 1.273 | 0.595 | 5.049 | True |
| bbMult | -20% | 2.000 | 238 | 0.723 | 0.292 | 3.329 | True |
| bbMult | +20% | 3.000 | 135 | 1.184 | 0.504 | 4.282 | True |
| kcLen | -20% | 16.000 | 144 | 1.155 | 0.518 | 4.462 | True |
| kcLen | +20% | 24.000 | 162 | 0.931 | 0.326 | 3.855 | True |
| kcMult | -20% | 1.600 | 123 | 1.058 | 0.397 | 3.986 | True |
| kcMult | +20% | 2.400 | 227 | 0.700 | 0.247 | 3.201 | True |

Ningun parametro es un pico aislado.

## Etapa 5: fuera de muestra (se mira UNA sola vez)

Set evaluado: `{"useA": true, "aLong": true, "aShort": false, "useB": true, "bLong": true, "bShort": true, "useC": false, "cLong": false, "cShort": false, "useD": true, "dLong": false, "dShort": true, "adxMin": 15, "pbBars": 3, "atrMult": 0.1, "minSqz": 8, "graceBars": 1, "needE200": true, "needMom": true, "invBars": 2, "dvL": 5, "dvR": 5, "dvMin": 5, "dvMax": 100, "dAtrMult": 0.5, "dMaxRisk": 5.0, "bbLen": 20, "bbMult": 2.5, "kcLen": 20, "kcMult": 2.0}`

| grupo | n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train (monedas train, 2017-2023) | 181 | 0.927 | 3.866 | 0.370 | 13.122 | 167.747 | 0.591 | 0.374 | 0.776 | 0.046 | 0.241 |
| test (monedas train, 2024-hoy) | 100 | 0.015 | 1.034 | 0.250 | 11.788 | 1.512 | -0.080 | -0.150 | 0.072 | -0.022 | 0.254 |
| holdout (monedas holdout, 2017-hoy) | 178 | 0.516 | 2.448 | 0.309 | 11.907 | 91.916 | 0.287 | 0.039 | 0.449 | 0.011 | 0.254 |
| OOS agregado (test + holdout) | 278 | 0.336 | 1.867 | 0.288 | 15.436 | 93.428 | 0.189 | -0.029 | 0.205 | 0.013 | 0.174 |

Vara: defaults v2 sin optimizar (mismos grupos; es solo comparacion, no se elige nada con esto):

| grupo | n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train (monedas train, 2017-2023) | 293 | 0.571 | 3.066 | 0.338 | 12.614 | 167.224 | 0.425 | 0.184 | 0.557 | 0.008 | 0.115 |
| test (monedas train, 2024-hoy) | 142 | 0.381 | 2.297 | 0.289 | 11.679 | 54.058 | 0.211 | 0.100 | 0.327 | -0.045 | 0.158 |
| holdout (monedas holdout, 2017-hoy) | 326 | 0.307 | 2.033 | 0.276 | 14.415 | 100.124 | 0.182 | 0.009 | 0.202 | -0.023 | 0.099 |
| OOS agregado (test + holdout) | 468 | 0.329 | 2.112 | 0.280 | 19.511 | 154.181 | 0.242 | 0.034 | 0.302 | -0.027 | 0.075 |

Criterios de escritura de `params/` (fijados antes): expectativa > 0,2R: SI; expectativa > p95 del baseline: SI; n >= 100: SI; sin el mejor trade > 0: SI; expectativa recortada (sin 2% mejores) > 0: NO; mediana por moneda > 0: SI. Entrenamiento factible: SI.
Criterios informativos (PROTOCOLO sec. 3): PF entre 1,5 y 2,5: SI; ganancia total >= 2x DD (en R): SI.

Por moneda (OOS):

| coin | n | exp | pf | win | total |
|---|---|---|---|---|---|
| ADA | 19 | 0.205 | 1.628 | 0.105 | 3.899 |
| BCH | 43 | 0.190 | 1.491 | 0.302 | 8.150 |
| BNB | 40 | 0.608 | 2.815 | 0.300 | 24.335 |
| BTC | 17 | 0.185 | 1.451 | 0.471 | 3.137 |
| DOGE | 14 | -0.040 | 0.934 | 0.143 | -0.556 |
| ETH | 13 | 0.221 | 1.665 | 0.385 | 2.872 |
| LINK | 39 | 0.449 | 2.262 | 0.282 | 17.501 |
| LTC | 21 | -0.266 | 0.460 | 0.190 | -5.577 |
| SOL | 26 | 0.322 | 2.056 | 0.423 | 8.381 |
| XLM | 30 | 1.118 | 3.871 | 0.267 | 33.549 |
| XRP | 16 | -0.141 | 0.717 | 0.250 | -2.264 |

Por senal y lado (OOS):

| kind | side | n | exp | pf | win | total |
|---|---|---|---|---|---|---|
| A | 1 | 84 | 0.243 | 1.529 | 0.310 | 20.429 |
| B | -1 | 78 | -0.158 | 0.619 | 0.231 | -12.363 |
| B | 1 | 79 | 1.047 | 3.752 | 0.329 | 82.751 |
| D | -1 | 37 | 0.071 | 1.394 | 0.270 | 2.610 |

Consistencia por anio (todas las monedas, set final):

| anio | n | exp | total |
|---|---|---|---|
| 2017 | 6 | 2.457 | 14.741 |
| 2018 | 7 | 1.562 | 10.936 |
| 2019 | 30 | 0.082 | 2.448 |
| 2020 | 60 | 1.223 | 73.403 |
| 2021 | 86 | 1.031 | 88.663 |
| 2022 | 33 | 0.315 | 10.380 |
| 2023 | 71 | 0.095 | 6.780 |
| 2024 | 59 | 1.008 | 59.481 |
| 2025 | 80 | -0.063 | -5.080 |
| 2026 | 27 | -0.021 | -0.578 |

Walk-forward informativo (train 3 anios -> test 1 anio, re-eligiendo el squeeze en cada fold):

| train | test | n_test | exp_test | elegido |
|---|---|---|---|---|
| 2017-2019 | 2020 | 50 | 1.457 | {"bbLen": 20, "bbMult": 1.5, "kcLen": 16, "kcMult": 2.0} |
| 2018-2020 | 2021 | 33 | 1.968 | {"bbLen": 26, "bbMult": 1.5, "kcLen": 16, "kcMult": 1.5} |
| 2019-2021 | 2022 | 6 | 0.745 | {"bbLen": 26, "bbMult": 2.5, "kcLen": 16, "kcMult": 2.0} |
| 2020-2022 | 2023 | 24 | -0.141 | {"bbLen": 26, "bbMult": 2.5, "kcLen": 16, "kcMult": 2.0} |

