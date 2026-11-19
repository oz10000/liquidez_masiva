# liquidez_masiva/docs/MANUAL.md
# Manual para principiantes absolutos

## 1. ¿Qué es Python?
Lenguaje de programación legible. `print("hola")` muestra texto.

## 2. ¿Qué es GitHub?
Sitio para guardar código con historial. Cada cambio = *commit*.

## 3. ¿Qué es un workflow?
Archivo YAML en `.github/workflows/`. Dice: "cuando pase X, ejecuta Y".

## 4. ¿Qué es una API?
URL que devuelve JSON. Ejemplo: `api.binance.com/api/v3/klines` devuelve velas.

## 5. ¿Qué es un exchange?
Plataforma de compra/venta (Binance, Kraken). API para leer y operar.

## 6. ¿Qué es una orden?
- **Market**: al mejor precio ya.
- **Limit**: sólo si el precio llega a X.
- **Stop**: se dispara al cruzar X.

## 7. ¿Qué es una vela?
`open, high, low, close, volume` en un intervalo. 1 vela 1h = 1 hora.

## 8. ¿Qué es un indicador?
Fórmula sobre precio/volumen: EMA (media), ATR (volatilidad), Donchian (canal).

## 9. ¿Qué es un backtest?
Simulación de la estrategia sobre datos pasados. NO predice el futuro.

## 10. ¿Qué es una estrategia?
Reglas claras de entrada/salida. Liquidez Masiva usa:
- Entrada: `z_vol>2` + `close > Donchian_upper(t-1)` + `EMA_slope>0`.
- Salida: `close < EMA_slow` o stop.

## 11. ¿Qué es el riesgo?
- `max_position_pct`: fracción del capital por trade.
- `stop_loss_atr_mult`: distancia del stop = `N × ATR`.
- `daily_loss_limit_pct`: kill-switch diario.

## 12. Cada número

| Número | Significado |
|---|---|
| Sharpe 1.5 | Retorno por unidad de volatilidad; decente. |
| Max DD −22% | Peor caída desde máximo. |
| PF 1.8 | Ganó 1.8€ por cada 1€ perdido. |
| Win Rate 54% | 54 de 100 trades ganaron. |
| Expectancy 0.3R | Gana 0.3× el riesgo por trade. |
| Liquidez Score 72 | Compuesto; 70–85 = bueno. |

## Aviso crítico
Los backtests muestran lo que **pudo haber pasado**, no lo que pasará.
Antes de operar con dinero real: walk-forward, out-of-sample y 3+ meses
de testnet. El capital mínimo realista es el que puedes permitirte perder.