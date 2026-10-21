# Cartera D1 (generado por `python -m sqzlab.portfolio`)

Set: `params/d1.json`. Monedas: BTC, ETH, XRP, LTC, ADA, DOGE, SOL, LINK, BNB, BCH, XLM. Entradas hasta 2026-10-20. Capital inicial 10.000; riesgo % sobre la equity realizada, compuesto.
Topes: riesgo abierto total 5% de la equity y maximo 6 posiciones ("sin topes de cartera" = cada trade entra siempre); tope de apalancamiento por trade como la strategy (maxLev 1). **Aproximaciones:** equity realizada (no marca a mercado lo abierto, el DD real puede ser peor), sin margen ni liquidez. **Leer con cuidado:** el tramo largo incluye los anios donde se ELIGIO el set (sesgo optimista); el tramo 2024-hoy es el que vale. No es asesoria financiera.

## 2017-hoy (incluye el tramo donde se eligio el set)

n=761 trades, 0.422R por trade, suma 321.4R. Comprar y mantener BTC en el mismo tramo: CAGR 56.3%, DD maximo 83.4% (cierres diarios).

| riesgo | topes | trades | salteados | equity_final | CAGR | DD_max | MAR | meses_neg | peor_mes |
|---|---|---|---|---|---|---|---|---|---|
| 0.5% | con topes | 689 | 72 | 32995.127 | 0.133 | 0.095 | 1.397 | 0.452 | -0.028 |
| 0.5% | sin topes de cartera | 761 | 0 | 41807.460 | 0.161 | 0.120 | 1.342 | 0.470 | -0.035 |
| 1% | con topes | 610 | 151 | 72388.675 | 0.229 | 0.123 | 1.863 | 0.435 | -0.048 |
| 1% | sin topes de cartera | 761 | 0 | 134233.037 | 0.311 | 0.227 | 1.368 | 0.470 | -0.070 |
| 2% | con topes | 362 | 399 | 96259.989 | 0.266 | 0.171 | 1.558 | 0.487 | -0.070 |
| 2% | sin topes de cartera | 761 | 0 | 830568.721 | 0.585 | 0.409 | 1.431 | 0.478 | -0.136 |

## 2024-hoy (despues del corte de train)

n=261 trades, 0.423R por trade, suma 110.4R. Comprar y mantener BTC en el mismo tramo: CAGR 25.1%, DD maximo 53.1% (cierres diarios).

| riesgo | topes | trades | salteados | equity_final | CAGR | DD_max | MAR | meses_neg | peor_mes |
|---|---|---|---|---|---|---|---|---|---|
| 0.5% | con topes | 237 | 24 | 14427.372 | 0.141 | 0.054 | 2.622 | 0.515 | -0.018 |
| 0.5% | sin topes de cartera | 261 | 0 | 15912.995 | 0.182 | 0.060 | 3.024 | 0.515 | -0.018 |
| 1% | con topes | 216 | 45 | 14120.056 | 0.132 | 0.089 | 1.482 | 0.515 | -0.037 |
| 1% | sin topes de cartera | 261 | 0 | 22470.324 | 0.339 | 0.117 | 2.898 | 0.515 | -0.037 |
| 2% | con topes | 125 | 136 | 15719.483 | 0.177 | 0.110 | 1.615 | 0.515 | -0.035 |
| 2% | sin topes de cartera | 261 | 0 | 36601.341 | 0.597 | 0.220 | 2.708 | 0.545 | -0.072 |

## Concurrencia (riesgo 1%, con topes, 2017-hoy)

- Maximo de posiciones abiertas a la vez: 5.
- Trades perdedores: 422; el 70% coincide en el tiempo con una perdedora de OTRA moneda (las cripto pierden juntas: la diversificacion entre monedas ayuda poco).
