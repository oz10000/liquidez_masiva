# liquidez_masiva/docs/UI.md
# Interfaz Streamlit

## Layout

### Sidebar
- Símbolo, intervalo, días de histórico.
- Capital inicial, % máximo por posición, stop-loss ×ATR.
- Fee taker, slippage bps, permitir shorts.
- Botón **Ejecutar backtest** (agrupado en `st.form` → un solo rerun).

### Main
1. **KPIs**: Liquidez Score, Sharpe, Max DD, Win Rate.
2. **Advertencias**: si n<30 trades o n<252 bars.
3. **Equity curve** (`st.line_chart`).
4. **Drawdown** (`st.area_chart`).
5. **Tabla de trades** (`st.dataframe`).
6. **Descargas**: JSON + CSV.

## Botones

| Botón | Efecto |
|---|---|
| Ejecutar backtest | Pipeline completo con spinners |
| Descargar JSON | Reporte estructurado |
| Descargar CSV | Trades en CSV |

## Cache
`@st.cache_data(ttl=3600)` en `_load_data` para no re-descargar.

## Manejo de errores
`try/except` global → `st.error` con mensaje; la app no muere.