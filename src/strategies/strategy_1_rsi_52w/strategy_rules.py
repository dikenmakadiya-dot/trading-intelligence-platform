import pandas as pd
import numpy as np
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    RSI_MIN_DAY3,
    VOL_SMA_PERIOD,
    VOL_SURGE_MULTIPLE,
    VOL_3DAY_AVG_MULTIPLE,
    USE_52W_FILTER,
    PROXIMITY_52W_PCT,
    LOOKBACK_52W_DAYS,
    USE_MARKET_BREADTH,
    MARKET_BREADTH_THRESHOLD,
)


def compute_market_breadth(df: pd.DataFrame) -> pd.Series:
    """
    Computes daily macro market breadth as the percentage of Nifty 500 stocks with Close > EMA 50.
    Returns a pd.Series indexed by Date with breadth values from 0.0 to 1.0.
    """
    if "Index_Name" in df.columns and "EMA_50" in df.columns:
        nifty500_mask = df["Index_Name"] == "NIFTY 500"
        breadth = df[nifty500_mask].groupby("Date").apply(lambda g: (g["Close"] > g["EMA_50"]).mean())
    elif "EMA_50" in df.columns:
        breadth = df.groupby("Date").apply(lambda g: (g["Close"] > g["EMA_50"]).mean())
    else:
        breadth = pd.Series(1.0, index=df["Date"].unique())
    return breadth


def scan_candidate_signals(
    df: pd.DataFrame,
    variant: str = "champion",  # 'champion', 'trend_aligned', or 'pure_momentum'
) -> pd.DataFrame:
    """
    Scans daily historical technical data for qualifying Day-3 setup breakout signals.
    """
    data = df.copy()

    # Ensure sorted by Symbol and Date
    data.sort_values(by=["Symbol", "Date"], inplace=True)
    data.reset_index(drop=True, inplace=True)

    # 10-day rolling volume average per symbol
    data["Vol_SMA10"] = data.groupby("Symbol")["Volume"].transform(
        lambda x: x.rolling(VOL_SMA_PERIOD).mean()
    )

    # Lagged RSI and Volume values
    data["RSI_Lag1"] = data.groupby("Symbol")["RSI_14"].shift(1)  # Day 2
    data["RSI_Lag2"] = data.groupby("Symbol")["RSI_14"].shift(2)  # Day 1

    data["Vol_Lag1"] = data.groupby("Symbol")["Volume"].shift(1)
    data["Vol_Lag2"] = data.groupby("Symbol")["Volume"].shift(2)
    data["Vol_3Day_Avg"] = (data["Volume"] + data["Vol_Lag1"] + data["Vol_Lag2"]) / 3.0

    # 52-Week Rolling High per symbol
    data["52W_High"] = data.groupby("Symbol")["High"].transform(
        lambda x: x.rolling(LOOKBACK_52W_DAYS, min_periods=50).max()
    )
    data["Near_52W_High"] = data["Close"] >= (PROXIMITY_52W_PCT * data["52W_High"])

    # Condition 1: RSI strictly rising across 3 setup days: Day 1 < Day 2 < Day 3
    cond_rsi_inc = (data["RSI_Lag2"] < data["RSI_Lag1"]) & (data["RSI_Lag1"] < data["RSI_14"])

    # Condition 2: Day-3 RSI >= 60.0 (No upper cap)
    cond_rsi_min = data["RSI_14"] >= RSI_MIN_DAY3

    # Condition 3: Volume surge (Day 3 >= 2.5x SMA10, 3-day average >= 2.5x SMA10)
    data["Vol_Multiple_Day3"] = data["Volume"] / data["Vol_SMA10"]
    cond_vol_day3 = data["Vol_Multiple_Day3"] >= VOL_SURGE_MULTIPLE
    cond_vol_avg = data["Vol_3Day_Avg"] >= (VOL_3DAY_AVG_MULTIPLE * data["Vol_SMA10"])

    # Calculate RSI jump on Day 3 for ranking
    data["RSI_Jump"] = data["RSI_14"] - data["RSI_Lag1"]

    # Base Pure Momentum Signal Mask
    signal_mask = cond_rsi_inc & cond_rsi_min & cond_vol_avg & cond_vol_day3

    # Trend Alignment: SuperTrend Bullish + EMA Trend Alignment
    if variant in ("champion", "trend_aligned"):
        cond_supertrend = data["SuperTrend_Dir"] == 1 if "SuperTrend_Dir" in data.columns else True
        cond_ema_trend = (
            (data["Close"] > data["EMA_20"]) & (data["EMA_20"] > data["EMA_50"])
            if ("EMA_20" in data.columns and "EMA_50" in data.columns)
            else True
        )
        signal_mask = signal_mask & cond_supertrend & cond_ema_trend

    # Champion Enhancement: 52-Week High Proximity Filter
    if variant == "champion" and USE_52W_FILTER:
        signal_mask = signal_mask & data["Near_52W_High"]

    qualifying_signals = data[signal_mask].copy()
    qualifying_signals.reset_index(drop=True, inplace=True)
    return qualifying_signals


def evaluate_candle_signal(row, prev_row, prev2_row, vol_sma10, rolling_52w_high):
    """
    Evaluates a single day's candle for Day-3 setup qualification.
    Used by the daily live screener.
    """
    if prev_row is None or prev2_row is None or pd.isna(vol_sma10) or vol_sma10 <= 0:
        return False, None

    c_t = float(row["Close"])
    h_t = float(row["High"])
    l_t = float(row["Low"])
    o_t = float(row["Open"])
    v_t = float(row["Volume"])

    rsi_t = float(row.get("RSI_14", 0))
    rsi_1 = float(prev_row.get("RSI_14", 0))
    rsi_2 = float(prev2_row.get("RSI_14", 0))

    # 1. 3-Day strictly rising RSI
    if not (rsi_2 < rsi_1 < rsi_t):
        return False, None

    # 2. RSI >= 60
    if rsi_t < RSI_MIN_DAY3:
        return False, None

    # 3. Volume Surge
    v_1 = float(prev_row.get("Volume", 0))
    v_2 = float(prev2_row.get("Volume", 0))
    v_3day_avg = (v_t + v_1 + v_2) / 3.0
    vol_mult = v_t / vol_sma10

    if vol_mult < VOL_SURGE_MULTIPLE or v_3day_avg < (VOL_3DAY_AVG_MULTIPLE * vol_sma10):
        return False, None

    # 4. SuperTrend & EMA Alignment
    st_dir = float(row.get("SuperTrend_Dir", 1))
    ema20 = float(row.get("EMA_20", 0))
    ema50 = float(row.get("EMA_50", 0))
    if st_dir != 1 or not (c_t > ema20 > ema50):
        return False, None

    # 5. 52-Week High Proximity
    if rolling_52w_high > 0 and c_t < (PROXIMITY_52W_PCT * rolling_52w_high):
        return False, None

    atr14 = float(row.get("ATR_14", 0.03 * c_t))
    rsi_jump = rsi_t - rsi_1

    metrics = {
        "day3_close": round(c_t, 2),
        "day3_high": round(h_t, 2),
        "day3_low": round(l_t, 2),
        "day3_open": round(o_t, 2),
        "day3_volume": int(v_t),
        "vol_multiple": round(vol_mult, 2),
        "rsi_day1": round(rsi_2, 2),
        "rsi_day2": round(rsi_1, 2),
        "rsi_day3": round(rsi_t, 2),
        "rsi_jump": round(rsi_jump, 2),
        "day3_atr": round(atr14, 2),
        "rolling_52w_high": round(rolling_52w_high, 2),
        "dist_to_52w_pct": round((c_t / rolling_52w_high - 1.0) * 100.0, 2) if rolling_52w_high > 0 else 0.0,
        "entry_trigger": round(h_t, 2),
        "initial_sl": round(h_t - 1.5 * atr14, 2),
    }

    return True, metrics
