"""
Unit Tests for Database Persistence & Storage Layer
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.db.database import DatabaseManager
from src.db.portfolio_manager import PortfolioManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_trading.db"
        self.db = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_schema_initialization(self):
        """Verify all 5 core tables exist in schema."""
        tables = self.db.get_all_table_names()
        expected = [
            "market_regime_history",
            "daily_signals_history",
            "active_positions",
            "strategy_kpis_history",
            "backtest_trade_history"
        ]
        for tbl in expected:
            self.assertIn(tbl, tables, f"Expected table '{tbl}' was not created.")

    def test_market_regime_crud(self):
        """Verify insert, update (upsert) and retrieval of market regime."""
        # Insert
        ok = self.db.save_market_regime(
            date_val="2026-09-11",
            breadth_pct=54.2,
            gate_open=True,
            status_label="AGGRESSIVE (GATE OPEN)",
            total_stocks=750,
            stocks_above_ema50=406
        )
        self.assertTrue(ok)

        latest = self.db.get_latest_market_regime()
        self.assertIsNotNone(latest)
        self.assertEqual(latest["date"], "2026-09-11")
        self.assertEqual(latest["breadth_pct"], 54.2)
        self.assertTrue(latest["gate_open"])

        # Upsert (update existing date)
        self.db.save_market_regime(
            date_val="2026-09-11",
            breadth_pct=34.0,
            gate_open=False,
            status_label="DEFENSIVE (CASH PROTECTION)"
        )
        updated = self.db.get_latest_market_regime()
        self.assertEqual(updated["breadth_pct"], 34.0)
        self.assertFalse(updated["gate_open"])

    def test_daily_signals_crud(self):
        """Verify daily signals persistence, deduplication, and metrics parsing."""
        sample_signals = [
            {
                "signal_date": "2026-09-11",
                "strategy_id": "rsi_52w_breakout",
                "strategy_name": "3-Day RSI UP + 52W High Breakout",
                "rank": 1,
                "symbol": "TATAMOTORS",
                "company_name": "Tata Motors Ltd.",
                "industry": "Automobile",
                "index_name": "NIFTY 500",
                "close": 1045.50,
                "entry_trigger": 1046.00,
                "trailing_sl": 1012.00,
                "target_price": None,
                "groww_chart_url": "https://groww.in/charts/stocks/tata-motors-ltd?exchange=NSE",
                "rsi_14": 64.2,
                "volume_surge": 3.4
            }
        ]

        saved = self.db.save_daily_signals(sample_signals)
        self.assertEqual(saved, 1)

        history = self.db.get_signals_history(signal_date="2026-09-11")
        self.assertEqual(len(history), 1)
        sig = history[0]
        self.assertEqual(sig["symbol"], "TATAMOTORS")
        self.assertEqual(sig["close_price"], 1045.50)
        self.assertEqual(sig["rsi_14"], 64.2)
        self.assertEqual(sig["volume_surge"], 3.4)

    def test_active_positions_and_lifecycle(self):
        """Verify active positions insert, mark-to-market update, and position closure."""
        pm = PortfolioManager(db=self.db)
        # Open position
        pm.open_position(
            strategy_id="rsi_52w_breakout",
            symbol="VBL",
            company_name="Varun Beverages Ltd.",
            entry_date="2026-09-01",
            entry_price=500.0,
            quantity=400,
            trailing_sl=480.0,
            allocated_capital=200000.0
        )

        open_pos = pm.get_open_positions()
        self.assertEqual(len(open_pos), 1)
        self.assertEqual(open_pos[0]["symbol"], "VBL")
        self.assertEqual(open_pos[0]["status"], "OPEN")

        # Close position
        closed = self.db.close_position(
            strategy_id="rsi_52w_breakout",
            symbol="VBL",
            entry_date="2026-09-01",
            exit_date="2026-09-10",
            exit_price=560.0,
            exit_reason="PROFIT_TARGET"
        )
        self.assertTrue(closed)

        open_after = pm.get_open_positions()
        self.assertEqual(len(open_after), 0)

        closed_pos = self.db.get_active_positions(status="CLOSED")
        self.assertEqual(len(closed_pos), 1)
        self.assertEqual(closed_pos[0]["exit_reason"], "PROFIT_TARGET")
        self.assertEqual(closed_pos[0]["realized_pnl"], 24000.0)
        self.assertEqual(closed_pos[0]["realized_pnl_pct"], 12.0)

    def test_strategy_kpis_and_backtest_trades(self):
        """Verify KPIs and backtest trade logs persistence."""
        kpis = {
            "initial_capital": 1000000.0,
            "final_equity": 3480000.0,
            "total_pnl": 2480000.0,
            "total_trades": 182,
            "win_rate_pct": 58.2,
            "profit_factor": 2.15,
            "cagr_pct": 28.5,
            "max_drawdown_pct": 21.26,
            "sharpe_ratio": 1.42,
            "sortino_ratio": 1.95,
            "calmar_ratio": 1.34,
            "expectancy_pct": 3.8,
            "expectancy_amt": 13626.0
        }

        self.db.save_strategy_kpis(
            strategy_id="rsi_52w_breakout",
            display_name="3-Day RSI UP + 52W High Breakout",
            kpis=kpis,
            run_date="2026-09-11"
        )

        latest_kpis = self.db.get_latest_kpis("rsi_52w_breakout")
        self.assertEqual(len(latest_kpis), 1)
        self.assertEqual(latest_kpis[0]["cagr_pct"], 28.5)
        self.assertEqual(latest_kpis[0]["win_rate_pct"], 58.2)

        # Backtest trade history
        trades = [
            {
                "symbol": "TRENT",
                "company_name": "Trent Ltd.",
                "entry_date": "2026-08-01",
                "entry_price": 5000.0,
                "exit_date": "2026-08-15",
                "exit_price": 5400.0,
                "quantity": 40,
                "allocated_capital": 200000.0,
                "proceeds_amount": 216000.0,
                "pnl_amount": 16000.0,
                "net_return_pct": 8.0,
                "exit_reason": "Target",
                "holding_days": 10,
                "groww_chart_url": "https://groww.in/charts/stocks/trent-ltd?exchange=NSE"
            }
        ]
        saved_trades = self.db.save_backtest_trades("rsi_52w_breakout", trades)
        self.assertEqual(saved_trades, 1)

        queried = self.db.get_backtest_trades("rsi_52w_breakout")
        self.assertEqual(len(queried), 1)
        self.assertEqual(queried[0]["symbol"], "TRENT")

    def test_database_integrity(self):
        """Verify integrity check reports OK."""
        res = self.db.verify_integrity()
        self.assertTrue(res["integrity_ok"])
        self.assertEqual(res["integrity_status"].lower(), "ok")

if __name__ == "__main__":
    unittest.main()
