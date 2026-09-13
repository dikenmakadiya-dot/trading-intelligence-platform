"""
Database Persistence & Storage Manager
Provides relational SQLite storage for Market Regime, Daily Signals,
Active Positions, Strategy KPIs, and Audited Trade Logs.
"""

import os
import sys
import sqlite3
import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import pandas as pd

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import DEFAULT_DB_PATH, DB_DIR

SCHEMA_SQL_PATH = DB_DIR / "schema.sql"

class DatabaseManager:
    """
    Manages persistent SQLite storage and querying for the Trading Intelligence Platform.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = self._get_connection()
        self.initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for high performance concurrency
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def initialize_schema(self):
        """Executes the DDL schema if tables do not exist."""
        if SCHEMA_SQL_PATH.exists():
            with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            with self.conn:
                self.conn.executescript(schema_sql)
        else:
            raise FileNotFoundError(f"Schema file not found at {SCHEMA_SQL_PATH}")

    # -------------------------------------------------------------------------
    # 1. Market Regime & Breadth Operations
    # -------------------------------------------------------------------------
    def save_market_regime(
        self,
        date_val: str,
        breadth_pct: float,
        gate_open: bool,
        status_label: str,
        total_stocks: int = 0,
        stocks_above_ema50: int = 0
    ) -> bool:
        """
        Saves or updates market breadth and regime status for a given date.
        """
        try:
            date_norm = pd.to_datetime(date_val).strftime("%Y-%m-%d")
        except Exception:
            date_norm = str(date_val)

        query = """
        INSERT INTO market_regime_history (
            date, breadth_pct, gate_open, status_label, total_stocks_evaluated, stocks_above_ema50, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(date) DO UPDATE SET
            breadth_pct = excluded.breadth_pct,
            gate_open = excluded.gate_open,
            status_label = excluded.status_label,
            total_stocks_evaluated = excluded.total_stocks_evaluated,
            stocks_above_ema50 = excluded.stocks_above_ema50,
            created_at = datetime('now');
        """
        with self.conn:
            self.conn.execute(
                query,
                (
                    date_norm,
                    float(breadth_pct),
                    1 if gate_open else 0,
                    str(status_label),
                    int(total_stocks),
                    int(stocks_above_ema50)
                )
            )
        return True

    def get_market_regime_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Fetches the most recent market regime records sorted chronologically descending."""
        query = """
        SELECT date, breadth_pct, gate_open, status_label, total_stocks_evaluated, stocks_above_ema50, created_at
        FROM market_regime_history
        ORDER BY date DESC
        LIMIT ?;
        """
        cursor = self.conn.cursor()
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        return [
            {
                "date": r["date"],
                "breadth_pct": float(r["breadth_pct"]),
                "gate_open": bool(r["gate_open"]),
                "status_label": r["status_label"],
                "total_stocks_evaluated": r["total_stocks_evaluated"],
                "stocks_above_ema50": r["stocks_above_ema50"],
                "created_at": r["created_at"]
            }
            for r in rows
        ]

    def get_latest_market_regime(self) -> Optional[Dict[str, Any]]:
        """Fetches the latest recorded market regime."""
        records = self.get_market_regime_history(limit=1)
        return records[0] if records else None

    # -------------------------------------------------------------------------
    # 2. Consolidated Daily Signals Operations
    # -------------------------------------------------------------------------
    def save_daily_signals(self, signals: List[Dict[str, Any]], target_date: Optional[str] = None) -> int:
        """
        Persists a list of consolidated signals.
        Upserts if the same strategy, date, and symbol already exists.
        """
        if not signals:
            return 0

        query = """
        INSERT INTO daily_signals_history (
            signal_date, strategy_id, strategy_name, rank, symbol, company_name,
            industry, index_name, close_price, entry_trigger, trailing_sl,
            target_price, groww_chart_url, metrics_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(signal_date, strategy_id, symbol) DO UPDATE SET
            strategy_name = excluded.strategy_name,
            rank = excluded.rank,
            company_name = excluded.company_name,
            industry = excluded.industry,
            index_name = excluded.index_name,
            close_price = excluded.close_price,
            entry_trigger = excluded.entry_trigger,
            trailing_sl = excluded.trailing_sl,
            target_price = excluded.target_price,
            groww_chart_url = excluded.groww_chart_url,
            metrics_json = excluded.metrics_json,
            created_at = datetime('now');
        """

        count = 0
        with self.conn:
            for sig in signals:
                s_date = sig.get("as_of_date") or sig.get("signal_date") or target_date or datetime.date.today().strftime("%Y-%m-%d")
                # Normalize date to YYYY-MM-DD if needed
                try:
                    s_date_norm = pd.to_datetime(s_date).strftime("%Y-%m-%d")
                except Exception:
                    s_date_norm = str(s_date)

                metrics = {
                    k: v for k, v in sig.items()
                    if k not in [
                        "signal_date", "as_of_date", "strategy_id", "strategy_name", "rank",
                        "symbol", "company_name", "industry", "index_name", "close", "close_price",
                        "entry_trigger", "trailing_sl", "target_price", "groww_chart_url"
                    ]
                }

                self.conn.execute(
                    query,
                    (
                        s_date_norm,
                        str(sig.get("strategy_id", "unknown")),
                        str(sig.get("strategy_name", sig.get("strategy_id", "Unknown"))),
                        int(sig.get("rank", 1)),
                        str(sig.get("symbol", "")),
                        str(sig.get("company_name", sig.get("symbol", ""))),
                        str(sig.get("industry", "Diversified")),
                        str(sig.get("index_name", "NIFTY 500")),
                        float(sig.get("close", sig.get("close_price", 0.0))),
                        float(sig.get("entry_trigger", sig.get("close", 0.0))),
                        float(sig.get("trailing_sl", 0.0)),
                        float(sig.get("target_price")) if sig.get("target_price") is not None else None,
                        str(sig.get("groww_chart_url", "")),
                        json.dumps(metrics, default=str)
                    )
                )
                count += 1

        return count

    def get_signals_history(
        self,
        signal_date: Optional[str] = None,
        strategy_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Queries recorded breakout signals with optional filtering."""
        query = """
        SELECT id, signal_date, strategy_id, strategy_name, rank, symbol, company_name,
               industry, index_name, close_price, entry_trigger, trailing_sl,
               target_price, groww_chart_url, metrics_json, created_at
        FROM daily_signals_history
        WHERE 1=1
        """
        params = []
        if signal_date:
            try:
                norm_date = pd.to_datetime(signal_date).strftime("%Y-%m-%d")
            except Exception:
                norm_date = signal_date
            query += " AND signal_date = ?"
            params.append(norm_date)
        if strategy_id:
            query += " AND strategy_id = ?"
            params.append(strategy_id)

        query += " ORDER BY signal_date DESC, rank ASC LIMIT ?"
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            metrics = {}
            if r["metrics_json"]:
                try:
                    metrics = json.loads(r["metrics_json"])
                except Exception:
                    pass
            d = {
                "id": r["id"],
                "signal_date": r["signal_date"],
                "strategy_id": r["strategy_id"],
                "strategy_name": r["strategy_name"],
                "rank": r["rank"],
                "symbol": r["symbol"],
                "company_name": r["company_name"],
                "industry": r["industry"],
                "index_name": r["index_name"],
                "close_price": float(r["close_price"]),
                "entry_trigger": float(r["entry_trigger"]),
                "trailing_sl": float(r["trailing_sl"]),
                "target_price": float(r["target_price"]) if r["target_price"] is not None else None,
                "groww_chart_url": r["groww_chart_url"],
                "metrics": metrics,
                "created_at": r["created_at"]
            }
            d.update(metrics)
            result.append(d)
        return result

    # -------------------------------------------------------------------------
    # 3. Active Portfolio Positions Operations
    # -------------------------------------------------------------------------
    def save_active_positions(self, positions: List[Dict[str, Any]]) -> int:
        """
        Persists or updates open/closed portfolio positions.
        """
        if not positions:
            return 0

        query = """
        INSERT INTO active_positions (
            strategy_id, symbol, company_name, entry_date, entry_price, quantity,
            allocated_capital, current_price, trailing_sl, target_price,
            unrealized_pnl, unrealized_pnl_pct, days_held, groww_chart_url,
            status, exit_date, exit_price, exit_reason, realized_pnl,
            realized_pnl_pct, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(strategy_id, symbol, entry_date) DO UPDATE SET
            company_name = excluded.company_name,
            quantity = excluded.quantity,
            allocated_capital = excluded.allocated_capital,
            current_price = excluded.current_price,
            trailing_sl = excluded.trailing_sl,
            target_price = excluded.target_price,
            unrealized_pnl = excluded.unrealized_pnl,
            unrealized_pnl_pct = excluded.unrealized_pnl_pct,
            days_held = excluded.days_held,
            groww_chart_url = excluded.groww_chart_url,
            status = excluded.status,
            exit_date = excluded.exit_date,
            exit_price = excluded.exit_price,
            exit_reason = excluded.exit_reason,
            realized_pnl = excluded.realized_pnl,
            realized_pnl_pct = excluded.realized_pnl_pct,
            updated_at = datetime('now');
        """

        count = 0
        with self.conn:
            for pos in positions:
                try:
                    e_date = pd.to_datetime(pos["entry_date"]).strftime("%Y-%m-%d")
                except Exception:
                    e_date = str(pos["entry_date"])

                ex_date = None
                if pos.get("exit_date"):
                    try:
                        ex_date = pd.to_datetime(pos["exit_date"]).strftime("%Y-%m-%d")
                    except Exception:
                        ex_date = str(pos["exit_date"])

                self.conn.execute(
                    query,
                    (
                        str(pos["strategy_id"]),
                        str(pos["symbol"]),
                        str(pos.get("company_name", pos["symbol"])),
                        e_date,
                        float(pos["entry_price"]),
                        int(pos.get("quantity", 1)),
                        float(pos.get("allocated_capital", 0.0)),
                        float(pos.get("current_price", pos["entry_price"])),
                        float(pos.get("trailing_sl", 0.0)),
                        float(pos.get("target_price")) if pos.get("target_price") is not None else None,
                        float(pos.get("unrealized_pnl", 0.0)),
                        float(pos.get("unrealized_pnl_pct", 0.0)),
                        int(pos.get("days_held", 0)),
                        str(pos.get("groww_chart_url", "")),
                        str(pos.get("status", "OPEN")),
                        ex_date,
                        float(pos.get("exit_price")) if pos.get("exit_price") is not None else None,
                        str(pos.get("exit_reason")) if pos.get("exit_reason") else None,
                        float(pos.get("realized_pnl")) if pos.get("realized_pnl") is not None else None,
                        float(pos.get("realized_pnl_pct")) if pos.get("realized_pnl_pct") is not None else None
                    )
                )
                count += 1
        return count

    def get_active_positions(self, strategy_id: Optional[str] = None, status: str = "OPEN") -> List[Dict[str, Any]]:
        """Fetches active positions matching status ('OPEN' or 'CLOSED')."""
        query = """
        SELECT id, strategy_id, symbol, company_name, entry_date, entry_price, quantity,
               allocated_capital, current_price, trailing_sl, target_price,
               unrealized_pnl, unrealized_pnl_pct, days_held, groww_chart_url,
               status, exit_date, exit_price, exit_reason, realized_pnl,
               realized_pnl_pct, updated_at
        FROM active_positions
        WHERE status = ?
        """
        params = [status]
        if strategy_id:
            query += " AND strategy_id = ?"
            params.append(strategy_id)

        query += " ORDER BY entry_date DESC, id DESC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [dict(r) for r in rows]

    def close_position(
        self,
        strategy_id: str,
        symbol: str,
        entry_date: str,
        exit_date: str,
        exit_price: float,
        exit_reason: str
    ) -> bool:
        """Closes an active position and calculates realized P&L."""
        try:
            e_date = pd.to_datetime(entry_date).strftime("%Y-%m-%d")
            ex_date = pd.to_datetime(exit_date).strftime("%Y-%m-%d")
        except Exception:
            e_date = entry_date
            ex_date = exit_date

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT entry_price, quantity, allocated_capital FROM active_positions WHERE strategy_id=? AND symbol=? AND entry_date=? AND status='OPEN'",
            (strategy_id, symbol, e_date)
        )
        row = cursor.fetchone()
        if not row:
            return False

        entry_price = float(row["entry_price"])
        qty = int(row["quantity"])
        cost = float(row["allocated_capital"]) if row["allocated_capital"] else (entry_price * qty)
        proceeds = exit_price * qty
        realized_pnl = proceeds - cost
        realized_pnl_pct = ((exit_price - entry_price) / entry_price) * 100.0

        update_sql = """
        UPDATE active_positions SET
            status = 'CLOSED',
            exit_date = ?,
            exit_price = ?,
            exit_reason = ?,
            current_price = ?,
            realized_pnl = ?,
            realized_pnl_pct = ?,
            unrealized_pnl = 0.0,
            unrealized_pnl_pct = 0.0,
            updated_at = datetime('now')
        WHERE strategy_id = ? AND symbol = ? AND entry_date = ? AND status = 'OPEN';
        """
        with self.conn:
            self.conn.execute(
                update_sql,
                (ex_date, float(exit_price), exit_reason, float(exit_price), round(realized_pnl, 2), round(realized_pnl_pct, 2), strategy_id, symbol, e_date)
            )
        return True

    # -------------------------------------------------------------------------
    # 4. Strategy KPIs & Backtest Summary Operations
    # -------------------------------------------------------------------------
    def save_strategy_kpis(
        self,
        strategy_id: str,
        display_name: str,
        kpis: Dict[str, Any],
        run_date: Optional[str] = None
    ) -> bool:
        """Saves strategy backtest KPIs snapshot for historical performance comparison."""
        r_date = run_date or datetime.date.today().strftime("%Y-%m-%d")
        try:
            r_date_norm = pd.to_datetime(r_date).strftime("%Y-%m-%d")
        except Exception:
            r_date_norm = r_date

        query = """
        INSERT INTO strategy_kpis_history (
            run_date, strategy_id, display_name, initial_capital, final_equity,
            total_pnl, total_trades, win_rate_pct, profit_factor, cagr_pct,
            max_drawdown_pct, sharpe_ratio, sortino_ratio, calmar_ratio,
            expectancy_pct, expectancy_amt, raw_kpis_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(run_date, strategy_id) DO UPDATE SET
            display_name = excluded.display_name,
            initial_capital = excluded.initial_capital,
            final_equity = excluded.final_equity,
            total_pnl = excluded.total_pnl,
            total_trades = excluded.total_trades,
            win_rate_pct = excluded.win_rate_pct,
            profit_factor = excluded.profit_factor,
            cagr_pct = excluded.cagr_pct,
            max_drawdown_pct = excluded.max_drawdown_pct,
            sharpe_ratio = excluded.sharpe_ratio,
            sortino_ratio = excluded.sortino_ratio,
            calmar_ratio = excluded.calmar_ratio,
            expectancy_pct = excluded.expectancy_pct,
            expectancy_amt = excluded.expectancy_amt,
            raw_kpis_json = excluded.raw_kpis_json,
            created_at = datetime('now');
        """

        with self.conn:
            self.conn.execute(
                query,
                (
                    r_date_norm,
                    strategy_id,
                    display_name,
                    float(kpis.get("initial_capital", 1000000.0)),
                    float(kpis.get("final_equity", 0.0)),
                    float(kpis.get("total_pnl", 0.0)),
                    int(kpis.get("total_trades", 0)),
                    float(kpis.get("win_rate_pct", 0.0)),
                    float(kpis.get("profit_factor", 0.0)),
                    float(kpis.get("cagr_pct", 0.0)),
                    float(kpis.get("max_drawdown_pct", 0.0)),
                    float(kpis.get("sharpe_ratio", 0.0)),
                    float(kpis.get("sortino_ratio", 0.0)),
                    float(kpis.get("calmar_ratio", 0.0)),
                    float(kpis.get("expectancy_pct", 0.0)),
                    float(kpis.get("expectancy_amt", 0.0)),
                    json.dumps(kpis, default=str)
                )
            )
        return True

    def get_latest_kpis(self, strategy_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves the latest recorded KPIs for strategies."""
        query = """
        SELECT k.*
        FROM strategy_kpis_history k
        INNER JOIN (
            SELECT strategy_id, MAX(run_date) as max_date
            FROM strategy_kpis_history
            GROUP BY strategy_id
        ) latest ON k.strategy_id = latest.strategy_id AND k.run_date = latest.max_date
        """
        params = []
        if strategy_id:
            query += " WHERE k.strategy_id = ?"
            params.append(strategy_id)

        query += " ORDER BY k.strategy_id ASC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("raw_kpis_json"):
                try:
                    d["raw_kpis"] = json.loads(d["raw_kpis_json"])
                except Exception:
                    pass
            result.append(d)
        return result

    # -------------------------------------------------------------------------
    # 5. Audited Backtest Trade History
    # -------------------------------------------------------------------------
    def save_backtest_trades(self, strategy_id: str, trades: List[Dict[str, Any]]) -> int:
        """Persists historical executed backtest trades for auditing and analytics."""
        if not trades:
            return 0

        query = """
        INSERT INTO backtest_trade_history (
            strategy_id, symbol, company_name, signal_date, entry_date, entry_price,
            exit_date, exit_price, quantity, allocated_capital, proceeds_amount,
            pnl_amount, net_return_pct, exit_reason, holding_days, groww_chart_url,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(strategy_id, symbol, entry_date, exit_date) DO UPDATE SET
            company_name = excluded.company_name,
            signal_date = excluded.signal_date,
            entry_price = excluded.entry_price,
            exit_price = excluded.exit_price,
            quantity = excluded.quantity,
            allocated_capital = excluded.allocated_capital,
            proceeds_amount = excluded.proceeds_amount,
            pnl_amount = excluded.pnl_amount,
            net_return_pct = excluded.net_return_pct,
            exit_reason = excluded.exit_reason,
            holding_days = excluded.holding_days,
            groww_chart_url = excluded.groww_chart_url,
            created_at = datetime('now');
        """

        count = 0
        with self.conn:
            for t in trades:
                e_date = str(t.get("entry_date", ""))
                ex_date = str(t.get("exit_date", ""))
                if not e_date or not ex_date:
                    continue

                self.conn.execute(
                    query,
                    (
                        strategy_id,
                        str(t.get("symbol", "")),
                        str(t.get("company_name", "")),
                        str(t.get("signal_date", "")),
                        e_date,
                        float(t.get("entry_price", 0.0)),
                        ex_date,
                        float(t.get("exit_price", 0.0)),
                        int(t.get("quantity", 1)),
                        float(t.get("allocated_capital", 0.0)),
                        float(t.get("proceeds_amount", 0.0)),
                        float(t.get("pnl_amount", 0.0)),
                        float(t.get("net_return_pct", 0.0)),
                        str(t.get("exit_reason", "Exit")),
                        int(t.get("holding_days", 0)),
                        str(t.get("groww_chart_url", ""))
                    )
                )
                count += 1
        return count

    def get_backtest_trades(self, strategy_id: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
        """Retrieves backtest trade logs."""
        query = "SELECT * FROM backtest_trade_history"
        params = []
        if strategy_id:
            query += " WHERE strategy_id = ?"
            params.append(strategy_id)
        query += " ORDER BY exit_date DESC, id DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # 6. Generic Table & DataFrame Helpers
    # -------------------------------------------------------------------------
    def get_all_table_names(self) -> List[str]:
        """Returns list of user tables in the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        return [r["name"] for r in cursor.fetchall()]

    def table_to_dataframe(self, table_name: str) -> pd.DataFrame:
        """Reads an entire table into a pandas DataFrame."""
        query = f"SELECT * FROM {table_name};"
        return pd.read_sql_query(query, self.conn)

    def verify_integrity(self) -> Dict[str, Any]:
        """Runs PRAGMA integrity_check and reports row counts across all tables."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchone()
        integrity_ok = (res[0].lower() == "ok") if res else False

        tables = self.get_all_table_names()
        table_counts = {}
        for tbl in tables:
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {tbl};")
            table_counts[tbl] = cursor.fetchone()["cnt"]

        return {
            "database_path": str(self.db_path),
            "integrity_ok": integrity_ok,
            "integrity_status": res[0] if res else "Unknown",
            "tables": table_counts,
            "checked_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def close(self):
        """Closes the underlying SQLite connection."""
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

# Singleton instance accessor
_db_instance: Optional[DatabaseManager] = None

def get_db(db_path: Optional[Union[str, Path]] = None) -> DatabaseManager:
    global _db_instance
    if db_path is not None:
        # Custom DB paths should get an independent instance without polluting default singleton
        p = Path(db_path)
        if _db_instance is not None and _db_instance.db_path == p and _db_instance.conn is not None:
            return _db_instance
        return DatabaseManager(db_path=p)
    if _db_instance is None or _db_instance.conn is None:
        _db_instance = DatabaseManager(db_path=DEFAULT_DB_PATH)
    return _db_instance

def reset_db():
    """Resets the singleton database manager, closing active connections."""
    global _db_instance
    if _db_instance is not None:
        _db_instance.close()
        _db_instance = None
