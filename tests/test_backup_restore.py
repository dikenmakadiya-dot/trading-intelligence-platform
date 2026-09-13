"""
Unit & Integration Tests for Backup & Disaster Recovery
"""

import os
import sys
import unittest
import tempfile
import shutil
import json
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.db.database import DatabaseManager
from src.db.backup_manager import BackupManager, compute_file_sha256
from src.db.restore_backup import restore_from_snapshot, list_backups, verify_db_cli, export_all_tables_cli

class TestBackupAndRestore(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "original.db"
        self.backup_dir = Path(self.test_dir) / "backups"
        self.db = DatabaseManager(db_path=self.db_path)

        # Seed sample data into db
        self.db.save_market_regime(
            date_val="2026-09-11",
            breadth_pct=42.5,
            gate_open=False,
            status_label="DEFENSIVE (CASH PROTECTION)"
        )
        self.db.save_daily_signals([
            {
                "signal_date": "2026-09-11",
                "strategy_id": "clean_candle_5y",
                "strategy_name": "5-Year High Breakout",
                "symbol": "BEL",
                "company_name": "Bharat Electronics Ltd.",
                "close": 315.0,
                "entry_trigger": 315.0,
                "trailing_sl": 304.5,
                "target_price": 340.2,
                "groww_chart_url": "https://groww.in/charts/stocks/bharat-electronics-ltd?exchange=NSE"
            }
        ])

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_backup_snapshot_creation(self):
        """Verify snapshot creates Parquet, JSON.GZ, SQLite DB, and valid manifest."""
        mgr = BackupManager(db=self.db, backup_dir=self.backup_dir)
        manifest = mgr.create_snapshot(tag="test_snap")

        self.assertTrue(manifest["database_integrity_ok"])
        snap_dir = Path(manifest["snapshot_directory"])
        self.assertTrue(snap_dir.exists())

        # Check DB file
        db_copy = snap_dir / "trading_platform.db"
        self.assertTrue(db_copy.exists())
        self.assertGreater(db_copy.stat().st_size, 0)
        self.assertEqual(compute_file_sha256(db_copy), manifest["db_backup_sha256"])

        # Check tables in manifest
        self.assertIn("market_regime_history", manifest["tables"])
        self.assertIn("daily_signals_history", manifest["tables"])

        # Check Parquet & JSON.GZ exist
        regime_meta = manifest["tables"]["market_regime_history"]
        self.assertEqual(regime_meta["row_count"], 1)
        self.assertTrue((snap_dir / regime_meta["parquet_file"]).exists())
        self.assertTrue((snap_dir / regime_meta["json_gz_file"]).exists())

    def test_restore_from_snapshot(self):
        """Verify database can be restored completely to a new location."""
        mgr = BackupManager(db=self.db, backup_dir=self.backup_dir)
        manifest = mgr.create_snapshot(tag="restore_test")

        # Destination DB path
        restored_db_path = Path(self.test_dir) / "restored.db"
        result = restore_from_snapshot(
            snapshot_identifier=manifest["snapshot_id"],
            db_path=restored_db_path,
            backup_dir=self.backup_dir,
            create_safety_backup=False
        )

        self.assertEqual(result["status"], "SUCCESS")
        self.assertTrue(restored_db_path.exists())

        # Query restored DB
        restored_db = DatabaseManager(db_path=restored_db_path)
        regime = restored_db.get_latest_market_regime()
        self.assertIsNotNone(regime)
        self.assertEqual(regime["breadth_pct"], 42.5)

        signals = restored_db.get_signals_history()
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["symbol"], "BEL")
        restored_db.close()

    def test_export_all_formats(self):
        """Verify export utility can export tables in parquet, json, and csv."""
        mgr = BackupManager(db=self.db, backup_dir=self.backup_dir)
        export_dir = Path(self.test_dir) / "exports"

        for fmt in ["parquet", "json", "csv"]:
            out_sub = export_dir / fmt
            files = mgr.export_all_tables(output_directory=out_sub, file_format=fmt)
            self.assertIn("market_regime_history", files)
            f_path = Path(files["market_regime_history"])
            self.assertTrue(f_path.exists())
            self.assertGreater(f_path.stat().st_size, 0)

if __name__ == "__main__":
    unittest.main()
