"""
Strategy 1: Champion 3-Day RSI UP + Volume Surge + 52W High Breakout
Implements BaseStrategy contract.
"""

import os
import sys
import pandas as pd
from typing import Dict, Any, Optional

from src.core.base_strategy import BaseStrategy
from src.core.data_loader import load_master_dataset
from config.groww_mapper import get_groww_chart_url
from config.settings import BREADTH_GATE_THRESHOLD

from .strategy_rules import scan_candidate_signals, compute_market_breadth
from .backtest_engine import run_backtest as execute_backtest
from .kpi_calculator import calculate_kpis

class Strategy1RSI52W(BaseStrategy):
    def __init__(self):
        super().__init__(
            strategy_id="rsi_52w_breakout",
            display_name="3-Day RSI UP + 52W High Breakout",
            description="Swing breakout strategy utilizing 3 consecutive days of rising RSI (>=60), 2.5x volume surge, 52-week high proximity, and dynamic Nifty 500 macro market breadth gating."
        )

    def load_data(self, data_path: Optional[str] = None) -> pd.DataFrame:
        if self.df is None or data_path:
            self.df = load_master_dataset(data_path)
        return self.df

    def run_screener(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        df = self.load_data()
        all_dates = sorted(df["Date"].unique())
        if not all_dates:
            return {"strategy_id": self.strategy_id, "fresh_signals": [], "market_regime": {}}

        t_date = pd.to_datetime(target_date) if target_date else all_dates[-1]

        # Compute Market Breadth
        breadth_series = compute_market_breadth(df)
        curr_breadth = float(breadth_series.get(t_date, 0.5)) * 100.0
        gate_open = curr_breadth >= BREADTH_GATE_THRESHOLD

        regime_info = {
            "breadth_pct": round(curr_breadth, 2),
            "gate_open": gate_open,
            "status_label": "AGGRESSIVE (GATE OPEN)" if gate_open else "DEFENSIVE (CASH PROTECTION)"
        }

        # Run candidate signal scanning
        all_signals = scan_candidate_signals(df, variant="champion")
        target_signals = all_signals[all_signals["Date"] == t_date].copy()

        fresh_signals = []
        if not target_signals.empty:
            target_signals.sort_values(by=["RSI_Jump", "Vol_Multiple_Day3"], ascending=[False, False], inplace=True)
            for rank, (_, row) in enumerate(target_signals.iterrows(), start=1):
                sym = str(row["Symbol"])
                company = str(row.get("Company_Name", sym))
                c = float(row["Close"])
                h = float(row["High"])
                atr = float(row.get("ATR_14", 0.03 * c))
                st = float(row.get("SuperTrend", c * 0.95))
                st_sl = round(max(st, h - 1.5 * atr), 2)

                fresh_signals.append({
                    "strategy_id": self.strategy_id,
                    "rank": rank,
                    "symbol": sym,
                    "company_name": company,
                    "industry": str(row.get("Industry", "Diversified")),
                    "index_name": str(row.get("Index_Name", "NIFTY 500")),
                    "close": round(c, 2),
                    "entry_trigger": round(h, 2),
                    "trailing_sl": st_sl,
                    "supertrend": round(st, 2),
                    "day3_rsi": round(float(row["RSI_14"]), 2),
                    "rsi_jump": round(float(row.get("RSI_Jump", 0.0)), 2),
                    "volume_surge": round(float(row.get("Vol_Multiple_Day3", 0.0)), 2),
                    "atr_14": round(atr, 2),
                    "groww_chart_url": get_groww_chart_url(sym, company),
                    "gate_blocked": not gate_open
                })

        return {
            "strategy_id": self.strategy_id,
            "display_name": self.display_name,
            "as_of_date": t_date.strftime("%d-%b-%Y"),
            "market_regime": regime_info,
            "fresh_signals_count": len(fresh_signals),
            "fresh_signals": fresh_signals
        }

    def run_backtest(self) -> Dict[str, Any]:
        df = self.load_data()
        trades_df, equity_df = execute_backtest(df, variant="champion")
        kpis = calculate_kpis(trades_df, equity_df)
        return {
            "strategy_id": self.strategy_id,
            "display_name": self.display_name,
            "kpis": kpis,
            "trades_count": len(trades_df),
            "trade_log": trades_df.to_dict(orient="records"),
            "equity_curve": equity_df.to_dict(orient="records")
        }
