# HANDOFF: SQZ+RSI Lab (actualizado 2026-10-21)

> Leé esto entero antes de tocar nada. Reemplaza a `HANDOFF_sqz_rsi.md` del 2026-10-20 (que quedó en el proyecto de claude.ai). Lo nuevo respecto de ese está marcado con **[NUEVO]**.

## 1. Quién es el usuario y cómo trabajar con él

- **Tiger = Franco Redoni.** Desarrollador .NET, Buenos Aires. Habla en **español rioplatense informal**. NO es experto en análisis técnico.
- Su TradingView es **plan gratis** (máx. 2 indicadores). Un slot es "Makroni" (de terceros, no se hace ingeniería inversa). Todo va en **UN solo script**.
- No puede exportar CSV de TradingView (es pago): manda **capturas** de "Estadísticas clave" ("Key stats"), "Lista de operaciones" y "Punto de referencia" (ahí está comprar-y-mantener).
- **Reglas de trabajo (preferencias explícitas suyas):**
  - Respuestas en **bullets, máx. 5, máx. 350 palabras**, más una conclusión de máx. 50 palabras. Si omitiste algo importante por ese límite, **avisarle**.
  - Tono **gracioso**, no serio.
  - **No inventar. No responder si no estás 100% seguro.**
  - El que construye entrega los archivos hechos. Cuando le pidas hacer algo en una UI, decile **exactamente dónde encontrarlo**.
  - **Todas las correcciones juntas**, de una sola vez (se enoja con el ida y vuelta eterno).
  - **Siempre decir si el Pine está compilado o no.** Ver sección 4: **ningún Pine de `ref/` fue compilado por nosotros**; lo único comprobado es que un script llamado "SQZ+RSI BT" (probablemente la strategy v1) corre en su TradingView.
  - "**No quiero que recortes cosas por ahora**": los defaults se pueden apagar, pero no se quitan features.
  - No saltear bloqueos de red (sección 7).

## 2. Objetivo

Un indicador Pine Script v5 que combine **Squeeze Momentum + RSI**, dé señales de compra/venta en **cualquier timeframe y cripto**, más una **versión strategy()** para backtestear.

**[NUEVO] Objetivo actual (decidido el 2026-10-20 en el chat):** optimizar y validar la strategy en **H4, D1 y semanal** (mínimo), sobre **muchas criptos** (meta: todas las razonables; arrancar con BTC, ETH, SOL), **incluyendo ajustar los niveles de entrada**. Instrumentos de validación históricos del usuario: los techos de **SOL D1 de ene-feb 2026 y may-jun 2026**. La optimización se hace **desde este repo, con Claude Code**; el chat de claude.ai queda como apoyo (el repo se sincroniza con el proyecto "Analisis tecnico").

## 3. Diseño del indicador (v8)

**Base:** BB(20,2) dentro de KC(20,1.5) = squeeze. `mom = linreg(close − avg(avg(highest20, lowest20), sma20), 20, 0)`; se escala `50 + momScaled` (normLen=100, momHeight=35). RSI(14) con SMA(14). EMAs 20/55/200. ADX(14) ≥ 20 y creciente. ATR(14).

**Señales (cada una se puede apagar):**

- **A, pullback a las EMAs.** Tendencia establecida (`ema1>ema2>ema3`, espejo para venta), pullback dentro de `pbBars`=5 velas a la EMA20 sin cerrar más allá de la EMA55; gatillo: cierre más allá de la EMA20 y del máx/mín previo; RSI vs su media. Stop = extremo del pullback ∓ 0.25×ATR.
- **B, ruptura de squeeze.** Squeeze ≥ 6 velas (`minSqz`), 2 velas de gracia, cierre fuera del rango, momentum a favor y creciente, precio del lado correcto de la EMA200 (`needE200`, default **true**). Stop = punto medio del rango. Invalidación dentro de `invBars`=3.
- **C, reversión en techos/pisos.** Venta: RSI ≥ 65 en las últimas 10 velas → `crossunder(rsi, rsiMa)` arma → dentro de 3 velas: rsi<rsiMa, mom cayendo, close<EMA20. Stop = `highest(high,7) + 0.25×ATR`; se descarta si el stop está a más de `cMaxRisk`=3 ATR. Compra = espejo con 35. **C compras apagadas por defecto en v8/strategy v2** (`cAllowLong=false` / `cLong=false`) porque no mostraron ventaja.
- **D, divergencia confirmada del momentum del SQZ (desde v8).** Alcista: mínimo de precio más bajo + mínimo de momentum más alto, ambos pivotes bajo cero (`dvZero`). Bajista = espejo. `dvL=5, dvR=5` (la señal llega `dvR` velas tarde), `dvMin=5, dvMax=60`, ocultas apagadas. Stop = precio del pivote ∓ `dAtrMult`(0.25)×ATR. `dNeedEma=true`. `dMaxRisk=0` (apagado por defecto; con 3 se descartan las que llegan tarde).

**Salidas estándar:** stop tocado intravela, o cierre contra la EMA20 (largo: close<ema1), o invalidación de B. Se leen en múltiplos de R (1R/2R).

**Modo de visualización (casilla `showLvls`):** tildada = etiquetas detalladas, formas por tipo de señal (A triángulos, B rombos, C flechas azules, D cuadrados amarillos) y X naranjas de salida. Destildada = solo "COMPRA" verde / "VENTA" roja.

## 4. Archivos y versiones

Todos en `ref/` (copias del proyecto de claude.ai, carpeta `claude/`), **solo lectura**:

- `sqz_rsi_senales_v8.pine`: **indicador vigente.** Título "Squeeze + RSI + Senales A+B+C" (aunque incluye D), `overlay=false` con `force_overlay=true`.
- `sqz_rsi_strategy_v2.pine`: **strategy vigente en papel**: `strategy("SQZ+RSI A+B+C+D Backtest", shorttitle="SQZ+RSI BT", overlay=true, initial_capital=10000, pyramiding=0, process_orders_on_close=true, calc_on_every_tick=false, comisión 0.05% por lado)`. **La comisión 0,05% es supuesto**, editable en Propiedades. Tamaño por riesgo: `equity × riesgo%(1.0) / |close − stop|`, tope `maxLev`(1.0)×equity/close. Cadena de entradas con prioridad B, A, C, D. Quirk heredado: si hay señal B del mismo lado de la posición abierta, la cadena `else if` se consume y no mira A/C/D esa vela.
- `python_port_y_tests.md`: contiene `eng.py` (port Python del indicador v4: A+B+C, **sin D**) y `divsig.py` (backtest solo de D). **[NUEVO] `divsig.py` importa `from div import pivots` y `div.py` no existe**: hay que reimplementar `pivots` (equivalente a `ta.pivotlow/pivothigh(L,R)`). El código lee CSVs de una carpeta de uploads de una sesión anterior que ya no existe.

**[NUEVO] Aviso de versión (corrección a lo dicho antes en el chat):** el script que el usuario tiene cargado hoy en TradingView se llama "SQZ+RSI BT" y su pestaña "Entradas" muestra solo A, B y C (sin D), con "C: COMPRAS (piso)" **tildada y sin la leyenda "apagada por defecto"** que sí tiene `ref/sqz_rsi_strategy_v2.pine`. Eso indica que es la **strategy v1 (A+B+C)**, no la v2. **No está verificado abriendo el editor Pine.** En el chat se dijo antes "la strategy compiló" asumiendo que era la v2: **eso no estaba verificado y era incorrecto.** Estado real:
- La v1 (cargada) corre en TradingView.
- ❌ **v2 y v8 siguen sin compilar en TradingView** (solo hubo chequeo de sintaxis por script).

## 5. Evidencia hasta ahora (para no repetir trabajo)

**Reconciliación con TradingView (SOL 1D, sesión anterior):** el port reprodujo **21 de 22** operaciones desde abr-2025 con el filtro EMA200 de B apagado. Diferencia: B venta 15-dic a 127.77 en TV vs 18-dic a 119.53 en el port.

**Corrida TV (SOL), filtro EMA200 de B APAGADO:** 52 trades, +625.95 USDT, PF 1.519, 17/52 ganadores, DD 3.62%. Por señal: C +409.16, B +315.58, A −98.79. Sin el trade #42 (+415.51, la venta in-sample ene→feb 2026) el total cae a ~+210 y las ventas quedan en −334; los trades 2025-26 sin #42 suman ~+44 (cero).

**Corrida TV (SOL), filtro EMA200 de B ENCENDIDO:** 40 trades, +878.37 (+8.78%), PF 2.094, 16/40 ganadores, DD 2.85%. Ojo: el benchmark comprar-y-mantener cambió entre corridas, no son comparables. En 6 monedas 1D (port) el filtro no mostró beneficio general: la mejora fue específica de SOL (2022-2024).

**C compras (TV, SOL, aislada):** 10 trades, 1 ganador, −17.06 USDT, PF 0.9. Port, 6 monedas 1D: 14 trades, 1 ganador, −0.19R → **apagadas por defecto**.

**C ventas (TV, SOL, aislada):** +410.23 USDT, PF 3.415, 4/9 ganadores, casi todo del trade #42. Port, 6 monedas 1D: 11 trades, +1.49R (sobre el p95 del baseline aleatorio, 0.92R). Evidencia modesta y diseñada in-sample. En 4h, C es negativa para ambos lados.

**D como señal de entrada:** sin ventaja demostrada. Defaults v8: 1D 10 trades +0.29R (compras 7 trades −0.13R; ventas 3 trades +1.27R); 4h 48 trades −0.16R. Retornos futuros de divergencias: 61 alcistas y 60 bajistas en 9 archivos, a 5/10/20 velas dentro de la banda aleatoria.

**Caso BTC semanal (captura del usuario):** el port encuentra UNA divergencia alcista (pivote semana 2026-08-10, mínimo 62,512; confirmada semana 2026-09-14). Al confirmar el cierre era 81,130 (+30% desde el mínimo); stop ≈60,928 → riesgo 3.2 ATR = 24.9% del precio. Conclusión: **contexto, no gatillo**. `dMaxRisk=3` la descartaría.

**[NUEVO] Bases de TradingView del 2026-10-20 (BTC y ETH en 1D/4h/1W):** están en `docs/TV_BASELINES.md`. Resumen: D1 es el único timeframe con muestra decente (BTC +1.059% PF 4,75 con 119 trades; ETH +88,6% PF 3,43 con 83 trades); H4 (solo desde 31-dic-2023) da BTC +20,9% PF 1,38 y ETH +8,5% PF 1,15; semanal tiene 7 a 12 trades, ruido. SOL no se corrió.

**Caveats estadísticos que hay que repetir al interpretar:** muestras de <100 trades, sesgo de mercado bajista en la muestra, episodios correlacionados, calibración in-sample, costo de 0.10% ida y vuelta asumido, baseline de entradas aleatorias.

## 6. Bugs y lecciones

- Bug mío (corregido) en el port: señales del mismo lado pisaban un trade abierto (38 casos). Fix: ignorarlas. Efecto: C ventas 1D pasó de 9 trades/+1.19R a 11 trades/+1.49R.
- Malentendido de "corrida aislada": para aislar hay que destildar **Señal A, Señal B y el lado opuesto**, no solo un lado.
- El usuario no encontraba la pestaña "Entradas", comprar-y-mantener ni el export CSV → por eso la regla de decirle siempre dónde hacer clic.
- **[NUEVO]** "H4 no se puede?" Sí se puede, pero TradingView gratis limita el historial intradía: ver sección 7.
- **[NUEVO]** Se asumió que el script cargado era la v2 sin verificarlo. Verificá siempre qué versión está cargada (nombre del script, casillas de "Que probar") antes de comparar números.
- **[NUEVO]** El Pine "compila" solo si se probó en TradingView. No usar esa palabra por intuición.

## 7. Entorno y datos

- Datos de validación previos: BingX, formato `time_utc,open,high,low,close,volume`. 1D: SOL, BTC, ETH, XRP, DOGE, LINK. 4h: SOL, BTC, ETH. **Eran archivos de una sesión anterior y no están**: hay que volver a bajarlos (lo hizo con Claude Code usando `fetch_candles.py`, que tampoco está: reescribirlo).
- **[NUEVO]** Los datos que muestra su TradingView en estas bases son de **Bitstamp** (BTCUSD, ETHUSD). Para calibrar el port, conseguir velas de la misma fuente; si se calibra contra BingX, esperar diferencias chicas de precios/horarios y documentarlas. No verificado: si TradingView ofrece feed de BingX para estos pares.
- **[NUEVO] Límite de historial de TradingView (verificado en el soporte de TradingView):** base de 5.000 velas por intervalo intradía (Essential/Plus 10.000, Premium 20.000, planes pro más); además "varias velas hacia atrás hasta el inicio de la semana/mes/año". En diario o mayor se muestra todo el historial. Hay un modo "Deep Backtesting" que calcula sobre todo el historial; **no verificado qué plan lo incluye ni su precio.** Consecuencia observada: en H4 el backtest arranca el **31-dic-2023**.
- Red del entorno de la sesión de chat bloqueada para varios sitios (Coinbase 403, Binance robots; Crypto.com solo da 50 velas). No se usaron workarounds y no hay que buscarlos. En Claude Code el acceso a red puede ser distinto: probalo y, si falla, reportalo.
- **[NUEVO] Notas de automatización de TradingView con Claude in Chrome (observado el 2026-10-20):** cambiar de símbolo se logra haciendo clic en la lista de seguimiento de la derecha; el temporizador de la barra superior (botón con "D", "4h", "W") abre un menú con "4 hours", "1 day", "1 week"; el panel del Strategy Tester tiene un botón de gráfico (stats clave + rendimiento) y uno de tabla ("List of trades"); la lista de trades está **virtualizada** (solo se ven ~10 filas, de la más reciente a la más vieja), así que bajar las 100+ filas requiere scrollear; la interfaz a veces sale en inglés y a veces en español. No está verificado si Claude Code puede usar Claude in Chrome en su entorno; si no, el usuario manda capturas.
- Proyecto "Analisis tecnico" de claude.ai: contiene PDFs de libros de análisis técnico (patrones de velas, acción del precio, manual de chartismo, guía de patrones, análisis chartista, patrones Elliott, "trading en la zona"). Son contexto para ideas de nuevas señales, no hay que leerlos para optimizar.

## 8. Estado real y pendientes (actualizado en la sesión de Claude Code del 2026-10-20)

### Hecho
- **Fase 0, repo**: `src/sqzlab/` (`fetch.py`, `data.py`, `indicators.py`, `strategy.py`, `calibrate.py`), `tests/` (11 tests verdes), `.venv` Python 3.12, `requirements.txt`, `pytest.ini`. Comandos en `CLAUDE.md`. No se commiteó nada.
- **Fase 1, datos** (en `data/`, gitignored): Bitstamp BTC 1d/4h desde 2011-08-18, ETH desde 2017-08-16, SOL desde 2022-08-18; BingX **perpetuo** BTC/ETH 1d desde 2021-05-14, SOL 1d desde 2021-11-04, 4h solo desde 2022-09-11. Hallazgos: (a) el spot de BingX no sirve (limita la consulta a 380 días y su vela diaria abre a las 16:00 UTC); (b) **ETH en Bitstamp arranca en 2017, pero la base de TV de ETH arranca en ago-2015 → el feed de ETH de TV NO es Bitstamp (feed real: no verificado)**; (c) Bitstamp no ofrece semanal: 1W se arma desde 1d con semanas que abren el **lunes 00:00 UTC** (consistente con BTC/ETH 1W; ETH 1W coincide).
- **Fase 2, calibración A+B+C (C compras encendida)**: ver `results/calibration.md`. `src/sqzlab/strategy.py` replica `strategy()` desde `ref/sqz rsi strategy v2.pine` con useD apagado (la v1 real no está en `ref/`: no verificado que sea idéntica).

### Resultados de la calibración (port vs TV)
| Base | Trades TV / port | PnL TV / port | PF TV / port |
|---|---|---|---|
| BTC 4h | 153 / 153 | 2.086,75 / 2.086,98 | 1,376 / 1,376 |
| BTC 1D | 119 / 121 | 105.963 / 96.118 | 4,751 / 4,818 |
| BTC 1W | 12 / 12 | 10.468 / 12.172 | 34,2 / 37,1 |
| ETH 1W | 7 / 7 | −181,64 / −181,73 | 0,160 / 0,161 |
| ETH 4h | 151 / 150 | 844,86 / 962,08 | 1,147 / 1,171 |
| ETH 1D | 83 / 73 | 8.863 / 1.011 | 3,426 / 1,490 |

- **Spot-checks**: BTC 1D 10/10 y BTC 4h 4/4 coinciden en lado, fecha y precios de entrada/salida. En BTC 1D la razón PnL_TV / PnL_port es **constante 1,0933 en los 10 trades** (y igual a la razón de PnL final): los trades desde oct-2025 son idénticos en R; la diferencia es solo de equity acumulada antes de oct-2025.
- **Lecciones de TradingView** (reemplazan supuestos de TV_BASELINES): (1) EMA con semilla SMA (`na` hasta n velas). (2) Hora de la lista de trades = apertura de la vela (4h en UTC−3; 1D/1W fecha UTC). (3) El PnL de la lista de trades es neto de comisión. (4) "Max equity drawdown" de TV se parece a la caída de la curva de trades cerrados (991,8 vs 1.002,3), no a la equity vela a vela. (5) Backtest 4h arranca en 2024-01-01 00:00 UTC.

### Estructura de parámetros y Pine (decisión del usuario, 2026-10-20)
- `params/{h4,d1,w1}.json` = fuente de verdad, **un set por temporalidad, nunca por moneda**. Hoy son los defaults de la v2 (marcados "SIN OPTIMIZAR").
- `python -m sqzlab.genpine` genera `pine/{h4,d1,w1}/sqz_rsi_strategy_<tf>.pine` y `pine/sqz_rsi_strategy_unified.pine` (presets con `timeframe.in_seconds()`: <1d H4, 1d a <1w D1, >=1w W1, opción Manual, cartel con el preset en uso). Verificado offline: el diff contra la v2 de `ref/` solo toca defaults, título y comentarios.
- **Pine: NO COMPILADO.** Ninguno de los 4 se probó en TradingView (tampoco v2 ni v8). Lo único corrido fue chequeo de texto y tests en Python.

### Sin explicar (no verificado)
- BTC 1D: 2 trades de más y equity −9,3% antes de oct-2025, casi seguro en 2011-2014 (precios de 3 a 30 USD; posible diferencia de datos o de redondeo a mintick; redondear OHLC a enteros dio 118 trades, peor). BTC 1W también diverge en PnL. Necesito la **lista de trades más viejos de TV** (BTC 1D) para localizarlo.
- ETH 4h: 1 trade de menos / PnL +14%: probable feed distinto de Bitstamp. ETH 1D: feed distinto seguro (TV arranca en 2015).
- El estado de los scripts: **ningún Pine fue compilado en TradingView por esta sesión**; la v1 cargada corre en su TV, v2 y v8 siguen sin compilar. Ojo: `ref/sqz rsi senales v8.pine` trae pegadas 66 líneas de interfaz de claude.ai al principio (no es Pine válido tal cual), y `divsig.py` NO está embebido en `ref/python port y tests.md` (solo `eng.py`).

### Próximos pasos
1. **El usuario decide si la calibración alcanza** (ver tabla). Para cerrar BTC 1D: capturas de la lista de trades de TV de BTCUSD 1D, los 15 más viejos (Strategy Tester > Lista de operaciones, bajar hasta el final).
2. Fase 3: portar D (con `indicators.pivots`, ya implementado y testeado; falta verificar empates contra TV) y toggles por lado; verificar contra `ref/` v2.
3. Fase 4: optimizar con `docs/PROTOCOLO.md` (corte train/test antes de mirar). 5. `pine/sqz_rsi_strategy_v3.pine` + `candidates/`. 6. Validar en TV. 7. SOL en TV (no se corrió).
4. Expectativa honesta: D no mostró ventaja en datos previos; si sale pobre, decirlo.
