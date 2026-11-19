# liquidez_masiva/docs/STATS.md
# Estadística aplicada

| Métrica | Uso correcto | Sesgo | Robustez |
|---|---|---|---|
| Sharpe | Comparar estrategias con misma frecuencia | Sobreestima si no-normal | Media |
| Sortino | Énfasis downside | Sensible a τ | Media-alta |
| PF | Ratio bruto | Outlier infla | Baja |
| Win Rate | Complementaria | Ignora magnitud | Baja |
| Expectancy | Sizing | Sólo estable con N≥30 | Media |
| Max DD | Risk-of-ruin | Sensible al período | Media |
| Calmar | Retorno ajustado a DD | Requiere ≥1 año | Media-alta |

## Advertencias automáticas
- `n_trades < 30` → muestra insuficiente.
- `n_bars < 252` → < 1 año.
- PF infinito → None + warning.

## Prácticas recomendadas
- Reportar IC95% bootstrap del Sharpe (roadmap v1.1).
- Reportar métricas OOS, no sólo in-sample.
- Nunca extrapolar más allá del régimen testado.
