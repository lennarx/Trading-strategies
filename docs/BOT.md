# BOT.md: señales para el bot propio (sin alertas de TradingView)

Su TradingView es plan gratis: no manda webhooks. Por eso el bot **no depende de TradingView**: pide las señales a `python -m sqzlab.signals`, que usa el mismo motor que el backtest (`strategy.simulate` + `params/<tf>.json`). Este archivo es solo el **contrato**; el código del bot vive en otro repo y no se toca desde acá.

## Cómo llamarlo (cron, una vez por cierre de vela)

```
python -m sqzlab.signals --tf h4 --symbols BTC ETH SOL --source binance [--no-fetch] [--donchian [DIAS ...]] [--out señales.json]
```

- `--tf`: `h4` | `d1` | `w1`. `--source`: `binance` (default, spot USDT) | `bingx` (perpetuo USDT-M) | `bitstamp`.
- Baja velas incrementalmente (`fetch.update_csv`), **descarta la vela en curso** (`forward.closed_only`) y devuelve la señal de la **última vela CERRADA**.
- Con `PYTHONPATH=src` y el `.venv` del repo. Imprime un arreglo JSON por stdout (y lo guarda con `--out`).
- Cron sugerido (UTC, unos minutos después del cierre para que el exchange publique la vela): H4 en `5 0,4,8,12,16,20 * * *`; D1 en `5 0 * * *`; W1 en `5 0 * * 1` (la semana abre el lunes 00:00 UTC). Si la vela cerrada todavía no está publicada, el `bar_time_utc` de la respuesta sigue siendo el de la anterior: **el bot tiene que comparar `bar_time_utc` con la vela que espera y reintentar** (nunca asumir).
- `--donchian` (apagado por defecto) agrega, por moneda, un segundo objeto con `kind: "E"` (ensamble de Donchian; ver abajo).

## Contrato del JSON (un objeto por moneda; el de `kind` A/B/C/D siempre sale)

| Campo | Tipo | Significado |
|---|---|---|
| `symbol` | string | moneda base (`BTC`) |
| `tf` | string | `h4` / `d1` / `w1` |
| `bar_time_utc` | string ISO | **apertura** de la vela cerrada a la que corresponde la señal (UTC, `2026-10-21T00:00:00Z`) |
| `action` | string | `long` / `short` (abrir) · `exit` (cerrar la posición del motor) · `none` |
| `kind` | string \| null | `A` / `B` / `C` / `D` (señal SQZ+RSI) o `E` (Donchian); `null` si `none` |
| `entry_ref` | number \| null | precio de referencia de la entrada = **cierre** de la vela (la strategy ejecuta al cierre) |
| `stop` | number \| null | stop inicial de la señal (precio) |
| `size_pct_equity` | number | % de la equity en **nocional** con el sizing de la strategy: `min(riskPct / distancia del stop, maxLev)`; `0` si no es una entrada |
| `params_hash` | string | hash de `params/<tf>.json` (el mismo que usa el forward test): si cambia, cambió la estrategia |
| `position` | object \| null | posición que el motor tiene abierta HOY (`side`, `kind`, `since_bar_time_utc`, `entry_ref`, `stop`); sirve para reconciliar el estado del bot |
| `closes_previous` | object (solo si hay reversa) | la entrada de esta vela cierra una posición contraria: `{kind, reason}` |
| `reason` | string (solo en `exit`) | `stop` / `ema` / `donch` / `inval` / `reversa` |

Reglas de uso:
- **`exit` y `stop`:** el stop vive en el exchange (orden `stop`) desde que se entra; el motor cierra intravela si lo toca. La señal `exit` por `reason: ema|donch|inval` es "cerrar al cierre de esa vela".
- **Idempotencia:** la clave de una señal es `(symbol, tf, bar_time_utc)`. Procesar dos veces la misma clave no debe duplicar la orden.
- **No hay repintado:** la señal de una vela cerrada **no cambia** cuando llegan velas nuevas (el motor es causal; `tests/test_signals.py` lo verifica corriendo con datos hasta t y hasta t+50). Si el exchange corrige una vela vieja, el `params_hash` y el historial pueden diferir: ante eso el bot debe reconciliar con `position`.
- **El tamaño es porcentaje de la equity del motor** (10.000 simulados). El bot debe aplicarlo a SU equity y respetar sus propios topes (el backtest de cartera usa máx. 6 monedas y 5% de riesgo abierto: no están en este JSON).
- Una señal de la vela en curso nunca sale: si el bot necesita velocidad, que espere el cierre.

## Señal E (`--donchian`)

Objeto extra por moneda: `kind: "E"`, `action` (`long` si alguna sub-señal entra en esta vela; `exit` si salió la última activa; `reduce` si salen algunas y otras siguen activas, o sea que el tamaño objetivo baja; `none`), `active_subsignals` / `total_subsignals`, `entering_days` / `exiting_days` (lookbacks en días que entran o salen en esta vela), `vol_ann` (vol anualizada de 90 días), `size_pct_equity` = `activas / K × min(0,25 / vol, 2) × 100` (**tamaño objetivo total de la moneda**, no incremental), `stop: null` (la salida es el mínimo de cierres previos de N/2 velas, no un precio fijo) y `e_days`. **Diferencias con el backtest:** el backtest fija el tamaño de cada sub-señal al entrar; acá el tamaño objetivo usa la vol de HOY, y `active_subsignals` depende de cuánta historia se baje (la máquina de estados arranca al principio de los datos): bajar siempre la misma historia. Es solo largo y **no es una recomendación**: la Fase 7 decide si sirve (`results/fase7.md`).

## Qué NO hace

- No manda órdenes ni toca el exchange. No cubre comisiones, funding ni slippage reales.
- No es asesoría financiera: es la salida de un modelo validado en backtest, con las limitaciones de `docs/PROTOCOLO.md` y `results/fase7.md`.
