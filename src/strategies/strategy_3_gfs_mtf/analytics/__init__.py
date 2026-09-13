"""
Analytics and Reporting Module for MTF RSI Swing Trading Strategy.
"""

from src.strategies.strategy_3_gfs_mtf.analytics.kpi import (
    StrategyKPIs,
    calculate_strategy_kpis,
)
from src.strategies.strategy_3_gfs_mtf.analytics.reporter import (
    export_trade_logs_csv,
    export_trade_logs_markdown,
    compute_return_distribution,
    compute_holding_duration_distribution,
    compute_sector_performance,
    compute_yearly_performance,
    compute_top_trades,
    compute_stock_performance,
    generate_backtest_report,
)

__all__ = [
    "StrategyKPIs",
    "calculate_strategy_kpis",
    "export_trade_logs_csv",
    "export_trade_logs_markdown",
    "compute_return_distribution",
    "compute_holding_duration_distribution",
    "compute_sector_performance",
    "compute_yearly_performance",
    "compute_top_trades",
    "compute_stock_performance",
    "generate_backtest_report",
]
