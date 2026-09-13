"""
Simulator Module for Trade Execution State Machine and Backtesting Engine.
"""

from src.strategies.strategy_3_gfs_mtf.simulator.order_engine import (
    TradeRecord,
    OrderState,
    ExitReason,
    OrderEngine,
    simulate_stock_trades,
)
from src.strategies.strategy_3_gfs_mtf.simulator.backtester import (
    UniverseBacktester,
    run_universe_backtest,
    trades_to_dataframe,
    TRADE_RECORD_COLUMNS,
)

__all__ = [
    "TradeRecord",
    "OrderState",
    "ExitReason",
    "OrderEngine",
    "simulate_stock_trades",
    "UniverseBacktester",
    "run_universe_backtest",
    "trades_to_dataframe",
    "TRADE_RECORD_COLUMNS",
]
