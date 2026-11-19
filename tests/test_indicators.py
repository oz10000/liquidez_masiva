# liquidez_masiva/tests/test_indicators.py
import numpy as np
import pandas as pd
import pytest

from core.indicators import atr, donchian, ema, zscore


def _df(n=100):
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0.1, 1.0, n)
    low = close - rng.uniform(0.1, 1.0, n)
    vol = rng.uniform(100, 1000, n)
    idx = pd.date_range("2022-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame(
        {"open": close, "high": high, "low": low, "close": close, "volume": vol},
        index=idx,
    )


def test_ema_length_and_no_nan_after_warmup():
    s = pd.Series(np.arange(1, 51, dtype=float))
    e = ema(s, 10)
    assert len(e) == len(s)
    assert not e.iloc[10:].isna().any()


def test_atr_positive():
    df = _df(60)
    a = atr(df, 14)
    assert (a.iloc[20:] > 0).all()


def test_donchian_upper_ge_lower():
    df = _df(60)
    u, l = donchian(df, 20)
    mask = u.notna() & l.notna()
    assert (u[mask] >= l[mask]).all()


def test_zscore_zero_std_yields_nan():
    s = pd.Series([5.0] * 30)
    z = zscore(s, 10)
    assert z.iloc[10:].isna().all()


def test_zscore_high_on_spike():
    s = pd.Series([1.0] * 50 + [100.0])
    z = zscore(s, 20)
    assert z.iloc[-1] > 2.0
