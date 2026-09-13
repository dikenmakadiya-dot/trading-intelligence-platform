"""
Integration Tests for Multi-Strategy Orchestrator Pipeline with Database & Backups
"""

import os
import sys
import unittest
import json
import tempfile
import shutil
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.db.database import get_db
from src.db.backup_manager import BackupManager
from src.orchestrator import run_all_screeners, run_all_backtests
from config.settings import CONSOLIDATED_SIGNALS_JSON, DEFAULT_DB_PATH

class TestOrchestratorIntegration(unittest.TestCase):
    def test_consolidated_payload_structure(self):
        """Verify that consolidated_signals.json exists and has valid Phase 2 schema."""
        self.assertTrue(CONSOLIDATED_SIGNALS_JSON.exists())
        with open(CONSOLIDATED_SIGNALS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check required fields
        self.assertIn("market_regime", data)
        self.assertIn("all_signals_unified", data)
        self.assertIn("portfolio_summary", data)
        self.assertIn("active_positions", data)
        self.assertIn("backup_status", data)

        # Check market regime fields
        regime = data["market_regime"]
        self.assertIn("breadth_pct", regime)
        self.assertIn("gate_open", regime)

        # Check active positions structure
        positions = data["active_positions"]
        self.assertIsInstance(positions, list)
        for pos in positions:
            self.assertIn("symbol", pos)
            self.assertIn("entry_price", pos)
            self.assertIn("current_price", pos)
            self.assertIn("trailing_sl", pos)
            self.assertIn("groww_chart_url", pos)
            self.assertIn("days_held", pos)

        # Check backup status
        self.assertTrue(data["backup_status"].get("integrity_ok"))

    def test_database_persistence_verification(self):
        """Verify that SQLite database was updated with tables and data."""
        self.assertTrue(DEFAULT_DB_PATH.exists())
        db = get_db()
        integrity = db.verify_integrity()
        self.assertTrue(integrity["integrity_ok"])
        self.assertGreater(integrity["tables"]["market_regime_history"], 0)
        self.assertGreater(integrity["tables"]["daily_signals_history"], 0)
        self.assertGreaterEqual(integrity["tables"]["active_positions"], 0)

if __name__ == "__main__":
    unittest.main()
