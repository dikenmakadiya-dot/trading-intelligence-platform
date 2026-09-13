"""
Strategy 2: 5-Year High Breakout Momentum (Clean Candle Quality Filter)
Implements BaseStrategy contract.
"""

import os
import sys
import pandas as pd
from typing import Dict, Any, Optional

from src.core.base_strategy import BaseStrategy
from src.core.data_loader import load_master_dataset
from config.groww_mapper import get_groww_chart_url

from .strategy_rules import scan_all_signals
from .backtest_engine import run_backtest as execute_backtest
from .kpi_calculator import calculate_kpis

class Strategy2CleanCandle5Y(BaseStrategy):
    def __init__(self):
        super().__init__(
            strategy_id="clean_candle_5y",
            display_name="5-Year High Breakout (Clean Candle Quality Filter)",
            description="Momentum breakout system detecting multi-year highs confirmed by >=3.0x volume surge, RSI impulse (+8 pts), and clean solid-body green candle filter (>=40% body ratio)."
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

        lookback_start = (t_date - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
        raw_signals = scan_all_signals(df, start_date=lookback_start)

        fresh_signals = []
        if raw_signals:
            all_signals_df = pd.DataFrame(raw_signals)
            if not all_signals_df.empty and "signal_date" in all_signals_df.columns:
                target_signals = all_signals_df[pd.to_datetime(all_signals_df["signal_date"]) == t_date].copy()
                if not target_signals.empty:
                    target_signals.sort_values(by=["momentum_score"], ascending=[False], inplace=True)
                    for rank, (_, row) in enumerate(target_signals.iterrows(), start=1):
                        sym = str(row["symbol"])
                        company = str(row.get("company_name", sym))
                        c = float(row.get("entry_price", row.get("close", 0.0)))
                        sl = float(row.get("sl_price", c * 0.95))
                        target = round(c * 1.08, 2)

                        fresh_signals.append({
                            "strategy_id": self.strategy_id,
                            "rank": rank,
                            "symbol": sym,
                            "company_name": company,
                            "industry": str(row.get("industry", "Diversified")),
                            "index_name": str(row.get("index_name", "NIFTY 500")),
                            "close": round(c, 2),
                            "entry_trigger": round(c, 2),
                            "target_price": target,
                            "trailing_sl": round(sl, 2),
                            "rsi": round(float(row.get("rsi_t", 0.0)), 2),
                            "rsi_delta": round(float(row.get("rsi_delta", 0.0)), 2),
                            "volume_surge": round(float(row.get("vol_ratio", 0.0)), 2),
                            "body_ratio_pct": round(float(row.get("body_ratio", 0.0)), 1),
                            "momentum_score": round(float(row.get("momentum_score", 0.0)), 2),
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
        df = self.load_data()
        kpis, executed_trades, daily_history = execute_backtest(df)
        return {
            "strategy_id": self.strategy_id,
            "display_name": self.display_name,
            "kpis": kpis,
            "trades_count": len(executed_trades),
            "trade_log": executed_trades,
            "equity_curve": daily_history
        }

