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

def get_registered_strategies():
    return [
        Strategy1RSI52W(),
        Strategy2CleanCandle5Y(),
        Strategy3GFSMTF()
    ]

def run_all_screeners(target_date: str = None) -> Dict[str, Any]:
    print("=" * 70)
    print("?? QUANTFLOW TRADING INTELLIGENCE - MULTI-STRATEGY SCREENER PIPELINE")
    print(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

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

    # Consolidated Master Payload
    consolidated = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "as_of_date": target_date or (next((v.get("as_of_date") for v in signals_by_strategy.values() if v.get("as_of_date")), "Latest")),
        "market_regime": market_regime,
        "total_triggers": len(all_signals_unified),
        "all_signals_unified": all_signals_unified,
        "strategies": signals_by_strategy
    }

    # Write to output file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(CONSOLIDATED_SIGNALS_JSON, "w", encoding="utf-8") as f:
        json.dump(consolidated, f, indent=2)

    print("\n" + "=" * 70)
    print(f"? Master Stage Consolidated Payload saved to:\n   {CONSOLIDATED_SIGNALS_JSON}")
    print(f"   Total Actionable Breakout Triggers Across All Strategies: {len(all_signals_unified)}")
    print("=" * 70)

    return consolidated

def run_all_backtests() -> Dict[str, Any]:
    print("=" * 70)
    print("?? EXECUTING ON-DEMAND BACKTEST REFRESH ACROSS ALL STRATEGIES")
    print("=" * 70)

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
            print(f"  +-- Backtest completed successfully.")
        except Exception as e:
            print(f"  +-- [ERROR] Backtest for {strat.strategy_id} failed: {e}")
            summaries[strat.strategy_id] = {"error": str(e)}

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(STRATEGY_SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2)

    print("\n" + "=" * 70)
    print(f"? Backtest Summary saved to:\n   {STRATEGY_SUMMARY_JSON}")
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
