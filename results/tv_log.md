# Log de pruebas en TradingView (cada corrida manual cuenta como una prueba)

Reglas: un set por temporalidad, nunca por moneda; anotar también lo que sale mal; Pine "compiló" solo si se probó en TradingView.

| # | Fecha | Script / versión | Preset o params (archivo y commit) | Símbolo | TF | Rango | Compiló (sí/no + error) | Trades | PnL USD | PF | DD | Ganadoras | Port (mismos números) | Notas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-21 | pine/h4/sqz_rsi_strategy_h4.pine ("SQZ+RSI BT H4") | params/h4.json OPTIMIZADO (sin commit) | ETHUSD (Bitstamp) | 4h | 2023-12-31 a 2026-10-20 | **SI** compiló (pegado en Pine Editor, "Add to chart", sin errores) | 25 | +512,16 | 1,487 | 401,80 | 10/25 | 25 / +512,25 / PF 1,488 / DD 384,77 / 10 | OK |
| 2 | 2026-10-21 | idem H4 | idem | BTCUSD (Bitstamp) | 4h | idem | si | 25 | +317,29 | 1,252 | 739,17 | 9/25 | 25 / +317,39 / PF 1,252 / DD 739,07 / 9 | OK |
| 3 | 2026-10-21 | idem H4 | idem | SOLUSDT (Binance) | 4h | idem | si | 29 | +2143,50 | 3,336 | 565,15 | 12/29 | 29 / +2143,79 / PF 3,336 / DD 532,64 / 12 | OK (el DD de TV no es igual al del port: ya se sabia) |
| 4 | 2026-10-21 | pine/sqz_rsi_strategy_unified.pine ("SQZ+RSI BT AUTO") | presets desde params/*.json | SOLUSDT (Binance) | 4h | idem | **SI** compiló | 29 | +2143,50 | 3,336 | 565,15 | 12/29 | = fila 3 (preset H4 automatico) | Identico al script H4 |
| 5 | 2026-10-21 | idem unificado | idem | SOLUSDT (Binance) | 1D | 2020-08-10 a 2026-10-20 | si | 44 | +1501,18 | 2,131 | 417,78 | 19/44 | 44 / +1495,89 / PF 2,134 / DD 362,69 / 19 | OK (preset D1 automatico) |
| 6 | 2026-10-21 | idem unificado | idem | SOLUSDT (Binance) | 1W | 2020-08-09 a 2026-10-18 | si | 5 | -30,01 | 0,639 | 92,73 | 2/5 | 5 / -29,99 / PF 0,639 / DD 66,48 / 2 | OK (preset W1 automatico) |
| 7 | 2026-10-21 | pine/w1/sqz_rsi_strategy_w1.pine ("SQZ+RSI BT W1") | params/w1.json (v2 sin optimizar) | SOLUSDT (Binance) | 1W | idem | **SI** compiló | 5 | -30,01 | 0,639 | 92,73 | 2/5 | = fila 6 | OK |
| 8 | 2026-10-21 | pine/d1/sqz_rsi_strategy_d1.pine ("SQZ+RSI BT D1") | params/d1.json (v2 sin optimizar) | SOLUSDT (Binance) | 1D | idem | **SI** compiló | 44 | +1501,84 | 2,131 | 417,78 | 19/44 | = fila 5 | La diferencia de $0,66 con la fila 5 es PnL abierto: el precio se movio entre lecturas |

Notas de las corridas del 2026-10-21 (hechas con Claude in Chrome, plan gratis, ver HANDOFF sec. 8):
- Para compilar hubo que sacar "SQZ+RSI BT" (la v1 cargada) del grafico: el plan gratis admite 2 indicadores y uno es Makroni. Esa v1 **no estaba en "My scripts"** (solo vivia en el layout). La restauré con "Deshacer" del grafico (ETHUSD 4h con su "SQZ+RSI BT"); verificado a ojo comparando la leyenda, no contra el codigo. Los scripts de prueba **no se guardaron** en la cuenta ("Untitled script" en el editor).
- Los scripts de la fila 1 a 8 se pegaron por portapapeles; las 4 versiones generadas compilan.
- Cuenta de pruebas manuales: 8 corridas, todas de verificacion de un set ya elegido en Python (ninguna se uso para tocar parametros).

## Tanda de la Fase 6.6 (2026-10-21, Claude in Chrome, plan gratis; el usuario autorizó reemplazar el slot de "SQZ+RSI BT" y NO guardar scripts en la cuenta)

| # | Script / versión | Símbolo | TF | Compiló | Resultado TV | Port (mismos números) | Notas |
|---|---|---|---|---|---|---|---|
| 9 | pine/sqz_rsi_senales_unified.pine (indicador "SQZ+RSI+SIG AUTO") | ETHUSD (Bitstamp) | 4h | **SI** compiló (pegado en Pine Editor, "Add to chart", sin errores) | corre; cartel **"Preset: H4"** | n/a (indicador) | primera vez que se prueba un indicador generado. `table.new` en un indicator anduvo |
| 10 | idem indicador | SOLUSDT (Binance) | 4h | si | carteles con SL de 7 señales B (fechas UTC de la vela de entrada): 8-ago L 73,74; 14-ago S 76,19; 19-ago L 75,75; 2-jun S 81,27; 6-may L 85,11; 2-abr S 83,37; 25-mar L 89,07 | port H4: stops 73,74 / 76,195 / 75,755 / 81,265 / 85,105 / 83,365 / 89,075 | **7 de 7 coinciden**; las X naranjas de salida del indicador caen donde sale el port (ej. 7-jun) |
| 11 | idem indicador | SOLUSDT | 1D | si | carteles: C venta SL 84,68 (11-jul), B venta SL 74,91 (1-ago), B compra SL 75,97 (21-ago), C venta SL 124,92 (7-oct) | port D1: 84,677 / 74,910 / 75,970 / 124,923 | **4 de 4 coinciden**. Además el indicador marca una B compra (SL 105,07, fines de sep) que el port NO toma porque la strategy ya estaba larga (A larga del 18-sep): diferencia esperada. **No verificado** el cartel de la A larga del 18-sep (se tapaba con otros) |
| 12 | idem indicador | SOLUSDT | 1D y 1W | si | cartel **"Preset: D1"** en 1D y **"Preset: W1"** en 1W | n/a | cartel verificado en los 3 presets |
| 13 | pine/h4/sqz_rsi_strategy_h4.pine (ya compilado en la tanda 1, se re-pegó) | LINKUSDT (Binance) | 4h | si | 35 trades, −762,39 (−7,62%), PF 0,55, 9/35, DD 882,75 | 35 / −761,80 / PF 0,550 / 9 / DD 793,81 | OK (DD de TV ≠ port: ya sabido) |
| 14 | idem H4 | BNBUSDT (Binance) | 4h | si | 40 trades, +1.277,04, PF 1,765, 17/40, DD 639,92 | 40 / +1.277,36 / PF 1,765 / 17 / DD 583,54 | OK |
| 15 | idem H4 | BCHUSD (Bitstamp) | 4h | si | 24 trades, −438,98, PF 0,653, 5/24 | 24 / −438,70 / PF 0,653 / 5 | OK (leído con el buscador de elementos, no con el texto completo) |
| 16 | idem H4 | XLMUSD (Bitstamp) | 4h | si | 23 trades, −641,59, PF 0,422, 5/23, DD 724,42 | 23 / −641,00 / PF 0,422 / 5 / DD 681,96 | OK (idem lectura) |
| 17 | pine/d1/sqz_rsi_strategy_d1.pine ("SQZ+RSI BT D1", se pegó y se actualizó sobre la H4 con "Update on chart") | BTCUSD (Bitstamp) | 1D | si | rango 17-ago-2011 a 20-oct-2026: **113 trades**, +65.954,74, PF 4,872, 42/113, DD 2.846,52 | **115** / +59.515,80 / PF 4,907 / 43 / DD 2.526,36 | **NO coincide: el port tiene 2 trades de más** (misma diferencia que con la v1). Ver "BTC 1D: dónde está la diferencia" abajo |

**BTC 1D: dónde está la diferencia (lista de operaciones de TV ordenada ascendente, trades 1 a 32 leídos; port con params/d1.json):**
- TV y port coinciden (lado, fecha de entrada y salida) en los primeros 32 trades **salvo tres puntos, todos en 2012 y 2016 (precios de 5 a 700 USD):**
  1. **2012-04-07 A corta (entrada 4,70, salida 11-abr): la toma el port, TV NO.**
  2. **2012-05-31: TV entra una B larga (sale 19-ago, +1.240,04); el port entra la B larga el 2012-07-09** (misma salida 19-ago).
  3. **2016-01-07 A larga (entrada 457,00, salida 12-ene): la toma el port, TV NO** (TV pasa del trade 22, 26-nov-2015 a 26-dic-2015, directo al 23, entrada 13-feb-2016).
- Eso explica los 2 trades de más (115 vs 113). **Causa NO identificada:** hipótesis (no verificada) = diferencias de OHLC entre la API de Bitstamp y el historial de TradingView en esas velas, o un borde de ADX/EMA con datos viejos. Mintick ya estaba descartado. No bloquea la optimización (entradas desde 2017) pero 2 de las 3 diferencias son en señales A.
- Cuenta de pruebas manuales: tanda 6.6 = 9 corridas (filas 9 a 17). Total desde la Fase 5: 17. Ninguna se usó para tocar parámetros.
- Gráfico del usuario: se sacó "SQZ+RSI BT" (con permiso), se probó, y se restauró con "Deshacer" (queda ETHUSD 4h con "SQZ+RSI BT" en su panel, **verificado a ojo**; el layout muestra cambios sin guardar). No se guardó ningún script en la cuenta.


## Tanda de la Fase 7 (2026-10-21, ~21:50 a 22:00 UTC-3, Claude in Chrome, plan gratis; permiso dado en el /goal: sacar/cargar scripts, cambiar símbolo/TF, guardar el script final sin publicar)

**Entregable validado = el set vigente** (ni H4, ni D1, ni W1 tuvieron candidato que SIRVA y R1 tampoco: `params/` sin cambios). Script: `pine/sqz_rsi_strategy_unified.pine` (24.992 caracteres, regenerado por `genpine`, sin diferencias con el commit). **Estado inicial del gráfico:** layout "Sin nombre" (`/chart/kPZnzVWr/`), BTCUSD 4h Bitstamp, solo el indicador demo de Makroni (el slot de la strategy estaba libre; la "SQZ+RSI BT" v1 ya no estaba). Para el Pine Editor se pisó el borrador "Untitled script" que ya estaba abierto (372 líneas, sin guardar, restos de la sesión anterior).

| # | Script | Símbolo | TF | Compiló | TV (Key stats, lectura ~21:52-21:58 UTC-3) | Port (`simulate` + `params/<tf>.json`, mismos datos y tramo) | Comparación |
|---|---|---|---|---|---|---|---|
| 18 | unificado ("SQZ+RSI BT AUTO") | BTCUSD 4h | 4h | **SI** compiló: pegado en el Pine Editor, "Add to chart", sin errores, aparece en el gráfico y en el Strategy Tester | 25 trades, 9/25 ganadoras, PnL total +370,08 (incluye 1 abierta), PF 1,249, DD 757,82; GP 1.577,33 / GL 1.263,04 | 25 cerrados, 9 ganadoras, +317,39 cerrado; abierta B larga +55,77 al precio vivo (84.170) menos 3,01 de comisión = **+370,15**; PF 1,252; GP 1.577,33 / GL 1.259,94 | **Coincide.** 0,07 USD en el total; la diferencia de GL (3,10) es la comisión de entrada de la posición abierta (TV la suma a la pérdida bruta) |
| 19 | idem | BTCUSD 1D | 1D | si | 17-ago-2011 a 21-oct-2026: 113 trades, 42/113, +65.954,74, PF 4,872, DD 2.846,52 | 115 trades, 43, +59.515,80, PF 4,907 | **NO coincide, diferencia ya explicada en la fila 17** (2 trades del port: 2012-04-07 y 2016-01-07; causa no identificada). TV da exactamente lo mismo que antes |
| 20 | idem | BTCUSD 1W | 1W | si | 6/10, +11.120,92, PF 37,484, DD 171,73; GP 11.393,29 / GL 303,95 | 10 cerrados, 6 ganadoras, +11.092,83 cerrado; abierta D larga +31,60 menos 0,42 = **+11.124,00**; PF 37,737 | **Coincide** en trades y ganadoras; total a 0,03% (3,08 USD) |
| 21 | idem | ETHUSD 4h | 4h | si | 25 trades, 10/25, +512,16, PF 1,487, DD 401,80 | 25, 10, +512,25, PF 1,488 | **Coincide** (igual que la fila 1) |
| 22 | idem | ETHUSD 1D | 1D | si | 82 trades, 32/82, +6.125,34, PF 2,826, DD 1.030,21 (desde 6-ago-2015) | 71 cerrados, 26, +827,11, PF 1,384 (Bitstamp desde 2017-08) | **NO coincide en totales, explicado:** el feed de TV arranca en 2015 y el del port en 2017-08. **Los últimos 6 trades coinciden 1 a 1** en fecha y precio (18-sep a 7-oct 2.611,4 a 2.573,6; 15 a 17-sep; 19-ago a 15-sep; 6 a 31-jul; 16-may a 15-jun; 21 a 23-mar) |
| 23 | idem | ETHUSD 1W | 1W | si | 5/8, +6.799,71, PF 25,451, DD 256,30 (desde 2-ago-2015) | 7 cerrados, 4 ganadoras, +2.777,35 + abierta D larga | **NO coincide en totales, explicado igual:** los últimos 6 trades de TV (incluida la D larga abierta del 17-ago-2026 a 2.462,8) coinciden con el port; TV tiene trades extra anteriores a 2017 |
| 24 | idem | SOLUSDT (Binance) 4h | 4h | si | 29 trades, 12/29, +2.143,50, PF 3,336, DD 565,15 | 29, 12, +2.143,79, PF 3,336 | **Coincide** |
| 25 | idem | SOLUSDT 1D | 1D | si | 44 trades, 19/44, +1.483,91, PF 2,131, DD 417,78 | 44 cerrados, 19; cerrado +1.367,99 + abierta C corta +117,73 menos 0,77 = **+1.484,95**; PF 2,134 | **Coincide** (1,04 USD) |
| 26 | idem | SOLUSDT 1W | 1W | si | 5 trades, 2/5, −30,01, PF 0,639, DD 92,73 | 5, 2, −29,99, PF 0,639 | **Coincide** |

- **Guardado:** el script quedó guardado en la cuenta como **"SQZ+RSI Fase 7"** (Pine Editor, botón Save; **sin publicar**).
- **Estado final del gráfico:** se sacó la strategy de la leyenda (icono del tacho) y se volvió a BTCUSD 4h; queda solo el demo de Makroni (como al empezar). No se tocó Makroni, no se publicó, no se crearon alertas ni se cambió nada de la cuenta. El layout "Sin nombre" no se guardó.
- **No verificado:** el cartel "Preset: ..." del unificado (el texto de la tabla no sale en `innerText`); el preset automático se infiere de que los números coinciden con los del script de cada TF (filas 4 a 6).
- **Cómo se leyó:** `javascript_tool` sobre `document.body.innerText` entre "Key stats" y "Performance analysis"; lista de trades con el panel maximizado y orden por "Trade number". Precios vivos para valuar la posición abierta del port: BTC 84.170 (4h) y 84.187 (1W), SOL 107,37, ETH 2.474,8.
- Cuenta de pruebas manuales: 9 corridas (filas 18 a 26). Total desde la Fase 5: **26**. Ninguna se usó para tocar parámetros.
