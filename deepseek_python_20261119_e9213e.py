# liquidez_masiva/core/metrics.py
"""
Métricas estadísticas y financieras del backtest.
Casos límite cubiertos: n pequeño, std≈0, downside≈0, sin trades.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .backtest import Trade
from .utils import clamp, safe_div


# Umbrales del Liquidez Score (lo, hi). Overrideables en tests; en v1.2 se
# moverán a [metrics] del settings.toml.
SCORE_THRESHOLDS: Dict[str, tuple] = {
    "sharpe":        (0.0, 2.0),
    "sortino":       (0.0, 3.0),
    "profit_factor": (1.0, 3.0),
    "calmar":        (0.0, 2.0),
    "win_rate":      (0.30, 0.70),
}


@dataclass
class Metrics:
    n_bars: int = 0
    n_trades: int = 0
    total_return: Optional[float] = None
    annual_return: Optional[float] = None
    sharpe: Optional[float] = None
    sortino: Optional[float] = None
    calmar: Optional[float] = None
    max_drawdown: Optional[float] = None
    profit_factor: Optional[float] = None
    win_rate: Optional[float] = None
    expectancy_R: Optional[float] = None
    omega_index: Optional[float] = None
    liquidez_score: Optional[float] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _pct_change(equity: pd.Series) -> pd.Series:
    return equity.pct_change().dropna()


def _norm(x: Optional[float], lo: float, hi: float) -> float:
    if x is None or not np.isfinite(x):
        return 50.0
    return clamp((x - lo) / (hi - lo) * 100.0, 0.0, 100.0)


def compute_metrics(equity: pd.Series, trades: List[Trade],
                    periods_per_year: int = 365) -> Metrics:
    m = Metrics()
    if equity is None or equity.empty:
        m.warnings.append("equity vacía")
        return m
    eq = equity.dropna()
    if len(eq) < 2:
        m.warnings.append("equity con < 2 puntos")
        return m

    m.n_bars = int(len(eq))
    m.n_trades = int(len(trades))

    total_return = eq.iloc[-1] / eq.iloc[0] - 1.0
    m.total_return = float(total_return)
    years = len(eq) / periods_per_year
    if years > 0 and (1 + total_return) > 0:
        m.annual_return = float((1 + total_return) ** (1 / years) - 1)

    rets = _pct_change(eq)
    if len(rets) >= 2:
        mean_r = float(rets.mean())
        std_r = float(rets.std(ddof=1))
        if std_r > 1e-12:
            m.sharpe = mean_r / std_r * float(np.sqrt(periods_per_year))

    if len(rets) >= 2:
        mean_r = float(rets.mean())
        downside = rets[rets < 0]
        if len(downside) >= 2:
            dstd = float(downside.std(ddof=1))
            if dstd > 1e-12:
                m.sortino = mean_r / dstd * float(np.sqrt(periods_per_year))

    cummax = eq.cummax()
    dd = (eq - cummax) / cummax
    m.max_drawdown = float(dd.min())

    if m.annual_return is not None and m.max_drawdown is not None:
        if abs(m.max_drawdown) > 1e-12:
            m.calmar = m.annual_return / abs(m.max_drawdown)

    if trades:
        pnls = [t.pnl for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        m.win_rate = len(wins) / len(pnls) if pnls else None
        gross_win = float(sum(wins))
        gross_loss = float(abs(sum(losses)))
        if gross_loss > 1e-12:
            m.profit_factor = gross_win / gross_loss
        elif gross_win > 0:
            m.profit_factor = None
            m.warnings.append("Profit Factor infinito (0 pérdidas)")

        r_mults = [t.pnl_R for t in trades if t.pnl_R is not None]
        if r_mults:
            p_win = sum(1 for r in r_mults if r > 0) / len(r_mults)
            wins_r = [r for r in r_mults if r > 0]
            loss_r = [r for r in r_mults if r < 0]
            avg_w = float(np.mean(wins_r)) if wins_r else 0.0
            avg_l = float(np.mean(loss_r)) if loss_r else 0.0
            m.expectancy_R = p_win * avg_w + (1 - p_win) * avg_l

    if len(rets) >= 10:
        pos = float(rets[rets > 0].sum())
        neg = float(-rets[rets < 0].sum())
        if neg > 1e-12:
            m.omega_index = pos / neg

    t = SCORE_THRESHOLDS
    score = (
        0.30 * _norm(m.sharpe, *t["sharpe"]) +
        0.20 * _norm(m.sortino, *t["sortino"]) +
        0.15 * _norm(m.profit_factor, *t["profit_factor"]) +
        0.20 * _norm(m.calmar, *t["calmar"]) +
        0.15 * _norm(m.win_rate, *t["win_rate"])
    )
    m.liquidez_score = float(score)

    if m.n_trades < 30:
        m.warnings.append(f"n_trades={m.n_trades}<30: muestra insuficiente")
    if m.n_bars < 252:
        m.warnings.append(f"n_bars={m.n_bars}<252: < 1 año de datos")

    return m