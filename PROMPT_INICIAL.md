Estás arrancando el repo "SQZ+RSI Lab". Todo el contexto está en archivos; no dependas de memoria de otras conversaciones.

1. Leé `CLAUDE.md`, `docs/HANDOFF.md`, `docs/PROTOCOLO.md` y `docs/TV_BASELINES.md`, en ese orden. Después leé `ref/` (los dos `.pine` y `python_port_y_tests.md`).
2. Si falta algo en `ref/`, decime exactamente qué falta y esperá. No lo reconstruyas de memoria.
3. Armá la estructura del repo (`src/`, `tests/`, `data/`, `results/`, `candidates/`, `pine/`), un entorno Python 3.11+ con `pytest`, `numpy` y `pandas`, y completá la sección "Convenciones técnicas" de `CLAUDE.md` con los comandos reales.
4. Pasá a la **Fase 1 (datos)** y la **Fase 2 (calibración)** de `docs/PROTOCOLO.md`. No optimices nada hasta que la calibración contra `docs/TV_BASELINES.md` esté aprobada, y mostrame la tabla de coincidencias y diferencias antes de seguir.
5. Dos advertencias que ya costaron tiempo: (a) el script que corre hoy en su TradingView parece ser la strategy v1 (A+B+C, con C compras encendida), no la v2 de `ref/`; calibrá primero A+B+C. (b) `divsig.py` importa un `div.py` que no existe; reimplementá `pivots`.
6. Respetá las reglas de trabajo de `CLAUDE.md` (español rioplatense, bullets máx. 5 y 350 palabras más conclusión de 50, tono gracioso, no inventar, todas las correcciones juntas, decir si un Pine compiló o no).
7. Al terminar cada fase, actualizá `docs/HANDOFF.md` (sección 8) con el estado real, para que una sesión nueva pueda retomar sin contexto.
