# Confirmacion W1 en Z1 (generado por `python -m sqzlab.confirm`)

- **Veredicto: SIN MUESTRA (n=27 < 100): ni confirma ni desmiente.** Sin tocar ningun parametro: es solo "confirma / no confirma".
- Monedas (6): AAVE, ATOM, DOT, FIL, NEAR, UNI. Datos hasta 2026-10-19.
- Set evaluado: `params/w1.json`; difiere de la v2 en: nada (= v2)
- Salvedad: monedas nuevas pero **en el mismo periodo** que las de train; no es un OOS en el tiempo (eso es `forward`).
- Criterios (PROTOCOLO): expectativa > 0,2R: NO; expectativa > p95 del baseline: NO; n >= 100: NO; sin el mejor trade > 0: NO; expectativa recortada (sin 2% mejores) > 0: NO.

## Set vigente

| grupo | n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Z1 todo el historial | 27 | -0.108 | 0.580 | 0.222 | 3.627 | -2.904 | -0.172 | -0.172 | -0.237 | -0.098 | 0.040 |
| Z1 2024-hoy | 18 | -0.044 | 0.835 | 0.333 | 3.550 | -0.789 | -0.139 | -0.139 | -0.229 | -0.091 | 0.115 |

## Vara: v2 sin optimizar (mismas monedas; solo comparacion)

| grupo | n | exp | pf | win | dd | total | exp_ex_best | exp_trim | med_coin | base_p50 | base_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Z1 todo el historial | 27 | -0.108 | 0.580 | 0.222 | 3.627 | -2.904 | -0.172 | -0.172 | -0.237 | -0.100 | 0.043 |
| Z1 2024-hoy | 18 | -0.044 | 0.835 | 0.333 | 3.550 | -0.789 | -0.139 | -0.139 | -0.229 | -0.087 | 0.093 |

## Por moneda (set vigente)

| coin | n | exp | pf | win | total |
|---|---|---|---|---|---|
| AAVE | 6 | 0.093 | 1.546 | 0.167 | 0.557 |
| ATOM | 6 | -0.256 | 0.139 | 0.167 | -1.533 |
| DOT | 3 | 0.343 | 13.430 | 0.667 | 1.029 |
| FIL | 2 | -0.224 | 0.554 | 0.500 | -0.447 |
| NEAR | 7 | -0.252 | 0.000 | 0.000 | -1.762 |
| UNI | 3 | -0.250 | 0.407 | 0.333 | -0.749 |

## Por senal y lado (set vigente)

| kind | side | n | exp | pf | win | total |
|---|---|---|---|---|---|---|
| A | -1 | 1 | -1.002 | 0.000 | 0.000 | -1.002 |
| A | 1 | 1 | -0.143 | 0.000 | 0.000 | -0.143 |
| B | -1 | 3 | -0.695 | 0.000 | 0.000 | -2.086 |
| B | 1 | 1 | 1.579 | inf | 1.000 | 1.579 |
| C | -1 | 11 | -0.053 | 0.728 | 0.364 | -0.579 |
| D | -1 | 4 | 0.095 | 1.755 | 0.250 | 0.378 |
| D | 1 | 6 | -0.175 | 0.000 | 0.000 | -1.051 |

## Por anio (set vigente)

| anio | n | exp | total |
|---|---|---|---|
| 2021 | 2 | -0.384 | -0.769 |
| 2022 | 3 | -0.199 | -0.598 |
| 2023 | 4 | -0.187 | -0.749 |
| 2024 | 5 | 0.127 | 0.634 |
| 2025 | 10 | 0.006 | 0.055 |
| 2026 | 3 | -0.493 | -1.478 |

