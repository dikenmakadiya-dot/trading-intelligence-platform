"""
Strategy 3: GFS Multi-Timeframe RSI Swing Engine
Implements BaseStrategy contract.
"""

import os
import sys
import pandas as pd
from typing import Dict, Any, Optional

from src.core.base_strategy import BaseStrategy
from src.core.data_loader import load_master_dataset
from config.groww_mapper import get_groww_chart_url

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from .scanner.daily_screener import scan_daily_signals
from .simulator.backtester import UniverseBacktester
from .analytics.kpi import calculate_strategy_kpis

class Strategy3GFSMTF(BaseStrategy):
    def __init__(self):
        super().__init__(
            strategy_id="gfs_mtf_rsi",
            display_name="GFS Multi-Timeframe RSI Swing Strategy",
            description="Institutional multi-timeframe swing trading engine requiring Monthly RSI > 60, Completed Weekly RSI > 60, and Daily RSI hook in pullback exhaustion zone [35, 48]."
        )

    def load_data(self, data_path: Optional[str] = None) -> pd.DataFrame:
        if self.df is None or data_path:
            self.df = load_master_dataset(data_path)
        return self.df

    def run_screener(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        df = self.load_data()
        all_dates = sorted(df["Date"].unique())
        if not all_dates:
            return {"strategy_id": self.strategy_id, "fresh_signals": []}

        t_date = pd.to_datetime(target_date) if target_date else all_dates[-1]

        try:
            signals_df, _ = scan_daily_signals(target_date=t_date.strftime("%Y-%m-%d"))
        except Exception as e:
            print(f"[Strategy 3] Screener warning: {e}")
            signals_df = pd.DataFrame()

        fresh_signals = []
        if isinstance(signals_df, pd.DataFrame) and not signals_df.empty:
            for rank, (_, row) in enumerate(signals_df.iterrows(), start=1):
                sym = str(row.get("Symbol", ""))
                company = str(row.get("Company_Name", sym))
                c = float(row.get("Current_Close", row.get("Close", 0.0)))
                trigger = float(row.get("Buy_Trigger_Price", row.get("Signal_High", c)))
                sl = float(row.get("Stop_Loss_Price", row.get("Stop_Loss", c * 0.95)))
                daily_rsi = float(row.get("Daily_RSI_14", row.get("Daily_RSI", 0.0)))
                weekly_rsi = float(row.get("Weekly_RSI_14", row.get("Weekly_RSI", 0.0)))
                monthly_rsi = float(row.get("Monthly_RSI_14", row.get("Monthly_RSI", 0.0)))

                fresh_signals.append({
                    "strategy_id": self.strategy_id,
                    "rank": rank,
                    "symbol": sym,
                    "company_name": company,
                    "industry": str(row.get("Industry", "Diversified")),
                    "index_name": str(row.get("Index_Name", "NIFTY 500")),
                    "close": round(c, 2),
                    "entry_trigger": round(trigger, 2),
                    "trailing_sl": round(sl, 2),
                    "daily_rsi": round(daily_rsi, 2),
                    "weekly_rsi": round(weekly_rsi, 2),
                    "monthly_rsi": round(monthly_rsi, 2),
                    "as_of_date": t_date.strftime("%d-%b-%Y"),
                    "groww_chart_url": get_groww_chart_url(sym, company)
                })

        return {
            "strategy_id": self.strategy_id,
            "display_name": self.display_name,
            "as_of_date": t_date.strftime("%d-%b-%Y"),
            "fresh_signals_count": len(fresh_signals),
            "fresh_signals": fresh_signals
        }

    def run_backtest(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "display_name": self.display_name,
            "status": "Backtest engine available via UniverseBacktester"
        }
