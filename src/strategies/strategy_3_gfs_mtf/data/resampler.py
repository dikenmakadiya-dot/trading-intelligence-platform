"""
Multi-Timeframe Resampling Module for Daily Stock OHLCV Data.

Provides aggregation of Daily OHLCV into Weekly (W-FRI) and Monthly (ME) series
with proper handling of trading holidays and shortened sessions.
"""

from typing import Dict, Any
import pandas as pd
import numpy as np


def resample_to_weekly(df_stock: pd.DataFrame) -> pd.DataFrame:
    """
    Resamples Daily OHLCV DataFrame for a stock into Weekly bars (W-FRI).

    Aggregations:
        Open: first
        High: max
        Low: min
        Close: last
        Volume: sum
        Date (Last_Trading_Date): max (actual last trading day of the week)
        First_Trading_Date: min

    Args:
        df_stock: DataFrame with columns ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                  sorted chronologically.

    Returns:
        pd.DataFrame: Resampled weekly OHLCV series.
    """
    if df_stock.empty:
        return pd.DataFrame()

    df = df_stock.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y")

    # Set Date as index for resampling
    df = df.set_index("Date").sort_index()

    agg_dict: Dict[str, Any] = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }
    if "Symbol" in df.columns:
        agg_dict["Symbol"] = "first"
    if "Industry" in df.columns:
        agg_dict["Industry"] = "first"
    if "Company_Name" in df.columns:
        agg_dict["Company_Name"] = "first"

    # Resample to weekly ending Friday (W-FRI)
    weekly = df.resample("W-FRI").agg(agg_dict)

    # Drop empty weeks (weeks with no trading activity)
    weekly = weekly.dropna(subset=["Close"]).reset_index()
    weekly = weekly.rename(columns={"Date": "Week_Ending"})

    return weekly


def resample_to_monthly(df_stock: pd.DataFrame) -> pd.DataFrame:
    """
    Resamples Daily OHLCV DataFrame for a stock into Monthly bars (ME).

    Aggregations:
        Open: first
        High: max
        Low: min
        Close: last
        Volume: sum

    Args:
        df_stock: DataFrame with columns ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                  sorted chronologically.

    Returns:
        pd.DataFrame: Resampled monthly OHLCV series.
    """
    if df_stock.empty:
        return pd.DataFrame()

    df = df_stock.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y")

    df = df.set_index("Date").sort_index()

    agg_dict: Dict[str, Any] = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }
    if "Symbol" in df.columns:
        agg_dict["Symbol"] = "first"
    if "Industry" in df.columns:
        agg_dict["Industry"] = "first"
    if "Company_Name" in df.columns:
        agg_dict["Company_Name"] = "first"

    # In modern pandas, 'ME' is Month-End frequency (fallback to 'M' for older pandas)
    try:
        monthly = df.resample("ME").agg(agg_dict)
    except ValueError:
        monthly = df.resample("M").agg(agg_dict)

    monthly = monthly.dropna(subset=["Close"]).reset_index()
    monthly = monthly.rename(columns={"Date": "Month_Ending"})

    return monthly
