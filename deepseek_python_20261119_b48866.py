# liquidez_masiva/app/streamlit_app.py
"""
Dashboard Streamlit para Liquidez Masiva.
Ejecutar con:
    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.backtest import run_backtest                     # noqa: E402
from core.config import Config                              # noqa: E402
from core.data import fetch_klines, load_cache, save_cache  # noqa: E402
from core.metrics import compute_metrics                    # noqa: E402
from core.report import build_report, save_trades_csv       # noqa: E402
from core.strategy import generate_signals                  # noqa: E402

st.set_page_config(page_title="Liquidez Masiva", layout="wide",
                   initial_sidebar_state="expanded")

st.title("Liquidez Masiva — Research & Backtest")
st.caption("Liquidity Breakout Strategy · datos públicos · modo research")


@st.cache_data(ttl=3600, show_spinner=False)
def _load_data(symbol: str, interval: str, days: int) -> pd.DataFrame:
    cfg = Config.from_file(ROOT / "config" / "settings.toml")
    data_cfg = replace(cfg.data, symbol=symbol, interval=interval,
                       history_days=days)
    cached = load_cache(data_cfg)
    if cached is not None and not cached.empty:
        # P1: la cache debe cubrir el rango solicitado
        needed_start = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
        if cached.index[0] <= needed_start:
            return cached
    df = fetch_klines(data_cfg)
    try:
        save_cache(df, data_cfg)
    except Exception:
        pass
    return df


def _sidebar():
    st.sidebar.header("Parámetros")
    # P0: usar st.sidebar.form (no st.form conteniendo st.sidebar.*)
    with st.sidebar.form("params"):
        symbol = st.text_input("Símbolo", "BTCUSDT")
        interval = st.selectbox("Intervalo", ["1h", "4h", "1d"], index=0)
        days = st.number_input("Días de histórico", 90, 3650, 730)
        capital = st.number_input("Capital inicial (USD)",
                                  100.0, 1_000_000.0, 10_000.0)
        max_pos = st.slider("Máx. posición (% capital)",
                            0.01, 0.20, 0.05, 0.01)
        stop_mult = st.slider("Stop-loss (×ATR)", 0.5, 5.0, 2.0, 0.5)
        fee = st.slider("Fee (taker)", 0.0, 0.005, 0.001, 0.0005)
        slip = st.slider("Slippage (bps)", 0.0, 50.0, 5.0, 1.0)
        allow_short = st.checkbox("Permitir shorts", value=True)
        submitted = st.form_submit_button("Ejecutar backtest")
    return {
        "symbol": symbol, "interval": interval, "days": int(days),
        "capital": float(capital), "max_pos": float(max_pos),
        "stop_mult": float(stop_mult), "fee": float(fee),
        "slip": float(slip), "allow_short": bool(allow_short),
        "submitted": submitted,
    }


def _run(p: dict) -> None:
    try:
        cfg = Config.from_file(ROOT / "config" / "settings.toml")
        data_cfg = replace(cfg.data, symbol=p["symbol"],
                           interval=p["interval"], history_days=p["days"])
        strat_cfg = replace(cfg.strategy, allow_short=p["allow_short"])
        risk_cfg = replace(cfg.risk, initial_capital=p["capital"],
                           max_position_pct=p["max_pos"],
                           stop_loss_atr_mult=p["stop_mult"])
        cost_cfg = replace(cfg.cost, fee_rate=p["fee"],
                           slippage_bps=p["slip"])

        with st.spinner("Descargando datos…"):
            df = _load_data(data_cfg.symbol, data_cfg.interval,
                            data_cfg.history_days)

        with st.spinner("Generando señales…"):
            signals = generate_signals(df, strat_cfg)

        with st.spinner("Ejecutando backtest…"):
            result = run_backtest(df, signals, risk_cfg, cost_cfg, cfg.backtest)
            metrics = compute_metrics(result.equity, result.trades,
                                      cfg.backtest.periods_per_year)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Liquidez Score",
                  f"{metrics.liquidez_score:.1f}"
                  if metrics.liquidez_score is not None else "N/D")
        c2.metric("Sharpe", f"{metrics.sharpe:.2f}"
                  if metrics.sharpe is not None else "N/D")
        c3.metric("Max DD",
                  f"{metrics.max_drawdown*100:.1f}%"
                  if metrics.max_drawdown is not None else "N/D")
        c4.metric("Win Rate",
                  f"{metrics.win_rate*100:.1f}%"
                  if metrics.win_rate is not None else "N/D")

        for w in metrics.warnings:
            st.warning(w)

        st.subheader("Curva de equity")
        if result.equity.empty:
            st.info("Sin datos de equity.")
        else:
            st.line_chart(result.equity, height=260)
            cummax = result.equity.cummax()
            dd = (result.equity - cummax) / cummax
            st.subheader("Drawdown")
            st.area_chart(dd, height=180)

        st.subheader("Trades")
        if result.trades:
            rows = [asdict(t) for t in result.trades]
            st.dataframe(pd.DataFrame(rows), height=280,
                         use_container_width=True)
        else:
            st.info("Sin trades en el período.")

        report = build_report(result, metrics, {
            "symbol": data_cfg.symbol, "interval": data_cfg.interval,
            "fee_rate": cost_cfg.fee_rate, "slippage_bps": cost_cfg.slippage_bps,
            "max_position_pct": risk_cfg.max_position_pct,
            "stop_loss_atr_mult": risk_cfg.stop_loss_atr_mult,
        })
        st.download_button("Descargar JSON",
                           data=json.dumps(report, indent=2, default=str),
                           file_name="report.json", mime="application/json")
        if result.trades:
            csv_path = ROOT / "reports" / "trades.csv"
            try:
                save_trades_csv(result, csv_path)
                st.download_button("Descargar CSV",
                                   data=csv_path.read_bytes(),
                                   file_name="trades.csv", mime="text/csv")
            except Exception:
                pass

    except Exception as e:
        st.error(f"Error en el backtest: {e}")


def main() -> None:
    try:
        p = _sidebar()
        if p["submitted"]:
            _run(p)
        else:
            st.info("Configura parámetros y pulsa **Ejecutar backtest**.")
    except Exception as e:
        st.error(f"Error en la UI: {e}")


if __name__ == "__main__":
    main()