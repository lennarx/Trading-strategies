# Confirmacion D1 en Z1 (generado por `python -m sqzlab.confirm`)

- **Veredicto: NO CONFIRMA.** Sin tocar ningun parametro: es solo "confirma / no confirma".
- Monedas (6): AAVE, ATOM, DOT, FIL, NEAR, UNI. Datos hasta 2026-10-20.
- Set evaluado: `params/d1.json`; difiere de la v2 en: nada (= v2)
- Salvedad: monedas nuevas pero **en el mismo periodo** que las de train; no es un OOS en el tiempo (eso es `forward`).
- Criterios (PROTOCOLO): expectativa > 0,2R: NO; expectativa > p95 del baseline: SI; n >= 100: SI; sin el mejor trade > 0: SI; expectativa recortada (sin 2% mejores) > 0: NO.

## Set vigente

| grupo | n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Z1 todo el historial | 335 | 0.136 | 1.512 | 0.290 | 11.689 | 45.479 | 0.098 | -0.013 | 0.125 | -0.049 | 0.020 |
| Z1 2024-hoy | 156 | 0.152 | 1.557 | 0.282 | 9.121 | 23.770 | 0.072 | -0.038 | 0.153 | -0.024 | 0.098 |

## Vara: v2 sin optimizar (mismas monedas; solo comparacion)

| grupo | n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Z1 todo el historial | 335 | 0.136 | 1.512 | 0.290 | 11.689 | 45.479 | 0.098 | -0.013 | 0.125 | -0.049 | 0.025 |
| Z1 2024-hoy | 156 | 0.152 | 1.557 | 0.282 | 9.121 | 23.770 | 0.072 | -0.038 | 0.153 | -0.026 | 0.092 |

## Por moneda (set vigente)

| coin | n | exp | pf | win | total |
|---|---|---|---|---|---|
| AAVE | 59 | -0.199 | 0.304 | 0.220 | -11.740 |
| ATOM | 85 | 0.051 | 1.172 | 0.212 | 4.306 |
| DOT | 55 | 0.255 | 2.079 | 0.382 | 14.033 |
| FIL | 39 | 0.199 | 1.694 | 0.333 | 7.750 |
| NEAR | 44 | 0.704 | 4.296 | 0.409 | 30.994 |
| UNI | 53 | 0.003 | 1.010 | 0.264 | 0.137 |

## Por senal y lado (set vigente)

| kind | side | n | exp | pf | win | total |
|---|---|---|---|---|---|---|
| A | -1 | 55 | -0.119 | 0.672 | 0.345 | -6.542 |
| A | 1 | 33 | 0.569 | 2.642 | 0.364 | 18.780 |
| B | -1 | 66 | 0.052 | 1.214 | 0.288 | 3.439 |
| B | 1 | 31 | 0.222 | 1.547 | 0.194 | 6.896 |
| C | -1 | 84 | 0.027 | 1.142 | 0.250 | 2.244 |
| D | -1 | 21 | 0.282 | 2.828 | 0.381 | 5.929 |
| D | 1 | 45 | 0.327 | 2.511 | 0.267 | 14.732 |

## Por anio (set vigente)

| anio | n | exp | total |
|---|---|---|---|
| 2019 | 2 | 2.047 | 4.094 |
| 2020 | 16 | 0.132 | 2.111 |
| 2021 | 51 | 0.146 | 7.430 |
| 2022 | 58 | 0.097 | 5.605 |
| 2023 | 52 | 0.047 | 2.468 |
| 2024 | 64 | 0.243 | 15.570 |
| 2025 | 52 | -0.003 | -0.141 |
| 2026 | 40 | 0.209 | 8.341 |

