"""
Multi-Timeframe (MTF) RSI Engine & Signal Screener.

Performs point-in-time, look-ahead free alignment of Weekly and Monthly RSI
onto Daily price bars and identifies Swing Trading Strategy Signal Candles.
"""

from typing import Optional
import pandas as pd
import numpy as np

from src.strategies.strategy_3_gfs_mtf.indicators.wilder_rsi import compute_wilder_rsi
from src.strategies.strategy_3_gfs_mtf.data.resampler import resample_to_weekly, resample_to_monthly


def compute_wilder_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Computes 14-period Wilder's Average True Range (ATR)."""
    n = len(close)
    if n < period:
        return np.full(n, np.nan, dtype=np.float64)
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr1 = high - low
    tr2 = np.abs(high - prev_close)
    tr3 = np.abs(low - prev_close)
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    atr = np.full(n, np.nan, dtype=np.float64)
    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def process_stock_mtf(
    df_stock: pd.DataFrame,
    rsi_period: int = 14,
    monthly_rsi_threshold: float = 60.0,
    weekly_rsi_threshold: float = 60.0,
    daily_rsi_min: float = 35.0,
    daily_rsi_max: float = 48.0,
    require_green_candle: bool = True,
    require_rsi_hook: bool = True,
) -> pd.DataFrame:
    """
    Processes a single stock's daily OHLCV dataframe through the MTF RSI engine:
    1. Computes Daily 14-period Wilder's RSI and 14-period Wilder's ATR.
    2. Resamples to Weekly (W-FRI), computes Weekly 14-period Wilder's RSI,
       and aligns the completed previous week's RSI onto daily bars (look-ahead free).
    3. Resamples to Monthly (ME), computes Monthly 14-period Wilder's RSI,
       and aligns the completed previous month's RSI onto daily bars (look-ahead free).
    4. Evaluates Signal Candle condition on Date T:
       Monthly_RSI_Completed > 60.0 AND Weekly_RSI_Completed > 60.0 AND 35.0 <= Daily_RSI_14 <= 48.0
       Plus Green Reversal Candle (Close > Open) and RSI Hook (Daily_RSI_T > Daily_RSI_T-1).

    Args:
        df_stock: DataFrame containing daily OHLCV for a single ticker, sorted by Date.
        rsi_period: Lookback period for Wilder's RSI (default 14).
        monthly_rsi_threshold: Minimum completed monthly RSI for macro bull regime (default 60.0).
        weekly_rsi_threshold: Minimum completed weekly RSI for intermediate bull regime (default 60.0).
        daily_rsi_min: Lower bound for daily RSI pullback zone (default 35.0).
        daily_rsi_max: Upper bound for daily RSI pullback zone (default 48.0).
        require_green_candle: If True, requires Close > Open on Signal Candle (default True).
        require_rsi_hook: If True, requires Daily_RSI_14 > Daily_RSI_14(T-1) (default True).

    Returns:
        pd.DataFrame: Augmented DataFrame with Daily_RSI_14, Weekly_RSI_Completed,
                      Monthly_RSI_Completed, Signal_Candle, Signal_High, Signal_Low, Signal_ATR.
    """
    if df_stock.empty:
        return df_stock.copy()

    df = df_stock.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y")

    # Clean up existing derived columns for idempotency
    cols_to_clean = [
        "Daily_RSI_14",
        "ATR_14",
        "Weekly_RSI_Completed",
        "Monthly_RSI_Completed",
        "Signal_Candle",
        "Signal_High",
        "Signal_Low",
        "Signal_ATR",
    ]
    df = df.drop(columns=[c for c in cols_to_clean if c in df.columns], errors="ignore")

    df = df.sort_values(by="Date", ascending=True).reset_index(drop=True)

    # 1. Compute Daily Wilder's RSI and 14-period ATR
    df["Daily_RSI_14"] = compute_wilder_rsi(df["Close"], period=rsi_period)
    df["ATR_14"] = compute_wilder_atr(
        df["High"].to_numpy(dtype=np.float64),
        df["Low"].to_numpy(dtype=np.float64),
        df["Close"].to_numpy(dtype=np.float64),
        period=14,
    )

    # 2. Resample Weekly & Compute Completed Weekly RSI (Zero Look-Ahead)
    weekly = resample_to_weekly(df)
    if not weekly.empty and len(weekly) > rsi_period:
        weekly["Weekly_RSI_14"] = compute_wilder_rsi(weekly["Close"], period=rsi_period)
        # Effective from the day after the week ending date
        weekly["Weekly_Effective_Date"] = weekly["Week_Ending"] + pd.Timedelta(days=1)
        
        # Merge onto daily using backward asof match
        weekly_align = weekly[["Weekly_Effective_Date", "Weekly_RSI_14"]].dropna().sort_values("Weekly_Effective_Date")
        if not weekly_align.empty:
            df = pd.merge_asof(
                df,
                weekly_align.rename(columns={"Weekly_RSI_14": "Weekly_RSI_Completed"}),
                left_on="Date",
                right_on="Weekly_Effective_Date",
                direction="backward",
            )
            df = df.drop(columns=["Weekly_Effective_Date"], errors="ignore")
        else:
            df["Weekly_RSI_Completed"] = np.nan
    else:
        df["Weekly_RSI_Completed"] = np.nan

    # 3. Resample Monthly & Compute Completed Monthly RSI (Zero Look-Ahead)
    monthly = resample_to_monthly(df)
    if not monthly.empty and len(monthly) > rsi_period:
        monthly["Monthly_RSI_14"] = compute_wilder_rsi(monthly["Close"], period=rsi_period)
        # Effective from the 1st of the next calendar month (day after month end)
        monthly["Monthly_Effective_Date"] = monthly["Month_Ending"] + pd.Timedelta(days=1)
        
        monthly_align = monthly[["Monthly_Effective_Date", "Monthly_RSI_14"]].dropna().sort_values("Monthly_Effective_Date")
        if not monthly_align.empty:
            df = pd.merge_asof(
                df,
                monthly_align.rename(columns={"Monthly_RSI_14": "Monthly_RSI_Completed"}),
                left_on="Date",
                right_on="Monthly_Effective_Date",
                direction="backward",
            )
            df = df.drop(columns=["Monthly_Effective_Date"], errors="ignore")
        else:
            df["Monthly_RSI_Completed"] = np.nan
    else:
        df["Monthly_RSI_Completed"] = np.nan

    # 4. Signal Candle Detection on Date T
    cond_monthly = df["Monthly_RSI_Completed"] > monthly_rsi_threshold
    cond_weekly = df["Weekly_RSI_Completed"] > weekly_rsi_threshold
    cond_daily = (df["Daily_RSI_14"] >= daily_rsi_min) & (df["Daily_RSI_14"] <= daily_rsi_max)

    signal_mask = cond_monthly & cond_weekly & cond_daily

    if require_green_candle:
        cond_green = df["Close"] > df["Open"]
        signal_mask = signal_mask & cond_green

    if require_rsi_hook:
        cond_rsi_hook = df["Daily_RSI_14"] > df["Daily_RSI_14"].shift(1)
        signal_mask = signal_mask & cond_rsi_hook

    df["Signal_Candle"] = signal_mask.fillna(False).astype(bool)

    # Signal reference levels
    df["Signal_High"] = np.where(df["Signal_Candle"], df["High"], np.nan)
    df["Signal_Low"] = np.where(df["Signal_Candle"], df["Low"], np.nan)
    df["Signal_ATR"] = np.where(df["Signal_Candle"], df["ATR_14"], np.nan)

    return df


def process_universe_mtf(
    df_universe: pd.DataFrame,
    rsi_period: int = 14,
    monthly_rsi_threshold: float = 60.0,
    weekly_rsi_threshold: float = 60.0,
    daily_rsi_min: float = 35.0,
    daily_rsi_max: float = 48.0,
    require_green_candle: bool = True,
    require_rsi_hook: bool = True,
) -> pd.DataFrame:
    """
    Processes all stocks in the universe DataFrame through the MTF RSI engine.

    Args:
        df_universe: Combined DataFrame containing OHLCV for all tickers.
        rsi_period: Lookback period for Wilder's RSI (default 14).
        monthly_rsi_threshold: Minimum completed monthly RSI (default 60.0).
        weekly_rsi_threshold: Minimum completed weekly RSI (default 60.0).
        daily_rsi_min: Lower bound for daily RSI pullback zone (default 35.0).
        daily_rsi_max: Upper bound for daily RSI pullback zone (default 48.0).
        require_green_candle: If True, requires Close > Open on Signal Candle (default True).
        require_rsi_hook: If True, requires Daily_RSI_14 > Daily_RSI_14(T-1) (default True).

    Returns:
        pd.DataFrame: Full augmented dataset sorted by ['Symbol', 'Date'].
    """
    if df_universe.empty:
        return pd.DataFrame()

    results = []
    # Group by Symbol without sorting to maintain fast iteration
    for symbol, group in df_universe.groupby("Symbol", sort=False):
        processed_group = process_stock_mtf(
            df_stock=group,
            rsi_period=rsi_period,
            monthly_rsi_threshold=monthly_rsi_threshold,
            weekly_rsi_threshold=weekly_rsi_threshold,
            daily_rsi_min=daily_rsi_min,
            daily_rsi_max=daily_rsi_max,
            require_green_candle=require_green_candle,
            require_rsi_hook=require_rsi_hook,
        )
        results.append(processed_group)

    df_out = pd.concat(results, ignore_index=True)
    df_out = df_out.sort_values(by=["Symbol", "Date"], ascending=[True, True]).reset_index(drop=True)
    return df_out
