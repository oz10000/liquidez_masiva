# liquidez_masiva/README.md
# Liquidez Masiva

Motor de research cuantitativo y backtest para la estrategia
**Liquidity Breakout** sobre datos públicos de Binance. Pensado para
ejecutarse en Pydroid 3 (Android), Linux, macOS y Windows, y para correr
automáticamente en GitHub Actions.

## Estado

- Versión: **1.0.0**
- Modo: **research / backtest** (no ejecuta órdenes reales)
- Certificación: ver `docs/` y conclusión al final del `README` extendido

## Características

- Descarga OHLCV paginado con reintentos y caché local.
- Indicadores: EMA, ATR, Donchian, z-score de volumen.
- Estrategia determinista (sin look-ahead: señal en `t`, ejecución en `t+1`).
- Backtest event-driven con fees, slippage y stop-loss por ATR.
- Métricas: Sharpe, Sortino, Calmar, Profit Factor, Max DD, Expectancy,
  Omega, Liquidez Score compuesto.
- Dashboard Streamlit + CLI headless.
- CI con ruff + mypy + pytest en Python 3.9/3.10/3.11.
- Workflows de actualización diaria y backtest semanal.

## Instalación

### Linux / macOS / Windows

```bash
git clone <repo>
cd liquidez_masiva
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements.txt --extra-index-url ""  # opcional UI
