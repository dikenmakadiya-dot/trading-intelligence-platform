"""
Top-level entrypoint for the Daily Live Stock Scanner.
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.strategies.strategy_3_gfs_mtf.scanner.daily_screener import scan_daily_signals, DEFAULT_DATA_PATH


def main():
    parser = argparse.ArgumentParser(description="Daily Live Stock Scanner for MTF RSI Swing Trading Strategy")
    parser.add_argument("--date", type=str, default=None, help="Target date to scan (YYYY-MM-DD or DD-MM-YYYY). Default: latest date in CSV")
    parser.add_argument("--capital", type=float, default=100000.0, help="Capital allocation per trade slot in INR (default: 100000.0)")
    parser.add_argument("--daily-rsi-min", type=float, default=35.0, help="Daily RSI lower bound (default: 35.0)")
    parser.add_argument("--daily-rsi-max", type=float, default=48.0, help="Daily RSI upper bound (default: 48.0)")
    parser.add_argument("--sl-atr-buffer", type=float, default=0.2, help="ATR buffer multiplier for Stop Loss (default: 0.2)")
    parser.add_argument("--data-path", type=str, default=DEFAULT_DATA_PATH, help="Path to historical technical dataset")
    args = parser.parse_args()

    scan_daily_signals(
        data_path=args.data_path,
        target_date=args.date,
        slot_capital=args.capital,
        daily_rsi_min=args.daily_rsi_min,
        daily_rsi_max=args.daily_rsi_max,
        sl_atr_buffer=args.sl_atr_buffer,
    )


if __name__ == "__main__":
    main()
