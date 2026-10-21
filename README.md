# SQZ+RSI Lab

Optimización y validación de una estrategia de trading de criptos (Squeeze Momentum + RSI, Pine Script v5) en H4, D1 y semanal. Simulación en Python, validación final en TradingView.

Empezá por `CLAUDE.md` (reglas) y `docs/HANDOFF.md` (estado). Método en `docs/PROTOCOLO.md`; números de TradingView para calibrar en `docs/TV_BASELINES.md`.

## Estructura prevista

```
CLAUDE.md                 # contexto que Claude Code carga solo
README.md
docs/                     # HANDOFF, PROTOCOLO, TV_BASELINES
ref/                      # código de referencia, solo lectura (3 archivos del proyecto de claude.ai)
src/                      # port Python, descarga de datos, optimizador
tests/                    # calibración contra TradingView
data/                     # CSV (gitignored)
params/                   # h4.json, d1.json, w1.json: UN set por temporalidad (nunca por moneda)
results/  candidates/
pine/                     # generado desde params/: pine/{h4,d1,w1}/ + sqz_rsi_strategy_unified.pine
```

## Archivos que hay que copiar a `ref/`

Del proyecto "Analisis tecnico" de claude.ai (carpeta `claude/`):
`sqz_rsi_senales_v8.pine`, `sqz_rsi_strategy_v2.pine`, `python_port_y_tests.md`.
