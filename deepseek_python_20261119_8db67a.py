# liquidez_masiva/scripts/update_data.py
"""
Descarga incremental de OHLCV (idempotente). Pensado para cron/GitHub Actions.
Solo ingiere velas cerradas: la vela en curso se excluye explícitamente.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import Config                              # noqa: E402
from core.data import (INTERVAL_MS, fetch_klines,           # noqa: E402
                       load_cache, save_cache)
from core.logging_utils import get_logger                   # noqa: E402

log = get_logger()


def main() -> int:
    try:
        cfg = Config.from_file("config/settings.toml")
    except Exception as e:
        log.error("Config inválida", extra={"err": str(e)})
        return 2

    try:
        cached = load_cache(cfg.data)
        if cached is None or cached.empty:
            df = fetch_klines(cfg.data)
            save_cache(df, cfg.data)
            log.info("Descarga completa", extra={"bars": len(df)})
            return 0

        step_ms = INTERVAL_MS[cfg.data.interval]
        last_ts_ms = int(cached.index[-1].timestamp() * 1000)
        start_ms = last_ts_ms + step_ms
        # P0: excluir la vela en curso restando un intervalo
        now_ms = int(time.time() * 1000) - step_ms
        if start_ms >= now_ms:
            log.info("Cache al día", extra={"last": str(cached.index[-1])})
            return 0

        new = fetch_klines(cfg.data, start_ms=start_ms, end_ms=now_ms)
        if new.empty:
            log.info("Sin velas nuevas")
            return 0

        merged = pd.concat([cached, new])
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
        save_cache(merged, cfg.data)
        log.info("Actualización OK", extra={
            "new": len(new), "total": len(merged)})
        return 0
    except Exception as e:
        log.error("Update falló", extra={"err": str(e)})
        return 3


if __name__ == "__main__":
    sys.exit(main())