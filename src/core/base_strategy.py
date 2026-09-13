"""
Base Strategy Abstract Interface
Defines the standard contract for all quantitative trading strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, strategy_id: str, display_name: str, description: str):
        self.strategy_id = strategy_id
        self.display_name = display_name
        self.description = description
        self.df: Optional[pd.DataFrame] = None

    @abstractmethod
    def load_data(self, data_path: Optional[str] = None) -> pd.DataFrame:
        """Loads and pre-processes required OHLCV and indicator data."""
        pass

    @abstractmethod
    def run_screener(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes daily live screener.
        Returns:
            Dict with keys:
                - strategy_id
                - display_name
                - as_of_date
                - market_regime (e.g., breadth %, gate status)
                - fresh_signals: List[Dict] (symbol, trigger, SL, groww_url, etc.)
                - active_positions: List[Dict]
        """
        pass

    @abstractmethod
    def run_backtest(self) -> Dict[str, Any]:
        """
        Executes full historical backtest.
        Returns:
            Dict with keys:
                - strategy_id
                - kpis: Dict (CAGR, MDD, WinRate, ProfitFactor, Sharpe, etc.)
                - equity_curve: List[Dict] (date, equity, cash, open_slots)
                - trade_log: List[Dict] (symbol, entry_date, exit_date, return_pct, etc.)
        """
        pass
