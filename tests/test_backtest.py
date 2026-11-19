# liquidez_masiva/tests/test_backtest.py
import numpy as np
import pandas as pd
import pytest

from core.backtest import run_backtest
from core.config import BacktestConfig, CostConfig, RiskConfig


def _synthetic_df(n=300, seed=7):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + 0.5
    low = close - 0.5
    idx = pd.date_range("2022-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame(
        {"open": close, "high": high, "low": low, "close": close,
         "volume": rng.uniform(100, 1000, n)},
        index=idx,
    )


def _signals_from(df, atr_value=1.0):
    long_entry = pd.Series(False, index=df.index)
    long_exit = pd.Series(False, index=df.index)
    long_entry.iloc[10] = True
    long_exit.iloc[20] = True
    return pd.DataFrame({
        "long_entry": long_entry,
        "long_exit": long_exit,
        "short_entry": False,
        "short_exit": False,
        "atr": atr_value,
    }, index=df.index)


def test_backtest_no_trades_when_no_signal():
    df = _synthetic_df(200)
    signals = pd.DataFrame({
        "long_entry": False, "long_exit": False,
        "short_entry": False, "short_exit": False,
        "atr": 1.0,
    }, index=df.index)
    result = run_backtest(df, signals,
                          RiskConfig(initial_capital=10_000),
                          CostConfig(), BacktestConfig(min_bars=50))
    assert len(result.trades) == 0
    assert abs(result.equity.iloc[-1] - 10_000) < 1e-6


def test_backtest_entry_at_open_t_plus_1():
    df = _synthetic_df(200)
    signals = _signals_from(df)
    result = run_backtest(df, signals,
                          RiskConfig(initial_capital=10_000,
                                     max_position_pct=0.1),
                          CostConfig(fee_rate=0.0, slippage_bps=0.0),
                          BacktestConfig(min_bars=50))
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert abs(trade.entry_price - df["open"].iloc[11]) < 1e-6


def test_stop_loss_triggers_and_reduces_loss():
    df = _synthetic_df(200)
    df.loc[df.index[12], "low"] = df["close"].iloc[11] - 5.0
    signals = pd.DataFrame({
        "long_entry": [i == 10 for i in range(len(df))],
        "long_exit": False,
        "short_entry": False,
        "short_exit": False,
        "atr": 1.0,
    }, index=df.index)
    result = run_backtest(df, signals,
                          RiskConfig(initial_capital=10_000,
                                     stop_loss_atr_mult=2.0),
                          CostConfig(fee_rate=0.0, slippage_bps=0.0),
                          BacktestConfig(min_bars=50))
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "stop"


# --- P0: pnl_R en stops no es None cuando ATR es válido ---
def test_stop_pnl_R_is_not_none():
    df = _synthetic_df(200)
    df.loc[df.index[12], "low"] = df["close"].iloc[11] - 5.0
    signals = pd.DataFrame({
        "long_entry": [i == 10 for i in range(len(df))],
        "long_exit": False,
        "short_entry": False,
        "short_exit": False,
        "atr": 1.0,
    }, index=df.index)
    result = run_backtest(df, signals,
                          RiskConfig(initial_capital=10_000,
                                     stop_loss_atr_mult=2.0),
                          CostConfig(fee_rate=0.0, slippage_bps=0.0),
                          BacktestConfig(min_bars=50))
    trade = result.trades[0]
    assert trade.exit_reason == "stop"
    assert trade.pnl_R is not None  # NO debe ser None
    assert trade.pnl_R < 0


# --- P0: entradas con ATR NaN se descartan (no se abre posición) ---
def test_entry_skipped_when_atr_is_nan():
    df = _synthetic_df(200)
    signals = pd.DataFrame({
        "long_entry": [i == 10 for i in range(len(df))],
        "long_exit": False,
        "short_entry": False,
        "short_exit": False,
        "atr": np.nan,  # ATR inválido
    }, index=df.index)
    result = run_backtest(df, signals,
                          RiskConfig(initial_capital=10_000),
                          CostConfig(),
                          BacktestConfig(min_bars=50))
    assert len(result.trades) == 0


# --- P1: liquidación final aplica slippage ---
def test_final_liquidation_applies_slippage():
    df = _synthetic_df(200)
    # Entrada en 10, sin exit → se liquida al final
    signals = pd.DataFrame({
        "long_entry": [i == 10 for i in range(len(df))],
        "long_exit": False,
        "short_entry": False,
        "short_exit": False,
        "atr": 1.0,
    }, index=df.index)
    # Sin slippage
    r_no_slip = run_backtest(
        df, signals,
        RiskConfig(initial_capital=10_000, max_position_pct=0.1),
        CostConfig(fee_rate=0.0, slippage_bps=0.0),
        BacktestConfig(min_bars=50),
    )
    # Con slippage alto
    r_slip = run_backtest(
        df, signals,
        RiskConfig(initial_capital=10_000, max_position_pct=0.1),
        CostConfig(fee_rate=0.0, slippage_bps=50.0),
        BacktestConfig(min_bars=50),
    )
    assert r_no_slip.trades[0].exit_reason == "end"
    assert r_slip.trades[0].exit_reason == "end"
    # Con slippage el PnL debe ser peor (o igual si el trade es 0)
    assert r_slip.trades[0].pnl <= r_no_slip.trades[0].pnl + 1e-9
