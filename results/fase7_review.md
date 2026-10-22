## Revisión independiente previa a Z2/Z3 (subagente que no vio el trabajo; hecha ANTES de mirar Z2, Z3 y pool)

El revisor leyó el código en solo lectura, no corrió ninguna mirada y no abrió datos de Z2/Z3. Corrió pytest (1 falla de un test viejo de `test_universe`, ya corregido) y comparó `simulate` de HEAD contra el actual en 15 combinaciones (moneda x TF x set): idénticos.

| # | Gravedad | Hallazgo | Qué se hizo |
|---|---|---|---|
| 1 | CRÍTICO (solo W1 R1) | ids de sub-trades duplicados (varios lookbacks de W1 dan 4 velas): el motor colapsaba posiciones y cobraba comisiones fantasma (Calmar de W1 R1 en train 1,21 con el bug vs 1,79 con ids únicos, antes de las demás correcciones) | ids únicos + `ValueError` si hay duplicados + test; chequeo contable eq-capital = suma de PnL en los 3 TF (diferencia 0) |
| 2 | MEDIO | el cupo de 6 monedas se asignaba por orden alfabético: CAGR de 0,40 a 0,58 y la mediana por moneda cambiaba de signo según el orden | 9 prioridades sorteadas con semilla fija; toda métrica = mediana (PROTOCOLO 5 ter) |
| 3 | MEDIO | "sin el mejor trade" quitaba el de mayor R, no el de mayor PnL (casi nunca fallaba) | se quita el de mayor PnL en USD |
| 4 | MEDIO | n contaba sub-trades de E (R1 D1: 2.035) | n = trades A/B/C/D + episodios de E; se informa n_sub aparte |
| 5 | MEDIO | la última barra semanal (2026-10-19) era parcial (cierre del 21-oct) | `DATA_END["1w"]` = 2026-10-12; el TF mayor de P4/P1 se carga sin cortar |
| 6 | MEDIO (informativo) | modo riesgo (sin tope bruto, llegó a 1,54x) y modo vol (tope 1,0x) no son comparables en CAGR/DD | anotado en PROTOCOLO 5 ter; se compara por Calmar |
| 7 | MENOR | `CALMAR_CAP` = 10 no estaba en el protocolo | anotado (nunca se activó) |
| 8 | MENOR | candados incompletos (allcoins sin candado, train re-corrible tras mirar) | candidato guardado en cada mirada; train se niega si hubo miradas; allcoins exige las miradas y se corre una vez |
| 9 | MENOR | años del CAGR hasta la apertura de la última vela | se suma un paso del TF |
| 10 | MENOR | `signals` E: salida parcial daba `none`; tamaño con la vol de hoy | acción `reduce`; diferencias documentadas en `docs/BOT.md` |
| 11-13 | MENOR | señales saltadas siguen "abiertas" para `simulate`; golden sin versionar; regla UP/DOWN descarta tickers como JUP; fan tokens con slippage optimista | anotados como limitaciones (PROTOCOLO 5 ter) |

Contradicciones del protocolo que señaló (frase "pueden cerrar después", "ninguna otra pierna" vs P1, "misma corrida" de allcoins, "sin dedupe" de W1, precedencia de SIN MUESTRA, definición de n y del cupo): corregidas en `docs/PROTOCOLO.md`.

**Lo que el revisor verificó sin problemas:** lookahead (HTF contra fuerza bruta independiente en 800 velas, pipeline truncado en 2022-03-07, vol y Donchian con ventanas previas); fuga train→test (curvas de train idénticas cortando los datos en 2024-01-01); costos (comisión y slippage adversos en cada entrada y salida, sin doble cobro); sizing y orden de topes; conteo de la grilla (96/128/16), meseta y elegido recalculados desde el CSV; buy&hold. **No pudo verificar:** Z2/Z3/pool (prohibido), reglas del paper, Pine/TradingView.

**Después de las correcciones se re-corrió todo el train (2.ª pasada)**; los candidatos de la 1.ª pasada quedan archivados (`fase7_train_pasada1_state.json`, `fase7_*_grid_pasada1.csv`): H4 `P1=off P2=E P3=20 P4=- P5=risk`, D1 `P1=off P2=E P3=10 P4=20 P5=vol`, W1 `P1=off P2=E P3=10 P4=- P5=vol`. Los de la 2.ª son los que se miran en Z2/Z3.
