# Fase 7: que la estrategia SIRVA (generado por `python -m sqzlab.fase7_report`)
Reglas fijadas ANTES en `docs/PROTOCOLO.md` ("Decisiones fijadas ANTES de la Fase 7"). No es asesoria financiera. Las reglas del ensamble de Donchian salen del resumen del plan: el paper (Zarattini, Pagani, Barbon 2025) **no se pudo bajar** (SSRN 403, abarbon.com 502) y por eso esta **no verificado** contra el texto.
## Veredicto por temporalidad

| TF | veredicto | nota | candidato | R1_cumple_Z2_y_Z3 | pruebas_nuevas | pruebas_acumuladas |
|---|---|---|---|---|---|---|
| H4 | NO SIRVE | falla algun criterio en algun grupo | P1=bear P2=E P3=20 P4=50 P5=risk | False | 196 | 562 |
| D1 | NO SIRVE | falla algun criterio en algun grupo | P1=bear P2=E P3=10 P4=20 P5=vol | False | 260 | 887 |
| W1 | SIN MUESTRA | sin candidato: el set vigente (R0) tiene n < 100 en la validacion y los puntos con E que llegan a n >= 100 fallan la concentracion por moneda en train | sin candidato | False | 36 | 37 |

Pruebas nuevas de la Fase 7: **492** (grilla + R0/R1 por TF; cada mirada a un grupo se cuenta aparte: 5 miradas en total, maximo 1 por TF y grupo).

## H4
- Train: monedas BTC, ETH, XRP, LTC, ADA, DOGE, tramo 2017-01-01 a 2023-12-31. 96 puntos de grilla + 2 referencias = 196 pruebas; factibles: 18. Candidato elegido por meseta: {'p1': 'bear', 'p2': True, 'p3': 20, 'p4': 50, 'p5': 'risk'}.

Train (referencias recalculadas con el mismo codigo; buy&hold en el mismo tramo):

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| candidato [P1=bear P2=E P3=20 P4=50 P5=risk] | 390 | 616.000 | 1.463 | 0.540 | 0.406 | 1.331 | 0.510 | 28543.806 | 0.371 | 0.717 | 0.839 | 0.854 | 0.664 |
| R0 | 377 | 377.000 | 0.850 | 0.488 | 0.179 | 2.727 | 0.359 | 10435.937 | 0.573 | 0.717 | 0.839 | 0.854 | 0.664 |
| R1 | 453 | 1980.000 | 0.888 | 0.997 | 0.515 | 1.938 | 0.970 | 232499.256 | 0.252 | 0.717 | 0.839 | 0.854 | 0.664 |


Train, top 10 por score de meseta (todas las filas en `results/fase7_h4_grid.csv`):

| config | n | R_medio | CAGR | DD | Calmar | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | factible | meseta | elegido |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P1=bear P2=E P3=20 P4=50 P5=risk | 390 | 1.463 | 0.540 | 0.406 | 1.331 | 0.510 | 28543.806 | 0.371 | True | 0.769 | True |
| P1=off P2=E P3=20 P4=100 P5=risk | 272 | 1.801 | 0.492 | 0.416 | 1.192 | 0.464 | 23875.106 | 0.357 | True | 0.546 | False |
| P1=off P2=E P3=EMA20 P4=- P5=vol | 320 | 1.779 | 1.219 | 0.635 | 1.920 | 1.132 | 340987.475 | 0.395 | True | 0.498 | False |
| P1=bear P2=E P3=EMA20 P4=- P5=vol | 423 | 1.464 | 1.217 | 0.622 | 1.956 | 1.117 | 380244.627 | 0.398 | True | 0.491 | False |
| P1=bear P2=- P3=20 P4=- P5=risk | 313 | 0.898 | 0.432 | 0.263 | 1.639 | 0.381 | 21301.137 | 0.383 | True | 0.489 | False |
| P1=bear P2=- P3=20 P4=50 P5=risk | 281 | 0.889 | 0.381 | 0.289 | 1.317 | 0.332 | 14117.234 | 0.313 | True | 0.466 | False |
| P1=off P2=- P3=20 P4=50 P5=risk | 167 | 1.409 | 0.356 | 0.261 | 1.367 | 0.308 | 14287.155 | 0.272 | True | 0.437 | False |
| P1=bear P2=E P3=EMA20 P4=50 P5=vol | 402 | 1.301 | 1.157 | 0.540 | 2.070 | 1.072 | 361599.775 | 0.385 | True | 0.305 | False |
| P1=off P2=E P3=EMA20 P4=50 P5=vol | 291 | 1.631 | 1.156 | 0.529 | 2.112 | 1.070 | 333543.098 | 0.369 | True | 0.300 | False |
| P1=bear P2=E P3=20 P4=100 P5=risk | 374 | 1.489 | 0.486 | 0.393 | 1.239 | 0.462 | 24313.333 | 0.345 | True | 0.262 | False |


### Z2 (una mirada; monedas: ALGO, AVAX, ETC, ICP, TRX, VET; tramo 2018-07-14 a 2026-10-20)

**todo el historial**

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados | criterios | veredicto_grupo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| candidato [P1=bear P2=E P3=20 P4=50 P5=risk] | 547 | 805.000 | 0.401 | 0.133 | 0.361 | 0.368 | 0.132 | 0.301 | 0.109 | 1557.627 | 0.593 | 0.367 | 0.771 | 0.476 | 0.110 | 71.000 | 6/8 | NO CUMPLE |
| R0 [P1=normal P2=- P3=EMA20 P4=- P5=risk] | 521 | 521.000 | 0.064 | 0.029 | 0.333 | 0.086 | 0.029 | 0.276 | 0.009 | 946.885 | 0.641 | 0.367 | 0.771 | 0.476 | 0.110 | 1.000 | 5/8 | NO CUMPLE |
| R1 | 538 | 2434.000 | 0.321 | 0.366 | 0.579 | 0.633 | 0.371 | 0.323 | 0.361 | 18890.575 | 0.441 | 0.367 | 0.771 | 0.476 | 0.110 | 319.000 | 6/8 | NO CUMPLE |
| R1 informativa (sin cupo ni tope bruto) | 486 | 2686.000 | 0.366 | 0.505 | 0.732 | 0.689 | 0.511 | 0.386 | 0.494 | 52006.084 | 0.518 | 0.367 | 0.771 | 0.476 | 0.110 | 60.000 | nan | nan |


**2024-hoy**

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados | criterios | veredicto_grupo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| candidato [P1=bear P2=E P3=20 P4=50 P5=risk] | 234 | 305.000 | 0.088 | -0.000 | 0.253 | -0.001 | -0.001 | 0.203 | -0.023 | 94.334 | nan | 0.271 | 0.536 | 0.506 | -0.125 | 21.000 | 4/8 | NO CUMPLE |
| R0 [P1=normal P2=- P3=EMA20 P4=- P5=risk] | 196 | 196.000 | 0.071 | 0.043 | 0.210 | 0.206 | 0.043 | 0.188 | 0.011 | 172.374 | 1.690 | 0.271 | 0.536 | 0.506 | -0.125 | 1.000 | 6/8 | NO CUMPLE |
| R1 | 282 | 921.000 | 0.139 | 0.117 | 0.532 | 0.219 | 0.123 | 0.237 | 0.100 | -484.251 | 1.210 | 0.271 | 0.536 | 0.506 | -0.125 | 137.000 | 4/8 | NO CUMPLE |
| R1 informativa (sin cupo ni tope bruto) | 247 | 1050.000 | 0.174 | 0.143 | 0.730 | 0.196 | 0.156 | 0.417 | 0.118 | 183.050 | 1.383 | 0.271 | 0.536 | 0.506 | -0.125 | 0.000 | nan | nan |


- Candidato vs R1 (Calmar, todo el historial): 0.37 vs 0.63 -> el candidato NO supera a R1.

### Z3 (una mirada; monedas: 1INCH, ACM, AGLD, ALICE, ANKR, AR, ARPA, ASR, ATM, AUDIO, AVA, AXS, BAND, BAR, BAT, BEL, BNT, C98, CAKE, CELO, CELR, CFX, CHR, CHZ; tramo 2019-04-06 a 2026-10-20)

**todo el historial**

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados | criterios | veredicto_grupo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| candidato [P1=bear P2=E P3=20 P4=50 P5=risk] | 886 | 1167.000 | 0.252 | 0.054 | 0.710 | 0.072 | 0.055 | 0.595 | 0.021 | -372.459 | 1.731 | 0.445 | 0.771 | 0.578 | -0.081 | 2053.000 | 4/8 | NO CUMPLE |
| R0 [P1=normal P2=- P3=EMA20 P4=- P5=risk] | 1878 | 1878.000 | -0.001 | -0.068 | 0.884 | -0.077 | -0.068 | 0.860 | -0.102 | -1774.988 | nan | 0.445 | 0.771 | 0.578 | -0.081 | 451.000 | 2/8 | NO CUMPLE |
| R1 | 600 | 3041.000 | 0.275 | 0.106 | 0.942 | 0.113 | 0.099 | 0.846 | 0.096 | -4254.889 | 5.089 | 0.445 | 0.771 | 0.578 | -0.081 | 6357.000 | 4/8 | NO CUMPLE |
| R1 informativa (sin cupo ni tope bruto) | 1001 | 5598.000 | 0.320 | -1.000 | 1.024 | -0.976 | -1.000 | 1.055 | -1.000 | -12527.010 | nan | 0.445 | 0.771 | 0.578 | -0.081 | 3816.000 | nan | nan |


**2024-hoy**

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados | criterios | veredicto_grupo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| candidato [P1=bear P2=E P3=20 P4=50 P5=risk] | 419 | 514.000 | -0.168 | -0.180 | 0.449 | -0.406 | -0.180 | 0.436 | -0.207 | -240.469 | nan | 0.271 | 0.536 | 0.506 | -0.443 | 954.000 | 2/8 | NO CUMPLE |
| R0 [P1=normal P2=- P3=EMA20 P4=- P5=risk] | 811 | 811.000 | -0.131 | -0.338 | 0.686 | -0.493 | -0.338 | 0.686 | -0.359 | -310.486 | nan | 0.271 | 0.536 | 0.506 | -0.443 | 226.000 | 1/8 | NO CUMPLE |
| R1 | 297 | 1271.000 | -0.131 | -0.344 | 0.788 | -0.436 | -0.356 | 0.731 | -0.350 | -251.046 | nan | 0.271 | 0.536 | 0.506 | -0.443 | 2985.000 | 2/8 | NO CUMPLE |
| R1 informativa (sin cupo ni tope bruto) | 1013 | 4219.000 | -0.063 | -0.863 | 0.999 | -0.863 | -0.878 | 0.999 | -0.867 | -529.166 | nan | 0.271 | 0.536 | 0.506 | -0.443 | 0.000 | nan | nan |


- Candidato vs R1 (Calmar, todo el historial): 0.07 vs 0.11 -> el candidato NO supera a R1.

### 2024-hoy en todas las monedas (informativa; contaminada: incluye train, holdout, Z1, Z2 y Z3)

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| candidato | 355 | 483.000 | -0.035 | -0.018 | 0.303 | -0.061 | -0.018 | 0.241 | -0.059 | -51.206 | nan | 0.271 | 0.536 | 0.506 | -0.213 | 2273.000 |
| R0 | 1015 | 1015.000 | 0.032 | 0.046 | 0.470 | 0.097 | 0.046 | 0.452 | -0.017 | -140.389 | 2.079 | 0.271 | 0.536 | 0.506 | -0.213 | 750.000 |
| R1 | 231 | 1186.000 | 0.021 | -0.040 | 0.601 | -0.067 | -0.060 | 0.384 | -0.081 | -135.382 | nan | 0.271 | 0.536 | 0.506 | -0.213 | 7281.000 |


## D1
- Train: monedas BTC, ETH, XRP, LTC, ADA, DOGE, tramo 2017-01-01 a 2023-12-31. 128 puntos de grilla + 2 referencias = 260 pruebas; factibles: 14. Candidato elegido por meseta: {'p1': 'bear', 'p2': True, 'p3': 10, 'p4': 20, 'p5': 'vol'}.

Train (referencias recalculadas con el mismo codigo; buy&hold en el mismo tramo):

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| candidato [P1=bear P2=E P3=10 P4=20 P5=vol] | 293 | 412.000 | 1.484 | 1.163 | 0.694 | 1.671 | 1.025 | 360143.337 | 0.387 | 0.708 | 0.834 | 0.849 | 0.668 |
| R0 | 287 | 287.000 | 0.556 | 0.237 | 0.254 | 0.933 | 0.176 | 5689.082 | 0.402 | 0.708 | 0.834 | 0.849 | 0.668 |
| R1 | 458 | 2068.000 | 1.246 | 1.211 | 0.721 | 1.700 | 0.986 | 237983.541 | 0.790 | 0.708 | 0.834 | 0.849 | 0.668 |


Train, top 10 por score de meseta (todas las filas en `results/fase7_d1_grid.csv`):

| config | n | R_medio | CAGR | DD | Calmar | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | factible | meseta | elegido |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P1=bear P2=E P3=10 P4=20 P5=vol | 293 | 1.484 | 1.163 | 0.694 | 1.671 | 1.025 | 360143.337 | 0.387 | True | 0.354 | True |
| P1=bear P2=E P3=10 P4=10 P5=vol | 291 | 1.480 | 1.207 | 0.686 | 1.761 | 1.081 | 565980.471 | 0.308 | True | 0.267 | False |
| P1=bear P2=E P3=EMA20 P4=20 P5=vol | 293 | 1.505 | 1.170 | 0.713 | 1.671 | 1.010 | 396111.909 | 0.356 | True | 0.144 | False |
| P1=off P2=E P3=EMA20 P4=20 P5=vol | 201 | 1.836 | 1.033 | 0.620 | 1.663 | 0.951 | 239992.924 | 0.394 | True | 0.132 | False |
| P1=off P2=E P3=EMA20 P4=10 P5=vol | 200 | 1.819 | 1.044 | 0.645 | 1.592 | 0.961 | 286557.458 | 0.362 | True | 0.129 | False |
| P1=bear P2=- P3=10 P4=10 P5=vol | 154 | 0.832 | 0.560 | 0.531 | 1.056 | 0.506 | 40525.760 | 0.359 | True | 0.040 | False |
| P1=off P2=E P3=10 P4=10 P5=vol | 204 | 1.806 | 1.086 | 0.652 | 1.646 | 1.003 | 363295.277 | 0.384 | True | -0.000 | False |
| P1=bear P2=- P3=10 P4=10 P5=risk | 162 | 0.807 | 0.192 | 0.348 | 0.552 | 0.144 | 4180.896 | 0.395 | True | -0.147 | False |
| P1=bear P2=E P3=10 P4=40 P5=vol | 299 | 1.463 | 1.201 | 0.699 | 1.731 | 1.060 | 431194.656 | 0.396 | True | -0.228 | False |
| P1=bear P2=- P3=10 P4=- P5=risk | 207 | 0.765 | 0.237 | 0.301 | 0.786 | 0.187 | 5306.374 | 0.346 | True | -0.266 | False |


### Z2 (una mirada; monedas: ALGO, AVAX, ETC, ICP, TRX, VET; tramo 2018-12-28 a 2026-10-20)

**todo el historial**

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados | criterios | veredicto_grupo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| candidato [P1=bear P2=E P3=10 P4=20 P5=vol] | 415 | 559.000 | 0.377 | 0.177 | 0.567 | 0.319 | 0.178 | 0.384 | 0.156 | 4742.233 | 0.666 | 0.480 | 0.767 | 0.626 | 0.202 | 161.000 | 5/8 | NO CUMPLE |
| R0 [P1=normal P2=- P3=EMA20 P4=- P5=risk] | 416 | 416.000 | 0.137 | 0.061 | 0.259 | 0.235 | 0.061 | 0.129 | 0.023 | 391.936 | 0.753 | 0.480 | 0.767 | 0.626 | 0.202 | 5.000 | 6/8 | NO CUMPLE |
| R1 | 537 | 2446.000 | 0.293 | 0.324 | 0.596 | 0.540 | 0.328 | 0.344 | 0.318 | 15133.250 | 0.495 | 0.480 | 0.767 | 0.626 | 0.202 | 301.000 | 5/8 | NO CUMPLE |
| R1 informativa (sin cupo ni tope bruto) | 487 | 2712.000 | 0.390 | 0.507 | 0.756 | 0.671 | 0.512 | 0.447 | 0.498 | 42432.562 | 0.589 | 0.480 | 0.767 | 0.626 | 0.202 | 28.000 | nan | nan |


**2024-hoy**

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados | criterios | veredicto_grupo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| candidato [P1=bear P2=E P3=10 P4=20 P5=vol] | 178 | 206.000 | 0.161 | -0.012 | 0.527 | -0.022 | -0.009 | 0.347 | -0.062 | 132.465 | nan | 0.252 | 0.531 | 0.475 | -0.135 | 78.000 | 3/8 | NO CUMPLE |
| R0 [P1=normal P2=- P3=EMA20 P4=- P5=risk] | 169 | 169.000 | 0.044 | 0.017 | 0.259 | 0.065 | 0.017 | 0.088 | -0.017 | 67.677 | 2.976 | 0.252 | 0.531 | 0.475 | -0.135 | 2.000 | 5/8 | NO CUMPLE |
| R1 | 274 | 953.000 | 0.092 | 0.065 | 0.586 | 0.110 | 0.070 | 0.355 | 0.053 | -652.858 | 1.895 | 0.252 | 0.531 | 0.475 | -0.135 | 121.000 | 4/8 | NO CUMPLE |
| R1 informativa (sin cupo ni tope bruto) | 242 | 1068.000 | 0.201 | 0.100 | 0.754 | 0.133 | 0.111 | 0.476 | 0.080 | -128.034 | 1.996 | 0.252 | 0.531 | 0.475 | -0.135 | 0.000 | nan | nan |


- Candidato vs R1 (Calmar, todo el historial): 0.32 vs 0.54 -> el candidato NO supera a R1.

### Z3 (una mirada; monedas: 1INCH, ACM, AGLD, ALICE, ANKR, AR, ARPA, ASR, ATM, AUDIO, AVA, AXS, BAND, BAR, BAT, BEL, BNT, C98, CAKE, CELO, CELR, CFX, CHR, CHZ; tramo 2019-09-20 a 2026-10-20)

**todo el historial**

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados | criterios | veredicto_grupo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| candidato [P1=bear P2=E P3=10 P4=20 P5=vol] | 611 | 813.000 | 0.234 | 0.166 | 0.904 | 0.184 | 0.133 | 0.856 | 0.144 | -1841.280 | 1.975 | 0.345 | 0.767 | 0.450 | -0.058 | 1621.000 | 4/8 | NO CUMPLE |
| R0 [P1=normal P2=- P3=EMA20 P4=- P5=risk] | 735 | 735.000 | 0.217 | 0.157 | 0.330 | 0.477 | 0.155 | 0.307 | 0.096 | 106.624 | 0.518 | 0.345 | 0.767 | 0.450 | -0.058 | 579.000 | 7/8 | NO CUMPLE |
| R1 | 634 | 3068.000 | 0.397 | 0.146 | 0.926 | 0.157 | 0.139 | 0.835 | 0.126 | -3511.998 | 3.931 | 0.345 | 0.767 | 0.450 | -0.058 | 6408.000 | 4/8 | NO CUMPLE |
| R1 informativa (sin cupo ni tope bruto) | 1006 | 5658.000 | 0.386 | -1.000 | 1.022 | -0.979 | -1.000 | 1.049 | -1.000 | -16635.999 | nan | 0.345 | 0.767 | 0.450 | -0.058 | 3835.000 | nan | nan |


**2024-hoy**

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados | criterios | veredicto_grupo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| candidato [P1=bear P2=E P3=10 P4=20 P5=vol] | 285 | 349.000 | -0.105 | -0.388 | 0.868 | -0.436 | -0.431 | 0.844 | -0.396 | -336.669 | nan | 0.252 | 0.531 | 0.475 | -0.455 | 801.000 | 2/8 | NO CUMPLE |
| R0 [P1=normal P2=- P3=EMA20 P4=- P5=risk] | 328 | 328.000 | 0.003 | -0.003 | 0.318 | -0.010 | -0.010 | 0.234 | -0.018 | -61.421 | nan | 0.252 | 0.531 | 0.475 | -0.455 | 289.000 | 2/8 | NO CUMPLE |
| R1 | 321 | 1268.000 | -0.150 | -0.338 | 0.803 | -0.426 | -0.350 | 0.748 | -0.355 | -257.894 | nan | 0.252 | 0.531 | 0.475 | -0.455 | 3013.000 | 2/8 | NO CUMPLE |
| R1 informativa (sin cupo ni tope bruto) | 1005 | 4242.000 | -0.080 | -0.899 | 1.000 | -0.899 | -0.913 | 1.000 | -0.906 | -420.689 | nan | 0.252 | 0.531 | 0.475 | -0.455 | 0.000 | nan | nan |


- Candidato vs R1 (Calmar, todo el historial): 0.18 vs 0.16 -> el candidato supera a R1.

### 2024-hoy en todas las monedas (informativa; contaminada: incluye train, holdout, Z1, Z2 y Z3)

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| candidato | 306 | 362.000 | -0.022 | -0.210 | 0.715 | -0.284 | -0.257 | 0.656 | -0.251 | -144.901 | nan | 0.252 | 0.531 | 0.475 | -0.229 | 1892.000 |
| R0 | 381 | 381.000 | 0.184 | 0.219 | 0.195 | 1.023 | 0.211 | 0.123 | 0.122 | -63.760 | 0.565 | 0.252 | 0.531 | 0.475 | -0.229 | 826.000 |
| R1 | 287 | 1220.000 | 0.249 | 0.109 | 0.664 | 0.181 | 0.093 | 0.475 | 0.056 | -156.318 | 2.337 | 0.252 | 0.531 | 0.475 | -0.229 | 7352.000 |


## W1
- Train: monedas BTC, ETH, XRP, LTC, ADA, DOGE, tramo 2017-01-01 a 2023-12-31. 16 puntos de grilla + 2 referencias = 36 pruebas; factibles: 0. Candidato elegido por meseta: ninguno.

Train (referencias recalculadas con el mismo codigo; buy&hold en el mismo tramo):

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 | 20 | 20.000 | 1.991 | 0.048 | 0.240 | 0.198 | 0.015 | 30.083 | 0.728 | 0.731 | 0.831 | 0.879 | 0.680 |
| R1 | 105 | 703.000 | 1.867 | 0.900 | 0.578 | 1.590 | 0.827 | 114630.521 | 0.427 | 0.731 | 0.831 | 0.879 | 0.680 |


Train, top 10 por score de meseta (todas las filas en `results/fase7_w1_grid.csv`):

(vacio)


### POOL (una mirada; monedas: SOL, LINK, BNB, BCH, XLM, AAVE, ATOM, DOT, FIL, NEAR, UNI, ALGO, AVAX, ETC, ICP, TRX, VET, 1INCH, ACM, AGLD, ALICE, ANKR, AR, ARPA, ASR, ATM, AUDIO, AVA, AXS, BAND, BAR, BAT, BEL, BNT, C98, CAKE, CELO, CELR, CFX, CHR, CHZ; tramo 2021-09-06 a 2026-10-12)

**todo el historial**

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados | criterios | veredicto_grupo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 [P1=normal P2=- P3=EMA20 P4=- P5=risk] | 79 | 79.000 | -0.029 | -0.000 | 0.071 | -0.005 | -0.004 | 0.084 | -0.003 | -6.507 | nan | 0.119 | 0.752 | 0.159 | -0.281 | 106.000 | 2/8 | SIN MUESTRA |
| R1 | 150 | 805.000 | -0.162 | -0.118 | 0.653 | -0.175 | -0.163 | 0.666 | -0.131 | -148.201 | nan | 0.119 | 0.752 | 0.159 | -0.281 | 4055.000 | 2/8 | NO CUMPLE |
| R1 informativa (sin cupo ni tope bruto) | 157 | 883.000 | -0.349 | -1.000 | 1.007 | -0.993 | -1.000 | 1.011 | -1.000 | -220.164 | nan | 0.119 | 0.752 | 0.159 | -0.281 | 3988.000 | nan | nan |


**2024-hoy**

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados | criterios | veredicto_grupo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 [P1=normal P2=- P3=EMA20 P4=- P5=risk] | 39 | 39.000 | 0.044 | 0.015 | 0.063 | 0.231 | 0.006 | 0.034 | 0.010 | 0.000 | 0.336 | 0.250 | 0.519 | 0.482 | -0.238 | 92.000 | 5/8 | SIN MUESTRA |
| R1 | 102 | 514.000 | -0.124 | -0.206 | 0.679 | -0.285 | -0.215 | 0.618 | -0.218 | -116.458 | nan | 0.250 | 0.519 | 0.482 | -0.238 | 2159.000 | 1/8 | NO CUMPLE |
| R1 informativa (sin cupo ni tope bruto) | 61 | 474.000 | 0.721 | -1.000 | 1.041 | -0.960 | -1.000 | 1.131 | -1.000 | -310.511 | nan | 0.250 | 0.519 | 0.482 | -0.238 | 2215.000 | nan | nan |


### 2024-hoy en todas las monedas (informativa; contaminada: incluye train, holdout, Z1, Z2 y Z3)

| config | n | n_sub | R_medio | CAGR | DD | Calmar | CAGR_cerrada | DD_cerrada | CAGR_sin_mejor | mediana_PnL_moneda | conc_max | BTC_CAGR | BTC_DD | BTC_Calmar | EW_Calmar | saltados |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 | 36 | 36.000 | -0.014 | 0.005 | 0.069 | 0.082 | -0.002 | 0.041 | 0.002 | 0.000 | 0.880 | 0.250 | 0.519 | 0.482 | -0.184 | 119.000 |
| R1 | 99 | 497.000 | -0.038 | -0.196 | 0.688 | -0.285 | -0.207 | 0.597 | -0.209 | -84.351 | nan | 0.250 | 0.519 | 0.482 | -0.184 | 2619.000 |


## Cómo leer esto (limitaciones, sin maquillaje)

- **Entregable:** como ningún candidato SQZ+RSI ni R1 cumplen, `params/{h4,d1,w1}.json` NO se tocaron (`git diff --stat params/` vacío) y el forward test sigue con su serie 1. El entregable es el set vigente y las herramientas nuevas (`sqzlab.signals`, `docs/BOT.md`); el Pine no cambia.
- **Z2 y Z3 se miraron una sola vez por TF** (H4 y D1: Z2 y Z3; W1: un pool de las 41 monedas no-train). Todas las pruebas de la Fase 7 y las miradas están contadas arriba (la grilla de train se corrió 2 veces: la 1.ª pasada archivada se descartó tras la revisión).
- **n** = trades A/B/C/D cerrados + episodios de E; `n_sub` cuenta cada sub-señal de E por separado.
- **Sesgo de supervivencia:** todos los grupos son monedas que HOY siguen listadas; eso favorece a la estrategia y al buy&hold por igual. Z3 incluye fan tokens de poco volumen donde 0,05% de slippage es optimista.
- **R1 no es una réplica exacta del paper:** el tamaño se fija en la entrada (no se re-dimensiona a diario) y se aplican cupo de 6 monedas y tope bruto 1,0x; el paper no se pudo bajar (SSRN 403, abarbon.com 502) y sus reglas están **no verificadas**. La "R1 informativa" sin cupo ni tope bruto apalanca hasta 2x por moneda con 24 a 41 monedas a la vez y por eso llega a −100%: es solo informativa y no decide nada.
- **Modo riesgo vs modo vol:** el modo riesgo no tiene tope bruto agregado y el modo vol sí (1,0x); CAGR y DD no son comparables entre modos, el Calmar es casi invariante a la escala.
- **Concentración por moneda:** con 6 monedas el criterio "ninguna moneda > 40% de la ganancia" es muy exigente y falla incluso en referencias razonables; se mantuvo tal cual estaba fijado (prohibido aflojarlo después de mirar).
- **2024-hoy** es el tramo donde las altcoins perdieron en general (buy&hold equiponderado negativo en todas las tablas): ahí ningún enfoque de esta fase gana plata de forma consistente.

## Plan B

Ningun TF tiene R1 cumpliendo los criterios en todos sus grupos: no hay plan B que entregar; se dice con numeros y se espera al usuario.

## Revisión independiente previa a Z2/Z3 (subagente que no vio el trabajo; hecha ANTES de mirar Z2, Z3 y pool)

El revisor leyó el código en solo lectura, no corrió ninguna mirada y no abrió datos de Z2/Z3. Corrió pytest (1 falla de un test viejo de `test_universe`, ya corregido) y comparó `simulate` de HEAD contra el actual en 15 combinaciones (moneda x TF x set): idénticos.

| # | Gravedad | Hallazgo | Qué se hizo |
|---|---|---|---|
| 1 | CRÍTICO (solo W1 R1) | ids de sub-trades duplicados (varios lookbacks de W1 dan 4 velas): el motor colapsaba posiciones y cobraba comisiones fantasma (Calmar de W1 R1 en train 1,21 con el bug vs 1,79 con ids únicos, antes de las demás correcciones) | ids únicos + `ValueError` si hay duplicados + test; chequeo contable eq-capital = suma de PnL en los 3 TF (diferencia 0) |
| 2 | MEDIO | el cupo de 6 monedas se asignaba por orden alfabético: CAGR de 0,40 a 0,58 y la mediana por moneda cambiaba de signo según el orden | 9 prioridades sorteadas con semilla fija; toda métrica = mediana (PROTOCOLO 5 ter) |
| 3 | MEDIO | "sin el mejor trade" quitaba el de mayor R, no el de mayor PnL (casi nunca fallaba) | se quita el de mayor PnL en USD |
| 4 | MEDIO | n contaba sub-trades de E (R1 D1: 2.035) | n = trades A/B/C/D + episodios de E; se informa n_sub aparte |
| 5 | MEDIO | la última barra semanal (2026-10-19) era parcial (cierre del 21-oct) | `DATA_END["1w"]` = 2026-10-12; el TF mayor de P4/P1 se carga sin cortar |
| 6 | MEDIO (informativo) | modo riesgo (sin tope bruto, llegó a 1,54x) y modo vol (tope 1,0x) no son comparables en CAGR/DD | anotado en PROTOCOLO 5 ter; se compara por Calmar |
| 7 | MENOR | `CALMAR_CAP` = 10 no estaba en el protocolo | anotado (nunca se activó) |
| 8 | MENOR | candados incompletos (allcoins sin candado, train re-corrible tras mirar) | candidato guardado en cada mirada; train se niega si hubo miradas; allcoins exige las miradas y se corre una vez |
| 9 | MENOR | años del CAGR hasta la apertura de la última vela | se suma un paso del TF |
| 10 | MENOR | `signals` E: salida parcial daba `none`; tamaño con la vol de hoy | acción `reduce`; diferencias documentadas en `docs/BOT.md` |
| 11-13 | MENOR | señales saltadas siguen "abiertas" para `simulate`; golden sin versionar; regla UP/DOWN descarta tickers como JUP; fan tokens con slippage optimista | anotados como limitaciones (PROTOCOLO 5 ter) |

Contradicciones del protocolo que señaló (frase "pueden cerrar después", "ninguna otra pierna" vs P1, "misma corrida" de allcoins, "sin dedupe" de W1, precedencia de SIN MUESTRA, definición de n y del cupo): corregidas en `docs/PROTOCOLO.md`.

**Lo que el revisor verificó sin problemas:** lookahead (HTF contra fuerza bruta independiente en 800 velas, pipeline truncado en 2022-03-07, vol y Donchian con ventanas previas); fuga train→test (curvas de train idénticas cortando los datos en 2024-01-01); costos (comisión y slippage adversos en cada entrada y salida, sin doble cobro); sizing y orden de topes; conteo de la grilla (96/128/16), meseta y elegido recalculados desde el CSV; buy&hold. **No pudo verificar:** Z2/Z3/pool (prohibido), reglas del paper, Pine/TradingView.

**Después de las correcciones se re-corrió todo el train (2.ª pasada)**; los candidatos de la 1.ª pasada quedan archivados (`fase7_train_pasada1_state.json`, `fase7_*_grid_pasada1.csv`): H4 `P1=off P2=E P3=20 P4=- P5=risk`, D1 `P1=off P2=E P3=10 P4=20 P5=vol`, W1 `P1=off P2=E P3=10 P4=- P5=vol`. Los de la 2.ª son los que se miran en Z2/Z3.
