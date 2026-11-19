# liquidez_masiva/core/config.py
"""
Carga y validación de config/settings.toml en dataclasses inmutables.
Fallback: tomllib (3.11+) → tomli (3.9/3.10) → error explícito.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Mapping, Type

try:
    import tomllib  # type: ignore[import-not-found]
except ImportError:  # Python < 3.11
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


def _check_unknown_keys(cls: Type, raw: Mapping[str, Any], section: str) -> None:
    """Falla si el TOML trae claves que no existen en la dataclass."""
    known = set(cls.__dataclass_fields__.keys())
    unknown = set(raw.keys()) - known
    if unknown:
        raise ValueError(
            f"Claves desconocidas en [{section}]: {sorted(unknown)}. "
            f"Válidas: {sorted(known)}"
        )


@dataclass(frozen=True)
class DataConfig:
    exchange: str = "binance"
    base_url: str = "https://api.binance.com"
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    history_days: int = 1095
    cache_dir: str = "data/raw"
    request_timeout: float = 30.0
    page_limit: int = 1000
    sleep_between_pages: float = 0.2
    retry_attempts: int = 4


@dataclass(frozen=True)
class StrategyConfig:
    ema_fast: int = 20
    ema_slow: int = 50
    atr_period: int = 14
    donchian_period: int = 20
    vol_zscore_period: int = 50
    vol_zscore_threshold: float = 2.0
    allow_short: bool = True


@dataclass(frozen=True)
class RiskConfig:
    initial_capital: float = 10_000.0
    max_position_pct: float = 0.05
    stop_loss_atr_mult: float = 2.0
    daily_loss_limit_pct: float = 0.03
    leverage: float = 1.0


@dataclass(frozen=True)
class CostConfig:
    fee_rate: float = 0.001
    slippage_bps: float = 5.0
    funding_rate_per_8h: float = 0.0


@dataclass(frozen=True)
class BacktestConfig:
    periods_per_year: int = 365
    min_bars: int = 200
    walk_forward_train_months: int = 12
    walk_forward_test_months: int = 3
    max_equity_points: int = 100_000


@dataclass(frozen=True)
class Config:
    schema_version: int
    data: DataConfig
    strategy: StrategyConfig
    risk: RiskConfig
    cost: CostConfig
    backtest: BacktestConfig

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Config":
        """Construye Config desde dict (tests, Streamlit, migraciones)."""
        data_raw = dict(raw.get("data", {}) or {})
        strat_raw = dict(raw.get("strategy", {}) or {})
        risk_raw = dict(raw.get("risk", {}) or {})
        cost_raw = dict(raw.get("cost", {}) or {})
        bt_raw = dict(raw.get("backtest", {}) or {})

        _check_unknown_keys(DataConfig, data_raw, "data")
        _check_unknown_keys(StrategyConfig, strat_raw, "strategy")
        _check_unknown_keys(RiskConfig, risk_raw, "risk")
        _check_unknown_keys(CostConfig, cost_raw, "cost")
        _check_unknown_keys(BacktestConfig, bt_raw, "backtest")

        cfg = cls(
            schema_version=int(raw.get("schema_version", 1)),
            data=DataConfig(**data_raw),
            strategy=StrategyConfig(**strat_raw),
            risk=RiskConfig(**risk_raw),
            cost=CostConfig(**cost_raw),
            backtest=BacktestConfig(**bt_raw),
        )
        cfg.validate()
        return cfg

    @classmethod
    def from_file(cls, path: str | Path) -> "Config":
        if tomllib is None:
            raise RuntimeError(
                "Falta parser TOML. Instalar 'tomli' (Python<3.11) o usar Python 3.11+."
            )
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"No existe la configuración: {p}")
        with open(p, "rb") as f:
            raw: Dict[str, Any] = tomllib.load(f)
        return cls.from_dict(raw)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def validate(self) -> None:
        s = self.strategy
        if s.ema_fast >= s.ema_slow:
            raise ValueError("strategy.ema_fast debe ser < strategy.ema_slow")
        if s.donchian_period < 5:
            raise ValueError("strategy.donchian_period debe ser >= 5")
        if s.vol_zscore_period < 2:
            raise ValueError("strategy.vol_zscore_period debe ser >= 2")
        r = self.risk
        if not (0 < r.max_position_pct <= 1):
            raise ValueError("risk.max_position_pct debe estar en (0, 1]")
        if r.initial_capital <= 0:
            raise ValueError("risk.initial_capital debe ser > 0")
        if r.leverage <= 0:
            raise ValueError("risk.leverage debe ser > 0")
        c = self.cost
        if not (0 <= c.fee_rate < 1):
            raise ValueError("cost.fee_rate debe estar en [0, 1)")
        if c.slippage_bps < 0:
            raise ValueError("cost.slippage_bps debe ser >= 0")
        if self.backtest.min_bars < 50:
            raise ValueError("backtest.min_bars debe ser >= 50")