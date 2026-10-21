# Prueba de estres de costos (Fase 6.0)

Medicion de los sets YA elegidos (`params/h4.json` optimizado, `params/d1.json` = v2): no se selecciona nada con esto. Comision 0,05% por lado en todos los casos; `slip_pct` se suma por lado, en contra del trade, en entrada, cierre y stop. **Pruebas de esta corrida: 8** (una por set x slippage; el conteo de optimizacion no cambia).

Lectura: R neto por trade. Si la expectativa recortada (`exp_trim`) se va a cero o negativo con 0,05%, la ventaja no sobrevive costos realistas de perpetuos/alts en H4.

| tf | slip_por_lado | grupo | n | exp | pf | exp_ex_best | exp_trim | dd | total |
|---|---|---|---|---|---|---|---|---|---|
| H4 | 0.00% | OOS agregado (test 2024-hoy + holdout) | 556 | 0.389 | 1.980 | 0.328 | 0.095 | 23.935 | 216.120 |
| H4 | 0.00% | todo 2017-hoy, todas las monedas | 933 | 0.585 | 2.487 | 0.491 | 0.191 | 23.935 | 545.651 |
| H4 | 0.02% | OOS agregado (test 2024-hoy + holdout) | 556 | 0.377 | 1.941 | 0.317 | 0.085 | 24.413 | 209.737 |
| H4 | 0.02% | todo 2017-hoy, todas las monedas | 933 | 0.572 | 2.440 | 0.478 | 0.180 | 24.413 | 533.702 |
| H4 | 0.05% | OOS agregado (test 2024-hoy + holdout) | 556 | 0.360 | 1.885 | 0.300 | 0.070 | 25.118 | 200.309 |
| H4 | 0.05% | todo 2017-hoy, todas las monedas | 933 | 0.553 | 2.373 | 0.460 | 0.165 | 25.118 | 516.065 |
| H4 | 0.10% | OOS agregado (test 2024-hoy + holdout) | 556 | 0.333 | 1.798 | 0.273 | 0.046 | 26.261 | 184.970 |
| H4 | 0.10% | todo 2017-hoy, todas las monedas | 933 | 0.522 | 2.266 | 0.430 | 0.140 | 26.261 | 487.405 |
| D1 | 0.00% | OOS agregado (test 2024-hoy + holdout) | 468 | 0.329 | 2.112 | 0.242 | 0.034 | 19.511 | 154.181 |
| D1 | 0.00% | todo 2017-hoy, todas las monedas | 761 | 0.422 | 2.464 | 0.366 | 0.086 | 25.285 | 321.405 |
| D1 | 0.02% | OOS agregado (test 2024-hoy + holdout) | 468 | 0.325 | 2.090 | 0.238 | 0.031 | 20.088 | 152.169 |
| D1 | 0.02% | todo 2017-hoy, todas las monedas | 761 | 0.418 | 2.438 | 0.362 | 0.083 | 25.818 | 317.883 |
| D1 | 0.05% | OOS agregado (test 2024-hoy + holdout) | 468 | 0.319 | 2.058 | 0.232 | 0.025 | 20.946 | 149.168 |
| D1 | 0.05% | todo 2017-hoy, todas las monedas | 761 | 0.411 | 2.400 | 0.355 | 0.077 | 26.611 | 312.636 |
| D1 | 0.10% | OOS agregado (test 2024-hoy + holdout) | 468 | 0.308 | 2.006 | 0.222 | 0.017 | 22.358 | 144.217 |
| D1 | 0.10% | todo 2017-hoy, todas las monedas | 761 | 0.399 | 2.340 | 0.344 | 0.068 | 27.964 | 303.988 |

