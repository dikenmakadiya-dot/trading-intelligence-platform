"""
System Health & Integrity Exporter
Generates system_health.json for both local execution and cloud GitHub Actions deployment.
"""

import os
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import (
    OUTPUT_DIR,
    REPO_PARQUET_PATH,
    REPO_CSV_PATH,
    DEFAULT_MASTER_CSV
)
from src.db.database import get_db
from src.db.backup_manager import BackupManager

NSE_HOLIDAYS_2026 = [
    {"date": "2026-01-26", "day": "Monday", "holiday": "Republic Day"},
    {"date": "2026-02-17", "day": "Tuesday", "holiday": "Mahashivratri"},
    {"date": "2026-03-03", "day": "Tuesday", "holiday": "Holi"},
    {"date": "2026-03-20", "day": "Friday", "holiday": "Eid-ul-Fitr"},
    {"date": "2026-04-03", "day": "Friday", "holiday": "Good Friday"},
    {"date": "2026-04-14", "day": "Tuesday", "holiday": "Dr. Ambedkar Jayanti"},
    {"date": "2026-05-01", "day": "Friday", "holiday": "Maharashtra Day"},
    {"date": "2026-05-27", "day": "Wednesday", "holiday": "Bakri Id / Eid-ul-Adha"},
    {"date": "2026-06-26", "day": "Friday", "holiday": "Muharram"},
    {"date": "2026-08-15", "day": "Saturday", "holiday": "Independence Day"},
    {"date": "2026-10-02", "day": "Friday", "holiday": "Mahatma Gandhi Jayanti"},
    {"date": "2026-10-20", "day": "Tuesday", "holiday": "Dussehra"},
    {"date": "2026-11-08", "day": "Sunday", "holiday": "Diwali Laxmi Pujan"},
    {"date": "2026-11-10", "day": "Tuesday", "holiday": "Diwali Balipratipada"},
    {"date": "2026-11-24", "day": "Tuesday", "holiday": "Guru Nanak Jayanti"},
    {"date": "2026-12-25", "day": "Friday", "holiday": "Christmas"}
]

def generate_system_health() -> Dict[str, Any]:
    db = get_db()
    integrity = db.verify_integrity()
    backup_mgr = BackupManager(db=db)
    snapshots = backup_mgr.list_snapshots()

    # Determine active dataset file
    active_data_path = None
    for p in [REPO_PARQUET_PATH, REPO_CSV_PATH, DEFAULT_MASTER_CSV]:
        if p.exists():
            active_data_path = p
            break

    data_file_info = {
        "path": active_data_path.name if active_data_path else "nifty750_historical_technical_data_5y.parquet",
        "exists": active_data_path is not None and active_data_path.exists(),
        "size_mb": round(active_data_path.stat().st_size / (1024 * 1024), 2) if active_data_path and active_data_path.exists() else 0,
        "last_modified": datetime.datetime.fromtimestamp(
            active_data_path.stat().st_mtime
        ).strftime("%Y-%m-%d %H:%M:%S") if active_data_path and active_data_path.exists() else None
    }

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    holiday_dates = {h["date"] for h in NSE_HOLIDAYS_2026}

    now_dt = datetime.datetime.now()
    is_weekend = now_dt.weekday() in (5, 6)
    is_holiday = today_str in holiday_dates
    is_market_hours = (not is_weekend) and (not is_holiday) and (
        (now_dt.hour == 9 and now_dt.minute >= 15) or
        (10 <= now_dt.hour < 15) or
        (now_dt.hour == 15 and now_dt.minute <= 30)
    )

    health_data = {
        "status": "HEALTHY" if integrity.get("integrity_ok") else "DEGRADED",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "database": integrity,
        "data_source": data_file_info,
        "universe": {
            "total_constituents": 750,
            "nifty_500_count": 500,
            "nifty_microcap_250_count": 250,
            "status": "TRACKING_ACTIVE"
        },
        "market_session": {
            "is_open": is_market_hours,
            "is_holiday": is_holiday,
            "is_weekend": is_weekend,
            "current_phase": "REGULAR_TRADING" if is_market_hours else "MARKET_CLOSED",
            "exchange": "NSE (National Stock Exchange of India)"
        },
        "nse_holidays_2026": NSE_HOLIDAYS_2026,
        "backups": {
            "total_snapshots": len(snapshots),
            "latest_snapshot": snapshots[0] if snapshots else None,
            "snapshots_list": snapshots[:15]
        }
    }

    # Save to output/system_health.json
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / "system_health.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(health_data, f, indent=2, default=str)

    # Sync to frontend distribution & public data
    import shutil
    for target_dir in [REPO_ROOT / "frontend" / "dist" / "data", REPO_ROOT / "frontend" / "public" / "data"]:
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(out_file, target_dir / "system_health.json")
        except Exception:
            pass

    return health_data

if __name__ == "__main__":
    h = generate_system_health()
    print(f"[HEALTH] Generated system health snapshot: {h['timestamp']} - Status: {h['status']}")
