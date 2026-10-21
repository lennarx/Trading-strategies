# Protocolo de optimización y validación

Objetivo: máximo rendimiento **robusto** de la strategy SQZ+RSI en **H4, D1 y semanal** (mínimo), en muchas criptos, incluyendo el ajuste de los niveles de entrada. Regla madre: preferimos una estrategia modesta y robusta antes que una espectacular y sobreajustada.

## 1. Fases (en este orden; no saltear)

1. **Datos.** Velas 1d y 4h de BTC, ETH, SOL desde BingX (columnas `time_utc,open,high,low,close,volume`, UTC). 1W se construye resampleando 1d. Para calibrar BTC/ETH, conseguir también velas de Bitstamp (es lo que mira TradingView en las bases). Para el universo de optimización y el holdout por monedas, sumar más monedas con historia larga: Binance spot `<SIM>USDT` (BTC, ETH, BNB, LTC, XRP, ADA, LINK, DOGE, SOL) y Bitstamp (LTC, XRP, BCH, LINK, ADA, DOGE, XLM). Un script de descarga versionado en `src/sqzlab/fetch.py`. Si hay bloqueo de red, no lo esquives: reportalo y pedí el archivo.
2. **Calibración (puerta de entrada).** Reproducir con el port las filas de `docs/TV_BASELINES.md`: mismo número de trades (o diferencia explicada), PF y PnL similares, y coincidencia de fechas y precios de entrada/salida en los spot-checks. Documentar cada divergencia (semilla de EMA/RMA, cierre de vela, comisión, tamaño por equity con PnL abierto, modelo de reversión). **Sin calibración aprobada no se optimiza nada.** Primero A+B+C (lo que corre en TradingView), después se suma D.
3. **Completar el port a strategy v2**: señal D, toggles por lado, tamaño por riesgo, tope de apalancamiento, comisión 0,05%/lado. Verificar contra `ref/sqz_rsi_strategy_v2.pine`.
4. **Optimizar** por temporalidad con las reglas de la sección 2.
5. **Escribir el set ganador de cada temporalidad en `params/{h4,d1,w1}.json`** y regenerar con `python -m sqzlab.genpine`: `pine/{h4,d1,w1}/` (un script por temporalidad) y `pine/sqz_rsi_strategy_unified.pine` (presets automáticos con `timeframe.in_seconds()`). Más `candidates/<tf>.md`.
6. **Validar en TradingView** (sección 4).
7. **Reportar**: qué se probó, cuántas combinaciones, qué quedó, qué se descartó y por qué.

## 2. Qué se puede mover y cómo

Parámetros ("niveles de entrada"): `adxMin, pbBars, atrMult, minSqz, graceBars, needE200, needMom, invBars, cHot, cCold, cLook, cWin, cStopBars, cAtrMult, cMaxRisk, dvL, dvR, dvMin, dvMax, dAtrMult, dMaxRisk, riesgo %`, la configuración de squeeze (`bbLen, bbMult, kcLen, kcMult`), y qué señales y lados están encendidos. Variantes estructurales de stop y salida (otra EMA de salida, objetivos en R, trailing) se documentan aparte, una por una.

### Decisiones fijadas ANTES de ver cualquier resultado de optimización (2026-10-20)
- **Ventana de datos para optimizar: desde 2017-01-01.** BTC 2011-2014 (precios de 3 a 1.000 USD, saltos enormes) domina el resultado en USD y justo ahí está la diferencia sin explicar contra TradingView. Los datos viejos quedan **solo para calibrar**. D1: entrenar 2017-01-01 a 2023-12-31, validar 2024-2026. H4: walk-forward desde 2017-01-01. Semanal: agregado entre monedas.
- **Calibrar solo con BTC.** ETH 1D/4h no se usa para calibrar (ver HANDOFF: el feed de ETH de TradingView no está resuelto).
- **`cLong` (C compras) es un parámetro más a evaluar por temporalidad**, no una decisión previa. La calibración usa `cLong=True` porque así corre la v1 cargada en TradingView; `params/*.json` traen `cLong=false` (v2, porque C compras no mostró ventaja en SOL 1D ni en 6 monedas 1D). La grilla evalúa `{false, true}`; `params/*.json` se queda en `false` hasta que haya evidencia fuera de muestra a favor.
- **Velocidad:** `simulate` tarda ~0,2 s en BTC 4h de 2017 a hoy (20.000 velas), ~0,04 s en 1D y casi nada en 1W; el costo de la grilla es combinaciones × monedas × tiempo por corrida, repartido en los 16 núcleos de la PC con `multiprocessing`. No se acelera con numba hasta ver el tamaño real de la grilla; si hace falta, cachear indicadores por set de parámetros o numba, siempre sin cambiar resultados y con un test de regresión contra la calibración (`tests/test_calibration.py`).

### Decisiones fijadas ANTES de la primera corrida del optimizador (Fase 4, 2026-10-21)
Todo lo de abajo se escribió antes de correr `sqzlab.optimize`. Si algo cambia después, se anota como cambio y se cuenta.
- **Universo** (una sola fuente por moneda, la de historia más larga; nunca la misma moneda de dos fuentes). Train: BTC, ETH, XRP, LTC (Bitstamp), ADA, DOGE (Binance). Holdout: SOL, LINK, BNB (Binance), BCH, XLM (Bitstamp). SOL queda limpio (decisión del usuario). Los datos se cortan en 2026-10-20 (la vela del día en curso no está cerrada).
- **Warm-up:** los indicadores se calculan desde 2016-01-01 (D1/H4) o con todo el historial (W1, porque la EMA200 semanal necesita 200 semanas); solo cuentan los trades con **entrada ≥ 2017-01-01**. Los trades abiertos al final no cuentan.
- **Cortes:** D1 y H4: train = entradas 2017-01-01..2023-12-31; test = 2024-01-01..hoy (en las monedas train); holdout = monedas holdout (todo el período 2017+). H4 además: walk-forward informativo (ventanas train 3 años → test 1 año: 2017-19→2020, 2018-20→2021, 2019-21→2022, 2020-22→2023) y 2024-hoy como OOS final (= tramo que muestra TV). W1: train = monedas train, todo 2017+; holdout = monedas holdout; si el agregado de train da < 100 trades → "sin muestra" y W1 hereda el set de D1.
- **Función objetivo (train):** expectativa en R neto por trade, agregada entre monedas (R = PnL neto / riesgo en USD de cada trade). Restricciones: n ≥ 100 trades en la combinación final (30 por señal aislada en D1, 40 en H4), expectativa **recortada > 0**, mediana de la expectativa por moneda > 0. Se elige por **score suavizado de meseta** (promedio del punto y sus vecinos ±1 paso de la grilla; un vecino infeasible cuenta −1) calculado sobre la expectativa recortada, nunca por el pico.
- **Ajuste hecho tras ver SOLO la etapa 0 (referencia v2 en train D1, antes de cualquier búsqueda):** la referencia dio +0,57R de media pero con mediana −0,17R y un solo trade de +43R (DOGE 2021): la media la manejan pocos trades gigantes. Por eso la métrica de selección pasó a **expectativa recortada = media sin el 2% de mejores trades (al menos 1)**; "sin el mejor trade" se sigue reportando. Estos ajustes se aplican por igual a todas las temporalidades.
- **Pierna "viva":** una señal/lado aislado (con los defaults v2) con n ≥ 15 en train y expectativa > p95 del baseline aleatorio. Las que no, quedan apagadas en las etapas siguientes (apagadas, no quitadas). Si ninguna está viva, se buscan igual las "débiles" (expectativa > p50 del baseline) y el veredicto lo da solo el fuera de muestra.
- **Baseline aleatorio:** entradas en barras al azar con los mismos lados y la misma cantidad que la estrategia, stop = entrada ∓ k·ATR (k = mediana de la distancia real de stops en ATR), salidas iguales (stop intravela, cierre contra la EMA20), 500 réplicas en las etapas de búsqueda y 1000 en la final, semilla fija.
- **Test, holdout y OOS se miran UNA sola vez** por candidato final (etapa 5); el optimizador lo traba en el estado y avisa si se repite.
- **Se escribe `params/<tf>.json` solo si** el fuera de muestra (test + holdout) da expectativa > 0,2R, > p95 del baseline, ≥ 100 trades agregados, y sigue > 0 sin el mejor trade y recortada (sin el 2% de mejores). Si no, `params/*.json` quedan en v2 y el informe lo dice.
- **Conteo de pruebas:** 1 prueba = 1 combinación de parámetros evaluada (sobre todas las monedas del grupo). Lo lleva `results/opt_<tf>.md`.

Reglas obligatorias:
- **Un set de parámetros por temporalidad (H4, D1, W1), nunca por moneda.** El optimizador evalúa cada combinación sobre todas las monedas del grupo de entrenamiento a la vez (agregado) y devuelve UN set por temporalidad; prohibido guardar parámetros por símbolo (mataría el holdout por monedas y es sobreajuste disfrazado).
- **Corte train/test fijado ANTES de mirar resultados.** D1: entrenar hasta 2023-12-31, validar 2024-2026 (afinable, pero se fija antes). H4: ventanas rodantes (walk-forward) sobre el historial largo del port. Semanal: agregado entre monedas.
- **Holdout por monedas**: optimizar en un grupo y probar en otro que no participó.
- **Mesetas, no picos**: un parámetro vale si al moverlo ±20% el resultado sigue razonable. Descartar óptimos aislados.
- **Contar las pruebas** (combinaciones evaluadas) e informarlas; más pruebas, más desconfianza.
- **Baseline aleatorio** de entradas con el mismo manejo de stops/salidas para ver si hay ventaja real.
- **Sin el mejor trade** el resultado debe seguir positivo.
- Medir en **R neto de comisión** (0,05%/lado, 0,10% ida y vuelta) y retorno por trade, no en USD acumulados (BTC 1D tiene saltos enormes en 2013-2014).
- Semillas fijas, todo reproducible con un comando.

## 3. Criterio de éxito (convenciones de uso común, no ley)

Fuera de muestra: **PF entre 1,5 y 2,5; expectativa neta > 0,2R; ≥100 trades agregados; ganancia total ≥ 2 a 3 veces el drawdown máximo; sin depender de un solo trade; resultados parecidos entre monedas.** PF > 3 es sospechoso hasta demostrar lo contrario. Semanal: nunca se juzga una moneda sola.

Si algún timeframe o señal no tiene ventaja, decirlo claro: es información, no un fracaso.

## 4. Ciclo de validación con TradingView

El port **no** es TradingView. Un candidato solo cuenta si TradingView lo confirma en el tramo reciente (para H4, desde 31-dic-2023; para D1 y semanal, todo el historial que muestre).

Por cada candidato final, escribir en `candidates/<tf>.md` (`h4`, `d1`, `w1`) una tabla con los parámetros usando los **nombres EXACTOS de las casillas y campos de la pestaña "Entradas"** del script (grupos "Que probar", "Backtest", "Squeeze", "RSI", "Senal A y base", "Senal B (squeeze)", "Senal C (reversion)", "Senal D (divergencia)", "Volumen (opcional)"), más el resultado esperado del port para ese mismo tramo y por símbolo.

Pasos: (1) cargar `pine/<tf>/sqz_rsi_strategy_<tf>.pine` (y después el unificado, para comprobar que el preset automático da lo mismo que el script de esa temporalidad) en TradingView; (2) **decir si compiló o no** y pegar cualquier error tal cual; (3) leer "Estadísticas clave" y el "Punto de referencia"; (4) comparar 1 a 1 contra el port; (5) corregir el port ante diferencias.

Si Claude Code no puede usar Claude in Chrome en su entorno (no verificado), pedirle al usuario que cargue los parámetros y mande capturas, **diciéndole exactamente dónde**: los parámetros se tipean en el engranaje del script (pestaña **Entradas**); "Estadísticas clave" está arriba del panel Strategy Tester (abajo en el gráfico); comprar-y-mantener está en la pestaña **Punto de referencia**.

## 5. Límites y recordatorios

- Plan gratis de TradingView: 2 indicadores, sin export de CSV, historial intradía limitado (H4 desde 31-dic-2023).
- Esto es validación técnica de una estrategia, no asesoría financiera ni decisión por el usuario.
- Si los resultados son pobres, decilo claro y proponé qué probar a continuación, sin vender humo.
