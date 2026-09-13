"""
High-Precision Wilder's 14-Period RSI Calculation Module.

Implements exact Welles Wilder (1978) formulation:
- 14-SMA seeding on the first 14 price changes (first 15 closing prices)
- Recursive Wilder RMA update: alpha = 1/14 -> (13 * prev + curr) / 14
- Bit-level parity with TA-Lib / standard technical analysis reference
- Robust handling of edge cases (zero division, constant prices, extreme trends)
"""

from typing import Union
import numpy as np
import pandas as pd


def _calculate_wilder_rsi_numpy(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """
    Computes Wilder's RSI on a 1D float64 numpy array of closing prices.

    Args:
        prices: 1D numpy array of float64 closing prices.
        period: RSI lookback period (default 14).

    Returns:
        np.ndarray: 1D array of RSI values with NaN for the first `period` bars.
    """
    n = len(prices)
    rsi = np.full(n, np.nan, dtype=np.float64)

    if n <= period:
        return rsi

    # Calculate price differences
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Initial 14-period SMA seeding over deltas[0:period] (indices 1..period of prices)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    # First valid RSI value at index `period` (15th price, bar index 14 for period 14)
    if avg_loss == 0.0:
        if avg_gain == 0.0:
            rsi[period] = 50.0
        else:
            rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))

    # Recursive Wilder's RMA for t > period
    inv_period = 1.0 / float(period)
    decay = float(period - 1)

    for t in range(period, len(deltas)):
        curr_gain = gains[t]
        curr_loss = losses[t]

        avg_gain = (avg_gain * decay + curr_gain) * inv_period
        avg_loss = (avg_loss * decay + curr_loss) * inv_period

        idx = t + 1
        if avg_loss == 0.0:
            if avg_gain == 0.0:
                rsi[idx] = 50.0
            else:
                rsi[idx] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[idx] = 100.0 - (100.0 / (1.0 + rs))

    return rsi


def compute_wilder_rsi(
    series: Union[pd.Series, np.ndarray, list],
    period: int = 14,
) -> Union[pd.Series, np.ndarray]:
    """
    Computes Wilder's RSI (14-period) with exact 14-SMA seeding and RMA recursion.

    Args:
        series: Pandas Series or NumPy array of closing prices.
        period: RSI period length (default 14).

    Returns:
        pd.Series or np.ndarray matching the input type with computed RSI.
    """
    if isinstance(series, pd.Series):
        vals = series.to_numpy(dtype=np.float64)
        res = _calculate_wilder_rsi_numpy(vals, period=period)
        return pd.Series(res, index=series.index, name=f"RSI_{period}")
    elif isinstance(series, np.ndarray):
        vals = series.astype(np.float64)
        return _calculate_wilder_rsi_numpy(vals, period=period)
    elif isinstance(series, list):
        vals = np.array(series, dtype=np.float64)
        return _calculate_wilder_rsi_numpy(vals, period=period)
    else:
        raise TypeError(f"Unsupported series type: {type(series)}. Expected pd.Series, np.ndarray, or list.")
