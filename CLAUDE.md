# CLAUDE.md — SQZ+RSI Lab

Repo para **optimizar y validar sin trampas** una estrategia de trading de criptos (Squeeze Momentum + RSI, Pine Script v5) en **H4, D1 y semanal**, sobre muchas monedas. Se simula en Python y se valida contra TradingView. Este archivo se carga solo en cada sesión: mantenelo corto y actualizado.

## Dónde está cada cosa (leé en este orden en una sesión nueva)

1. `docs/HANDOFF.md`: estado, diseño del indicador, evidencia previa, bugs y lecciones, pendientes.
2. `docs/PROTOCOLO.md`: método de optimización, criterios de éxito, ciclo de validación con TradingView.
3. `docs/TV_BASELINES.md`: números reales de TradingView para calibrar el port y semántica de `strategy()` a replicar.
4. `ref/`: código de referencia, **solo lectura**: `sqz_rsi_senales_v8.pine`, `sqz_rsi_strategy_v2.pine`, `python_port_y_tests.md` (contiene `eng.py` y `divsig.py` embebidos).

## Usuario y reglas de trabajo (innegociables)

- **Tiger = Franco Redoni**, desarrollador .NET, Buenos Aires. **Español rioplatense informal.** Nivel de análisis técnico: básico. Directo, técnicamente denso, sin exceso de cautela.
- Respuestas en **bullets, máx. 5 y 350 palabras**, más una conclusión de máx. 50 palabras. Si omitís algo importante por ese límite, avisale. Tono **gracioso**, no serio.
- **No inventar. Si no estás 100% seguro, decilo** y marcá lo no verificado.
- Vos sos quien construye: entregá archivos hechos. Cuando le pidas hacer algo en una UI, decile **exactamente dónde está**.
- **Todas las correcciones juntas, de una sola vez** (se enoja con el ida y vuelta eterno).
- **Siempre decir si un Pine está compilado o no.** Un Pine solo cuenta como compilado si se probó en TradingView. No lo afirmes sin esa prueba.
- No recortar features: los defaults se pueden apagar, no quitar.
- Su TradingView es **plan gratis**: máx. 2 indicadores a la vez (uno es "Makroni", de terceros, no se toca) y **no puede exportar CSV**. Todo debe vivir en UN solo script.
- No es asesoría financiera: es validación técnica de una estrategia. Si los resultados son pobres, decilo claro, sin vender humo.

## Reglas duras del proyecto

- **El port Python no es TradingView.** Un candidato solo vale si TradingView lo confirma en el tramo reciente.
- **Calibrar antes de optimizar** (`docs/TV_BASELINES.md`). Sin calibración aprobada no se optimiza nada.
- **Protocolo anti-sobreajuste obligatorio** (`docs/PROTOCOLO.md`): corte train/test fijado ANTES de mirar resultados, holdout por monedas, mesetas y no picos, contar y reportar todas las pruebas.
- Medir en **R neto de comisión** y retorno por trade, no en USD acumulados.
- Nunca pisar `ref/`. Los Pine nuevos son copias **generadas**, nunca editadas a mano.
- **Un set de parámetros por temporalidad, NUNCA por moneda.** La fuente de verdad es `params/{h4,d1,w1}.json` (claves = nombres exactos de los inputs del Pine). De ahí salen `pine/{h4,d1,w1}/sqz_rsi_strategy_<tf>.pine` (un script por temporalidad) y `pine/sqz_rsi_strategy_unified.pine` (un solo script que elige el preset solo con `timeframe.in_seconds()`: <1d H4, 1d a <1w D1, >=1w W1; caja "Manual" para probar). Si se cambia un JSON, regenerar con `python -m sqzlab.genpine` (un test avisa si quedó desactualizado). Hasta que corra la Fase 4, los JSON son los defaults de la v2 sin optimizar.
- Si hay un bloqueo de red, **no lo esquives**: reportalo y pedí el archivo al usuario.
- `data/` está en `.gitignore`; el script de descarga sí se versiona.

## Convenciones técnicas

- Python 3.12 en `.venv` (en esta PC no hay `make`; los comandos van directos). Paquete en `src/sqzlab/`, tests en `tests/`. Semillas fijas en todo lo aleatorio.
- Setup (una vez): `py -3.12 -m venv .venv` y `.venv\Scripts\python -m pip install -r requirements.txt`.
- Todos los comandos con `PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH="src"`):
  - Datos: `python -m sqzlab.fetch --source bitstamp --symbols BTC ETH SOL --tf 1d 4h` y `--source bingx ...` (perpetuo USDT-M). Salen a `data/<fuente>_<SIM>_<tf>.csv` (gitignored).
  - Calibración (Fase 2): `python -m sqzlab.calibrate` (imprime tabla y escribe `results/calibration.md`).
  - Generar Pine desde `params/*.json`: `python -m sqzlab.genpine` (`--init-params` crea los JSON solo si no existen).
  - Tests: `python -m pytest -q`.
- Optimización (Fase 4): todavía no existe; cuando exista, documentar el comando acá.
