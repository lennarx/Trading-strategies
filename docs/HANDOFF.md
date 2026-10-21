# HANDOFF: SQZ+RSI Lab (actualizado 2026-10-21)

> Leé esto entero antes de tocar nada. Reemplaza a `HANDOFF_sqz_rsi.md` del 2026-10-20 (que quedó en el proyecto de claude.ai). Lo nuevo respecto de ese está marcado con **[NUEVO]**.

## 0. Trabajo multisesión: reglas obligatorias para TODA sesión

Este proyecto se hace a lo largo de muchas sesiones y agentes distintos. Nadie recuerda nada de la sesión anterior: **el repo es la memoria.**

1. **Al empezar, leer primero este HANDOFF entero** (y después `docs/PROTOCOLO.md`, `docs/TV_BASELINES.md` y `results/tv_log.md`). No empezar a trabajar ni proponer nada antes.
2. **Al terminar cada tarea o fase (y siempre antes de cerrar la sesión), dejar asentado el avance:**
   - Actualizar la **sección 8** con el estado real: qué se hizo, qué quedó sin explicar y los próximos pasos en orden. Si algo cambia lo dicho en otra sección, corregir esa sección y marcar la corrección.
   - Anotar en `results/tv_log.md` toda corrida en TradingView (también las que salen mal).
   - Registrar cuántas pruebas/combinaciones se evaluaron (el protocolo exige contarlas).
   - Si se cambió un parámetro, editar `params/*.json` y regenerar los Pine con `python -m sqzlab.genpine`; no editar los `.pine` generados a mano.
3. **Separar lo verificado de lo supuesto**: marcar "no verificado" lo que no se probó. Un Pine solo "compiló" si se probó en TradingView.
4. Dejar el repo en estado usable: tests verdes (`python -m pytest -q`) y nada a medio hacer sin avisar en la sección 8. Commit y push solo cuando lo pida el usuario.
5. Si el HANDOFF y la realidad no coinciden, **gana la realidad**: corregir el HANDOFF.

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
- `python_port_y_tests.md`: contiene `eng.py` (port Python del indicador v4: A+B+C, **sin D**) y `divsig.py` (backtest solo de D). **[NUEVO] `divsig.py` importa `from div import pivots` y `div.py` no existe.** Corrección 2026-10-20: `python_port_y_tests.md` trae embebido solo `eng.py`; `divsig.py` NO está en `ref/`. No hace falta: D se portó desde el Pine v2 (fuente de verdad) con `indicators.pivots`. No reconstruirlo de memoria. El código lee CSVs de una carpeta de uploads de una sesión anterior que ya no existe.

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

## 8. Estado real y pendientes (última actualización: sesión del 2026-10-20, pasada de revisión sobre el commit f431709)

### Hecho
- **Repo y entorno**: `src/sqzlab/` (`fetch`, `data`, `indicators`, `strategy`, `calibrate`, `genpine`), `tests/` (23 verdes), `.venv` Python 3.12, `requirements.txt`, `pytest.ini`. Comandos en `CLAUDE.md`.
- **Datos** (`data/`, gitignored): Bitstamp BTC 1d/4h desde 2011-08-18, ETH desde 2017-08-16, SOL desde 2022-08-18, LTC 2017-06, XRP 2016-12, BCH 2017-12, LINK 2020-10, ADA 2021-11, DOGE 2022-12, XLM 2020-05. Binance spot USDT (sin bloqueo de red): BTC y ETH desde 2017-08, BNB 2017-11, LTC 2017-12, ADA 2018-04, XRP 2018-05, LINK 2019-01, DOGE 2019-07, SOL 2020-08. BingX perpetuo: BTC/ETH 1d desde 2021-05, SOL 1d desde 2021-11, 4h solo desde 2022-09 (BingX spot no sirve: limita a 380 días y su vela diaria abre 16:00 UTC). Binance 4h tiene 2 a 8 huecos por mantenimiento en cada moneda (Bitstamp no tiene huecos). 1W se arma desde 1d con semanas que abren el lunes 00:00 UTC (ETH 1W coincide con TV).
- **Calibración A+B+C (C compras encendida)**: `python -m sqzlab.calibrate`, tabla en `results/calibration.md`. Resumen: BTC 4h 153/153 trades, PnL 2.086,98 vs 2.086,75, PF 1,376 en ambos; ETH 1W 7/7 (−181,73 vs −181,64); BTC 1D 121 vs 119 trades (PnL 96.118 vs 105.964); BTC 1W 12/12 trades pero PnL 12.172 vs 10.468; ETH 1D/4h no coinciden. Spot-checks: BTC 1D 10/10 y BTC 4h 4/4 en lado, fecha y precios; en BTC 1D la razón PnL_TV/PnL_port es constante 1,0933 en los 10 trades (la lógica coincide; la diferencia es equity acumulada antes de oct-2025).
- **Calibración: APROBADA CON SALVEDAD** (decisión del usuario): BTC 4h clava TV y la lógica reciente de BTC 1D coincide. Queda sin explicar la diferencia previa a oct-2025 en BTC 1D/1W. Para calibrar solo se usa BTC.
- **Hipótesis mintick probada y NEGATIVA** (opción `mintick`, `tick_stop`, `tick_fill` en `simulate`, apagada por defecto; también probé redondear los OHLC a enteros): ninguna variante converge. BTC 1D (objetivo 119 trades, +105.963,62): base 121 trades/+96.118; stop 122/+86.406; fill 121/+97.991; stop+fill 122/+88.576; con datos redondeados 118/+38.022, y con stop o stop+fill 119 trades pero +18.029 (peor). BTC 1W (objetivo 12 trades, +10.467,53): 12 trades en todas, PnL 12.120 a 12.161 (no se mueve). BTC 4h: idéntico en todas las variantes (no empeora). Queda como "sin explicar".
- **Lecciones de TradingView** (corrigen supuestos previos): (1) la EMA tiene semilla SMA (`na` hasta n velas), no arranca en el primer valor: eso arregló BTC 4h (de 156 a 153 trades); (2) la hora de la lista de trades es la apertura de la vela (4h en UTC−3; 1D/1W fecha UTC); (3) el PnL de la lista es neto de comisión; (4) "Max equity drawdown" se parece a la caída de la curva de trades cerrados (991,8 vs 1.002,3 en BTC 4h); (5) el backtest 4h arranca en 2024-01-01 00:00 UTC.
- **Fase 3 hecha (port de D y toggles de la v2)**: `strategy.py` incluye la señal D (`indicators.pivots` vectorizado y testeado), toggles `useD/dLong/dShort`, filtro de volumen y `v2_params()` (cLong apagada, D encendida = lo que traen `params/*.json`). `DEFAULTS` deja D apagada para no alterar la calibración. **No verificado contra TradingView**: la señal D y el tratamiento de empates de pivotes (TV_BASELINES pide verificarlo; con momentum en punto flotante los empates son raros). Referencia de cordura, no calibración: BTC Bitstamp desde 2017 con defaults v2: 1D 12 trades D (+2,1R), 4h 101 trades D (−8,0R), consistente con "D no tiene ventaja demostrada".
- **Estructura de parámetros y Pine (decisión del usuario)**: `params/{h4,d1,w1}.json` = fuente de verdad, un set por temporalidad, **nunca por moneda**; hoy son los defaults de la v2 ("SIN OPTIMIZAR"). `python -m sqzlab.genpine` genera `pine/{h4,d1,w1}/sqz_rsi_strategy_<tf>.pine` y `pine/sqz_rsi_strategy_unified.pine`. **Unificado rediseñado**: preset automático con `timeframe.in_seconds()` (<1d H4, 1d a <1w D1, >=1w W1, opción Manual, cartel con el preset); los parámetros optimizables siguen al preset; **`riskPct` y `maxLev` son siempre inputs del usuario**; las casillas de "Que probar" tienen su interruptor "Que probar: usar mis casillas (en vez del preset)" (apagado por defecto) y, tildado, valen las del usuario sin importar el preset, para poder aislar señales y lados.
- **`ref/` limpiado (excepción a "solo lectura", pedida por el usuario)**: se borraron las 66 líneas de interfaz de claude.ai de `sqz_rsi_senales_v8.pine` (queda con 449 líneas desde `//@version=5`; verificado con `diff` que el cuerpo es idéntico al original), y se renombraron los 3 archivos con guiones bajos (`sqz_rsi_senales_v8.pine`, `sqz_rsi_strategy_v2.pine`, `python_port_y_tests.md`) con todas las referencias actualizadas. `divsig.py` no está en `ref/` y no hace falta.
- **Velocidad**: `simulate` ~0,2 s por corrida en BTC 4h 2017+ (20.000 velas; indicadores 0,06 s), ~0,04 s en 1D, casi nada en 1W; PC con 16 núcleos. No se aceleró: ver `docs/PROTOCOLO.md` ("Velocidad").
- **Pine: NINGUNO compiló en TradingView** (los 4 generados, la v2 ni la v8). Solo hay chequeos de texto y tests en Python.

### Sin explicar / no verificado
- BTC 1D: 2 trades de más y equity −9,3% antes de oct-2025 (probablemente 2011-2014); BTC 1W: PnL +16%. Mintick descartado como explicación. Necesito la lista de trades más viejos de TV para localizarlo (sección 9.4, tarea 1). Como la optimización usa datos desde 2017, esto no bloquea.
- ETH: 1D (73 trades del port vs 83 de TV) y 4h (150 vs 151) no coinciden. **"El feed de ETH de TV no es Bitstamp" es hipótesis, no hecho**: el gráfico del usuario dice "Bitstamp" y arranca en 2015, mientras la API de Bitstamp arranca en 2017-08.
- La v1 realmente cargada en TV no está en `ref/`: `simulate` con D apagada y cLong encendida replica sus números, pero no está verificado que sea idéntica.

### Próximos pasos (en orden)
1. **Fase 4: optimizar** por temporalidad con `docs/PROTOCOLO.md`, usando las decisiones ya fijadas (ventana desde 2017-01-01, un set por temporalidad, cLong como parámetro a evaluar). Falta construir el optimizador (grilla agregada entre monedas con `multiprocessing`, baseline aleatorio, mesetas, conteo de pruebas, holdout por monedas, semillas fijas) y definir el grupo de entrenamiento y el de holdout **antes de mirar resultados**. Escribir el set ganador en `params/*.json`, regenerar los Pine y llenar `candidates/<tf>.md`.
2. **Validar en TradingView** (sección 9; no hay Pine compilado todavía) y llevar `results/tv_log.md`.
3. Correr SOL en TradingView (no se hizo) y completar `docs/TV_BASELINES.md`.
4. Expectativa honesta: D no mostró ventaja en datos previos; si la optimización sale pobre, no implica que la strategy esté rota. Reportarlo tal cual.

## 9. Plan para el próximo agente: validar y calibrar en TradingView con Claude in Chrome

> Decisión del usuario (2026-10-20): **esta sesión NO tocó TradingView.** Pidió dejar documentado todo para que otro agente lo ejecute. Nada de esta sección fue probado: lo marcado "no verificado" hay que comprobarlo.

### 9.1 Dónde y qué
- **Gráfico del usuario:** layout guardado en su cuenta (plan gratis). **El link NO está en el repo porque es público: pedírselo al usuario** (no commitearlo).
- **Script cargado hoy:** "SQZ+RSI BT" (probablemente la strategy v1). Máx. 2 indicadores a la vez: uno es "Makroni" (**no se toca**), el otro es este slot. Para probar los scripts nuevos hay que **reemplazar ese slot**; no verificado si una strategy cuenta como indicador en el límite. **Preguntarle al usuario antes de borrar o reemplazar el script cargado** y antes de guardar scripts en su cuenta.
- **Captura que mandó** (probablemente ETH 4h; el símbolo no se ve, pero coincide con la base de ETHUSD 4h: +844,86 USD / +8,45%, DD 1.144,33 / 10,98%, 35/151, PF 1,147): el panel inferior es el **Strategy Tester** en inglés. Barra superior: rango de fechas (`Dec 31, 2023 — Oct 20, 2026`), capital (`10K USD`), `Default detalization`, `Script execution 1`, engranaje, alerta. Debajo: **Key stats** (Total PnL, Max drawdown, Profitable trades, Profit factor) y el gráfico **Performance** (Cumulative PnL, Buy and hold, Trades excursions, Run-ups and drawdowns). A la derecha, la lista de seguimiento. La UI a veces sale en español.

### 9.2 Cómo operar el navegador (no verificado)
1. `tabs_context_mcp` con `createIfEmpty: true` (en esta sesión no había grupo de pestañas propio); abrir el link del gráfico en una pestaña nueva. Si no hay sesión iniciada en ese Chrome, pedirle al usuario que la inicie (**nunca ingresar contraseñas**).
2. Cambiar símbolo: clic en la lista de seguimiento. Cambiar temporalidad: botón de la barra superior (muestra "D", "4h", "W") > "4 hours" / "1 day" / "1 week". Para saber qué feed es un símbolo (pendiente, ver 9.4), clic en el nombre del símbolo arriba a la izquierda.
3. Cargar un Pine: pestaña **Pine Editor** (abajo) > pegar el archivo de `pine/` > guardar/agregar al gráfico. Los errores de compilación salen en la consola del editor: **pegarlos tal cual en el log y decir si compiló o no.** El script unificado es el de más riesgo (ternarios por input, `table.new`).
4. Cambiar parámetros: engranaje del script > pestaña **Entradas** (nombres exactos en `params/*.json`; con el script unificado alcanza el desplegable "Preset" en `Auto / H4 / D1 / W1 / Manual`).
5. Leer resultados con `get_page_text` o `read_page` (Key stats) y capturas. La **lista de operaciones está virtualizada** (~10 filas, de la más reciente a la más vieja): hay que scrollear para bajarla entera. Sin export CSV.
6. Si la extensión falla 2 o 3 veces seguidas, **parar y reportar**; no insistir.

### 9.3 Regla madre: TradingView valida, no optimiza
El pedido original fue "calibrar hasta lograr el máximo rendimiento posible". Ojo: tocar parámetros a mano en TradingView mirando el Key stats es **optimizar sobre el mismo tramo que se mide** (H4 solo tiene 2,8 años, sin train/test): garantiza sobreajuste y viola `docs/PROTOCOLO.md`. Por eso:
- La búsqueda de parámetros va **en Python** (Fase 4, agregada entre monedas, con corte train/test fijado antes). TradingView solo **confirma candidatos** ya elegidos (`candidates/<tf>.md`).
- **Un set por temporalidad, nunca por moneda.** Ninguna prueba en TradingView puede terminar en parámetros por símbolo.
- **Toda corrida manual en TradingView cuenta como una prueba** y se anota en `results/tv_log.md` (plantilla incluida), incluidas las que salen mal. Si se prueban muchas variantes a mano, reportar el número y desconfiar más.
- "Máximo rendimiento" se interpreta como los criterios de `PROTOCOLO.md` sección 3 (PF 1,5 a 2,5, expectativa neta > 0,2R, 100 o más trades, sin depender de un solo trade), no como el PnL más alto. Si no hay ventaja, decirlo.

### 9.4 Tareas concretas que necesitan TradingView (en orden)
1. **BTC 1D, trades más viejos:** abrir la lista de operaciones de BTCUSD 1D, bajar hasta el final y anotar los ~15 primeros (lado, fechas, precios, PnL). Sirve para localizar los 2 trades de más del port (121 vs 119). Comparar con `simulate(load('bitstamp','BTC','1d',end='2026-10-20')).table()` (ver `src/sqzlab/calibrate.py`).
2. **Feed de ETHUSD:** el gráfico del usuario dice "Bitstamp" pero TV arranca en ago-2015 y la API de Bitstamp en 2017-08. Hipótesis a resolver (no hecho): TV puede estar mostrando historia de otro feed o índice anterior. Verificar qué dice exactamente el selector de símbolo y la fecha de la primera vela. No se usa ETH para calibrar.
3. **BTC 4h:** ya coincide (153/153); no hace falta repetir salvo que cambie el port.
4. **SOL:** correr 1D, 4h y 1W y agregar las filas a `docs/TV_BASELINES.md` (hoy no existen). Verificar antes que el script cargado siga siendo la misma versión (nombre y casillas de "Que probar").
5. **Verificar compilación** de `pine/{h4,d1,w1}/*.pine` y `pine/sqz_rsi_strategy_unified.pine`, en ese orden de menor a mayor riesgo; pegar errores tal cual.
6. Con el unificado, comprobar en 4h, 1D y 1W que el preset automático da **exactamente** los mismos números que el script de esa temporalidad y que el cartel muestra el preset correcto.
7. **Candidatos de la Fase 4:** cargar el set de `params/<tf>.json` (regenerar los Pine con `python -m sqzlab.genpine`), leer Key stats por símbolo del grupo de holdout y comparar 1 a 1 contra el port.

### 9.5 Restricciones y cuidado
- No es asesoría financiera ni operar: solo leer el Strategy Tester. No tocar alertas, no publicar scripts, no cambiar configuración de la cuenta, no tocar "Makroni". Cualquier guardado de scripts o cambio del layout, **confirmarlo antes con el usuario**.
- H4 en plan gratis arranca el 2023-12-31 (hora local UTC−3). Si se quiere historia larga hay que usar el port.
- Alternativa para chequear sintaxis sin TradingView (no probado): `hoox-pyne` (parser ANTLR + `pyne-lsp`) y PyneIDE (extensión de VS Code). Son reimplementaciones no oficiales: que pasen **no** es "compiló en TradingView".
