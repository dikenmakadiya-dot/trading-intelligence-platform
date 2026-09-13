"""
Universal Data Loader for NIFTY 750 Technical Dataset
"""

import os
import sys
from pathlib import Path
from typing import Optional, List
import pandas as pd

from config.settings import DEFAULT_MASTER_CSV

def load_master_dataset(filepath: Optional[str] = None, columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Loads and standardizes the Nifty 750 historical dataset.
    """
    path = Path(filepath or DEFAULT_MASTER_CSV)
    if not path.exists():
        raise FileNotFoundError(f"Master technical dataset not found at: {path}")

    df = pd.read_csv(path, usecols=columns, low_memory=False)

    # Standardize Date column
    if "Date" in df.columns:
        if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
            df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y", errors="coerce")
            if df["Date"].isna().sum() > 0:
                df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Date"]).copy()

    # Sort chronologically by Symbol and Date
    if "Symbol" in df.columns and "Date" in df.columns:
        df = df.sort_values(by=["Symbol", "Date"]).reset_index(drop=True)

    # Ensure numeric columns
    numeric_cols = [
        "Open", "High", "Low", "Close", "Volume",
        "SMA_10", "SMA_20", "SMA_50", "SMA_100", "SMA_150", "SMA_200",
        "EMA_10", "EMA_20", "EMA_50", "EMA_100", "EMA_150", "EMA_200",
        "RSI_14", "ATR_14", "MACD", "MACD_Signal", "MACD_Hist",
        "BB_Upper", "BB_Middle", "BB_Lower",
        "SuperTrend", "SuperTrend_Dir", "ADX_14", "Plus_DI_14", "Minus_DI_14"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
