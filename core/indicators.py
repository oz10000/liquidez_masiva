# liquidez_masiva/core/indicators.py
"""
Indicadores técnicos puros y vectorizados.
Todas las funciones reciben Series/DataFrame y devuelven Series/DataFrame;
sin efectos secundarios, sin look-ahead bias.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """Media móvil exponencial estándar con adjust=False."""
    return series.ewm(span=period, adjust=False).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range. Usa Wilder smoothing (EMA con alpha=1/period)
    para replicar la convención clásica.
    """
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def donchian(df: pd.DataFrame, period: int = 20) -> tuple[pd.Series, pd.Series]:
    """Canal de Donchian: (upper, lower) sobre high/low rodantes."""
    upper = df["high"].rolling(period, min_periods=period).max()
    lower = df["low"].rolling(period, min_periods=period).min()
    return upper, lower


def zscore(series: pd.Series, period: int) -> pd.Series:
    """Z-score rodante robusto a std≈0 (devuelve NaN en ese caso)."""
    mean = series.rolling(period, min_periods=period).mean()
    std = series.rolling(period, min_periods=period).std(ddof=0)
    safe_std = std.where(std > 1e-12, np.nan)
    return (series - mean) / safe_std


def compute_all(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """Calcula todos los indicadores necesarios para la estrategia."""
    out = df.copy()
    out["ema_fast"] = ema(df["close"], cfg.ema_fast)
    out["ema_slow"] = ema(df["close"], cfg.ema_slow)
    out["ema_slope"] = out["ema_slow"].diff()
    out["atr"] = atr(df, cfg.atr_period)
    upper, lower = donchian(df, cfg.donchian_period)
    out["donchian_upper"] = upper
    out["donchian_lower"] = lower
    out["vol_z"] = zscore(df["volume"], cfg.vol_zscore_period)
    return out
