# liquidez_masiva/core/risk.py
"""
Gestión de riesgo: sizing por fracción de capital, stop-loss por ATR,
kill-switch diario. Funciones puras; el estado (equity, día) lo lleva el
backtest o el runner de paper-trading.

KillSwitchState NO es thread-safe por diseño (un runner por proceso).
"""
from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass
from typing import Optional

from .config import RiskConfig
from .utils import clamp


@dataclass
class KillSwitchState:
    """Estado por sesión para el límite de pérdida diaria."""
    day_start_equity: Optional[float] = None
    day: Optional[_dt.date] = None
    tripped: bool = False

    def _ensure_day(self, current_equity: float, today: _dt.date) -> None:
        if self.day != today:
            self.day = today
            self.day_start_equity = current_equity
            self.tripped = False

    def check(self, current_equity: float, today: _dt.date,
              limit_pct: float) -> bool:
        """True si el trading debe detenerse hoy. Llamar en cada barra."""
        self._ensure_day(current_equity, today)
        if self.tripped:
            return True
        if self.day_start_equity is None or self.day_start_equity <= 0:
            return False
        drawdown = (current_equity - self.day_start_equity) / self.day_start_equity
        if drawdown <= -abs(limit_pct):
            self.tripped = True
            return True
        return False


def position_qty(cash: float, price: float, max_position_pct: float,
                 leverage: float = 1.0) -> float:
    """Cantidad a comprar dado cash, % máximo de notional y apalancamiento."""
    if price <= 0 or cash <= 0:
        return 0.0
    pct = clamp(max_position_pct, 0.0, 1.0)
    notional = cash * pct * clamp(leverage, 0.1, 10.0)
    return notional / price


def stop_price(entry: float, side: str, atr_value: float,
               mult: float) -> float:
    """Precio de stop-loss a N×ATR del entry. NaN/inf → entry (sin stop útil)."""
    if not math.isfinite(atr_value) or atr_value <= 0:
        return entry
    if side == "long":
        return entry - mult * atr_value
    return entry + mult * atr_value


def risk_per_share(atr_value: float, mult: float) -> float:
    """Distancia monetaria por unidad entre entry y stop. NaN/inf → 0."""
    if not math.isfinite(atr_value) or atr_value <= 0:
        return 0.0
    return mult * atr_value


def validate_risk_config(cfg: RiskConfig) -> None:
    if not (0 < cfg.max_position_pct <= 1):
        raise ValueError("max_position_pct fuera de (0, 1]")
    if cfg.stop_loss_atr_mult <= 0:
        raise ValueError("stop_loss_atr_mult debe ser > 0")
    if not (0 < cfg.daily_loss_limit_pct < 1):
        raise ValueError("daily_loss_limit_pct fuera de (0, 1)")