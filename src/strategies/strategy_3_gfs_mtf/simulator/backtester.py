"""
Universe Backtester Module.

Orchestrates full-universe backtesting across all 500 Nifty stocks,
providing high performance simulation, structured trade extraction,
and conversion to analysis-ready DataFrames.
"""

from typing import List, Optional, Dict, Any, Union
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import pandas as pd
import numpy as np

from src.strategies.strategy_3_gfs_mtf.simulator.order_engine import (
    TradeRecord,
    OrderEngine,
    simulate_stock_trades,
    ExitReason,
)


TRADE_RECORD_COLUMNS = [
    "symbol",
    "signal_date",
    "signal_high",
    "signal_low",
    "signal_close",
    "entry_date",
    "entry_price",
    "stop_loss",
    "exit_date",
    "exit_price",
    "exit_reason",
    "return_pct",
    "holding_days",
    "holding_calendar_days",
    "planned_risk_pct",
    "r_multiple",
    "is_closed",
    "entry_bar_idx",
    "exit_bar_idx",
]


def trades_to_dataframe(trades: List[TradeRecord]) -> pd.DataFrame:
    """
    Converts a list of TradeRecord objects into a structured pandas DataFrame.

    Args:
        trades: List of TradeRecord instances.

    Returns:
        pd.DataFrame: Formatted DataFrame sorted by entry_date and symbol.
    """
    if not trades:
        return pd.DataFrame(columns=TRADE_RECORD_COLUMNS)

    records = [t.to_dict() for t in trades]
    df = pd.DataFrame(records)

    # Convert date columns to Timestamp
    if "signal_date" in df.columns:
        df["signal_date"] = pd.to_datetime(df["signal_date"])
    if "entry_date" in df.columns:
        df["entry_date"] = pd.to_datetime(df["entry_date"])
    if "exit_date" in df.columns:
        df["exit_date"] = pd.to_datetime(df["exit_date"])

    # Ensure correct column ordering
    cols = [c for c in TRADE_RECORD_COLUMNS if c in df.columns] + [
        c for c in df.columns if c not in TRADE_RECORD_COLUMNS
    ]
    df = df[cols]

    # Sort chronologically by entry_date and symbol
    df = df.sort_values(by=["entry_date", "symbol"], ascending=[True, True]).reset_index(drop=True)
    return df


class UniverseBacktester:
    """
    High-Performance Universe Backtesting Runner.
    Processes multi-stock datasets across 500+ symbols over 5-year periods.
    """

    def __init__(
        self,
        exit_mode: str = "user_momentum_exhaustion",
        sl_atr_buffer: float = 0.2,
        target_rsi_threshold: float = 60.0,
        trail_sl_to_cost: bool = False,
        include_open_trades: bool = False,
    ):
        self.exit_mode = exit_mode
        self.sl_atr_buffer = sl_atr_buffer
        self.target_rsi_threshold = target_rsi_threshold
        self.trail_sl_to_cost = trail_sl_to_cost
        self.include_open_trades = include_open_trades
        self.order_engine = OrderEngine(
            exit_mode=exit_mode,
            sl_atr_buffer=sl_atr_buffer,
            target_rsi_threshold=target_rsi_threshold,
            trail_sl_to_cost=trail_sl_to_cost,
            include_open_trades=include_open_trades,
        )

    def run(self, df_universe: pd.DataFrame) -> List[TradeRecord]:
        """
        Executes backtest across all symbols present in df_universe.

        Args:
            df_universe: DataFrame containing multi-symbol technical data
                         with OHLCV, Daily_RSI_14, and Signal_Candle.

        Returns:
            List[TradeRecord]: Flat list of all executed trades across all symbols.
        """
        if df_universe.empty:
            return []

        all_trades: List[TradeRecord] = []

        if "Symbol" not in df_universe.columns:
            # Single stock case without Symbol column
            return self.order_engine.simulate(df_universe)

        # Iterate over groups per symbol
        for symbol, group in df_universe.groupby("Symbol", sort=False):
            stock_trades = self.order_engine.simulate(group)
            all_trades.extend(stock_trades)

        # Sort all trades by entry_date and symbol
        all_trades.sort(key=lambda t: (t.entry_date, t.symbol))
        return all_trades

    def run_to_dataframe(self, df_universe: pd.DataFrame) -> pd.DataFrame:
        """
        Executes backtest and returns a sorted DataFrame.
        """
        trades = self.run(df_universe)
        return trades_to_dataframe(trades)


def run_universe_backtest(
    df_all: pd.DataFrame,
    exit_mode: str = "user_momentum_exhaustion",
    sl_atr_buffer: float = 0.2,
    target_rsi_threshold: float = 60.0,
    trail_sl_to_cost: bool = False,
    include_open_trades: bool = False,
) -> List[TradeRecord]:
    """
    Standard interface contract function to run the full universe backtest.
    """
    backtester = UniverseBacktester(
        exit_mode=exit_mode,
        sl_atr_buffer=sl_atr_buffer,
        target_rsi_threshold=target_rsi_threshold,
        trail_sl_to_cost=trail_sl_to_cost,
        include_open_trades=include_open_trades,
    )
    return backtester.run(df_all)
