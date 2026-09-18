"""
Data Loader Module for Nifty 500 5-Year Historical Technical Dataset.

Provides high-speed ingestion, strict DD-MM-YYYY date parsing, memory optimization,
and comprehensive integrity validation.
"""

from typing import List, Optional
import os
import pandas as pd
import numpy as np


DEFAULT_OHLCV_COLS = [
    "Symbol",
    "Company_Name",
    "Industry",
    "ISIN_Code",
    "Date",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
]

CORE_REQUIRED_COLS = ["Symbol", "Date", "Open", "High", "Low", "Close", "Volume"]


def validate_ohlcv_data(df: pd.DataFrame) -> bool:
    """
    Validates OHLCV DataFrame integrity:
    1. Checks for missing / null values in core required columns.
    2. Verifies logical price bounds: Low <= Open <= High, Low <= Close <= High, Low <= High.
    3. Verifies non-negative prices and volume.
    4. Verifies strictly monotonic chronological ordering per symbol.

    Raises:
        ValueError: If any validation rule is violated.

    Returns:
        bool: True if validation passes.
    """
    for col in CORE_REQUIRED_COLS:
        if col not in df.columns:
            raise ValueError(f"Missing required column: '{col}' in DataFrame.")
        if df[col].isnull().any():
            null_count = df[col].isnull().sum()
            raise ValueError(f"Found {null_count} null/NaN values in required column '{col}'.")

    # Verify price bounds
    if not (df["Low"] <= df["High"] + 1e-6).all():
        invalid = df[df["Low"] > df["High"] + 1e-6]
        raise ValueError(f"Found {len(invalid)} records where Low > High.")

    if not ((df["Low"] <= df["Open"] + 1e-6) & (df["Open"] <= df["High"] + 1e-6)).all():
        invalid = df[(df["Open"] < df["Low"] - 1e-6) | (df["Open"] > df["High"] + 1e-6)]
        raise ValueError(f"Found {len(invalid)} records where Open is outside [Low, High].")

    if not ((df["Low"] <= df["Close"] + 1e-6) & (df["Close"] <= df["High"] + 1e-6)).all():
        invalid = df[(df["Close"] < df["Low"] - 1e-6) | (df["Close"] > df["High"] + 1e-6)]
        raise ValueError(f"Found {len(invalid)} records where Close is outside [Low, High].")

    if not (df["Close"] > 0).all():
        invalid = df[df["Close"] <= 0]
        raise ValueError(f"Found {len(invalid)} records with non-positive Close price.")

    if not (df["Volume"] >= 0).all():
        invalid = df[df["Volume"] < 0]
        raise ValueError(f"Found {len(invalid)} records with negative Volume.")

    # 4. Verify strictly monotonic chronological ordering per symbol
    if "Symbol" in df.columns and "Date" in df.columns and len(df) > 1:
        date_diffs = df.groupby("Symbol", sort=False)["Date"].diff()
        # Non-null diffs must be strictly positive (> 0)
        invalid_diffs = date_diffs[date_diffs.notnull()]
        if (invalid_diffs <= pd.Timedelta(0)).any():
            # Identify first failing symbol for clear error reporting
            for symbol, grp in df.groupby("Symbol", sort=False):
                if not grp["Date"].is_monotonic_increasing or grp["Date"].duplicated().any():
                    raise ValueError(f"Dates are not strictly monotonically increasing for symbol '{symbol}'.")
            raise ValueError("Dates are not strictly monotonically increasing within each symbol.")

    return True


def discover_latest_historical_dataset(preferred_name: Optional[str] = None) -> str:
    """
    Dynamically scans surrounding directories to discover the latest historical technical dataset.
    Prioritizes active Nifty 750/500 files by latest modification time and file size.
    """
    try:
        from config.settings import REPO_PARQUET_PATH, REPO_CSV_PATH, DEFAULT_MASTER_CSV
        if REPO_PARQUET_PATH.exists():
            return str(REPO_PARQUET_PATH)
        if REPO_CSV_PATH.exists():
            return str(REPO_CSV_PATH)
        if DEFAULT_MASTER_CSV.exists():
            return str(DEFAULT_MASTER_CSV)
    except Exception:
        pass

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    search_dirs = [
        os.path.join(project_root, "data"),
        os.path.abspath(os.path.join(project_root, "..", "5Y Stock Historical Data")),
        os.path.abspath(os.path.join(project_root, "..", "..", "5Y Stock Historical Data")),
        os.path.abspath(os.path.join(project_root, "..", "Stock Historical Data")),
        os.path.abspath(os.path.join(project_root, "..", "..", "Stock Historical Data")),
        os.path.abspath(os.path.join(project_root, "..")),
        project_root,
    ]

    found_files = []
    for d in search_dirs:
        if os.path.exists(d) and os.path.isdir(d):
            for fname in os.listdir(d):
                if (fname.endswith(".parquet") or fname.endswith(".csv")) and ("nifty" in fname.lower() or "technical" in fname.lower() or "historical" in fname.lower()):
                    full_p = os.path.join(d, fname)
                    if os.path.isfile(full_p):
                        try:
                            stat = os.stat(full_p)
                            # Give priority to parquet (3), 750 (2), 500 (1)
                            prio = 3 if fname.endswith(".parquet") else (2 if "750" in fname else (1 if "500" in fname else 0))
                            found_files.append((prio, stat.st_mtime, stat.st_size, full_p))
                        except Exception:
                            pass

    if found_files:
        # Sort by priority desc, mtime desc, size desc
        found_files.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        return found_files[0][3]

    return str(REPO_PARQUET_PATH)


def load_nifty500_data(
    csv_path: Optional[str] = None,
    usecols: Optional[List[str]] = None,
    validate: bool = True,
) -> pd.DataFrame:
    """
    Loads historical technical dataset dynamically with strict date parsing,
    sorting by ['Symbol', 'Date'], and type optimization. Supports both Parquet and CSV.

    Args:
        csv_path: Absolute or relative path to file. If None or not found, dynamically discovers latest file.
        usecols: Optional list of column names to load. If None, loads DEFAULT_OHLCV_COLS.
        validate: Whether to run integrity validation checks.

    Returns:
        pd.DataFrame: Clean, sorted, validated DataFrame.
    """
    if csv_path is None:
        csv_path = discover_latest_historical_dataset()
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Historical dataset not found at: {csv_path}")

    # Read with specified columns
    cols_to_load = usecols if usecols is not None else DEFAULT_OHLCV_COLS
    
    if csv_path.endswith(".parquet"):
        try:
            df = pd.read_parquet(csv_path, columns=cols_to_load)
        except Exception:
            df = pd.read_parquet(csv_path)
            avail = [c for c in cols_to_load if c in df.columns]
            df = df[avail]
    else:
        try:
            df = pd.read_csv(csv_path, usecols=cols_to_load)
        except ValueError:
            df = pd.read_csv(csv_path)
            avail = [c for c in cols_to_load if c in df.columns]
            df = df[avail]

    # Fast explicit format parsing using unique date map
    if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        unique_dates = df["Date"].dropna().unique()
        try:
            date_map = dict(zip(unique_dates, pd.to_datetime(unique_dates, format="%d-%m-%Y")))
            df["Date"] = df["Date"].map(date_map)
        except Exception:
            df["Date"] = pd.to_datetime(df["Date"])

    # Ensure numeric columns are float64 / int64
    for num_col in ["Open", "High", "Low", "Close"]:
        if num_col in df.columns:
            df[num_col] = df[num_col].astype(np.float64)

    if "Volume" in df.columns:
        df["Volume"] = df["Volume"].astype(np.int64)

    # Sort strictly by ['Symbol', 'Date']
    df = df.sort_values(by=["Symbol", "Date"], ascending=[True, True]).reset_index(drop=True)

    if validate:
        validate_ohlcv_data(df)

    return df
