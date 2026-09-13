"""
Daily Live Stock Scanner & Order Sheet Generator.
Multi-Timeframe RSI Swing Trading Strategy.

Scans the Nifty 500 universe for active Signal Candles on the latest market close
and exports actionable Buy Stop and Stop Loss order levels with position sizing.
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Optional, Tuple
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.strategies.strategy_3_gfs_mtf.data.loader import load_nifty500_data, discover_latest_historical_dataset
from src.strategies.strategy_3_gfs_mtf.indicators.mtf_engine import process_universe_mtf
from src.strategies.strategy_3_gfs_mtf.scanner.signal_tracker import (
    consolidate_existing_signal_files,
    track_signal_performance,
    generate_signal_report_html,
)

DEFAULT_DATA_PATH = discover_latest_historical_dataset()
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "live_signals")


def scan_daily_signals(
    data_path: str = DEFAULT_DATA_PATH,
    target_date: Optional[str] = None,
    slot_capital: float = 100000.0,
    daily_rsi_min: float = 35.0,
    daily_rsi_max: float = 48.0,
    sl_atr_buffer: float = 0.2,
    require_green_candle: bool = True,
    require_rsi_hook: bool = True,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> Tuple[pd.DataFrame, str]:
    """
    Executes daily screening across the universe for the specified or latest date.
    Consolidates all signals into a single master file with Signal_Date in column 1,
    tracks post-signal performance, and generates the warm HTML Signal Report.
    """
    print("=" * 85)
    print(" V3: MTF RSI HOOK + MOMENTUM EXHAUSTION + ATR BUFFER — DAILY LIVE SCANNER")
    print("=" * 85)
    print(f" Dataset Path       : {data_path}")
    print(f" Strategy Setup     : Monthly RSI > 60 | Weekly RSI > 60 | Daily RSI [{daily_rsi_min}, {daily_rsi_max}]")
    print(f" Confirmation Rules : Green Candle (Close > Open) = {require_green_candle} | RSI Hook = {require_rsi_hook}")
    print(f" Stop Loss Setup    : Signal Low - {sl_atr_buffer} * ATR_14 (Noise Buffer)")
    print(f" Trade Slot Capital : Rs. {slot_capital:,.2f}")
    print("=" * 85)

    # 1. Ingestion
    print(f"\n[Step 1/3] Loading Historical Technical Dataset ({os.path.basename(data_path)})...")
    df_raw = load_nifty500_data(data_path, validate=False)
    num_symbols = df_raw["Symbol"].nunique() if "Symbol" in df_raw.columns else 1
    print(f"  -> Successfully loaded {len(df_raw):,} bars across {num_symbols} tickers.")
    available_dates = df_raw["Date"].drop_duplicates().sort_values()
    latest_market_date = available_dates.iloc[-1]

    # Resolve scan target date
    if target_date:
        parsed_target_date = pd.to_datetime(target_date)
        if parsed_target_date not in available_dates.values:
            closest = available_dates[available_dates <= parsed_target_date]
            if not closest.empty:
                scan_dt = closest.iloc[-1]
                print(f"  -> Requested date '{target_date}' not found. Using closest trading day: {scan_dt.strftime('%Y-%m-%d')}")
            else:
                scan_dt = latest_market_date
                print(f"  -> Requested date '{target_date}' out of range. Using latest date: {scan_dt.strftime('%Y-%m-%d')}")
        else:
            scan_dt = parsed_target_date
    else:
        scan_dt = latest_market_date

    scan_date_str = scan_dt.strftime("%Y-%m-%d")
    print(f"  -> Screening Market Close Date: {scan_date_str}")

    # 2. Multi-Timeframe Indicator & Confirmation Engine
    print("\n[Step 2/3] Processing Multi-Timeframe RSI & Screener Rules...")
    df_aug = process_universe_mtf(
        df_raw,
        daily_rsi_min=daily_rsi_min,
        daily_rsi_max=daily_rsi_max,
        require_green_candle=require_green_candle,
        require_rsi_hook=require_rsi_hook,
    )

    # Filter for target date & Signal_Candle == True
    day_signals = df_aug[(df_aug["Date"] == scan_dt) & (df_aug["Signal_Candle"] == True)].copy()

    # 3. Order Sheet Generation
    print(f"\n[Step 3/3] Generating Actionable Order Sheet ({len(day_signals)} Stocks Triggered)...")
    records = []
    if not day_signals.empty:
        for _, row in day_signals.iterrows():
            sym = row["Symbol"]
            comp = row.get("Company_Name", sym)
            ind = row.get("Industry", "Unclassified")
            
            close_px = float(row["Close"])
            raw_high = float(row["High"])
            raw_low = float(row["Low"])
            
            buy_trigger = round(raw_high, 2)
            atr_val = float(row.get("ATR_14", 0.0))
            stop_loss = round(raw_low - (sl_atr_buffer * atr_val), 2)
            
            risk_per_share = round(buy_trigger - stop_loss, 2)
            planned_risk_pct = round((risk_per_share / buy_trigger) * 100.0, 2) if buy_trigger > 0 else 0.0
            
            d_rsi = round(float(row["Daily_RSI_14"]), 2) if pd.notnull(row["Daily_RSI_14"]) else 0.0
            w_rsi = round(float(row["Weekly_RSI_Completed"]), 2) if pd.notnull(row["Weekly_RSI_Completed"]) else 0.0
            m_rsi = round(float(row["Monthly_RSI_Completed"]), 2) if pd.notnull(row["Monthly_RSI_Completed"]) else 0.0
            
            # Position sizing
            qty = max(1, int(slot_capital // buy_trigger)) if buy_trigger > 0 else 0
            pos_val = round(qty * buy_trigger, 2)
            max_loss = round(qty * risk_per_share, 2)
            
            # Put Signal_Date as the FIRST column
            records.append({
                "Signal_Date": scan_date_str,
                "Symbol": sym,
                "Company_Name": comp,
                "Industry": ind,
                "Current_Close": round(close_px, 2),
                "Buy_Trigger_Price": round(buy_trigger, 2),
                "Stop_Loss_Price": round(stop_loss, 2),
                "ATR_14": round(atr_val, 2),
                "Risk_Per_Share_Rs": risk_per_share,
                "Planned_Risk_Pct": planned_risk_pct,
                "Daily_RSI_14": d_rsi,
                "Weekly_RSI_Completed": w_rsi,
                "Monthly_RSI_Completed": m_rsi,
                "Suggested_Quantity_1Lakh": qty,
                "Est_Position_Value_Rs": pos_val,
                "Est_Max_Loss_Rs": max_loss,
            })
            
        out_df = pd.DataFrame(records)
        out_df = out_df.sort_values(by=["Planned_Risk_Pct", "Daily_RSI_14"], ascending=[True, True]).reset_index(drop=True)
    else:
        out_df = pd.DataFrame(columns=[
            "Signal_Date", "Symbol", "Company_Name", "Industry", "Current_Close", "Buy_Trigger_Price",
            "Stop_Loss_Price", "ATR_14", "Risk_Per_Share_Rs", "Planned_Risk_Pct", "Daily_RSI_14",
            "Weekly_RSI_Completed", "Monthly_RSI_Completed", "Suggested_Quantity_1Lakh",
            "Est_Position_Value_Rs", "Est_Max_Loss_Rs"
        ])

    # 4. Signal Performance Tracking & Consolidation
    existing_signals = consolidate_existing_signal_files(output_dir)
    if not out_df.empty:
        if not existing_signals.empty:
            combined_signals = pd.concat([existing_signals, out_df], ignore_index=True)
            combined_signals = combined_signals.drop_duplicates(subset=["Signal_Date", "Symbol"]).reset_index(drop=True)
        else:
            combined_signals = out_df.copy()
    else:
        combined_signals = existing_signals.copy()

    # Track performance against subsequent bars (sorted old to latest)
    if not combined_signals.empty:
        tracked_signals_df = track_signal_performance(combined_signals, df_raw)
    else:
        tracked_signals_df = pd.DataFrame()

    consolidated_csv_path = os.path.join(output_dir, "consolidated_signals.csv")
    tracked_signals_df.to_csv(consolidated_csv_path, index=False)

    # 5. Generate Warm-Themed HTML Signal Report
    html_report_path = os.path.join(output_dir, "signal_report.html")
    generate_signal_report_html(tracked_signals_df, html_report_path)

    print(f"  -> Saved Master Consolidated Signals: {consolidated_csv_path}")
    print(f"  -> Generated Signal Efficacy Report: {html_report_path}")

    # Print Summary Table
    print("\n" + "=" * 105)
    print(f"                     ACTIONABLE ORDER SHEET — MARKET CLOSE: {scan_date_str}")
    print("=" * 105)
    if out_df.empty:
        print(" [!] No stocks currently qualified on this date. Re-run after next market close.")
    else:
        header = f"{'Symbol':<12} | {'Close (Rs)':<10} | {'Buy Trigger':<11} | {'Stop Loss':<10} | {'Risk %':<8} | {'Daily RSI':<10} | {'Qty (1L)':<8} | {'Industry':<25}"
        print(header)
        print("-" * 105)
        for _, r in out_df.iterrows():
            row_str = f"{r['Symbol']:<12} | {r['Current_Close']:<10.2f} | {r['Buy_Trigger_Price']:<11.2f} | {r['Stop_Loss_Price']:<10.2f} | {r['Planned_Risk_Pct']:<7.2f}% | {r['Daily_RSI_14']:<10.2f} | {r['Suggested_Quantity_1Lakh']:<8} | {r['Industry'][:25]:<25}"
            print(row_str)
    print("\n [Order Instructions for Next Trading Day (T+1)]:")
    print("  1. Place 'BUY STOP' order at 'Buy_Trigger_Price' before market open.")
    print("  2. If triggered, set 'STOP LOSS' at 'Stop_Loss_Price' (includes 0.2*ATR noise buffer).")
    print("  3. If High is NOT breached on T+1, cancel the order at market close.")
    print("  4. Target Exit (V3 Momentum Exhaustion): When Daily RSI reaches >= 60.0, ride position until either (a) RSI drops < 60, or (b) 2 down RSI days + 3rd day Red candle at Close.")
    print("=" * 105 + "\n")

    return out_df, scan_date_str


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily Live Stock Scanner for MTF RSI Strategy")
    parser.add_argument("--date", type=str, default=None, help="Target date to scan (YYYY-MM-DD). Default: latest date in CSV")
    parser.add_argument("--capital", type=float, default=100000.0, help="Capital allocation per slot in INR (default: 100000.0)")
    parser.add_argument("--data-path", type=str, default=DEFAULT_DATA_PATH, help="Path to Nifty 500 historical technical CSV")
    args = parser.parse_args()

    scan_daily_signals(
        data_path=args.data_path,
        target_date=args.date,
        slot_capital=args.capital,
    )
