"""
Global Configuration & Settings for Quant Trading Intelligence Platform
"""

import os
from pathlib import Path

# Base Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
TRADING_ROOT = REPO_ROOT.parent

BASE_DIR = REPO_ROOT
CONFIG_DIR = REPO_ROOT / "config"
SRC_DIR = REPO_ROOT / "src"
OUTPUT_DIR = REPO_ROOT / "output"
BACKTEST_OUTPUT_DIR = OUTPUT_DIR / "backtest_results"
LIVE_SIGNALS_OUTPUT_DIR = OUTPUT_DIR / "live_signals"

# Ensure output directories exist
for p in [OUTPUT_DIR, BACKTEST_OUTPUT_DIR, LIVE_SIGNALS_OUTPUT_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# Historical Data Paths
HISTORICAL_DATA_DIR = TRADING_ROOT / "5Y Stock Historical Data"
DEFAULT_MASTER_CSV = HISTORICAL_DATA_DIR / "nifty750_historical_technical_data_5y.csv"
DEFAULT_MASTER_XLSX = HISTORICAL_DATA_DIR / "nifty750_historical_technical_data_5y.xlsx"
DATA_FILE_PATH = DEFAULT_MASTER_CSV

CONSOLIDATED_SIGNALS_JSON = OUTPUT_DIR / "consolidated_signals.json"
STRATEGY_SUMMARY_JSON = OUTPUT_DIR / "strategy_summary.json"

# Universal Strategy Portfolio Settings
INITIAL_CAPITAL = 1000000.0          # INR 10 Lakh starting capital
MAX_OPEN_POSITIONS = 5               # 5 concurrent positions (20% equity per slot)
POSITION_SIZE_FRACTION = 0.20        # 20% target allocation per trade
USE_COMPOUNDING = True               # Dynamic equity compounding
COST_PER_ROUND_TRIP = 0.0015         # 0.15% friction (brokerage + STT + slippage)
RISK_FREE_RATE = 0.065               # 6.5% Annual Risk-Free Rate for Sharpe Ratio

# Market Breadth Configuration
BREADTH_GATE_THRESHOLD = 50.0        # Entry gate opens when >= 50% Nifty 500 stocks > EMA50
USE_MARKET_BREADTH = True
MARKET_BREADTH_THRESHOLD = 0.50

# Strategy 1 (3-Day RSI UP + 52W High Breakout) Settings
RSI_MIN_DAY3 = 60.0                  # Minimum RSI on Day 3 (no upper cap)
VOL_SMA_PERIOD = 10                  # Volume SMA baseline period
VOL_SURGE_MULTIPLE = 2.5             # Day 3 volume >= 2.5x SMA10
VOL_3DAY_AVG_MULTIPLE = 2.5          # 3-day average volume >= 2.5x SMA10
USE_52W_FILTER = True
PROXIMITY_52W_PCT = 0.90             # Day 3 Close within 10% of 52-week rolling high
LOOKBACK_52W_DAYS = 252
ENTRY_MODE = "breakout_high"
ATR_SL_MULTIPLIER = 1.5              # Dynamic Stop Loss: Entry - 1.5x ATR(14)
TRAIL_EXIT_MODE = "supertrend"
STAGNATION_EXIT_DAYS = 15            # Exit after 15 days if gain < +3.0%
STAGNATION_MIN_GAIN = 0.03

# Strategy 2 (5-Year High Breakout Clean Candle) Settings
LOOKBACK_YEARS = 5
BACKTEST_START_DATE = "2024-08-25"
VOLUME_SURGE_MULTIPLIER = 3.0        # Breakout volume >= 3x previous day
RSI_INCREASE_MIN = 8.0               # RSI increases by >= 8 points
CLEAN_CANDLE_BODY_RATIO = 0.40       # Body >= 40% of high-low range (Marubozu quality filter)
PROFIT_TARGET_PCT = 0.08             # +8.0% fixed profit target
MAX_HOLDING_DAYS = 10                # 10 trading days maximum time-stop
