# Confirmacion H4 en Z1 (generado por `python -m sqzlab.confirm`)

- **Veredicto: NO CONFIRMA.** Sin tocar ningun parametro: es solo "confirma / no confirma".
- Monedas (6): AAVE, ATOM, DOT, FIL, NEAR, UNI. Datos hasta 2026-10-20 20:00.
- Set evaluado: `params/h4.json`; difiere de la v2 en: useC=False, aShort=False, cShort=False, useD=False, dLong=False, dShort=False, bbLen=26, kcLen=16, kcMult=2.0, adxMin=30.0, pbBars=3, atrMult=0.1, minSqz=12, invBars=0
- Salvedad: monedas nuevas pero **en el mismo periodo** que las de train; no es un OOS en el tiempo (eso es `forward`).
- Criterios (PROTOCOLO): expectativa > 0,2R: NO; expectativa > p95 del baseline: SI; n >= 100: SI; sin el mejor trade > 0: SI; expectativa recortada (sin 2% mejores) > 0: NO.

## Set vigente

| grupo | n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Z1 todo el historial | 446 | 0.079 | 1.202 | 0.341 | 28.078 | 35.435 | 0.054 | -0.089 | 0.051 | -0.026 | 0.043 |
| Z1 2024-hoy | 208 | 0.021 | 1.057 | 0.389 | 28.078 | 4.380 | -0.007 | -0.089 | 0.021 | -0.020 | 0.092 |

## Vara: v2 sin optimizar (mismas monedas; solo comparacion)

| grupo | n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Z1 todo el historial | 2365 | 0.070 | 1.232 | 0.296 | 35.510 | 165.465 | 0.063 | -0.054 | 0.056 | -0.073 | -0.051 |
| Z1 2024-hoy | 1029 | 0.084 | 1.279 | 0.315 | 35.510 | 86.573 | 0.069 | -0.028 | 0.114 | -0.039 | -0.003 |

## Por moneda (set vigente)

| coin | n | exp | pf | win | total |
|---|---|---|---|---|---|
| AAVE | 89 | 0.016 | 1.043 | 0.315 | 1.410 |
| ATOM | 105 | 0.163 | 1.391 | 0.343 | 17.156 |
| DOT | 59 | -0.118 | 0.711 | 0.322 | -6.977 |
| FIL | 63 | 0.273 | 1.703 | 0.365 | 17.217 |
| NEAR | 66 | 0.072 | 1.171 | 0.288 | 4.768 |
| UNI | 64 | 0.029 | 1.085 | 0.422 | 1.861 |

## Por senal y lado (set vigente)

| kind | side | n | exp | pf | win | total |
|---|---|---|---|---|---|---|
| A | 1 | 93 | 0.216 | 1.547 | 0.344 | 20.046 |
| B | -1 | 190 | -0.044 | 0.882 | 0.379 | -8.299 |
| B | 1 | 163 | 0.145 | 1.348 | 0.294 | 23.688 |

## Por anio (set vigente)

| anio | n | exp | total |
|---|---|---|---|
| 2019 | 6 | 0.533 | 3.201 |
| 2020 | 27 | 0.053 | 1.435 |
| 2021 | 78 | 0.410 | 31.955 |
| 2022 | 54 | -0.160 | -8.631 |
| 2023 | 73 | 0.042 | 3.095 |
| 2024 | 82 | 0.268 | 21.938 |
| 2025 | 59 | -0.128 | -7.578 |
| 2026 | 67 | -0.149 | -9.980 |

