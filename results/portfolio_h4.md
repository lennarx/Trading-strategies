# Cartera H4 (generado por `python -m sqzlab.portfolio`)

Set: `params/h4.json`. Monedas: BTC, ETH, XRP, LTC, ADA, DOGE, SOL, LINK, BNB, BCH, XLM. Entradas hasta 2026-10-20 20:00. Capital inicial 10.000; riesgo % sobre la equity realizada, compuesto.
Topes: riesgo abierto total 5% de la equity y maximo 6 posiciones ("sin topes de cartera" = cada trade entra siempre); tope de apalancamiento por trade como la strategy (maxLev 1). **Aproximaciones:** equity realizada (no marca a mercado lo abierto, el DD real puede ser peor), sin margen ni liquidez. **Leer con cuidado:** el tramo largo incluye los anios donde se ELIGIO el set (sesgo optimista); el tramo 2024-hoy es el que vale. No es asesoria financiera.

## 2017-hoy (incluye el tramo donde se eligio el set)

n=933 trades, 0.585R por trade, suma 545.7R. Comprar y mantener BTC en el mismo tramo: CAGR 56.8%, DD maximo 83.4% (cierres diarios).

| riesgo | topes | trades | salteados | equity_final | CAGR | DD_max | MAR | meses_neg | peor_mes |
|---|---|---|---|---|---|---|---|---|---|
| 0.5% | con topes | 925 | 8 | 121838.311 | 0.295 | 0.113 | 2.607 | 0.440 | -0.046 |
| 0.5% | sin topes de cartera | 933 | 0 | 121746.093 | 0.295 | 0.113 | 2.606 | 0.448 | -0.046 |
| 1% | con topes | 890 | 43 | 856238.880 | 0.585 | 0.211 | 2.770 | 0.431 | -0.091 |
| 1% | sin topes de cartera | 933 | 0 | 1032428.378 | 0.616 | 0.215 | 2.869 | 0.448 | -0.091 |
| 2% | con topes | 650 | 283 | 9087453.248 | 1.024 | 0.278 | 3.684 | 0.388 | -0.112 |
| 2% | sin topes de cartera | 933 | 0 | 30544957.475 | 1.295 | 0.379 | 3.417 | 0.448 | -0.173 |

## 2024-hoy (despues del corte de train)

n=323 trades, 0.248R por trade, suma 80.2R. Comprar y mantener BTC en el mismo tramo: CAGR 26.0%, DD maximo 53.1% (cierres diarios).

| riesgo | topes | trades | salteados | equity_final | CAGR | DD_max | MAR | meses_neg | peor_mes |
|---|---|---|---|---|---|---|---|---|---|
| 0.5% | con topes | 318 | 5 | 14360.851 | 0.139 | 0.113 | 1.223 | 0.606 | -0.028 |
| 0.5% | sin topes de cartera | 323 | 0 | 14399.881 | 0.140 | 0.113 | 1.233 | 0.636 | -0.028 |
| 1% | con topes | 302 | 21 | 18667.830 | 0.251 | 0.211 | 1.188 | 0.576 | -0.056 |
| 1% | sin topes de cartera | 323 | 0 | 19458.171 | 0.270 | 0.215 | 1.256 | 0.636 | -0.056 |
| 2% | con topes | 215 | 108 | 30484.429 | 0.492 | 0.278 | 1.768 | 0.576 | -0.078 |
| 2% | sin topes de cartera | 323 | 0 | 30360.652 | 0.490 | 0.379 | 1.292 | 0.636 | -0.102 |

## Concurrencia (riesgo 1%, con topes, 2017-hoy)

- Maximo de posiciones abiertas a la vez: 5.
- Trades perdedores: 541; el 60% coincide en el tiempo con una perdedora de OTRA moneda (las cripto pierden juntas: la diversificacion entre monedas ayuda poco).
