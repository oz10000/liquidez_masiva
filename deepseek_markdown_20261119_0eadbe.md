# liquidez_masiva/docs/BACKTEST.md
# Backtest

## Cómo funciona
1. OHLCV indexado por timestamp UTC.
2. Señales en `t` con `donchian.shift(1)` (anti look-ahead).
3. Ejecución al `open[t+1]` ± slippage.
4. Stop-loss contra `low[t]`/`high[t]`.
5. Fees en ambas patas.

## Qué valida
- Coherencia interna.
- Sensibilidad a fees/slippage.
- Comportamiento por régimen.

## Qué NO valida
- Ejecución real (fills parciales, latencia).
- Impacto de mercado.
- Cambios de régimen futuros.

## Anti-sobreajuste
1. Walk-forward 12m/3m.
2. Holdout out-of-sample 12m.
3. Sensibilidad a parámetros (superficie estable → robusto).
4. Mínimo 100 trades + 2 años.

## Interpretación
| Resultado | Lectura |
|---|---|
| Sharpe > 1.0 OOS | señal, no prueba |
| MDD > 30% | reconsiderar sizing |
| N_trades < 100 | no concluyente |
| PF > 5 | sospecha de overfit / look-ahead |