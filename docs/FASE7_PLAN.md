# Plan Fase 7 v2: "que la estrategia SIRVA" (SQZ+RSI Lab) — guardar como `docs/FASE7_PLAN.md`

> **Modo /goal:** este plan se ejecuta con el comando `/goal` de Claude Code. Dentro del /goal: (a) cualquier "PARÁ y reportá" de este plan significa: anotar el bloqueo en `docs/HANDOFF.md` sección 8 y terminar con un mensaje al usuario explicando qué tiene que hacer; (b) la validación en TradingView (secciones 5.3 y 5 ter) va ADENTRO del /goal, con Claude in Chrome como en la Fase 5, y el usuario ya dio el permiso en el texto del /goal (no se le vuelve a preguntar, pero se respetan los límites que pone ahí); (c) la meta es correr el protocolo y reportar un veredicto honesto, NO forzar que algo pase.

Estás en el repo "SQZ+RSI Lab" (GitHub `lennarx/Trading-strategies`). El repo es la única memoria: no dependas de otras conversaciones.

## 0. Antes de tocar nada
1. Leé enteros y en orden: `CLAUDE.md`, `docs/HANDOFF.md` (secciones 0 y 8 sobre todo), `docs/PROTOCOLO.md`, `docs/TV_BASELINES.md`, `results/tv_log.md`, `results/confirm_*_z1.md`, `results/varsearch_*.md`, `results/portfolio_*.md`.
2. `git status` y `python -m pytest -q` (con `PYTHONPATH=src`). Si los tests no están verdes, o el HANDOFF no coincide con el código o con la sección 1 de este prompt, **PARÁ y reportá** (gana la realidad).
3. Reglas de `CLAUDE.md` vigentes: rioplatense informal, bullets ≤5 y ≤350 palabras + conclusión ≤50, gracioso, no inventar, todas las correcciones juntas, decir siempre si un Pine compiló en TradingView. Commit/push solo si el usuario lo pide.

## 1. Estado al 2026-10-21 (verificalo)
- H4: `params/h4.json` optimizado (OOS Fase 5 +0,39R) pero **Z1 NO CONFIRMA** (+0,079R, recortada −0,089R).
- D1: `params/d1.json` = v2, **Z1 NO CONFIRMA** (+0,136R, recortada −0,013R). W1: sin muestra (n=43).
- V1-V4 (trailing ATR, break-even, salida EMA55, régimen BTC) no pasaron en train. Z2 (ALGO, AVAX, ETC, ICP, TRX, VET) **virgen**. Forward test serie 1 corriendo (hash congelado, entradas ≥ 2026-10-22).
- Lo que SÍ funcionó en todo lo medido: **A largos y B largos** (H4 train aislados: +0,80R y +0,95R). Lo flojo: cortos, C y D.
- Cartera 6.3, tramo 2024-hoy (optimista por universo): H4 ≈ CAGR 25%, DD 21% vs BTC buy&hold CAGR 26%, DD 53%.

## 2. Qué cambia y por qué (el usuario quiere que la estrategia SIRVA, no un "no sirve")
"Sirve" NO es un backtest lindo sobreajustado (eso pierde plata en vivo y es justamente "no sirve"). Se reorienta la estrategia hacia lo que tiene **evidencia publicada en cripto** y hacia lo que ya funcionó en nuestros datos:
- **Momentum de series de tiempo / seguimiento de tendencia** tiene evidencia fuerte en cripto (Liu & Tsyvinski, "Risks and Returns of Cryptocurrency"; estudios posteriores encuentran evidencia fuerte de time-series momentum y débil de cross-sectional). Varios trabajos encuentran exceso de retorno en carteras **solo largas** pero no en largo-corto.
- Zarattini, Pagani y Barbon (2025, "Catching Crypto Trends", SFI Research Paper 25-80): ensamble de canales de Donchian con varios lookbacks + tamaño por volatilidad, solo largo, top 20 monedas, Sharpe > 1,5 neto (dato de los autores, **no verificado por nosotros**). Reglas reportadas: entrada cuando el cierre diario supera el máximo de cierres de N días, N ∈ {5, 10, 20, 30, 60, 90, 150, 250, 360}; posición re-dimensionada a 25% de volatilidad anual objetivo (25% / vol anualizada de 90 días), apalancamiento tope 200%; cartera = promedio del ensamble. Leé el paper si podés bajarlo (si la red bloquea, reportalo, no lo esquives) y anotá cualquier diferencia con este resumen.
- Seguimiento de tendencia vive de **pocas operaciones gigantes** (colas). Por eso la métrica "expectativa recortada" (sin el 2% mejor) castiga por construcción a este tipo de estrategia. **Cambio declarado** (justificado por literatura, no por resultados): la selección pasa a métricas de **cartera**; la recortada se sigue reportando.
- Libro del usuario "Trading en la zona": operar a favor de la tendencia del marco mayor y usar otros marcos como filtro.

## 3. Primero se escribe, después se implementa
Antes de implementar o correr NADA: agregá en `docs/PROTOCOLO.md` la sección **"Decisiones fijadas ANTES de la Fase 7 (fecha)"** con TODO lo de esta sección (incluidos los cambios declarados de métrica y de uso de Z2). Recién después implementás.

### 3.1 Definición de "SIRVE" (fijada antes; es el criterio de éxito)
Sobre una **cartera** (todas las monedas del grupo, sizing de 3.2, tope de riesgo abierto 5%, máx. 6 posiciones como en 6.3, costos 0,05%/lado + slippage 0,05%/lado), en el grupo evaluado:
1. CAGR neto > 0 y **Calmar (CAGR / DD máx.) > Calmar del buy&hold de BTC** y > Calmar del buy&hold equiponderado de las monedas del grupo, en el mismo tramo.
2. DD máx. ≤ 50% del DD del buy&hold de BTC.
3. n ≥ 100 trades; sigue con CAGR > 0 sin el mejor trade; mediana por moneda del PnL > 0; ninguna moneda aporta > 40% de la ganancia.
4. Equity con curva cerrada **y** marcada a mercado (no solo realizada).

### 3.2 Palancas (todas apagadas por defecto en `simulate`; calibración intacta)
- **P1, sesgo largo:** cortos apagados, o cortos solo si la temporalidad mayor está bajista (ver P4). Opciones: {off, solo-con-TF-mayor-bajista}.
- **P2, señal E nueva, ensamble de Donchian** (del paper): entrada larga cuando el cierre supera el máximo de cierres de N velas. Lookbacks en días del paper {20, 60, 150, 250} (subconjunto fijo, sin optimizar) convertidos a velas de cada TF (H4 ×6; W1 ÷7 redondeado, mínimo 4). Cada lookback es una "sub-señal" y la exposición es el promedio del ensamble. Stop/salida de E: cierre bajo el mínimo de cierres de N/2 velas (salida de Donchian clásica).
- **P3, salida de A y B por trailing de Donchian** en vez de la EMA20 (corta ganadoras): salida si cierre < mínimo de cierres de M velas, M ∈ {10, 20, 40} (en velas del TF). Distinto de V1 (V1 sumaba trailing a la salida EMA20, no la reemplazaba).
- **P4, filtro de tendencia del TF mayor de la MISMA moneda:** largos solo si el cierre de la última vela CERRADA del TF mayor > su EMA(N). D1→W1 con N ∈ {10, 20, 40}; H4→D1 con N ∈ {50, 100}; W1 sin filtro. Semántica exacta = Pine `request.security(syminfo.tickerid, tfMayor, close[1] > ta.ema(close, N)[1], lookahead=barmerge.lookahead_on)` (H4 del día D usa D−1; D1 de la semana W usa W−1).
- **P5, sizing:** {riesgo fijo 1% por trade (actual), volatilidad objetivo 25% anual por posición con vol de 90 días y tope 2x (paper)}.

Grilla total por TF ≈ 2 (P1) × 2 (P2 on/off) × 4 (P3: EMA20 o M∈{10,20,40}) × (1 + |N| de P4) × 2 (P5). Contá exacto, reportalo y sumalo a los totales acumulados. **No agregues palancas después de mirar.**

### 3.3 Referencias obligatorias (se reportan siempre al lado)
- **R0:** set vigente (`params/<tf>.json`) en la misma cartera.
- **R1:** réplica del paper SIN SQZ+RSI (Donchian ensamble completo con los 9 lookbacks, solo largo, vol 25%, tope 2x), sin optimizar.
- Buy&hold BTC y buy&hold equiponderado.

### 3.4 Selección y validación
- **Train:** monedas train (BTC, ETH, XRP, LTC, ADA, DOGE), 2017-01-01..2023-12-31. Elegir por **meseta** del Calmar de cartera (promedio del punto y sus vecinos ±1 paso), con las condiciones 3.1.3 cumplidas en train. Nunca por el pico.
- **Validación (una sola mirada por TF, trabada en estado):**
  - Z2 (cambio declarado: deja de estar reservado solo a la 6.4, que no tuvo sobrevivientes).
  - **Z3 nuevo:** Binance spot USDT, monedas nunca usadas, primera vela 1D ≤ 2021-10-20, sin stablecoins/envueltos/apalancados, mismos descartes por huecos que la 6.1, orden alfabético, hasta 24. Regla fijada antes de bajar; registrar descartes. Red bloqueada → reportar y pedir archivo.
  - Tramo 2024-hoy en todas las monedas.
- **Veredicto "SIRVE" por TF** si cumple 3.1 en Z2 **y** en Z3. Si el candidato no supera a R1 en Z2+Z3, decirlo explícito.
- **W1:** con P2 en W1 y pooling sobre todas las monedas no-train como validación; si n < 100 → "sin muestra" y W1 se usa solo como filtro (P4) de D1.

### 3.5 Plan B honesto (fijado antes, para que haya entregable útil)
Si ningún candidato SQZ+RSI cumple 3.1 pero **R1 sí** (en Z2 y Z3), el entregable es: el script unificado con la **señal E (Donchian) como motor principal** y sizing por volatilidad, y A/B/C/D + SQZ/RSI como contexto visual (no se borra nada: se apaga). Si ni R1 cumple, decirlo con números y esperar al usuario. **Prohibido** aflojar 3.1 después de mirar.

## 4. Implementación sin errores
- Todo apagado por defecto. Test de regresión: `simulate` con defaults = trades idénticos antes/después.
- Tests: sin lookahead (truncar datos en t y verificar que la señal en t no cambia; P4 usa D−1/W−1); Donchian contra cálculo a mano; vol-target (tamaño = 0,25 / vol anual 90d, tope 2x) contra cálculo a mano; equity marcada a mercado contra un caso sintético.
- Cartera: costos en cada entrada/salida y en cada re-balanceo de tamaño si P5 re-dimensiona.
- **Antes de mirar Z2/Z3:** subagente revisor que NO haya visto el trabajo busca lookahead, fuga train→test, errores de costos/sizing/conteo. Corregir y anotar ANTES de mirar.
- Pine (solo si algo SIRVE): `genpine.py` inyecta señal E, salida Donchian, filtro P4 y sizing por volatilidad (`strategy.entry` con `qty` calculada). Un solo script (plan gratis, 2 indicadores, uno es Makroni). Nunca editar `.pine` a mano.

## 5. Si algo SIRVE
1. Escribir `params/<tf>.json`, regenerar Pine, tests verdes.
2. Avisar que el forward test arranca **serie nueva** (cambia el hash).
3. TradingView (HANDOFF sec. 9): **pedir permiso** antes de tocar su gráfico; comparar port vs TV en SOL, BTC, ETH; anotar en `results/tv_log.md`; decir si compiló. Si le pedís hacer algo en una UI, decile exactamente dónde está.

## 5 bis. Señales para el bot del usuario (siempre, haya o no candidato)
El usuario quiere pasarle las señales a un bot de trading propio. Su TradingView es plan gratis, que no manda webhooks, así que **el bot NO debe depender de alertas de TradingView**.
- Crear `python -m sqzlab.signals --tf h4|d1|w1 --symbols ... [--source bingx]`: baja velas (reusar `fetch.update_csv`), descarta la vela en curso (como `forward.closed_only`) y devuelve JSON por moneda con la señal de la **última vela CERRADA**: `{symbol, tf, bar_time_utc, action: long|short|exit|none, kind: A|B|C|D|E, entry_ref, stop, size_pct_equity, params_hash}`. Es la misma lógica de `simulate` y de `params/<tf>.json`: un solo motor, cero duplicación.
- **Sin repintado por diseño:** una señal emitida para una vela cerrada no cambia nunca después. Test: correr con datos hasta t, guardar las señales; correr con datos hasta t+50 y verificar que las señales ≤ t son idénticas. Test de que coincide con los trades de `simulate`.
- Documentar en `docs/BOT.md` el contrato del JSON y cómo llamarlo cada cierre de vela (cron). No tocar el código del bot (está en otro repo); solo el contrato.

## 5 ter. TradingView
La validación en TradingView (sección 5.3) se hace sobre el entregable final, sea el candidato o el plan B, siempre con permiso previo del usuario. Si nada sirve, igual se hace sobre el set vigente para dejar asentado que el Pine coincide con `sqzlab.signals`.

## 6. Cierre
- Informe `results/fase7.md`: palancas, grillas, pruebas por TF y totales acumulados, miradas a Z2/Z3, tablas train/Z2/Z3/2024-hoy vs R0, R1 y buy&holds, veredicto por TF.
- Actualizar `docs/HANDOFF.md` sección 8. Respuesta final con el formato del usuario, avisando si omitiste algo importante. No es asesoría financiera.
