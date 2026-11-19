# liquidez_masiva/core/strategy.py
"""
Liquidity Breakout Strategy:

  Long entry:  z_vol > θ  AND  close > donchian_upper(t-1)  AND  ema_slope > 0
  Long exit:   close < ema_slow
  Short entry: z_vol > θ  AND  close < donchian_lower(t-1)  AND  ema_slope < 0
  Short exit:  close > ema_slow

Sin look-ahead: señales en t se ejecutan en t+1 (ver core/backtest.py).

Nota: long_entry y short_entry son MUTUAMENTE EXCLUYENTES por construcción
(`ema_slope > 0` vs `ema_slope < 0`); no hay necesidad de desempate.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import StrategyConfig
from .indicators import compute_all


def generate_signals(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """
    Devuelve DataFrame con las señales booleanas y el ATR de la vela de señal.
    Columnas: long_entry, long_exit, short_entry, short_exit, atr.
    Entradas con atr NaN o <= 0 se fuerzan a False (defensa en profundidad).
    """
    if len(df) < max(cfg.donchian_period, cfg.vol_zscore_period, cfg.ema_slow) + 5:
        raise ValueError("Dataset demasiado corto para la estrategia.")

    ind = compute_all(df, cfg)

    upper_prev = ind["donchian_upper"].shift(1)
    lower_prev = ind["donchian_lower"].shift(1)

    # ATR válido (finito y > 0) — necesario para calcular stop/riesgo.
    atr_valid = ind["atr"].notna() & (ind["atr"] > 0) & np.isfinite(ind["atr"])

    long_entry = (
        (ind["vol_z"] > cfg.vol_zscore_threshold)
        & (df["close"] > upper_prev)
        & (ind["ema_slope"] > 0)
        & atr_valid
    )
    long_exit = df["close"] < ind["ema_slow"]

    if cfg.allow_short:
        short_entry = (
            (ind["vol_z"] > cfg.vol_zscore_threshold)
            & (df["close"] < lower_prev)
            & (ind["ema_slope"] < 0)
            & atr_valid
        )
        short_exit = df["close"] > ind["ema_slow"]
    else:
        short_entry = pd.Series(False, index=df.index)
        short_exit = pd.Series(False, index=df.index)

    signals = pd.DataFrame({
        "long_entry": long_entry.fillna(False).astype(bool),
        "long_exit": long_exit.fillna(False).astype(bool),
        "short_entry": short_entry.fillna(False).astype(bool),
        "short_exit": short_exit.fillna(False).astype(bool),
        "atr": ind["atr"],
    }, index=df.index)
    return signals