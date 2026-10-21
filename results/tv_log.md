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
