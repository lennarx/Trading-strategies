# Fase 8: R1-fiel (generado por `python -m sqzlab.fase8 --stage look`, 2026-10-22 03:46 UTC)
> No es asesoria financiera. **Veredicto D1: NO SIRVE** (n_B = 567 operaciones cerradas con salida en B; minimo 30).

## Reglas (fijadas ANTES en `docs/PROTOCOLO.md`, "Decisiones fijadas ANTES de la Fase 8")
- **Estrategia:** solo largo, ensamble de Donchian con N = 5, 10, 20, 30, 60, 90, 150, 250, 360 dias. Entra al cierre si `close` > maximo de los N cierres previos; trailing stop = max(stop de ayer, (max+min)/2 de los N cierres previos); sale al cierre si `close` < stop. Peso = (sub-senales abiertas/9) x min(2, 0,25/vol 90d anualizada); si el bruto pasa de 2,0 se escala todo a 2,0. Rebalanceo diario solo si el peso efectivo se aparta > 20% relativo del objetivo (entradas y salidas siempre).
- **Universo dinamico:** por dia t, con datos <= t-1: >= 365 dias de historia y mediana del volumen USD de 30 dias >= 2 M; top 20 por esa mediana (empates alfabeticos). Sale del top 20 -> se vende al cierre. Deslistada o cortada -> cierre forzado en su ultima vela.
- **Costos:** por lado sobre el nocional operado: 0,15% base (0,10 comision + 0,05 slippage); tambien 0,10% y 0,25%. El veredicto usa el base. **H4** = conversion declarada (N x 6, vol 540 velas, sqrt(6x365)), sin veredicto.
- **Ventanas:** A = 2018-01-01 a `END` (inicio efectivo = primer dia con una moneda elegible); B = 2025-04-01 a `END` (juez; tramo de la misma corrida continua, con la equity re-basada). SIRVE (D1) = en A y en B: CAGR > 0, Sharpe > BTC, DD < BTC, ninguna moneda > 50% de la ganancia; en A ademas CAGR > 0 sin el mejor mes. n_B < 30 operaciones cerradas (episodios por moneda con salida en B) = SIN MUESTRA EN B.
- **Cero optimizacion:** 1 configuracion por TF, 0 grillas. B se miro **una sola vez** (candado en `results/fase8_state.json`).

## Diferencias con el paper (Zarattini, Pagani, Barbon 2025) — TODO "no verificado": el texto del paper no se pudo bajar (SSRN 403, abarbon.com 502)
Las reglas salen del resumen de `docs/FASE8_PLAN.md` (CXO Advisory). Diferencias o supuestos nuestros que pueden no coincidir con el paper:
- **Tope bruto 2,0 de la cartera** (escalado de todos los pesos): el plan describe un tope de 200%; el paper puede aplicarlo por posicion. Supuesto nuestro.
- **Banda de rebalanceo de 20%**: supuesto nuestro anti-costos (el paper re-dimensiona a diario).
- **Ventana del stop = N cierres previos** (misma convencion que la entrada) y ejecucion **al cierre de la senal**: optimista; el paper puede ejecutar a la apertura siguiente.
- **Universo:** regla del plan (>= 365 dias, mediana 30d >= 2 M USD, top 20), sobre Binance spot USDT; el paper usa su propia fuente y definiciones.
- **Sin costo de financiamiento ni de prestamo** con bruto > 1 (optimista). Costos 0,15% por lado, mayores que muchos supuestos de la literatura.
- **Cortes de serie** (|salto| > 20x en un dia) y **cierre forzado de deslistadas al ultimo cierre**: ambos optimistas si hubo un crash real sin salida posible.
- **H4** es una conversion mecanica (N x 6), no algo probado por el paper.

## Datos (resumen; detalle en `results/fase8_data.md`)
# Fase 8: datos (generado por `python -m sqzlab.fase8 --stage data`)
- Pares *USDT bajados (1d): **771** (API: 770, data.binance.vision: 1). `data.binance.vision` lista 757 simbolos USDT y `exchangeInfo` 770.
- **Deslistados incluidos: SI.** 254 pares con status BREAK (deslistados, historia completa por API) + 1 fuera de exchangeInfo (NBT, via vision) = 255 pares con ultima vela anterior a END (2026-10-21). No se puede garantizar que falte alguno que Binance haya borrado de ambas fuentes: sesgo de supervivencia residual no medible.
- Velas diarias faltantes (rellenadas con el ultimo cierre y volumen 0): 1491 en 23 pares (maximo 310 en un par).
- Excluidos por nombre/peg: 78 ({'apalancado': 48, 'stable/fiat': 22, 'envuelto/staked': 3, 'respaldado por oro': 2, 'peg (regla mecanica)': 3}). Activos tras cortes: 701.
- Cortes de serie por salto > 20x en un dia (excluyendo apalancados): [('BNX', '2023-02-22', 0.009031), ('COCOS', '2021-01-23', 1295.395683), ('DREP', '2021-04-02', 107.577602), ('LUNA', '2022-05-12', 0.000297), ('LUNA', '2022-05-31', 177400.0), ('QUICK', '2023-07-21', 0.000804), ('SUN', '2021-06-18', 0.001199), ('VEN', '2018-10-19', 5.5e-05)].
- Universo dinamico: primer dia con al menos una moneda elegible **2018-08-17**; primer dia con 20 elegibles 2020-03-03; tamano medio del universo 17.8. Bases que alguna vez estuvieron en el top 20: 160; de ellas, activos deslistados o cortados antes de END: 39 (['AGIX', 'BAKE', 'BCC', 'BCHABC', 'BLZ', 'BNX#2', 'BOND', 'BTT', 'BURGER', 'DENT', 'EOS', 'ERD', 'FLM', 'FRONT', 'FTM', 'HIGH', 'ICX', 'IDEX', 'LEVER', 'LINA', 'LRC', 'LUNA', 'MATIC', 'MKR', 'NPXS', 'OM', 'OMG', 'REN', 'RNDR', 'SRM', 'STMX', 'STORJ', 'SXP', 'TON', 'TROY', 'TRU', 'UNFI', 'WAVES', 'XMR']).
- H4: se bajaron los pares 4h de las 160 bases que alguna vez estuvieron en el top 20 diario (regla mecanica sobre volumen).

## D1 (la estrategia)
### Ventana A (informativa): 2018-08-17 a 2026-10-21

| config | CAGR | Sharpe | DD max | Calmar | retorno total | n cerradas (salida en ventana) | mejor moneda (% de la ganancia) | CAGR sin mejor mes | exposicion bruta prom. | rotacion anual |
|---|---|---|---|---|---|---|---|---|---|---|
| R1-fiel, costo 0,10% por lado | 43.3% | 0.88 | 94.9% | 0.46 | 1803.1% | 2479 | BNB 87% | 27.5% | 1.22x | 66.4x |
| R1-fiel, costo 0,15% (base) por lado | 38.8% | 0.85 | 95.3% | 0.41 | 1364.1% | 2479 | BNB 105% | 23.5% | 1.22x | 66.0x |
| R1-fiel, costo 0,25% por lado | 30.3% | 0.79 | 96.0% | 0.32 | 773.6% | 2479 | BNB 156% | 16.0% | 1.22x | 65.2x |
| buy&hold BTC (sin costos) | 37.2% | 0.83 | 76.6% | 0.49 | 1232.3% | - | - | - | 1.00x | - |
| equiponderado top 20 dinamico (costo base) | 2.8% | 0.46 | 90.4% | 0.03 | 25.8% | - | BNB 354% | -3.4% | 1.00x | 12.5x |
| R1 de la Fase 7 (cupo 6, bruto 1,0x, tamano fijo; costo base) | 41.6% | 0.96 | 72.9% | 0.57 | 1623.2% | 2973 (toda la corrida) | - | - | - | - |

Detalle (R1-fiel, costo base): 2479 operaciones cerradas con salida en la ventana, de las cuales **428 salen porque la moneda cae del top 20** (o cierre forzado) y no por la senal; mediana de duracion 4.0 dias; n con entrada y salida en la ventana: 2479; exposicion bruta maxima 2.23x; costos pagados = 81% de la equity media.

### Ventana B (juez): 2025-04-01 a 2026-10-21

| config | CAGR | Sharpe | DD max | Calmar | retorno total | n cerradas (salida en ventana) | mejor moneda (% de la ganancia) | CAGR sin mejor mes | exposicion bruta prom. | rotacion anual |
|---|---|---|---|---|---|---|---|---|---|---|
| R1-fiel, costo 0,10% por lado | -0.1% | 0.40 | 71.2% | -0.00 | -0.2% | 567 | ZEC - | -30.0% | 1.32x | 73.8x |
| R1-fiel, costo 0,15% (base) por lado | -4.0% | 0.35 | 72.4% | -0.05 | -6.1% | 567 | ZEC - | -32.6% | 1.32x | 73.6x |
| R1-fiel, costo 0,25% por lado | -11.3% | 0.25 | 74.7% | -0.15 | -17.1% | 567 | ZEC - | -37.5% | 1.32x | 73.3x |
| buy&hold BTC (sin costos) | 1.2% | 0.24 | 53.0% | 0.02 | 1.9% | - | - | - | 1.00x | - |
| equiponderado top 20 dinamico (costo base) | -20.4% | 0.00 | 71.0% | -0.29 | -29.9% | - | ZEC - | -33.1% | 1.00x | 10.2x |
| R1 de la Fase 7 (cupo 6, bruto 1,0x, tamano fijo; costo base) | 2.9% | 0.24 | 40.6% | 0.07 | 4.5% | 2973 (toda la corrida) | - | - | - | - |

Detalle (R1-fiel, costo base): 567 operaciones cerradas con salida en la ventana, de las cuales **74 salen porque la moneda cae del top 20** (o cierre forzado) y no por la senal; mediana de duracion 4.0 dias; n con entrada y salida en la ventana: 564; exposicion bruta maxima 2.22x; costos pagados = 17% de la equity media.

- Monedas en el panel: 161; tamano medio del universo: 17.8; dias con tope bruto activo (escala < 1): 961; bruto crudo maximo: 6.84x; cambios de membresia del top 20 por vela: 0.48; monedas deslistadas/cortadas en el panel: 39; cierres forzados CON posicion: 6 [['BCHABC', '2019-11-28'], ['NPXS', '2021-04-05'], ['RNDR', '2024-07-22'], ['MATIC', '2024-09-10'], ['BNX#2', '2025-03-18'], ['TON', '2026-06-30']].
- Chequeo de identidad contable (max |sum pnl - delta equity|): 6.40e-10 USD.

## H4 (conversion declarada, secundaria)
### Ventana A (informativa): 2018-08-17 a 2026-10-21

| config | CAGR | Sharpe | DD max | Calmar | retorno total | n cerradas (salida en ventana) | mejor moneda (% de la ganancia) | CAGR sin mejor mes | exposicion bruta prom. | rotacion anual |
|---|---|---|---|---|---|---|---|---|---|---|
| R1-fiel, costo 0,10% por lado | 55.0% | 0.94 | 90.3% | 0.61 | 3517.9% | 2925 | BNB 84% | 37.7% | 1.14x | 79.4x |
| R1-fiel, costo 0,15% (base) por lado | 49.5% | 0.91 | 91.1% | 0.54 | 2586.1% | 2925 | BNB 101% | 32.9% | 1.14x | 78.8x |
| R1-fiel, costo 0,25% por lado | 39.0% | 0.83 | 93.3% | 0.42 | 1383.0% | 2925 | BNB 149% | 23.7% | 1.14x | 77.6x |
| buy&hold BTC (sin costos) | 37.2% | 0.83 | 76.6% | 0.49 | 1232.3% | - | - | - | 1.00x | - |
| equiponderado top 20 dinamico (costo base) | 0.4% | 0.43 | 91.8% | 0.00 | 3.7% | - | BNB 2164% | -5.6% | 1.00x | 12.8x |
| R1 de la Fase 7 (cupo 6, bruto 1,0x, tamano fijo; costo base) | 38.1% | 0.93 | 65.7% | 0.58 | 1305.5% | 2814 (toda la corrida) | - | - | - | - |

Detalle (R1-fiel, costo base): 2925 operaciones cerradas con salida en la ventana, de las cuales **386 salen porque la moneda cae del top 20** (o cierre forzado) y no por la senal; mediana de duracion 3.0 dias; n con entrada y salida en la ventana: 2925; exposicion bruta maxima 2.34x; costos pagados = 97% de la equity media.

### Ventana B (juez): 2025-04-01 a 2026-10-21

| config | CAGR | Sharpe | DD max | Calmar | retorno total | n cerradas (salida en ventana) | mejor moneda (% de la ganancia) | CAGR sin mejor mes | exposicion bruta prom. | rotacion anual |
|---|---|---|---|---|---|---|---|---|---|---|
| R1-fiel, costo 0,10% por lado | -8.3% | 0.29 | 72.9% | -0.11 | -12.7% | 678 | ZEC - | -33.6% | 1.28x | 91.1x |
| R1-fiel, costo 0,15% (base) por lado | -13.0% | 0.22 | 74.3% | -0.17 | -19.5% | 678 | ZEC - | -36.7% | 1.27x | 91.1x |
| R1-fiel, costo 0,25% por lado | -20.7% | 0.10 | 76.8% | -0.27 | -30.4% | 678 | ZEC - | -42.0% | 1.28x | 90.6x |
| buy&hold BTC (sin costos) | 1.2% | 0.24 | 53.0% | 0.02 | 1.9% | - | - | - | 1.00x | - |
| equiponderado top 20 dinamico (costo base) | -21.6% | -0.02 | 71.6% | -0.30 | -31.6% | - | ZEC - | -34.0% | 1.00x | 10.3x |
| R1 de la Fase 7 (cupo 6, bruto 1,0x, tamano fijo; costo base) | 2.1% | 0.23 | 37.9% | 0.06 | 3.4% | 2814 (toda la corrida) | - | - | - | - |

Detalle (R1-fiel, costo base): 678 operaciones cerradas con salida en la ventana, de las cuales **69 salen porque la moneda cae del top 20** (o cierre forzado) y no por la senal; mediana de duracion 2.5 dias; n con entrada y salida en la ventana: 675; exposicion bruta maxima 2.25x; costos pagados = 21% de la equity media.

- Monedas en el panel: 161; tamano medio del universo: 17.8; dias con tope bruto activo (escala < 1): 874; bruto crudo maximo: 6.80x; cambios de membresia del top 20 por vela: 0.08; monedas deslistadas/cortadas en el panel: 39; cierres forzados CON posicion: 6 [['BCHABC', '2019-11-28'], ['NPXS', '2021-04-05'], ['RNDR', '2024-07-22'], ['MATIC', '2024-09-10'], ['BNX#2', '2025-03-18'], ['TON', '2026-06-30']].
- Chequeo de identidad contable (max |sum pnl - delta equity|): 8.47e-10 USD.

## Criterios SIRVE (D1, costo base)

**Ventana A**

| criterio | cumple | valor |
|---|---|---|
| 1. CAGR neto > 0 | SI | 38.80% |
| 2. Sharpe > Sharpe buy&hold BTC | SI | 0.85 vs 0.83 |
| 3. DD max < DD max buy&hold BTC | NO | 95.3% vs 76.6% |
| 4. Ninguna moneda aporta > 50% de la ganancia | NO | BNB 105% |
| 5. (solo A) CAGR > 0 sin el mejor mes | SI | 23.49% |

**Ventana B**

| criterio | cumple | valor |
|---|---|---|
| 1. CAGR neto > 0 | NO | -3.96% |
| 2. Sharpe > Sharpe buy&hold BTC | SI | 0.35 vs 0.24 |
| 3. DD max < DD max buy&hold BTC | NO | 72.4% vs 53.0% |
| 4. Ninguna moneda aporta > 50% de la ganancia | SI | ganancia total <= 0 (ZEC) |

**Veredicto D1: NO SIRVE.**

## Revision independiente previa a B (subagente que no vio el trabajo; hecha ANTES de `--stage look`)
Resultado: **sin hallazgos criticos**. Reimplemento por su cuenta el universo (coincide en 9 fechas), la senal Donchian/trailing, la vol, el motor de cartera (diferencia relativa de equity 7e-15), los costos (identidad contable 3,5e-10 USD), el CAGR/Sharpe/DD del buy&hold, y corrio todo el camino de `look` sobre un pseudo-B sin errores. Tests: 115 verdes antes de sus correcciones.

| # | Gravedad | Hallazgo | Que se hizo |
|---|---|---|---|
| 1 | MEDIO (solo bot) | si `update_all` falla para una moneda TRADING, sale del top y el bot leeria objetivo 0 (vender por un error de red) | `signals --strategy r1fiel` aborta con "DATOS INCOMPLETOS" si una moneda TRADING del top de ayer no tiene la vela de hoy |
| 2 | MENOR | `update_all` escribia en los mismos CSV que el backtest | el bot usa `data/f8_live/` (copia aparte) |
| 3 | MENOR | el criterio 4 agrupa por base: LUNA clasica y LUNA 2.0 (`LUNA#3`) cuentan como una sola moneda | anotado: en A casi no mueve nada y en B no hay cortes |
| 4 | INFO | el tope bruto 2,0 es sobre el objetivo; con la banda del 20% la exposicion efectiva llega a ~2,2x (antes de B: 2,23x) | anotado; `gross_max` se informa en cada tabla |
| 5-6 | MENOR | rotulo "dias con tope" contaba velas en H4; ventana hardcodeada en `sanity` | corregidos |
| 7-8 | MENOR | tests faltantes (precedencia del veredicto, bordes de ventana, `to_daily` H4, microsegundos, E<=0, BASE#2) | agregados |
| 9 | INFO | cortes de serie: efecto nulo en A (LUNA no tenia posicion al crash) y ningun corte cae en B; 5 cierres forzados con posicion antes de B son migraciones/renombres (BCHABC, NPXS, RNDR, MATIC, BNX#2) | anotado |
| 10 | INFO | renombres (MATIC>POL, EOS>A, MKR>SKY, FTM>S, RNDR>RENDER) se tratan como venta + moneda nueva que necesita 365 dias: sesga la cobertura del universo, no los precios | anotado (supuesto declarado) |
| 12 | INFO | n mide en parte el recambio del universo (30% de los episodios duran <= 2 velas, 18% salen por caer del top 20) | se informa al lado el n que sale por universo y la mediana de duracion |
| 15 | INFO | 2018-2019: solo 2 a 10 monedas elegibles (BTC/ETH/BNB sobre todo); recien en marzo 2020 hay 20 | anotado |

**No verificado:** compilacion del Pine (se prueba en TradingView mas abajo); texto del paper; pares que Binance haya borrado de ambas fuentes.

