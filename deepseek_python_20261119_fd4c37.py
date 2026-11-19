# liquidez_masiva/core/backtest.py
"""
Motor de backtest event-driven, sin look-ahead.

Reglas de ejecución:
  · Señal en vela t → orden pendiente.
  · Orden se ejecuta al open[t+1] + slippage.
  · Stop-loss chequeado contra low[t] (long) / high[t] (short).
  · Comisión aplicada en ambas patas (entrada y salida).
  · Entradas con ATR inválido (NaN/0) se DESCARTAN (no hay stop posible).

Liquidación final: la posición abierta se cierra al último close CON
slippage aplicado, para no sobreestimar PnL.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from .config import BacktestConfig, CostConfig, RiskConfig
from .risk import position_qty, risk_per_share, stop_price
from .utils import safe_div


@dataclass
class Trade:
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    side: str
    entry_price: float
    exit_price: float
    qty: float
    fees: float
    pnl: float
    pnl_R: Optional[float]
    exit_reason: str


@dataclass
class BacktestResult:
    equity: pd.Series
    trades: List[Trade]
    bars: int
    initial_capital: float

    @classmethod
    def empty(cls, initial_capital: float) -> "BacktestResult":
        return cls(
            equity=pd.Series(dtype=float),
            trades=[],
            bars=0,
            initial_capital=initial_capital,
        )


def _apply_slippage(price: float, is_buy: bool, slippage_bps: float) -> float:
    """Aplica slippage en la dirección del side."""
    slip = slippage_bps / 10_000.0
    return price * (1.0 + slip) if is_buy else price * (1.0 - slip)


def run_backtest(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    risk: RiskConfig,
    cost: CostConfig,
    bt: BacktestConfig,
) -> BacktestResult:
    """Ejecuta el backtest sobre df (OHLCV) + signals."""
    if df.empty or signals.empty:
        return BacktestResult.empty(risk.initial_capital)
    if len(df) < bt.min_bars:
        raise ValueError(f"Dataset muy corto: {len(df)} < min_bars={bt.min_bars}")

    common = df.index.intersection(signals.index)
    if len(common) < bt.min_bars:
        return BacktestResult.empty(risk.initial_capital)
    df = df.loc[common]
    signals = signals.loc[common]

    n = len(df)
    cash = float(risk.initial_capital)
    pos = 0.0
    entry_price = 0.0
    entry_ts: Optional[pd.Timestamp] = None
    stop = 0.0
    risk_per_unit = 0.0

    o = df["open"].to_numpy()
    h = df["high"].to_numpy()
    lo = df["low"].to_numpy()
    c = df["close"].to_numpy()
    idx = df.index
    atrs = signals["atr"].to_numpy(dtype=float)
    le = signals["long_entry"].to_numpy(dtype=bool)
    lx = signals["long_exit"].to_numpy(dtype=bool)
    se = signals["short_entry"].to_numpy(dtype=bool)
    sx = signals["short_exit"].to_numpy(dtype=bool)

    equity = np.empty(n, dtype=float)
    trades: List[Trade] = []

    pending: Optional[Tuple[str, str]] = None  # (kind, side)
    fee = cost.fee_rate
    slip = cost.slippage_bps

    def _record_trade(exit_p: float, ts: pd.Timestamp, reason: str) -> None:
        nonlocal cash, pos, entry_price, entry_ts, stop, risk_per_unit
        if pos > 0:
            gross = (exit_p - entry_price) * pos
        else:
            gross = (entry_price - exit_p) * abs(pos)
        fees = (entry_price * abs(pos) + exit_p * abs(pos)) * fee
        pnl = gross - fees
        risk_money = risk_per_unit * abs(pos)
        pnl_R = safe_div(pnl, risk_money)
        trades.append(Trade(
            entry_ts=entry_ts,  # type: ignore[arg-type]
            exit_ts=ts,
            side="long" if pos > 0 else "short",
            entry_price=entry_price,
            exit_price=exit_p,
            qty=abs(pos),
            fees=fees,
            pnl=pnl,
            pnl_R=pnl_R,
            exit_reason=reason,
        ))
        if pos > 0:
            cash += pos * exit_p * (1 - fee)
        else:
            cash -= abs(pos) * exit_p * (1 + fee)
        pos = 0.0
        entry_price = 0.0
        entry_ts = None
        stop = 0.0
        risk_per_unit = 0.0

    for t in range(n):
        # --- 1. Ejecutar pendiente al open[t] ---
        if pending is not None:
            kind, side = pending
            pending = None
            if kind == "entry" and pos == 0.0:
                atr_prev = float(atrs[t - 1]) if t >= 1 else 0.0
                # P0: entrada con ATR inválido → se descarta (no hay stop posible)
                if np.isfinite(atr_prev) and atr_prev > 0:
                    if side == "long":
                        exec_p = _apply_slippage(o[t], is_buy=True,
                                                 slippage_bps=slip)
                        q = position_qty(cash, exec_p,
                                         risk.max_position_pct, risk.leverage)
                        if q > 0 and q * exec_p * (1 + fee) <= cash:
                            cash -= q * exec_p * (1 + fee)
                            pos = q
                            entry_price = exec_p
                            entry_ts = idx[t]
                            stop = stop_price(exec_p, "long", atr_prev,
                                              risk.stop_loss_atr_mult)
                            risk_per_unit = risk_per_share(
                                atr_prev, risk.stop_loss_atr_mult)
                    elif side == "short":
                        exec_p = _apply_slippage(o[t], is_buy=False,
                                                 slippage_bps=slip)
                        q = position_qty(cash, exec_p,
                                         risk.max_position_pct, risk.leverage)
                        if q > 0:
                            cash += q * exec_p * (1 - fee)
                            pos = -q
                            entry_price = exec_p
                            entry_ts = idx[t]
                            stop = stop_price(exec_p, "short", atr_prev,
                                              risk.stop_loss_atr_mult)
                            risk_per_unit = risk_per_share(
                                atr_prev, risk.stop_loss_atr_mult)
            elif kind == "exit" and pos != 0.0:
                is_buy = pos < 0
                exec_p = _apply_slippage(o[t], is_buy=is_buy,
                                         slippage_bps=slip)
                _record_trade(exec_p, idx[t], "signal")

        # --- 2. Chequear stop dentro de la vela t ---
        if pos > 0 and stop > 0 and lo[t] <= stop:
            exec_p = _apply_slippage(stop, is_buy=False, slippage_bps=slip)
            _record_trade(exec_p, idx[t], "stop")
        elif pos < 0 and stop > 0 and h[t] >= stop:
            exec_p = _apply_slippage(stop, is_buy=True, slippage_bps=slip)
            _record_trade(exec_p, idx[t], "stop")

        # --- 3. Mark-to-market ---
        equity[t] = cash + pos * c[t]

        # --- 4. Generar pendiente para t+1 ---
        if t + 1 < n and pending is None:
            if pos == 0.0:
                if le[t]:
                    pending = ("entry", "long")
                elif se[t]:
                    pending = ("entry", "short")
            elif pos > 0 and lx[t]:
                pending = ("exit", "long")
            elif pos < 0 and sx[t]:
                pending = ("exit", "short")

    # Liquidar posición abierta al final con slippage
    if pos != 0.0:
        if pos > 0:
            exec_p = _apply_slippage(float(c[-1]), is_buy=False,
                                     slippage_bps=slip)
        else:
            exec_p = _apply_slippage(float(c[-1]), is_buy=True,
                                     slippage_bps=slip)
        _record_trade(exec_p, idx[-1], "end")
        equity[-1] = cash

    equity_series = pd.Series(equity, index=idx, name="equity")
    return BacktestResult(equity=equity_series, trades=trades,
                          bars=n, initial_capital=risk.initial_capital)