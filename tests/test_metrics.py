# liquidez_masiva/tests/test_metrics.py
import numpy as np
import pandas as pd
import pytest

from core.backtest import Trade
from core.metrics import compute_metrics


def _trade(pnl, pnl_R=0.0, reason="signal"):
    ts = pd.Timestamp("2022-01-01", tz="UTC")
    return Trade(entry_ts=ts, exit_ts=ts, side="long",
                 entry_price=100.0, exit_price=100.0 + pnl / 10,
                 qty=10.0, fees=0.0, pnl=pnl, pnl_R=pnl_R,
                 exit_reason=reason)


def test_empty_equity_returns_warnings():
    m = compute_metrics(pd.Series(dtype=float), [])
    assert m.n_trades == 0
    assert m.warnings


def test_zero_volatility_returns_none_sharpe():
    eq = pd.Series([100.0] * 100, index=pd.date_range("2022-01-01", periods=100, freq="1h"))
    m = compute_metrics(eq, [])
    assert m.sharpe is None
    assert m.sortino is None


def test_max_drawdown_non_positive():
    eq = pd.Series([100, 110, 105, 120, 90, 130],
                   index=pd.date_range("2022-01-01", periods=6, freq="1h"))
    m = compute_metrics(eq, [])
    assert m.max_drawdown is not None
    assert m.max_drawdown <= 0


def test_profit_factor_with_only_wins_is_none():
    eq = pd.Series([100, 110, 120, 130],
                   index=pd.date_range("2022-01-01", periods=4, freq="1h"))
    trades = [_trade(10), _trade(10)]
    m = compute_metrics(eq, trades)
    assert m.profit_factor is None


def test_expectancy_sign():
    eq = pd.Series([100 + i for i in range(50)],
                   index=pd.date_range("2022-01-01", periods=50, freq="1h"))
    trades = [_trade(10, pnl_R=2.0), _trade(-5, pnl_R=-1.0)]
    m = compute_metrics(eq, trades)
    assert m.expectancy_R is not None
    assert m.expectancy_R > 0  # (0.5*2 + 0.5*(-1)) = 0.5
