# liquidez_masiva/core/data.py
"""
Ingesta de OHLCV desde API pública de Binance, con paginación, reintentos
exponenciales y caché local en CSV.

Regla clave: SOLO se ingieren velas cerradas. La vela en curso se excluye
restando un intervalo al timestamp actual.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry  # type: ignore[import-not-found]
except ImportError:
    Retry = None  # type: ignore[assignment,misc]

from .config import DataConfig
from .logging_utils import get_logger

log = get_logger()

INTERVAL_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000,
}
KLINE_COLUMNS = ["open_time", "open", "high", "low", "close", "volume",
                 "close_time", "qav", "trades", "tbb", "tbq", "ignore"]


def _build_session(retries: int) -> requests.Session:
    s = requests.Session()
    if Retry is not None:
        r = Retry(
            total=retries,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            respect_retry_after_header=True,
        )
        s.mount("https://", HTTPAdapter(max_retries=r))
        s.mount("http://", HTTPAdapter(max_retries=r))
    s.headers.update({"User-Agent": "liquidez-masiva/1.0"})
    return s


def _fetch_page(session: requests.Session, base_url: str, symbol: str,
                interval: str, start_ms: int, end_ms: int, limit: int,
                timeout: float) -> list:
    url = f"{base_url}/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": limit,
    }
    r = session.get(url, params=params, timeout=timeout)
    if r.status_code == 400:
        try:
            msg = r.json().get("msg", r.text)
        except Exception:
            msg = r.text
        raise ValueError(
            f"Binance rechazó la petición (symbol={symbol!r}, "
            f"interval={interval!r}): {msg}"
        )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Respuesta inesperada de Binance: {data!r}")
    return data


def fetch_klines(cfg: DataConfig,
                 start_ms: Optional[int] = None,
                 end_ms: Optional[int] = None) -> pd.DataFrame:
    """
    Descarga OHLCV paginado. Devuelve DataFrame indexado por timestamp UTC.
    Por defecto, EXCLUYE la vela en curso (aún no cerrada).
    """
    if cfg.interval not in INTERVAL_MS:
        raise ValueError(f"interval no soportado: {cfg.interval}")
    step_ms = INTERVAL_MS[cfg.interval]

    if start_ms is None:
        start_ms = int((time.time() - cfg.history_days * 86_400) * 1000)
    if end_ms is None:
        # Excluir la vela abierta: retroceder un intervalo.
        end_ms = int(time.time() * 1000) - step_ms

    session = _build_session(cfg.retry_attempts)
    all_rows: list = []
    cursor = start_ms

    while cursor < end_ms:
        try:
            page = _fetch_page(session, cfg.base_url, cfg.symbol, cfg.interval,
                               cursor, end_ms, cfg.page_limit, cfg.request_timeout)
        except ValueError:
            raise  # errores de validación (400) no se reintentan
        except Exception as e:
            log.warning("fetch falló; reintentando", extra={
                "err": str(e), "cursor": cursor})
            time.sleep(2.0)
            continue
        if not page:
            break
        all_rows.extend(page)
        last_close = int(page[-1][6])
        if last_close <= cursor:
            break
        cursor = last_close + 1
        if len(page) < cfg.page_limit:
            break
        time.sleep(cfg.sleep_between_pages)

    if not all_rows:
        raise RuntimeError("No se recibieron velas de la API.")

    df = pd.DataFrame(all_rows, columns=KLINE_COLUMNS)
    df = df[["open_time", "open", "high", "low", "close", "volume"]].copy()
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("timestamp").drop(columns=["open_time"])
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    validate_ohlcv(df)
    return df


def validate_ohlcv(df: pd.DataFrame) -> None:
    """Verifica invariantes OHLCV. Falla rápido si el dataset es inválido."""
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        raise ValueError(f"Faltan columnas OHLCV: {required - set(df.columns)}")
    if df.empty:
        raise ValueError("DataFrame vacío.")
    bad_hl = int((df["high"] < df["low"]).sum())
    bad_h = int((df["high"] < df[["open", "close"]].max(axis=1)).sum())
    bad_l = int((df["low"] > df[["open", "close"]].min(axis=1)).sum())
    if bad_hl or bad_h or bad_l:
        raise ValueError(f"OHLCV inconsistente: hl={bad_hl} h={bad_h} l={bad_l}")
    if (df["volume"] < 0).any():
        raise ValueError("Volumen negativo detectado.")


def cache_path(cfg: DataConfig) -> Path:
    return Path(cfg.cache_dir) / f"{cfg.symbol}_{cfg.interval}.csv"


def save_cache(df: pd.DataFrame, cfg: DataConfig) -> Path:
    path = cache_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=True)
    return path


def load_cache(cfg: DataConfig) -> Optional[pd.DataFrame]:
    path = cache_path(cfg)
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        return df
    except Exception as e:
        log.warning("No se pudo leer cache", extra={"err": str(e)})
        return None
