# liquidez_masiva/docs/MATH.md
# Fórmulas y justificación

## EMA
`EMA_t = α·P_t + (1-α)·EMA_{t-1}`, `α = 2/(N+1)`
- **Por qué:** suavizado con peso reciente.
- **Limitación:** sensible a outliers.
- **Alternativa:** Hull MA, KAMA.

## ATR