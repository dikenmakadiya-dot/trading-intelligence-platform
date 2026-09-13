"""
Automated Disaster Recovery & Backup Manager
Produces daily versioned compressed snapshots (Parquet, JSON.GZ, SQLite DB)
with cryptographic checksum verification and retention pruning.
"""

import os
import sys
import json
import gzip
import shutil
import hashlib
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import sqlite3

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import BACKUP_DIR, DEFAULT_DB_PATH, BACKUP_RETENTION_DAYS
from src.db.database import DatabaseManager, get_db

def compute_file_sha256(filepath: Union[str, Path]) -> str:
    """Computes SHA-256 hash of a file for integrity verification."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

class BackupManager:
    """
    Manages automated versioned backups and point-in-time recovery archives.
    """

    def __init__(self, db: Optional[DatabaseManager] = None, backup_dir: Optional[Union[str, Path]] = None):
        self.db = db or get_db()
        self.backup_dir = Path(backup_dir) if backup_dir else BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = BACKUP_RETENTION_DAYS

    def create_snapshot(self, tag: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a complete versioned snapshot:
        1. Verifies database integrity.
        2. Exports each table to compressed Parquet (.parquet).
        3. Exports each table to compressed JSON (.json.gz).
        4. Copies the SQLite database file (.db).
        5. Computes cryptographic hashes and records manifest.json.
        6. Prunes obsolete backups per retention policy.
        """
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d_%H%M%S")
        snapshot_name = f"snapshot_{timestamp_str}"
        if tag:
            clean_tag = "".join(c if c.isalnum() or c in "-_" else "_" for c in tag)
            snapshot_name += f"_{clean_tag}"

        snapshot_path = self.backup_dir / snapshot_name
        snapshot_path.mkdir(parents=True, exist_ok=True)

        # 1. Database integrity check
        integrity = self.db.verify_integrity()

        # 2. Flush pending WAL transactions
        try:
            with self.db.conn:
                self.db.conn.execute("PRAGMA wal_checkpoint(FULL);")
        except Exception as e:
            print(f"[BACKUP WARNING] WAL checkpoint: {e}")

        # 3. Export each table
        tables = self.db.get_all_table_names()
        table_manifest = {}

        for table in tables:
            df = self.db.table_to_dataframe(table)
            row_count = len(df)

            # Export Parquet
            parquet_path = snapshot_path / f"{table}.parquet"
            try:
                df.to_parquet(parquet_path, engine="pyarrow", compression="snappy", index=False)
                parquet_size = parquet_path.stat().st_size
                parquet_sha = compute_file_sha256(parquet_path)
            except Exception as e:
                print(f"[BACKUP WARNING] Could not write Parquet for {table}: {e}")
                parquet_size = 0
                parquet_sha = None

            # Export Compressed JSON (JSON.GZ)
            json_gz_path = snapshot_path / f"{table}.json.gz"
            json_records = df.to_dict(orient="records")
            json_bytes = json.dumps(json_records, indent=2, default=str).encode("utf-8")
            with gzip.open(json_gz_path, "wb") as gz:
                gz.write(json_bytes)
            json_gz_size = json_gz_path.stat().st_size
            json_gz_sha = compute_file_sha256(json_gz_path)

            table_manifest[table] = {
                "row_count": row_count,
                "parquet_file": parquet_path.name if parquet_size > 0 else None,
                "parquet_size_bytes": parquet_size,
                "parquet_sha256": parquet_sha,
                "json_gz_file": json_gz_path.name,
                "json_gz_size_bytes": json_gz_size,
                "json_gz_sha256": json_gz_sha,
            }

        # 4. Backup SQLite DB binary file
        db_backup_path = snapshot_path / "trading_platform.db"
        try:
            # Use SQLite online backup API for crash-consistent binary copy
            backup_conn = sqlite3.connect(str(db_backup_path))
            with backup_conn:
                self.db.conn.backup(backup_conn)
            backup_conn.close()
            db_size = db_backup_path.stat().st_size
            db_sha = compute_file_sha256(db_backup_path)
        except Exception as e:
            print(f"[BACKUP WARNING] SQLite online backup failed, falling back to copy: {e}")
            if Path(self.db.db_path).exists():
                shutil.copy2(self.db.db_path, db_backup_path)
                db_size = db_backup_path.stat().st_size
                db_sha = compute_file_sha256(db_backup_path)
            else:
                db_size = 0
                db_sha = None

        # 5. Write manifest.json
        manifest = {
            "snapshot_id": snapshot_name,
            "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "created_at_ist": now.strftime("%Y-%m-%d %H:%M:%S IST"),
            "database_path": str(self.db.db_path),
            "database_integrity_ok": integrity["integrity_ok"],
            "db_backup_size_bytes": db_size,
            "db_backup_sha256": db_sha,
            "tables": table_manifest,
            "total_tables": len(tables),
            "tag": tag or "daily_screener_backup"
        }

        manifest_file = snapshot_path / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # Update latest pointer in BACKUP_DIR
        latest_pointer_file = self.backup_dir / "latest_manifest.json"
        with open(latest_pointer_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 6. Apply retention pruning
        pruned_count = self.prune_old_snapshots()

        manifest["pruned_old_snapshots"] = pruned_count
        manifest["snapshot_directory"] = str(snapshot_path)
        return manifest

    def prune_old_snapshots(self, min_to_keep: int = 5) -> int:
        """
        Deletes snapshots older than `self.retention_days`,
        guaranteeing at least `min_to_keep` most recent snapshots are preserved.
        """
        all_snapshots = sorted(
            [d for d in self.backup_dir.iterdir() if d.is_dir() and d.name.startswith("snapshot_")],
            key=lambda p: p.name
        )

        if len(all_snapshots) <= min_to_keep:
            return 0

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=self.retention_days)
        pruned = 0

        for s_dir in all_snapshots[:-min_to_keep]:
            # Parse timestamp from directory name: snapshot_YYYY-MM-DD_HHMMSS
            parts = s_dir.name.split("_")
            if len(parts) >= 3:
                try:
                    date_str = parts[1]
                    s_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                    if s_date < cutoff_date:
                        shutil.rmtree(s_dir, ignore_errors=True)
                        pruned += 1
                except Exception:
                    pass
        return pruned

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Lists all available snapshots sorted latest first."""
        snapshots = []
        for s_dir in sorted(self.backup_dir.iterdir(), reverse=True):
            if not s_dir.is_dir() or not s_dir.name.startswith("snapshot_"):
                continue
            manifest_file = s_dir / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        m = json.load(f)
                        snapshots.append(m)
                except Exception:
                    snapshots.append({"snapshot_id": s_dir.name, "path": str(s_dir), "error": "Invalid manifest"})
            else:
                snapshots.append({"snapshot_id": s_dir.name, "path": str(s_dir), "error": "Missing manifest"})
        return snapshots

    def export_all_tables(
        self,
        output_directory: Union[str, Path],
        file_format: str = "parquet"
    ) -> Dict[str, str]:
        """
        Exports all current database tables to a specified directory
        in 'parquet', 'json', or 'csv' format.
        """
        out_dir = Path(output_directory)
        out_dir.mkdir(parents=True, exist_ok=True)
        tables = self.db.get_all_table_names()
        results = {}

        for table in tables:
            df = self.db.table_to_dataframe(table)
            if file_format == "parquet":
                target_file = out_dir / f"{table}.parquet"
                df.to_parquet(target_file, engine="pyarrow", compression="snappy", index=False)
            elif file_format == "json":
                target_file = out_dir / f"{table}.json"
                df.to_json(target_file, orient="records", indent=2, date_format="iso")
            elif file_format == "csv":
                target_file = out_dir / f"{table}.csv"
                df.to_csv(target_file, index=False)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")

            results[table] = str(target_file)
        return results
