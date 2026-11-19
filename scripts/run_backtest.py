# liquidez_masiva/scripts/run_backtest.py
"""
CLI headless para CI y ejecución manual.
Uso:
    python -m scripts.run_backtest --config config/settings.toml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.backtest import run_backtest                     # noqa: E402
from core.config import Config                              # noqa: E402
from core.data import fetch_klines, load_cache, save_cache  # noqa: E402
from core.logging_utils import get_logger                   # noqa: E402
from core.metrics import compute_metrics                    # noqa: E402
from core.report import (build_report, save_json,           # noqa: E402
                         save_markdown, save_trades_csv)
from core.strategy import generate_signals                  # noqa: E402

log = get_logger()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/settings.toml")
    ap.add_argument("--out", default="reports")
    args = ap.parse_args()

    try:
        cfg = Config.from_file(args.config)
    except Exception as e:
        log.error("Configuración inválida", extra={"err": str(e)})
        return 2

    try:
        df = load_cache(cfg.data)
        if df is None or df.empty:
            df = fetch_klines(cfg.data)
            save_cache(df, cfg.data)
    except Exception as e:
        log.error("Descarga fallida", extra={"err": str(e)})
        return 3

    try:
        signals = generate_signals(df, cfg.strategy)
        result = run_backtest(df, signals, cfg.risk, cfg.cost, cfg.backtest)
        metrics = compute_metrics(result.equity, result.trades,
                                  cfg.backtest.periods_per_year)
    except Exception as e:
        log.error("Backtest falló", extra={"err": str(e)})
        return 4

    out = Path(args.out)
    report = build_report(result, metrics, {
        "symbol": cfg.data.symbol, "interval": cfg.data.interval,
        "fee_rate": cfg.cost.fee_rate, "slippage_bps": cfg.cost.slippage_bps,
        "max_position_pct": cfg.risk.max_position_pct,
        "stop_loss_atr_mult": cfg.risk.stop_loss_atr_mult,
    })
    save_json(report, out / "latest.json")
    save_markdown(result, metrics, out / "latest.md")
    if result.trades:
        save_trades_csv(result, out / "trades.csv")

    log.info("Backtest OK", extra={
        "n_trades": metrics.n_trades,
        "sharpe": metrics.sharpe,
        "max_dd": metrics.max_drawdown,
        "score": metrics.liquidez_score,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
