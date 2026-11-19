# liquidez_masiva/docs/MAINTENANCE.md
# Runbook de mantenimiento

## Operaciones diarias (automáticas)
- `daily_update.yml` a las 00:15 UTC: descarga incremental.
- Verificar commits en `data/raw/`.
- Si falla: revisar logs del run en GitHub Actions.

## Operaciones semanales
- `weekly_backtest.yml` los lunes: backtest completo.
- Reporte en `reports/latest.json` + `reports/latest.md`.
- Comparar con semana previa (diferencias > 20% en Sharpe → investigar).

## Roturas frecuentes

| Síntoma | Causa probable | Acción |
|---|---|---|
| 429 de Binance | Rate-limit | Aumentar `sleep_between_pages` |
| OHLCV inconsistente | Vela corrupta | Borrar `data/raw/*.csv` y re-descargar |
| Sharpe `None` | std=0 | Datos planos; revisar activo |
| PF `None` | 0 pérdidas | Sospecha overfit; revisar trades |
| Streamlit no arranca | Falta `streamlit` | `pip install streamlit` |

## Rotación de datos
- `data/raw/*.csv` puede crecer. `scripts/update_data.py` es incremental.
- Si >50 MB: archivar por año en `data/archive/`.

## Actualización de dependencias
```bash
pip install --upgrade -r requirements.txt
pytest -q
ruff check .