# Línea base de TradingView y semántica a replicar

Medido el 2026-10-20 en TradingView (plan gratis), leyendo "Estadísticas clave" del Strategy Tester. Capital inicial 10.000 USD, comisión 0,05% por lado, riesgo por trade 1%, apalancamiento máx. 1, parámetros por defecto del script cargado. **Los datos son de Bitstamp (BTCUSD, ETHUSD), no de BingX.**

## Qué script estaba cargado (importante)

El script se llama **"SQZ+RSI BT"** y su pestaña "Entradas" mostraba en "Que probar": Senal A (pullback), Senal B (ruptura de squeeze), Senal C (reversion), A: COMPRAS/VENTAS, B: COMPRAS/VENTAS, C: COMPRAS (piso)/VENTAS (techo), todas tildadas. **No hay señal D ni toggles de D.** Es decir, parece la **strategy v1 (A+B+C)** y no la v2 de `ref/` (que se llama "SQZ+RSI A+B+C+D Backtest" y tiene D). No está verificado abriendo el editor Pine. Consecuencias:

- Las bases de abajo son de A+B+C, con **C compras encendida** (en la v2 de `ref/` está apagada por defecto).
- Eso coincide con `eng.py` (indicador v4, A+B+C, sin toggle separado de C compras). **Calibrá primero A+B+C** y recién después sumá D.

## Bases (A+B+C, parámetros por defecto)

| Símbolo / TF | Rango del backtest | PnL | Factor de beneficio | DD máx. | Ganadoras | Trades |
|---|---|---|---|---|---|---|
| BTCUSD 1D | 17-ago-2011 → 19-oct-2026 | +105.963,62 USD (+1.059,64%) | 4,751 | 4.790,17 USD (4,31%) | 32,77% (39/119) | 119 |
| BTCUSD 4h | 31-dic-2023 → 20-oct-2026 | +2.086,75 USD (+20,87%) | 1,376 | 1.002,29 USD (9,18%) | 28,10% (43/153) | 153 |
| BTCUSD 1W | 14-ago-2011 → 18-oct-2026 | +10.467,53 USD (+104,68%) | 34,191 | 164,71 USD (0,82%) | 58,33% (7/12) | 12 |
| ETHUSD 1D | 6-ago-2015 → 20-oct-2026 | +8.863,10 USD (+88,63%) | 3,426 | 899,46 USD (4,93%) | 37,35% (31/83) | 83 |
| ETHUSD 4h | 31-dic-2023 → 20-oct-2026 | +844,86 USD (+8,45%) | 1,147 | 1.144,33 USD (10,98%) | 23,18% (35/151) | 151 |
| ETHUSD 1W | 2-ago-2015 → 18-oct-2026 | −181,64 USD (−1,82%) | 0,16 | 200,12 USD (2,00%) | 28,57% (2/7) | 7 |

SOL: **no corrida todavía** (pendiente).

## Lectura honesta de esas bases

- **H4 solo existe desde 31-dic-2023 en TradingView gratis**: el límite base de historial intradía es de 5.000 velas (Essential/Plus 10.000, Premium 20.000 según el soporte de TradingView). Para H4 con historia larga solo sirve el port.
- **Semanal tiene 7 a 12 trades por moneda**: el PF 34 de BTC y el PF 0,16 de ETH son ruido. Solo se juzga agregado entre monedas.
- BTC 1D: la curva de equity da saltos grandes en 2013-2014; mucha de la ganancia en USD viene de ahí. Medir en R.
- Spot-checks de BTCUSD 1D (últimos trades, orden descendente; fechas de entrada → salida): #119 Short, 7-oct-2026 → 11-oct-2026, entrada 83.275, salida 83.679, −126,04 USD; #118 Long, 18-sep-2026 → 7-oct-2026, 80.879 → 83.275, +408,56 USD; #117 Long, 20-ago-2026 → 10-sep-2026, 73.008 → 76.529, +470,47 USD; #116 Short, 13-jul-2026 → 14-jul-2026, 62.257 → 64.976, −1.118,11 USD; #115 Long, 3-jul-2026 → 8-jul-2026, 62.522 → 62.238, −75,24 USD; #114 Short, 15-may-2026 → 3-jul-2026, 79.062 → 62.522, +4.663,42 USD; #113 Short, 29-ene-2026 → 2-mar-2026, 84.530 → 68.821, +2.599,39 USD; #112 Short, 15-dic-2025 → 30-dic-2025, 86.412 → 88.390, −281,12 USD; #111 Short, 4-nov-2025 → 3-dic-2025, 101.466 → 93.472, +1.068,05 USD; #110 Long, 26-oct-2025 → 29-oct-2025, 114.551 → 110.038, −537,66 USD. (Leídos de la pantalla; el orden Entry/Exit de la lista de TradingView aparece invertido visualmente, así que verificá fechas al comparar.)
- **Zona horaria:** el reloj del gráfico de TradingView mostraba **UTC-3**, y las horas de la lista de trades 4h (21:00, 01:00, 05:00, 09:00, 13:00, 17:00) son consistentes con velas H4 que abren a 00/04/08/12/16/20 UTC. Convertí a UTC antes de comparar con el port. No verificado si la hora mostrada es la de apertura de la vela (muy probable) o la de la ejecución.
- Spot-checks de BTCUSD 4h (últimos, descendente, hora UTC-3): #153 Long 18-oct-2026 21:00 → 19-oct-2026 09:00, 82.425 → 81.833, −78,66 USD; #152 Short 14-oct-2026 09:00 → 16-oct-2026 05:00, 81.549 → 82.533, −67,79 USD; #151 Long 4-oct-2026 05:00 → 5-oct-2026 09:00, 85.293 → 85.259, −16,07 USD; #150 Long 1-oct-2026 21:00 → 2-oct-2026 13:00, 85.487 → 84.297, −60,99 USD.

## Semántica de `strategy()` a replicar (leída del código de `ref/sqz_rsi_strategy_v2.pine`)

- `process_orders_on_close=true`, `calc_on_every_tick=false`, `pyramiding=0`: las señales se evalúan al cierre de cada vela y las entradas se ejecutan **al cierre de esa misma vela**.
- Tamaño: `min(equity×riesgo%/|close−stop|, equity×maxLev/close)`, con `strategy.equity` = capital inicial + PnL realizado + PnL abierto (marca a mercado). En una reversión, la equity que se usa incluye el PnL abierto de la posición que se va a cerrar. Replicar esto afecta el tamaño.
- Stop: `strategy.exit(stop=...)` colocado en la entrada; se ejecuta intravela al precio del stop, o al open si la vela abre más allá (gap). Del lado largo se toca con `low <= stop`; del corto, con `high >= stop`.
- Salida por condición (`strategy.close`) al cierre de la vela: largo si `close < ema1`; corto si `close > ema1`; invalidación de B: `posType==2` y `bar_index − entryBar <= invBars` y `close < entHi` (largo) / `close > entLo` (corto).
- Cadena de entradas con prioridad **B largo, B corto, A largo, A corto, C largo, C corto, D largo, D corto**, como `else if`. **Quirk:** si hay señal B del mismo lado de la posición abierta, la cadena se consume y no mira A/C/D esa vela; lo mismo si `qty <= 0`.
- Una señal del mismo lado que la posición abierta se ignora. Una del lado opuesto **revierte** (cierra y abre en el mismo cierre de vela). El port actual registra la reversión así; **verificar contra TradingView** que el modelo de reversión coincide.
- C y D exigen `posNow != lado` (no generan señal si ya hay posición de ese lado). `posNow` sale de `strategy.position_size`, o sea que ya refleja los stops tocados.
- Comisión: porcentaje 0,05% del valor de la orden, por lado.
- D (en v2): pivotes con `ta.pivotlow/pivothigh(mom, dvL, dvR)` sobre el momentum crudo; la señal llega `dvR` velas tarde. **Verificá en la calibración** cómo trata TradingView los empates en pivotes y reproducilo exacto.
- Arranque: **[CORREGIDO en la calibración del 2026-10-20]** la EMA de TradingView usa **semilla SMA** (vale `na` hasta tener n velas), NO arranca en el primer valor: con eso BTC 4h cierra en 153 trades y PnL 2.086,98 vs 2.086,75 de TV. RMA también usa semilla SMA. (Texto original, ya desmentido: «EMA arranca en el primer valor».) El port actual salta velas hasta que no haya NaN. Eso puede dar diferencias en los primeros trades (BTC desde 2011): documentalas, no las "arregles" a ciegas.
- Velas semanales: **no asumas** el día de inicio de la semana de TradingView; descubrilo calibrando contra la base semanal.

## Agregado Fase 6 (2026-10-21): SOL y BTC 1D con los scripts de `params/*.json`

**Ojo: estas filas NO son A+B+C con defaults (la v1).** Son los scripts generados (H4 optimizado; D1 y W1 = v2) corridos en TradingView el 2026-10-21; el detalle está en `results/tv_log.md` filas 3 a 8 y 17.
- SOLUSDT (Binance): 4h (desde 2023-12-31) 29 trades, +2.143,50, PF 3,336; 1D (desde 2020-08-10) 44 trades, +1.501,18, PF 2,131; 1W 5 trades, −30,01, PF 0,639. El port coincide en trades, ganadoras y PF (PnL dentro de ±0,02% en 4h; en 1D el port da +1.495,89).
- BTCUSD (Bitstamp) 1D, historia completa 2011-hoy, script D1 (= v2): TV **113 trades, +65.954,74, PF 4,872**; port 115 trades, +59.515,80, PF 4,907. **Localizado (no explicado):** el port toma de más la A corta del 2012-04-07 y la A larga del 2016-01-07, y entra la B larga del 2012-07-09 donde TV entra el 2012-05-31. Todo lo demás coincide en los primeros 32 trades. Ver `results/tv_log.md` (sección Fase 6.6).
- Holdout H4 (2024-01 a hoy) contra el port: LINK, BNB, BCH, XLM coinciden (trades, ganadoras, PF; PnL a ±0,3 USD).
