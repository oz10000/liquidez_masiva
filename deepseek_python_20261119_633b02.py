# liquidez_masiva/core/report.py
"""
Serialización de resultados de backtest a JSON / CSV / Markdown.
Escritura atómica para que Streamlit y CI no corrompan el destino.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .backtest import BacktestResult, Trade
from .metrics import Metrics
from .utils import atomic_write, fmt_num, fmt_pct


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_report(result: BacktestResult, metrics: Metrics,
                 cfg_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "generated_at": _utc_iso(),   # P1: timestamp real, no path
        "config": cfg_snapshot,
        "metrics": metrics.to_dict(),
        "trades": [_trade_dict(t) for t in result.trades],
        "equity_first": float(result.equity.iloc[0]) if not result.equity.empty else None,
        "equity_last": float(result.equity.iloc[-1]) if not result.equity.empty else None,
        "bars": result.bars,
    }


def _trade_dict(t: Trade) -> Dict[str, Any]:
    return {
        "entry_ts": t.entry_ts.isoformat() if t.entry_ts is not None else None,
        "exit_ts": t.exit_ts.isoformat() if t.exit_ts is not None else None,
        "side": t.side,
        "entry_price": t.entry_price,
        "exit_price": t.exit_price,
        "qty": t.qty,
        "fees": t.fees,
        "pnl": t.pnl,
        "pnl_R": t.pnl_R,
        "exit_reason": t.exit_reason,
    }


def save_json(report: Dict[str, Any], path: str | Path) -> Path:
    p = Path(path)
    with atomic_write(p) as f:
        json.dump(report, f, ensure_ascii=True, indent=2, default=str)
    return p


def save_trades_csv(result: BacktestResult, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with atomic_write(p) as f:
        w = csv.writer(f)
        w.writerow(["entry_ts", "exit_ts", "side", "entry_price", "exit_price",
                    "qty", "fees", "pnl", "pnl_R", "exit_reason"])
        for t in result.trades:
            w.writerow([
                t.entry_ts.isoformat() if t.entry_ts is not None else "",
                t.exit_ts.isoformat() if t.exit_ts is not None else "",
                t.side, t.entry_price, t.exit_price, t.qty, t.fees,
                t.pnl, t.pnl_R, t.exit_reason,
            ])
    return p


def save_markdown(result: BacktestResult, metrics: Metrics, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Liquidez Masiva — Reporte de Backtest\n")
    lines.append(f"- Generado: {_utc_iso()}")
    lines.append(f"- Bars: {metrics.n_bars}")
    lines.append(f"- Trades: {metrics.n_trades}")
    lines.append(f"- Total return: {fmt_pct(metrics.total_return)}")
    lines.append(f"- Annual return: {fmt_pct(metrics.annual_return)}")
    lines.append(f"- Sharpe: {fmt_num(metrics.sharpe)}")
    lines.append(f"- Sortino: {fmt_num(metrics.sortino)}")
    lines.append(f"- Calmar: {fmt_num(metrics.calmar)}")
    lines.append(f"- Max DD: {fmt_pct(metrics.max_drawdown)}")
    lines.append(f"- Profit Factor: {fmt_num(metrics.profit_factor)}")
    lines.append(f"- Win Rate: {fmt_pct(metrics.win_rate)}")
    lines.append(f"- Expectancy (R): {fmt_num(metrics.expectancy_R)}")
    lines.append(f"- Omega: {fmt_num(metrics.omega_index)}")
    lines.append(f"- Liquidez Score: {fmt_num(metrics.liquidez_score, 1)} / 100\n")
    if metrics.warnings:
        lines.append("## Advertencias")
        for w in metrics.warnings:
            lines.append(f"- {w}")
        lines.append("")
    with atomic_write(p) as f:
        f.write("\n".join(lines))
    return p