# Plan Fase 8: "estrategia operable" (SQZ+RSI Lab) — guardar como `docs/FASE8_PLAN.md`

> Se ejecuta con `/goal` (texto en `GOAL_fase8.txt`). El repo es la única memoria. Rioplatense, bullets ≤5 y ≤350 palabras + conclusión ≤50, gracioso, no inventar, todas las correcciones juntas, decir si un Pine compiló en TV. Sin commit ni push.

## 0. Por qué hay Fase 8 (diagnóstico, con los números de `results/fase7.md`)
La Fase 7 dio NO SIRVE, pero mirando las tablas aparecen tres errores de diseño **nuestros**, no del mercado:
1. **Universo equivocado.** Z2/Z3 eran monedas viejas elegidas por orden alfabético (Z3 = fan tokens ACM, ASR, ATM, BAR, etc.). El buy&hold equiponderado de esos grupos dio negativo en 2024-hoy. Ningún sistema solo-largo gana plata comprando monedas que se van a cero. El paper opera las **20 más líquidas, con universo dinámico**.
2. **R1 no era el paper.** Reglas reales (según el resumen de CXO Advisory del paper de Zarattini, Pagani y Barbon, 2025):
   - Salida por **trailing stop** = máx(stop previo, punto medio entre el máximo y el mínimo de cierres del lookback); nosotros usamos "cierre < mínimo de N/2".
   - Tamaño **re-dimensionado a diario**; nosotros lo fijábamos al entrar.
   - **Sin cupo de 6 monedas ni tope bruto 1x**; tope 200%.
   - Universo: monedas con ≥ 1 año listadas y volumen diario mediano ≥ 2 M USD en los 30 días previos.
3. **Criterios que castigan al seguimiento de tendencia por construcción** ("ninguna moneda > 40%" con 6 monedas; el propio informe lo admite).

Aun así, el R1 "lisiado" en Z2 H4 le ganó al Calmar de BTC: 0,63 contra 0,48, con CAGR 37%. Hay algo ahí.

## 1. Regla madre de esta fase: CERO parámetros elegidos por nosotros
Todos los parámetros salen del paper. No hay grilla y no hay optimización. Eso es lo que hace creíble un backtest sobre datos ya vistos.
- **Contaminación declarada:** ya vimos el R1 lisiado en Z2/Z3/pool. Por eso el juez principal es el **OOS real post-paper** (sección 4): el paper usa datos hasta marzo de 2025, así que de abril de 2025 a hoy no lo vio nadie.

## 2. Estrategia (R1-fiel). Escribirla en `docs/PROTOCOLO.md` ("Decisiones fijadas ANTES de la Fase 8") ANTES de bajar datos o correr nada
- **Datos:** Binance spot, **todos** los pares USDT diarios, **incluidos los deslistados** (data.binance.vision guarda los archivos mensuales de klines; **verificar** que incluya deslistados; si no, declarar el sesgo de supervivencia y seguir). Excluir stablecoins, envueltos y apalancados (*UP/*DOWN/*BULL/*BEAR). Si la red bloquea algo: reportar y pedir el archivo, no esquivar.
- **Universo dinámico (diario, sin lookahead):** elegibles = ≥ 365 días de historia y mediana del volumen en USD de los 30 días previos ≥ 2 M. Se toman las **top 20 por esa mediana** (empates por orden alfabético). Si una moneda sale del top 20, su posición se cierra al cierre siguiente.
- **Señal (ensamble):** lookbacks N ∈ {5, 10, 20, 30, 60, 90, 150, 250, 360} días. Por moneda y por N:
  - Entra largo al cierre cuando close > máximo de los cierres de las N velas **previas**.
  - Trailing stop diario = máx(stop de ayer, (máx + mín de cierres de N)/2).
  - Sale al cierre si close < stop.
- **Tamaño:** peso de moneda = (sub-señales abiertas / 9) × min(2, 0,25 / vol anualizada de 90 días de retornos diarios). Cartera = suma de pesos entre las 20 monedas; si el bruto total supera **2,0**, escalar todo a 2,0 (supuesto nuestro: el paper habla de tope 200% por posición; declarar la diferencia). Re-balanceo diario solo si el peso cambia > 20% relativo (banda anti-costos; supuesto nuestro, declarado).
- **Costos:** 0,10% por lado + slippage 0,05% por lado en cada cambio de peso. Informar también con 0,25% por lado.
- **SQZ+RSI:** no entra en las decisiones de esta fase. Queda como contexto visual en el Pine (se apaga, no se borra).

## 3. Temporalidades
- **D1 = la estrategia** (es lo que tiene evidencia).
- **H4 = conversión declarada, sin tocar nada:** N × 6, vol de 90 días = 540 velas, anualización √(6×365). Se informa aparte y es secundaria.
- **W1:** no se opera (no hay muestra). Se informa solo como contexto.

## 4. Ventanas y criterio SIRVE (fijado ANTES)
- **Ventana A:** 2018-01-01 a hoy (informativa: el paper también la usó).
- **Ventana B (juez):** 2025-04-01 a la última vela cerrada (OOS real: posterior a los datos del paper y nunca mirada con R1-fiel).
- **SIRVE (D1)** si en **A y en B**, con curva marcada a mercado:
  1. CAGR neto > 0.
  2. Sharpe diario anualizado > Sharpe del buy&hold de BTC en la misma ventana.
  3. DD máx. < DD máx. del buy&hold de BTC.
  4. Ninguna moneda aporta > 50% de la ganancia.
  5. En A, sigue con CAGR > 0 sacando el mejor mes.
- Si B tiene menos de 30 operaciones cerradas: **SIN MUESTRA EN B**; el veredicto final pasa al forward/demo (sección 6).
- Informar siempre al lado: buy&hold BTC, buy&hold equiponderado del top 20 dinámico, y el R1 lisiado de la Fase 7, como contraste.

## 5. Implementación sin errores
- Módulos nuevos (`universe_dyn.py`, `r1fiel.py`, `pf8.py`, `fase8.py`). No tocar `simulate` ni la calibración: test de regresión contra el golden.
- Tests obligatorios:
  - Universo sin lookahead: el top 20 del día t usa solo datos ≤ t−1.
  - Señal y trailing contra un cálculo a mano.
  - Vol-target y tope 2,0 contra un cálculo a mano.
  - Costos en cada cambio de peso.
  - Equity marcada a mercado en un caso sintético.
  - Monedas deslistadas: cierre forzado en la última vela.
- **Subagente revisor** que no vio el trabajo: audita lookahead, supervivencia, costos, sizing y anualización ANTES de mirar B. Corregir y anotar.
- **Una sola mirada a B**, trabada en estado (`--stage look`, sin `--force`).

## 6. Si SIRVE (o SIN MUESTRA EN B)
1. `params/r1fiel.json` y `python -m sqzlab.signals --strategy r1fiel` → JSON con **pesos objetivo por moneda** para la última vela cerrada (contrato nuevo en `docs/BOT.md`; el bot de BingX re-balancea a esos pesos).
2. Pine: `genpine.py` agrega la señal E fiel (entradas, trailing y nivel del stop) como capa visual por moneda en el script unificado. TradingView no puede mostrar la cartera (es multi-moneda). Validar en TV que entradas y stops coinciden con el port en BTC, ETH y SOL D1, por fechas.
3. Forward test nuevo (`results/forward_r1fiel.md`). Recomendación al usuario: **demo de BingX 8 semanas** antes de plata real, y después como máximo el capital que ya definió para probar.

## 7. Si NO SIRVE
Decirlo con números, sin vueltas. Proponer UNA sola cosa: forward en demo. Nada de grillas nuevas.

## 8. Cierre
- `results/fase8.md` con: reglas, diferencias con el paper, tablas A/B vs referencias, costos 0,10/0,25, veredicto.
- HANDOFF sección 8, `docs/BOT.md` y `results/tv_log.md` actualizados.
