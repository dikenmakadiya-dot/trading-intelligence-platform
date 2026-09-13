"""
Lightweight API and Static File Server for QuantFlow Trading Intelligence Platform
Built with standard library http.server.ThreadingHTTPServer for zero-dependency deployment.
"""

import os
import sys
import json
import mimetypes
import datetime
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    OUTPUT_DIR, CONSOLIDATED_SIGNALS_JSON, STRATEGY_SUMMARY_JSON,
    BACKTEST_OUTPUT_DIR, DATA_FILE_PATH, DEFAULT_DB_PATH
)
from src.db.database import get_db
from src.db.backup_manager import BackupManager
from src.orchestrator import run_all_screeners, run_all_backtests

FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

# Official NSE Trading Holidays for 2026
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

class QuantFlowRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP Request Handler serving JSON APIs and the PWA bundle."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIST_DIR), **kwargs)

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def _send_json(self, data: Any, status_code: int = 200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Route API endpoints
        if path == "/api/signals":
            self.handle_get_signals()
        elif path == "/api/health":
            self.handle_get_health()
        elif path == "/api/backtest-data":
            self.handle_get_backtest_data(query)
        elif path == "/api/backups":
            self.handle_get_backups()
        elif path == "/api/backups/download":
            self.handle_download_backup(query)
        elif path.startswith("/api/"):
            self._send_json({"error": f"API endpoint not found: {path}"}, 404)
        else:
            # Static file serving from frontend/dist
            self.handle_static_or_spa(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/refresh":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"
            try:
                payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            except Exception:
                payload = {}
            self.handle_post_refresh(payload)
        else:
            self._send_json({"error": f"Endpoint not found: {path}"}, 404)

    # -------------------------------------------------------------------------
    # API Handlers
    # -------------------------------------------------------------------------
    def handle_get_signals(self):
        """Returns consolidated signals payload."""
        try:
            if CONSOLIDATED_SIGNALS_JSON.exists():
                with open(CONSOLIDATED_SIGNALS_JSON, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._send_json(data)
            else:
                # Fallback run screener or query DB
                db = get_db()
                regime = db.get_latest_market_regime() or {
                    "breadth_pct": 50.0,
                    "gate_open": True,
                    "status_label": "BULLISH (GATE OPEN)",
                    "total_stocks_evaluated": 500,
                    "stocks_above_ema50": 250
                }
                signals = db.get_signals_history(limit=50)
                positions = db.get_active_positions(status="OPEN")
                data = {
                    "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
                    "as_of_date": datetime.date.today().strftime("%d-%b-%Y"),
                    "market_regime": regime,
                    "total_triggers": len(signals),
                    "all_signals_unified": signals,
                    "portfolio_summary": {
                        "total_open_positions": len(positions),
                        "max_slots": 5,
                        "available_slots": max(0, 5 - len(positions)),
                        "slots_label": f"{len(positions)} / 5 Filled",
                        "positions": positions
                    },
                    "active_positions": positions
                }
                self._send_json(data)
        except Exception as e:
            self._send_json({"error": f"Failed to retrieve signals: {str(e)}"}, 500)

    def handle_post_refresh(self, payload: Dict[str, Any]):
        """Executes screener or backtest refresh on demand."""
        mode = payload.get("mode", "screener")
        target_date = payload.get("date")

        try:
            if mode == "backtest":
                res = run_all_backtests()
                self._send_json({"success": True, "mode": "backtest", "result": res})
            else:
                res = run_all_screeners(target_date=target_date)
                self._send_json({"success": True, "mode": "screener", "result": res})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def handle_get_health(self):
        """Returns system health, database integrity, backups, and NSE calendar."""
        try:
            db = get_db()
            integrity = db.verify_integrity()
            backup_mgr = BackupManager(db=db)
            snapshots = backup_mgr.list_snapshots()

            # Data file info
            data_file_info = {
                "path": str(DATA_FILE_PATH),
                "exists": DATA_FILE_PATH.exists(),
                "size_mb": round(DATA_FILE_PATH.stat().st_size / (1024 * 1024), 2) if DATA_FILE_PATH.exists() else 0,
                "last_modified": datetime.datetime.fromtimestamp(
                    DATA_FILE_PATH.stat().st_mtime
                ).strftime("%Y-%m-%d %H:%M:%S") if DATA_FILE_PATH.exists() else None
            }

            # Next trading session calculation
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            holiday_dates = {h["date"] for h in NSE_HOLIDAYS_2026}
            
            # Check market status
            now_dt = datetime.datetime.now()
            is_weekend = now_dt.weekday() in (5, 6) # Sat, Sun
            is_holiday = today_str in holiday_dates
            # NSE trading hours: 09:15 to 15:30 IST
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
                    "snapshots_list": snapshots[:10]
                }
            }
            self._send_json(health_data)
        except Exception as e:
            self._send_json({"error": f"Failed to retrieve health status: {str(e)}"}, 500)

    def handle_get_backtest_data(self, query: Dict[str, List[str]]):
        """Returns strategy KPIs, equity curve, and audited trade logs."""
        strategy_id = query.get("strategy_id", [None])[0]

        try:
            # 1. KPIs
            kpis = {}
            if STRATEGY_SUMMARY_JSON.exists():
                with open(STRATEGY_SUMMARY_JSON, "r", encoding="utf-8") as f:
                    kpis = json.load(f)

            # 2. Equity curve
            equity_curve = []
            eq_csv = BACKTEST_OUTPUT_DIR / "equity_curve.csv"
            if eq_csv.exists():
                import pandas as pd
                df_eq = pd.read_csv(eq_csv)
                equity_curve = df_eq.to_dict(orient="records")

            # 3. Trade logs from DB or CSV
            limit_val = 2000
            if "limit" in query:
                try:
                    limit_val = int(query["limit"][0])
                except Exception:
                    limit_val = 2000

            db = get_db()
            trades = db.get_backtest_trades(strategy_id=strategy_id, limit=limit_val)
            if not trades:
                t_csv = BACKTEST_OUTPUT_DIR / "trade_log.csv"
                if t_csv.exists():
                    import pandas as pd
                    df_trades = pd.read_csv(t_csv)
                    if strategy_id:
                        if "strategy_id" in df_trades.columns:
                            df_trades = df_trades[df_trades["strategy_id"] == strategy_id]
                    trades = df_trades.head(limit_val).to_dict(orient="records")

            data = {
                "kpis": kpis,
                "equity_curve": equity_curve,
                "trades": trades,
                "strategy_id": strategy_id
            }
            self._send_json(data)
        except Exception as e:
            self._send_json({"error": f"Failed to retrieve backtest data: {str(e)}"}, 500)

    def handle_get_backups(self):
        """Lists backups."""
        try:
            db = get_db()
            backup_mgr = BackupManager(db=db)
            snapshots = backup_mgr.list_snapshots()
            self._send_json({"snapshots": snapshots, "total": len(snapshots)})
        except Exception as e:
            self._send_json({"error": f"Failed to list backups: {str(e)}"}, 500)

    def handle_download_backup(self, query: Dict[str, List[str]]):
        """Allows direct download of backup database or export archive."""
        snapshot_id = query.get("snapshot_id", [None])[0]
        file_type = query.get("type", ["db"])[0]

        if not snapshot_id:
            self._send_json({"error": "Missing snapshot_id parameter"}, 400)
            return

        db = get_db()
        backup_mgr = BackupManager(db=db)
        s_dir = backup_mgr.backup_dir / snapshot_id
        if not s_dir.exists() or not s_dir.is_dir():
            self._send_json({"error": f"Snapshot {snapshot_id} not found"}, 404)
            return

        # Target file
        if file_type == "db":
            target = s_dir / "trading_platform.db"
            content_type = "application/x-sqlite3"
        elif file_type == "manifest":
            target = s_dir / "manifest.json"
            content_type = "application/json"
        else:
            target = s_dir / "manifest.json"
            content_type = "application/json"

        if not target.exists():
            self._send_json({"error": f"Requested file not found in snapshot: {target.name}"}, 404)
            return

        try:
            with open(target, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
            self.send_header("Content-Length", str(len(content)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_json({"error": f"Error reading file: {str(e)}"}, 500)

    # -------------------------------------------------------------------------
    # SPA Static File Serving
    # -------------------------------------------------------------------------
    def handle_static_or_spa(self, path: str):
        """Serves files from FRONTEND_DIST_DIR with SPA routing fallback to index.html."""
        if not FRONTEND_DIST_DIR.exists():
            # If frontend hasn't been built yet, render helpful status page
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """<!DOCTYPE html>
<html>
<head>
    <title>QuantFlow Platform</title>
    <style>
        body { background: #020617; color: #f8fafc; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { background: #0F172A; border: 1px solid #1E293B; border-radius: 12px; padding: 32px; max-width: 500px; text-align: center; }
        h1 { color: #38BDF8; margin-top: 0; }
        p { color: #94A3B8; line-height: 1.6; }
        code { background: #1E293B; color: #22C55E; padding: 2px 6px; border-radius: 4px; font-family: monospace; }
    </style>
</head>
<body>
    <div class="card">
        <h1>QuantFlow Intelligence API Server</h1>
        <p>The backend API server is operational.</p>
        <p>Run <code>npm run build</code> in <code>frontend/</code> to generate the PWA static bundle.</p>
        <p><a href="/api/signals" style="color: #38BDF8;">View /api/signals</a> &bull; <a href="/api/health" style="color: #38BDF8;">View /api/health</a></p>
    </div>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
            return

        # Attempt to find file in dist
        rel_path = path.lstrip("/")
        if not rel_path:
            rel_path = "index.html"

        candidate_file = FRONTEND_DIST_DIR / rel_path

        # If file exists and is a file, serve it directly
        if candidate_file.exists() and candidate_file.is_file():
            mime_type, _ = mimetypes.guess_type(str(candidate_file))
            if rel_path.endswith(".webmanifest") or rel_path.endswith("manifest.json"):
                mime_type = "application/manifest+json"
            elif rel_path.endswith(".js") or rel_path.endswith(".mjs"):
                mime_type = "application/javascript"
            elif rel_path.endswith(".css"):
                mime_type = "text/css"
            elif not mime_type:
                mime_type = "application/octet-stream"

            try:
                with open(candidate_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type or "javascript" in mime_type or "json" in mime_type else mime_type)
                self.send_header("Content-Length", str(len(content)))
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception as e:
                self._send_json({"error": f"Error serving file: {str(e)}"}, 500)
                return

        # Fallback to index.html for SPA client-side routing
        index_file = FRONTEND_DIST_DIR / "index.html"
        if index_file.exists():
            try:
                with open(index_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self._send_json({"error": f"Error serving index.html: {str(e)}"}, 500)
        else:
            self._send_json({"error": "Resource not found"}, 404)


def run_server(host: str = "0.0.0.0", port: int = 8000):
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, QuantFlowRequestHandler)
    print("=" * 70)
    print(f"[API SERVER] QuantFlow Trading Intelligence Server running on http://{host}:{port}")
    print(f"  +-- Signals API:      http://localhost:{port}/api/signals")
    print(f"  +-- System Health:    http://localhost:{port}/api/health")
    print(f"  +-- Backtest Data:    http://localhost:{port}/api/backtest-data")
    print(f"  +-- Backups List:     http://localhost:{port}/api/backups")
    print(f"  +-- Frontend Root:    {FRONTEND_DIST_DIR}")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[API SERVER] Server shutting down...")
        httpd.server_close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="QuantFlow API & PWA Web Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Binding host")
    parser.add_argument("--port", type=int, default=8000, help="Binding port")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
