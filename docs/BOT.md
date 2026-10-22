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


## Contrato de PESOS OBJETIVO: `--strategy r1fiel` (Fase 8)

```
python -m sqzlab.signals --strategy r1fiel [--tf d1] [--no-fetch] [--out pesos.json]
```

Cambia el tipo de contrato: **no hay señales de entrada/salida por moneda sino una cartera**. El bot re-balancea a estos pesos. Solo `d1` (H4 es una conversión sin veredicto). Cron sugerido: `5 0 * * *` UTC (la vela diaria cierra a las 00:00 UTC). Baja las velas de TODOS los pares USDT con status TRADING (`f8data.update_all`, unos 500 llamados), descarta la vela en curso y calcula con la **última vela diaria CERRADA** `D`. Mismo código que el backtest (`universe_dyn` + `r1fiel`; `tests/test_fase8.py` verifica que los pesos coinciden con los del backtest en la última vela).

| Campo | Significado |
|---|---|
| `bar_time_utc` | apertura de la vela diaria cerrada `D` (los pesos son los de **su cierre**, o sea los que hay que tener desde `D+1 00:00 UTC`) |
| `params_hash` | hash de `params/r1fiel.json`; si cambia, cambió la estrategia |
| `universe` | las 20 monedas del top 20 dinámico del día `D` (datos ≤ `D−1`: ≥ 365 días y mediana de volumen 30 d ≥ 2 M USD) |
| `targets[]` | por moneda: `symbol`, `pair` (`BTCUSDT`), `weight_pct_equity` (**peso objetivo = % de la equity en nocional**, ya con el tope bruto), `weight_raw_pct_equity` (antes del tope), `active_subsignals` (de 9), `vol_ann` (vol 90 d anualizada), `close`, `stop_by_lookback_days` (stop de cada sub-señal abierta; `null` = cerrada) |
| `gross_raw`, `gross_scale`, `gross` | suma de pesos sin tope, factor `min(1, 2,0 / gross_raw)` y suma final (≤ 2,0) |
| `rebalance_band` | 0,20 |

Reglas para el bot:
- **Toda moneda que no figure en `targets` tiene objetivo 0** (vender si la tiene). Una moneda con `weight_pct_equity = 0` también.
- **Re-balanceo con banda:** operar una moneda solo si pasa de 0 a >0 (entrar) o de >0 a 0 (salir: siempre), o si el peso efectivo actual (`valor de la posición / equity`) se aparta del objetivo en más de **20% relativo** (`|objetivo − actual| > 0,20 × actual`); al operar, llevar la posición al objetivo. Es la misma regla del backtest.
- **Pesos = apalancamiento:** el bruto puede llegar a 2,0× la equity. Con una cuenta spot eso no se puede (hay que escalar el bruto a ≤ 1,0 o usar margen/perpetuos); el backtest **no cobra financiamiento**. Cualquier escalado que haga el bot es una decisión del bot y cambia el riesgo.
- **Costos reales:** el backtest asume 0,15% por lado sobre el nocional operado (0,10% comisión + 0,05% slippage); la rotación del backtest es alta (ver `results/fase8.md`).
- **Idempotencia:** clave `(strategy, tf, bar_time_utc)`. Si la vela `D` todavía no está publicada, `bar_time_utc` sigue siendo el del día anterior: **comparar y reintentar**, nunca asumir.
- **Deslistadas:** una moneda deslistada deja de aparecer; vender al último precio posible (el backtest la cierra al último cierre, supuesto optimista).
- No es asesoría financiera. El veredicto de la Fase 8 está en `results/fase8.md`.
