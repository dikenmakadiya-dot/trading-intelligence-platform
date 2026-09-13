"""
Portfolio & Active Positions Manager
Tracks live portfolio holdings, mark-to-market valuations,
trailing stop-loss progressions, holding periods, and trade lifecycle.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import datetime

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import MAX_OPEN_POSITIONS, INITIAL_CAPITAL, POSITION_SIZE_FRACTION
from config.groww_mapper import get_groww_chart_url
from src.db.database import DatabaseManager, get_db
from src.core.data_loader import load_master_dataset

class PortfolioManager:
    """
    Manages active trading positions, evaluates daily stop losses,
    computes unrealized returns, and maintains portfolio capacity.
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()
        self.max_slots = MAX_OPEN_POSITIONS

    def get_open_positions(self, strategy_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all currently active (OPEN) positions."""
        return self.db.get_active_positions(strategy_id=strategy_id, status="OPEN")

    def open_position(
        self,
        strategy_id: str,
        symbol: str,
        company_name: str,
        entry_date: str,
        entry_price: float,
        quantity: int,
        trailing_sl: float,
        target_price: Optional[float] = None,
        allocated_capital: Optional[float] = None,
        groww_chart_url: Optional[str] = None
    ) -> bool:
        """Opens a new position in the active portfolio."""
        url = groww_chart_url or get_groww_chart_url(symbol, company_name)
        cost = allocated_capital if allocated_capital is not None else (entry_price * quantity)

        pos_dict = {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "company_name": company_name,
            "entry_date": entry_date,
            "entry_price": entry_price,
            "quantity": quantity,
            "allocated_capital": cost,
            "current_price": entry_price,
            "trailing_sl": trailing_sl,
            "target_price": target_price,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0,
            "days_held": 0,
            "groww_chart_url": url,
            "status": "OPEN"
        }
        self.db.save_active_positions([pos_dict])
        return True

    def update_active_positions(
        self,
        target_date: Optional[str] = None,
        market_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Updates all open positions using the given target date's market data:
        - Evaluates high/low against trailing stop loss and targets.
        - Triggers stop loss exit if low <= trailing_sl.
        - Upgrades trailing stop loss if SuperTrend moved higher.
        - Calculates current mark-to-market value and unrealized P&L.
        """
        open_positions = self.get_open_positions()
        if not open_positions:
            return self.get_portfolio_summary()

        if market_df is None:
            market_df = load_master_dataset()

        # Determine target date
        all_dates = sorted(market_df["Date"].unique())
        t_date = pd.to_datetime(target_date) if target_date else all_dates[-1]
        t_date_str = t_date.strftime("%Y-%m-%d")

        # Filter market data for target date
        day_df = market_df[market_df["Date"] == t_date]
        day_stocks = {str(row["Symbol"]): row for _, row in day_df.iterrows()}

        updated_positions = []
        for pos in open_positions:
            sym = pos["symbol"]
            strat_id = pos["strategy_id"]
            e_date = pos["entry_date"]
            e_price = float(pos["entry_price"])
            qty = int(pos["quantity"])
            current_sl = float(pos["trailing_sl"])
            target = float(pos["target_price"]) if pos.get("target_price") else None

            # Calculate days held
            try:
                e_dt = pd.to_datetime(e_date)
                # Count trading days between entry and target date
                trading_days_held = len([d for d in all_dates if e_dt <= d <= t_date])
                days_held = max(0, trading_days_held - 1)
            except Exception:
                days_held = pos.get("days_held", 0) + 1

            if sym in day_stocks:
                bar = day_stocks[sym]
                c_close = float(bar["Close"])
                c_high = float(bar["High"])
                c_low = float(bar["Low"])
                supertrend = float(bar.get("SuperTrend", 0.0))

                # Check 1: Target Price Hit
                if target is not None and c_high >= target:
                    self.db.close_position(
                        strategy_id=strat_id,
                        symbol=sym,
                        entry_date=e_date,
                        exit_date=t_date_str,
                        exit_price=target,
                        exit_reason="PROFIT_TARGET_HIT"
                    )
                    continue

                # Check 2: Stop Loss Hit
                if c_low <= current_sl:
                    # Exited at SL price or open if lower
                    exit_px = min(c_close, current_sl)
                    self.db.close_position(
                        strategy_id=strat_id,
                        symbol=sym,
                        entry_date=e_date,
                        exit_date=t_date_str,
                        exit_price=exit_px,
                        exit_reason="TRAILING_STOP_LOSS_HIT"
                    )
                    continue

                # Upward trailing SL ratchet (never lower SL, only trail when SuperTrend is bullish support below close)
                st_dir = float(bar.get("SuperTrend_Dir", 1))
                new_sl = current_sl
                if st_dir == 1 and 0 < supertrend < c_close and supertrend > new_sl:
                    new_sl = round(supertrend, 2)

                # Mark to market
                unrealized_pnl = (c_close - e_price) * qty
                unrealized_pct = ((c_close - e_price) / e_price) * 100.0

                pos_update = dict(pos)
                pos_update["current_price"] = round(c_close, 2)
                pos_update["trailing_sl"] = round(new_sl, 2)
                pos_update["unrealized_pnl"] = round(unrealized_pnl, 2)
                pos_update["unrealized_pnl_pct"] = round(unrealized_pct, 2)
                pos_update["days_held"] = days_held
                updated_positions.append(pos_update)
            else:
                # No data bar for today, keep current price but advance days held
                pos_update = dict(pos)
                pos_update["days_held"] = days_held
                updated_positions.append(pos_update)

        if updated_positions:
            self.db.save_active_positions(updated_positions)

        return self.get_portfolio_summary()

    def sync_from_backtest_open_trades(
        self,
        strategy_id: str,
        trades: List[Dict[str, Any]],
        market_df: Optional[pd.DataFrame] = None
    ) -> int:
        """
        Extracts trades that ended with 'FinalDate_Close' (or open status)
        from a backtest run and imports them as active portfolio positions.
        """
        if not trades:
            return 0

        # Find trades that were active on the final date
        open_candidates = [
            t for t in trades
            if t.get("exit_reason") == "FinalDate_Close" or t.get("is_closed") is False
        ]

        if not open_candidates:
            return 0

        positions_to_save = []
        for t in open_candidates:
            sym = str(t["symbol"])
            company = str(t.get("company_name", sym))
            e_date = str(t["entry_date"])
            e_price = float(t["entry_price"])
            c_price = float(t.get("exit_price", e_price))
            qty = int(t.get("quantity", 1))
            cost = float(t.get("allocated_capital", e_price * qty))
            pnl = (c_price - e_price) * qty
            pnl_pct = ((c_price - e_price) / e_price) * 100.0

            positions_to_save.append({
                "strategy_id": strategy_id,
                "symbol": sym,
                "company_name": company,
                "entry_date": e_date,
                "entry_price": round(e_price, 2),
                "quantity": qty,
                "allocated_capital": round(cost, 2),
                "current_price": round(c_price, 2),
                "trailing_sl": round(float(t.get("stop_loss", e_price * 0.95)), 2),
                "target_price": round(float(t.get("target_price")), 2) if t.get("target_price") else None,
                "unrealized_pnl": round(pnl, 2),
                "unrealized_pnl_pct": round(pnl_pct, 2),
                "days_held": int(t.get("holding_days", 1)),
                "groww_chart_url": t.get("groww_chart_url") or get_groww_chart_url(sym, company),
                "status": "OPEN"
            })

        self.db.save_active_positions(positions_to_save)
        return len(positions_to_save)

    def seed_initial_positions_if_empty(self, market_df: Optional[pd.DataFrame] = None) -> int:
        """
        Seeds active portfolio positions if currently empty, using real market data
        from the NIFTY 750 universe matching PRD baseline slots (e.g. VBL and TRENT).
        """
        if len(self.get_open_positions()) > 0:
            return 0

        if market_df is None:
            market_df = load_master_dataset()

        all_dates = sorted(market_df["Date"].unique())
        if len(all_dates) < 15:
            return 0

        latest_date = all_dates[-1]
        seeds = [
            {"symbol": "VBL", "name": "Varun Beverages Ltd.", "strat": "rsi_52w_breakout", "days_ago": 8},
            {"symbol": "TRENT", "name": "Trent Ltd.", "strat": "clean_candle_5y", "days_ago": 12},
        ]

        seeded = []
        for s in seeds:
            sym = s["symbol"]
            sym_df = market_df[market_df["Symbol"] == sym].sort_values(by="Date")
            if sym_df.empty:
                continue

            entry_idx = max(0, len(sym_df) - s["days_ago"])
            entry_row = sym_df.iloc[entry_idx]
            latest_row = sym_df.iloc[-1]

            e_price = float(entry_row["Close"])
            c_price = float(latest_row["Close"])
            e_date = pd.to_datetime(entry_row["Date"]).strftime("%Y-%m-%d")
            atr = float(entry_row.get("ATR_14", e_price * 0.03))
            sl = round(e_price - 1.5 * atr, 2)
            st_dir = float(latest_row.get("SuperTrend_Dir", 1))
            st = float(latest_row.get("SuperTrend", 0.0))
            if st_dir == 1 and 0 < st < c_price and st > sl:
                sl = round(st, 2)
            # Guarantee SL is below current market price
            if sl >= c_price:
                sl = round(c_price * 0.95, 2)
            
            # Position sizing (20% of 10L = 200,000 INR)
            qty = max(1, int(200000.0 / e_price))
            invested = qty * e_price
            pnl = (c_price - e_price) * qty
            pnl_pct = ((c_price - e_price) / e_price) * 100.0

            seeded.append({
                "strategy_id": s["strat"],
                "symbol": sym,
                "company_name": s["name"],
                "entry_date": e_date,
                "entry_price": round(e_price, 2),
                "quantity": qty,
                "allocated_capital": round(invested, 2),
                "current_price": round(c_price, 2),
                "trailing_sl": sl,
                "target_price": round(e_price * 1.15, 2),
                "unrealized_pnl": round(pnl, 2),
                "unrealized_pnl_pct": round(pnl_pct, 2),
                "days_held": s["days_ago"],
                "groww_chart_url": get_groww_chart_url(sym, s["name"]),
                "status": "OPEN"
            })

        if seeded:
            self.db.save_active_positions(seeded)
        return len(seeded)

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Returns high-level summary of active portfolio holdings and slot capacity.
        """
        positions = self.get_open_positions()
        total_open = len(positions)
        available_slots = max(0, self.max_slots - total_open)

        total_invested = sum(float(p.get("allocated_capital", 0.0)) for p in positions)
        total_current_val = sum(float(p["current_price"]) * int(p["quantity"]) for p in positions)
        total_unrealized_pnl = sum(float(p.get("unrealized_pnl", 0.0)) for p in positions)
        total_pnl_pct = ((total_unrealized_pnl / total_invested) * 100.0) if total_invested > 0 else 0.0

        return {
            "total_open_positions": total_open,
            "max_slots": self.max_slots,
            "available_slots": available_slots,
            "slots_label": f"{total_open} / {self.max_slots} Filled",
            "total_invested_capital": round(total_invested, 2),
            "total_current_value": round(total_current_val, 2),
            "total_unrealized_pnl": round(total_unrealized_pnl, 2),
            "total_unrealized_pnl_pct": round(total_pnl_pct, 2),
            "positions": positions
        }
