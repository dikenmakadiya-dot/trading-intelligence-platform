"""
Central Pipeline Orchestrator for Multi-Strategy Trading Intelligence Platform
Coordinates sequenced screener runs, consolidated signals generation, and on-demand backtest refreshes.
"""

import os
import sys
import json
import argparse
import datetime
from typing import Dict, Any, List

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.settings import OUTPUT_DIR, CONSOLIDATED_SIGNALS_JSON, STRATEGY_SUMMARY_JSON
from src.strategies.strategy_1_rsi_52w.strategy import Strategy1RSI52W
from src.strategies.strategy_2_clean_candle_5y.strategy import Strategy2CleanCandle5Y
from src.strategies.strategy_3_gfs_mtf.strategy import Strategy3GFSMTF
from src.db.database import get_db
from src.db.portfolio_manager import PortfolioManager
from src.db.backup_manager import BackupManager

def get_registered_strategies():
    return [
        Strategy1RSI52W(),
        Strategy2CleanCandle5Y(),
        Strategy3GFSMTF()
    ]

def run_all_screeners(target_date: str = None) -> Dict[str, Any]:
    print("=" * 70)
    print("[PIPELINE] QUANTFLOW TRADING INTELLIGENCE - MULTI-STRATEGY SCREENER PIPELINE")
    print(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    db = get_db()
    portfolio_mgr = PortfolioManager(db=db)
    backup_mgr = BackupManager(db=db)

    strategies = get_registered_strategies()
    signals_by_strategy = {}
    all_signals_unified = []
    market_regime = {}

    for strat in strategies:
        print(f"\n[ORCHESTRATOR] Executing Screener: {strat.display_name}...")
        try:
            res = strat.run_screener(target_date=target_date)
            signals_by_strategy[strat.strategy_id] = res
            
            # Use market regime from strategy 1 if available
            if "market_regime" in res and res["market_regime"]:
                market_regime = res["market_regime"]

            for sig in res.get("fresh_signals", []):
                sig_copy = dict(sig)
                sig_copy["strategy_name"] = strat.display_name
                all_signals_unified.append(sig_copy)

            print(f"  +-- Finished. Triggers found: {len(res.get('fresh_signals', []))}")
        except Exception as e:
            print(f"  +-- [ERROR] Strategy {strat.strategy_id} screener failed: {e}")
            signals_by_strategy[strat.strategy_id] = {"error": str(e), "fresh_signals": []}

    as_of_date = target_date or (next((v.get("as_of_date") for v in signals_by_strategy.values() if v.get("as_of_date")), "Latest"))

    # 1. Persist Market Regime History
    if market_regime:
        try:
            db.save_market_regime(
                date_val=as_of_date,
                breadth_pct=float(market_regime.get("breadth_pct", 0.0)),
                gate_open=bool(market_regime.get("gate_open", False)),
                status_label=str(market_regime.get("status_label", "")),
                total_stocks=int(market_regime.get("total_stocks_evaluated", 0)),
                stocks_above_ema50=int(market_regime.get("stocks_above_ema50", 0))
            )
            print(f"[DATABASE] Market Regime persisted for date: {as_of_date}")
        except Exception as e:
            print(f"[DATABASE ERROR] Failed saving market regime: {e}")

    # 2. Persist Daily Signals History
    if all_signals_unified:
        try:
            saved_count = db.save_daily_signals(all_signals_unified, target_date=as_of_date)
            print(f"[DATABASE] Persisted {saved_count} fresh breakout signals.")
        except Exception as e:
            print(f"[DATABASE ERROR] Failed saving daily signals: {e}")

    # 3. Track & Update Active Portfolio Positions
    try:
        portfolio_mgr.seed_initial_positions_if_empty()
        portfolio_summary = portfolio_mgr.update_active_positions(target_date=as_of_date)
        print(f"[PORTFOLIO] Active Positions: {portfolio_summary['slots_label']} | Unrealized P&L: INR {portfolio_summary['total_unrealized_pnl']:,.2f} ({portfolio_summary['total_unrealized_pnl_pct']:+.2f}%)")
    except Exception as e:
        print(f"[PORTFOLIO WARNING] Active portfolio update: {e}")
        portfolio_summary = portfolio_mgr.get_portfolio_summary()

    # 4. Trigger Automated Daily Versioned Backup
    backup_status = {}
    try:
        snapshot_res = backup_mgr.create_snapshot(tag="daily_screener")
        backup_status = {
            "last_snapshot_id": snapshot_res.get("snapshot_id"),
            "created_at": snapshot_res.get("created_at_ist"),
            "integrity_ok": snapshot_res.get("database_integrity_ok", True)
        }
        print(f"[BACKUP] Automated disaster recovery snapshot created: {snapshot_res.get('snapshot_id')}")
    except Exception as e:
        print(f"[BACKUP WARNING] Automated backup failed: {e}")
        backup_status = {"error": str(e)}

    # Consolidated Master Payload
    consolidated = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "as_of_date": as_of_date,
        "market_regime": market_regime,
        "total_triggers": len(all_signals_unified),
        "all_signals_unified": all_signals_unified,
        "portfolio_summary": portfolio_summary,
        "active_positions": portfolio_summary.get("positions", []),
        "backup_status": backup_status,
        "strategies": signals_by_strategy
    }

    # Write to output file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(CONSOLIDATED_SIGNALS_JSON, "w", encoding="utf-8") as f:
        json.dump(consolidated, f, indent=2)

    print("\n" + "=" * 70)
    print(f"[SUCCESS] Master Stage Consolidated Payload saved to:\n   {CONSOLIDATED_SIGNALS_JSON}")
    print(f"   Total Actionable Breakout Triggers Across All Strategies: {len(all_signals_unified)}")
    print(f"   Active Open Positions Tracked: {len(portfolio_summary.get('positions', []))}")
    print("=" * 70)

    return consolidated

def run_all_backtests() -> Dict[str, Any]:
    print("=" * 70)
    print("[BACKTEST] EXECUTING ON-DEMAND BACKTEST REFRESH ACROSS ALL STRATEGIES")
    print("=" * 70)

    db = get_db()
    portfolio_mgr = PortfolioManager(db=db)
    backup_mgr = BackupManager(db=db)

    strategies = get_registered_strategies()
    summaries = {}

    for strat in strategies:
        print(f"\n[BACKTEST ENGINE] Re-simulating: {strat.display_name}...")
        try:
            res = strat.run_backtest()
            summaries[strat.strategy_id] = {
                "display_name": strat.display_name,
                "kpis": res.get("kpis", {}),
                "trades_count": res.get("trades_count", 0)
            }

            # Persist KPIs
            if "kpis" in res and res["kpis"]:
                db.save_strategy_kpis(strat.strategy_id, strat.display_name, res["kpis"])
                print(f"  +-- Saved Strategy KPIs to database.")

            # Persist Trade History
            if "trade_log" in res and res["trade_log"]:
                saved_t = db.save_backtest_trades(strat.strategy_id, res["trade_log"])
                print(f"  +-- Saved {saved_t} audited trades to database.")
                # Sync any open trades at end of backtest into active positions
                synced_pos = portfolio_mgr.sync_from_backtest_open_trades(strat.strategy_id, res["trade_log"])
                if synced_pos:
                    print(f"  +-- Synced {synced_pos} open positions to portfolio tracker.")

            print(f"  +-- Backtest completed successfully.")
        except Exception as e:
            print(f"  +-- [ERROR] Backtest for {strat.strategy_id} failed: {e}")
            summaries[strat.strategy_id] = {"error": str(e)}

    # Automated Snapshot after backtest refresh
    try:
        snap = backup_mgr.create_snapshot(tag="backtest_refresh")
        summaries["backup_status"] = {
            "snapshot_id": snap.get("snapshot_id"),
            "created_at": snap.get("created_at_ist")
        }
    except Exception as e:
        print(f"[BACKUP WARNING] Backtest backup snapshot failed: {e}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(STRATEGY_SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2)

    print("\n" + "=" * 70)
    print(f"[SUCCESS] Backtest Summary saved to:\n   {STRATEGY_SUMMARY_JSON}")
    print("=" * 70)

    return summaries

def main():
    parser = argparse.ArgumentParser(description="Multi-Strategy Trading Pipeline Orchestrator")
    parser.add_argument("--mode", choices=["screener", "backtest", "all"], default="screener",
                        help="Execution mode: screener, backtest, or all")
    parser.add_argument("--date", type=str, default=None,
                        help="Target date for screener (YYYY-MM-DD or DD-MM-YYYY)")
    args = parser.parse_args()

    if args.mode in ("screener", "all"):
        run_all_screeners(target_date=args.date)
    if args.mode in ("backtest", "all"):
        run_all_backtests()

if __name__ == "__main__":
    main()
