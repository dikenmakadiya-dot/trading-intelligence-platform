"""
Disaster Recovery, Restore & Export Utility Script
Provides CLI tools and programmatic APIs to backup, restore, export,
import, and verify database integrity across Parquet, JSON, and SQLite formats.
"""

import os
import sys
import json
import gzip
import shutil
import argparse
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import sqlite3

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import DEFAULT_DB_PATH, BACKUP_DIR, DB_DIR
from src.db.database import DatabaseManager, get_db
from src.db.backup_manager import BackupManager

def list_backups(backup_dir: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
    """Lists all available snapshots with status and row counts."""
    mgr = BackupManager(backup_dir=backup_dir)
    snapshots = mgr.list_snapshots()
    
    print("\n" + "=" * 80)
    print("[CATALOG] QUANTFLOW TRADING PLATFORM - BACKUP SNAPSHOT CATALOG")
    print(f"Directory: {mgr.backup_dir}")
    print("=" * 80)
    
    if not snapshots:
        print("  No snapshots found.")
        print("=" * 80 + "\n")
        return []

    for idx, s in enumerate(snapshots, start=1):
        snap_id = s.get("snapshot_id", "Unknown")
        created = s.get("created_at_ist", s.get("created_at_utc", "N/A"))
        tag = s.get("tag", "daily")
        db_size_kb = round(s.get("db_backup_size_bytes", 0) / 1024, 1)
        tables = s.get("tables", {})
        table_summary = ", ".join([f"{k}: {v.get('row_count', 0)} rows" for k, v in tables.items()])
        
        print(f"\n  [{idx}] Snapshot ID: {snap_id}")
        print(f"      Created: {created} | Tag: {tag} | SQLite DB Size: {db_size_kb} KB")
        print(f"      Tables:  {table_summary if table_summary else 'No table manifest'}")

    print("\n" + "=" * 80 + "\n")
    return snapshots

def restore_from_snapshot(
    snapshot_identifier: str,
    db_path: Optional[Union[str, Path]] = None,
    backup_dir: Optional[Union[str, Path]] = None,
    create_safety_backup: bool = True
) -> Dict[str, Any]:
    """
    Restores database from a given snapshot directory or snapshot ID.
    Supports binary SQLite copy restoration as well as Parquet / JSON reconstruction.
    Supports 'latest' to resolve the newest available backup snapshot automatically.
    """
    target_db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    b_dir = Path(backup_dir) if backup_dir else BACKUP_DIR

    # Resolve snapshot path
    snap_path = Path(snapshot_identifier)
    if snapshot_identifier.strip().lower() == "latest":
        latest_manifest = b_dir / "latest_manifest.json"
        if latest_manifest.exists():
            try:
                with open(latest_manifest, "r", encoding="utf-8") as f:
                    m_data = json.load(f)
                    snap_path = b_dir / m_data.get("snapshot_id", "")
            except Exception:
                snap_path = Path("")
        if not snap_path.exists() or not snap_path.is_dir():
            candidates = sorted(
                [d for d in b_dir.iterdir() if d.is_dir() and d.name.startswith("snapshot_")],
                key=lambda p: p.name,
                reverse=True
            )
            if candidates:
                snap_path = candidates[0]
            else:
                raise FileNotFoundError(f"No backup snapshots found in {b_dir}")
    elif not snap_path.exists() or not snap_path.is_dir():
        snap_path = b_dir / snapshot_identifier
        if not snap_path.exists():
            raise FileNotFoundError(f"Snapshot '{snapshot_identifier}' not found in {b_dir}")

    print(f"[RESTORE] Initiating restore from: {snap_path}")
    manifest_file = snap_path / "manifest.json"
    manifest = {}
    if manifest_file.exists():
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    # 1. Checkpoint WAL and create safety backup of current target DB if it exists
    if target_db_path.exists():
        try:
            with sqlite3.connect(str(target_db_path)) as checkpoint_conn:
                checkpoint_conn.execute("PRAGMA wal_checkpoint(FULL);")
        except Exception:
            pass

        if create_safety_backup:
            safety_name = f"{target_db_path.name}.safety_pre_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            safety_path = target_db_path.parent / safety_name
            shutil.copy2(target_db_path, safety_path)
            print(f"[RESTORE] Created safety backup of current database at:\n  {safety_path}")

    # Remove any stale WAL/SHM files to prevent header/salt corruption on restored DB
    for ext in ["-wal", "-shm"]:
        comp_file = Path(str(target_db_path) + ext)
        if comp_file.exists():
            try:
                comp_file.unlink()
            except Exception:
                pass

    # 2. Check if binary DB file exists in snapshot
    snap_db_file = snap_path / "trading_platform.db"
    restored_method = ""

    if snap_db_file.exists() and snap_db_file.stat().st_size > 0:
        print(f"[RESTORE] Restoring via direct binary SQLite copy ({snap_db_file.name})...")
        target_db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snap_db_file, target_db_path)
        restored_method = "binary_sqlite_copy"
    else:
        # Reconstruct from Parquet or JSON.GZ
        print("[RESTORE] Binary DB not found in snapshot; reconstructing from Parquet/JSON archives...")
        # Remove old DB to recreate cleanly
        if target_db_path.exists():
            target_db_path.unlink()

        db = DatabaseManager(db_path=target_db_path)
        tables = db.get_all_table_names()

        for tbl in tables:
            parquet_file = snap_path / f"{tbl}.parquet"
            json_gz_file = snap_path / f"{tbl}.json.gz"
            df = None

            if parquet_file.exists():
                try:
                    df = pd.read_parquet(parquet_file, engine="pyarrow")
                    print(f"  +-- Reconstructing table '{tbl}' from Parquet ({len(df)} rows)")
                except Exception as e:
                    print(f"  +-- [WARN] Failed reading Parquet for {tbl}: {e}")

            if df is None and json_gz_file.exists():
                try:
                    with gzip.open(json_gz_file, "rt", encoding="utf-8") as gz:
                        records = json.load(gz)
                        df = pd.DataFrame(records)
                        print(f"  +-- Reconstructing table '{tbl}' from JSON.GZ ({len(df)} rows)")
                except Exception as e:
                    print(f"  +-- [WARN] Failed reading JSON.GZ for {tbl}: {e}")

            if df is not None and not df.empty:
                # Clean table before inserting to prevent duplicate keys and ensure clean state
                db.conn.execute(f"DELETE FROM {tbl};")
                # Insert via append mode into schema-initialized table to preserve PRIMARY KEY & UNIQUE constraints
                df.to_sql(tbl, db.conn, if_exists="append", index=False)
                db.conn.commit()

        db.close()
        restored_method = "parquet_json_reconstruction"

    # 3. Verify integrity of restored database
    db_restored = DatabaseManager(db_path=target_db_path)
    integrity = db_restored.verify_integrity()
    db_restored.close()

    result = {
        "status": "SUCCESS" if integrity["integrity_ok"] else "INTEGRITY_WARNING",
        "restored_from": str(snap_path),
        "target_db": str(target_db_path),
        "method": restored_method,
        "integrity": integrity
    }

    print("\n" + "=" * 80)
    print("[RESTORE] RESTORE OPERATION COMPLETED SUCCESSFULLY")
    print(f"  Database Path: {target_db_path}")
    print(f"  Integrity Check: {integrity['integrity_status']}")
    print(f"  Restored Table Counts: {integrity['tables']}")
    print("=" * 80 + "\n")

    return result

def export_all_tables_cli(output_dir: str, file_format: str = "parquet", db_path: Optional[str] = None):
    """Exports all tables to a directory."""
    db = DatabaseManager(db_path=db_path) if db_path else get_db()
    mgr = BackupManager(db=db)
    files = mgr.export_all_tables(output_directory=output_dir, file_format=file_format)
    print(f"\n[EXPORT] Successfully exported {len(files)} tables in '{file_format}' format to: {output_dir}")
    for tbl, path in files.items():
        print(f"  +-- {tbl} -> {path}")
    return files

def verify_db_cli(db_path: Optional[str] = None):
    """Verifies database integrity and outputs summary."""
    db = DatabaseManager(db_path=db_path) if db_path else get_db()
    integrity = db.verify_integrity()
    print("\n" + "=" * 80)
    print("[AUDIT] DATABASE INTEGRITY AUDIT")
    print(f"Database Path: {integrity['database_path']}")
    print(f"Integrity Status: {integrity['integrity_status']} (OK: {integrity['integrity_ok']})")
    print(f"Audit Timestamp:  {integrity['checked_at']}")
    print("-" * 80)
    print("Tables & Row Counts:")
    for tbl, cnt in integrity["tables"].items():
        print(f"  - {tbl.ljust(30)}: {cnt:>8} rows")
    print("=" * 80 + "\n")
    return integrity

def main():
    parser = argparse.ArgumentParser(description="Disaster Recovery, Restore & Export Utility")
    parser.add_argument("--backup", action="store_true", help="Trigger an immediate versioned backup snapshot")
    parser.add_argument("--tag", type=str, default=None, help="Optional label/tag for the backup snapshot")
    parser.add_argument("--list", action="store_true", help="List all available backup snapshots")
    parser.add_argument("--restore", type=str, default=None, help="Snapshot ID or directory path to restore from")
    parser.add_argument("--export-all", type=str, default=None, help="Directory to export all tables to")
    parser.add_argument("--format", choices=["parquet", "json", "csv"], default="parquet", help="Export format")
    parser.add_argument("--verify", action="store_true", help="Run SQLite integrity verification")
    parser.add_argument("--db-path", type=str, default=None, help="Custom SQLite database file path")
    parser.add_argument("--backup-dir", type=str, default=None, help="Custom backups directory")

    args = parser.parse_args()

    if args.backup:
        db = DatabaseManager(db_path=args.db_path) if args.db_path else get_db()
        mgr = BackupManager(db=db, backup_dir=args.backup_dir)
        snap = mgr.create_snapshot(tag=args.tag)
        print(f"\n[BACKUP] Snapshot created successfully:")
        print(f"  Snapshot ID: {snap['snapshot_id']}")
        print(f"  Directory:   {snap['snapshot_directory']}")
        print(f"  Tables:      {list(snap['tables'].keys())}")
        return

    if args.list:
        list_backups(backup_dir=args.backup_dir)
        return

    if args.restore:
        restore_from_snapshot(
            snapshot_identifier=args.restore,
            db_path=args.db_path,
            backup_dir=args.backup_dir
        )
        return

    if args.export_all:
        export_all_tables_cli(output_dir=args.export_all, file_format=args.format, db_path=args.db_path)
        return

    if args.verify or len(sys.argv) == 1:
        verify_db_cli(db_path=args.db_path)
        return

if __name__ == "__main__":
    main()
