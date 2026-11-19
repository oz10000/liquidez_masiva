# liquidez_masiva/docs/API.md
# API y modos

## Público (research)
`GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1000`
Sin auth. Rate-limit: peso 2 por petición (renovar cada minuto).

## Demo (paper trading)
`ccxt` testnet (no incluido en v1.0). Cuando se añada:
- `exchange.set_sandbox_mode(True)`.
- Flag `demo=True` en el reporte.
- Sin impacto real.

## Real (producción)
**No implementado en v1.0.**

Reglas obligatorias si se añade:
1. API key sólo en `os.environ` o GitHub `secrets`.
2. `enableRateLimit=True`.
3. IP whitelist en el exchange.
4. 2FA.
5. `kill_switch` diario (ya implementado en `core/risk.py`).
6. Log de cada orden pre y post.
7. `max_notional` por trade (ya implementado vía `max_position_pct`).

## Manejo de errores
- HTTP 429/5xx → Retry con backoff (`core/data.py`).
- Timeout → `request_timeout` configurable.
- Respuesta inválida → `RuntimeError` explícito.