"""
Master Entrypoint for Multi-Timeframe RSI Swing Trading Strategy Backtesting Suite.

Orchestrates:
1. Historical Dataset Ingestion & Validation
2. Multi-Timeframe (MTF) RSI Engine (Zero Look-Ahead Bias)
3. Full Universe Deterministic Backtesting (500 Stocks)
4. Comprehensive KPI Performance Analytics
5. Artifact Generation (trade_logs.csv, trade_logs.md, backtest_report.md)
"""

import os
import sys
import time
import argparse
from typing import Optional
import numpy as np
import pandas as pd

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.strategies.strategy_3_gfs_mtf.data.loader import load_nifty500_data, discover_latest_historical_dataset
from src.strategies.strategy_3_gfs_mtf.indicators.mtf_engine import process_universe_mtf
from src.strategies.strategy_3_gfs_mtf.simulator.backtester import UniverseBacktester, trades_to_dataframe
from src.strategies.strategy_3_gfs_mtf.analytics.kpi import calculate_strategy_kpis
from src.strategies.strategy_3_gfs_mtf.analytics.reporter import (
    export_trade_logs_csv,
    export_trade_logs_markdown,
    generate_backtest_report,
    generate_backtest_report_html,
)

DEFAULT_DATA_PATH = discover_latest_historical_dataset()
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "historical_backtest")



def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Nifty 500 Multi-Timeframe RSI Swing Trading Strategy Backtest"
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=DEFAULT_DATA_PATH,
        help="Path to 5-year Nifty 500 historical technical data CSV",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save output trade logs and reports",
    )
    parser.add_argument(
        "--rsi-period",
        type=int,
        default=14,
        help="Lookback period for Wilder's RSI (default: 14)",
    )
    parser.add_argument(
        "--monthly-rsi",
        type=float,
        default=60.0,
        help="Monthly completed RSI threshold (default: 60.0)",
    )
    parser.add_argument(
        "--weekly-rsi",
        type=float,
        default=60.0,
        help="Weekly completed RSI threshold (default: 60.0)",
    )
    parser.add_argument(
        "--daily-rsi-min",
        type=float,
        default=35.0,
        help="Daily RSI lower bound for pullback zone (default: 35.0)",
    )
    parser.add_argument(
        "--daily-rsi-max",
        type=float,
        default=48.0,
        help="Daily RSI upper bound for pullback zone (default: 48.0)",
    )
    parser.add_argument(
        "--require-green-candle",
        action="store_true",
        default=True,
        help="Require Close > Open on signal candle (default: True)",
    )
    parser.add_argument(
        "--require-rsi-hook",
        action="store_true",
        default=True,
        help="Require Daily RSI(T) > Daily RSI(T-1) on signal candle (default: True)",
    )
    parser.add_argument(
        "--exit-mode",
        type=str,
        default="user_momentum_exhaustion",
        choices=["user_momentum_exhaustion", "hard_rsi_60"],
        help="Target exit mode: 'user_momentum_exhaustion' or 'hard_rsi_60' (default: user_momentum_exhaustion)",
    )
    parser.add_argument(
        "--sl-atr-buffer",
        type=float,
        default=0.2,
        help="Multiplier for ATR buffer subtracted from Signal_Low (default: 0.2)",
    )
    parser.add_argument(
        "--trail-sl-to-cost",
        action="store_true",
        default=False,
        help="Trail stop loss to entry price once RSI reaches 60 (default: False)",
    )
    parser.add_argument(
        "--target-rsi",
        type=float,
        default=60.0,
        help="Daily RSI threshold for target profit exit (default: 60.0)",
    )
    parser.add_argument(
        "--include-open-trades",
        action="store_true",
        help="Whether to include trades still open at end of data",
    )
    return parser.parse_args()


def run_pipeline(
    data_path: str = DEFAULT_DATA_PATH,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    rsi_period: int = 14,
    monthly_rsi: float = 60.0,
    weekly_rsi: float = 60.0,
    daily_rsi_min: float = 35.0,
    daily_rsi_max: float = 48.0,
    require_green_candle: bool = True,
    require_rsi_hook: bool = True,
    exit_mode: str = "user_momentum_exhaustion",
    sl_atr_buffer: float = 0.2,
    target_rsi: float = 60.0,
    trail_sl_to_cost: bool = False,
    include_open_trades: bool = False,
):
    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 80)
    print(" V3: MTF RSI HOOK + MOMENTUM EXHAUSTION + ATR BUFFER (PRODUCTION) — MASTER PIPELINE")
    print("=" * 80)
    print(f" Dataset Path       : {data_path}")
    print(f" Output Directory   : {output_dir}")
    print(f" MTF Strategy Setup : Monthly RSI > {monthly_rsi} | Weekly RSI > {weekly_rsi} | Daily RSI [{daily_rsi_min}, {daily_rsi_max}]")
    print(f" Confirmation Rules : Green Candle (Close > Open) = {require_green_candle} | RSI Hook (RSI_T > RSI_T-1) = {require_rsi_hook}")
    print(f" Exit & SL Setup    : Exit Mode = {exit_mode} | SL = Signal_Low - {sl_atr_buffer}*ATR | Target RSI = {target_rsi}")
    print("=" * 80)

    # 1. Ingestion
    print(f"\n[Step 1/5] Loading Historical Technical Dataset ({os.path.basename(data_path)})...")
    t0 = time.time()
    df_raw = load_nifty500_data(data_path, validate=True)
    num_rows = len(df_raw)
    num_symbols = df_raw["Symbol"].nunique() if "Symbol" in df_raw.columns else 1
    date_min = df_raw["Date"].min().strftime("%Y-%m-%d")
    date_max = df_raw["Date"].max().strftime("%Y-%m-%d")
    print(f"  -> Ingested {num_rows:,} bars across {num_symbols} tickers ({date_min} to {date_max}) in {time.time() - t0:.2f}s")

    # Extract symbol metadata for reporting
    meta_cols = [c for c in ["Symbol", "Company_Name", "Industry"] if c in df_raw.columns]
    symbol_meta = df_raw[meta_cols].drop_duplicates(subset=["Symbol"]) if "Symbol" in df_raw.columns else None

    # 2. MTF RSI Engine
    print("\n[Step 2/5] Running Multi-Timeframe RSI Engine (Zero Look-Ahead Bias)...")
    t0 = time.time()
    df_mtf = process_universe_mtf(
        df_universe=df_raw,
        rsi_period=rsi_period,
        monthly_rsi_threshold=monthly_rsi,
        weekly_rsi_threshold=weekly_rsi,
        daily_rsi_min=daily_rsi_min,
        daily_rsi_max=daily_rsi_max,
        require_green_candle=require_green_candle,
        require_rsi_hook=require_rsi_hook,
    )
    total_signals = int(df_mtf["Signal_Candle"].sum()) if "Signal_Candle" in df_mtf.columns else 0
    print(f"  -> Processed {len(df_mtf):,} bars across {num_symbols} tickers.")
    print(f"  -> Total Signal Candles Identified: {total_signals:,} signals in {time.time() - t0:.2f}s")

    # 3. Deterministic Simulation
    print("\n[Step 3/5] Executing 5-State Deterministic Order Simulation...")
    t0 = time.time()
    backtester = UniverseBacktester(
        exit_mode=exit_mode,
        sl_atr_buffer=sl_atr_buffer,
        target_rsi_threshold=target_rsi,
        trail_sl_to_cost=trail_sl_to_cost,
        include_open_trades=include_open_trades,
    )
    trades = backtester.run(df_mtf)
    trades_df = trades_to_dataframe(trades)
    print(f"  -> Executed {len(trades):,} total trades across universe in {time.time() - t0:.2f}s")

    # 4. KPI Analytics Engine
    print("\n[Step 4/5] Computing Performance Scorecard & Statistical KPIs...")
    t0 = time.time()
    kpis = calculate_strategy_kpis(trades_df)
    print(f"  -> KPI Analytics computed successfully in {time.time() - t0:.2f}s")

    # 5. Report & Log Exporters
    print("\n[Step 5/5] Generating Trade Logs, Distribution Tables & Executive Reports (MD + HTML)...")
    t0 = time.time()
    csv_path = os.path.join(output_dir, "trade_logs.csv")
    md_logs_path = os.path.join(output_dir, "trade_logs.md")
    report_path = os.path.join(output_dir, "backtest_report.md")
    html_report_path = os.path.join(output_dir, "backtest_report.html")

    export_trade_logs_csv(trades_df, csv_path, symbol_metadata=symbol_meta)
    export_trade_logs_markdown(trades_df, md_logs_path, symbol_metadata=symbol_meta)
    generate_backtest_report(kpis, trades_df, report_path, symbol_metadata=symbol_meta)
    generate_backtest_report_html(kpis, trades_df, html_report_path, symbol_metadata=symbol_meta)

    print(f"  -> Exported: {csv_path}")
    print(f"  -> Exported: {md_logs_path}")
    print(f"  -> Exported: {report_path}")
    print(f"  -> Exported: {html_report_path}")
    print(f"  -> Reporting artifacts generated in {time.time() - t0:.2f}s")


    total_time = time.time() - start_time

    # Display Terminal Summary
    print("\n" + "=" * 80)
    print("                     BACKTEST PERFORMANCE SCORECARD")
    print("=" * 80)
    print(f" Total Trades Taken       : {kpis.total_trades}")
    print(f" Winning / Losing Trades  : {kpis.winning_trades} Wins / {kpis.losing_trades} Losses ({kpis.breakeven_trades} Breakeven)")
    print(f" Win Ratio                : {kpis.win_ratio:.2f}%")
    print(f" Realized Risk-to-Reward  : {kpis.realized_risk_reward_ratio:.2f} : 1")
    print(f" Average Planned R:R      : {kpis.avg_r_multiple:.2f}R")
    print(f" Average Return per Trade : {kpis.avg_return_pct:+.2f}%")
    print(f" Lowest / Highest Return  : {kpis.lowest_return_pct:+.2f}% / {kpis.highest_return_pct:+.2f}%")
    print(f" Profit Factor            : {kpis.profit_factor:.2f}")
    print(f" Strategy Expectancy      : {kpis.strategy_expectancy_pct:+.2f}% per trade ({kpis.strategy_expectancy_r:+.2f}R)")
    print(f" Average Investment Span  : {kpis.avg_holding_days:.1f} Trading Days ({kpis.min_holding_days} Min / {kpis.max_holding_days} Max)")
    print(f" Total Cumulative Return  : {kpis.total_return_pct:+.2f}%")
    print(f" Maximum Drawdown         : {kpis.max_drawdown_pct:.2f}%")
    print(f" Stop Loss / Target Exits : {kpis.sl_trades_count} SL / {kpis.target_trades_count} Target")
    print("=" * 80)
    print(f" Total Pipeline Run Time  : {total_time:.2f} seconds")
    print("=" * 80 + "\n")

    return kpis, trades_df


def main():
    args = parse_args()
    run_pipeline(
        data_path=args.data_path,
        output_dir=args.output_dir,
        rsi_period=args.rsi_period,
        monthly_rsi=args.monthly_rsi,
        weekly_rsi=args.weekly_rsi,
        daily_rsi_min=args.daily_rsi_min,
        daily_rsi_max=args.daily_rsi_max,
        require_green_candle=args.require_green_candle,
        require_rsi_hook=args.require_rsi_hook,
        exit_mode=args.exit_mode,
        sl_atr_buffer=args.sl_atr_buffer,
        target_rsi=args.target_rsi,
        trail_sl_to_cost=args.trail_sl_to_cost,
        include_open_trades=args.include_open_trades,
    )


if __name__ == "__main__":
    main()
