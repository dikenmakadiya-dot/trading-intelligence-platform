import pandas as pd
import numpy as np
from pathlib import Path
import sys
import time
import shutil

# Ensure UTF-8 output on Windows console if available
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    LIVE_SIGNALS_OUTPUT_DIR,
    BASE_DIR,
    INITIAL_CAPITAL,
    MAX_OPEN_POSITIONS,
    MARKET_BREADTH_THRESHOLD,
    COST_PER_ROUND_TRIP,
    STAGNATION_EXIT_DAYS,
    STAGNATION_MIN_GAIN,
)
from src.data_loader import load_data
from .strategy_rules import scan_candidate_signals, compute_market_breadth, evaluate_candle_signal

def safe_save_csv(dataframe, filepath):
    """
    Saves a DataFrame to CSV safely. Handles file locks if opened in Excel.
    """
    filepath = Path(filepath)
    try:
        dataframe.to_csv(filepath, index=False)
        return filepath
    except PermissionError:
        print(f"\n[NOTICE] '{filepath.name}' is currently open in Excel.")
        for _ in range(2):
            time.sleep(1)
            try:
                dataframe.to_csv(filepath, index=False)
                return filepath
            except PermissionError:
                pass
                
        fallback_path = filepath.parent / f"{filepath.stem}_latest.csv"
        try:
            dataframe.to_csv(fallback_path, index=False)
            print(f"[INFO] Saved updated signals to: {fallback_path}")
            return fallback_path
        except Exception as e:
            print(f"[ERROR] Could not write fallback CSV: {e}")
            return filepath

def get_live_signals_for_date(df, target_date):
    """
    Scans all stocks on target_date for Champion 3-Day RSI Breakout setup.
    """
    all_signals = scan_candidate_signals(df, variant="champion")
    target_signals = all_signals[all_signals["Date"] == target_date].copy()
    if target_signals.empty:
        return []

    # Rank by RSI Jump and Volume Multiple
    target_signals.sort_values(by=["RSI_Jump", "Vol_Multiple_Day3"], ascending=[False, False], inplace=True)
    target_signals.reset_index(drop=True, inplace=True)

    signals_list = []
    slot_capital = INITIAL_CAPITAL / MAX_OPEN_POSITIONS

    for rank, (_, row) in enumerate(target_signals.iterrows(), start=1):
        c = float(row["Close"])
        h = float(row["High"])
        atr = float(row.get("ATR_14", 0.03 * c))
        st = float(row.get("SuperTrend", c * 0.95))
        st_sl = round(max(st, h - 1.5 * atr), 2)
        qty = int(slot_capital / h) if h > 0 else 0

        signals_list.append({
            "signal_date": target_date.strftime("%Y-%m-%d"),
            "rank_on_date": rank,
            "is_top5_priority": rank <= 5,
            "symbol": str(row["Symbol"]),
            "company_name": str(row.get("Company_Name", row["Symbol"])),
            "industry": str(row.get("Industry", "Diversified")),
            "index_name": str(row.get("Index_Name", "NIFTY 500")),
            "signal_close": round(c, 2),
            "entry_trigger": round(h, 2),
            "trailing_sl": st_sl,
            "supertrend": round(st, 2),
            "day3_rsi": round(float(row["RSI_14"]), 2),
            "day3_rsi_jump": round(float(row.get("RSI_Jump", 0.0)), 2),
            "vol_multiple": round(float(row.get("Vol_Multiple_Day3", 0.0)), 2),
            "atr_14": round(atr, 2),
            "suggested_qty": qty,
            "allocated_capital": round(qty * h, 2),
            "current_status": "BUY @ NEXT OPEN",
            "current_market_price": round(c, 2),
            "holding_days": 0,
            "unrealized_pnl_pct": 0.0,
        })

    return signals_list

def run_live_screener(df=None):
    """
    Main Live Screener with macro market breadth gating and visual reporting.
    """
    if df is None:
        df = load_data()

    latest_date = df["Date"].max()
    latest_date_str = latest_date.strftime("%Y-%m-%d")

    print("\n" + "=" * 80)
    print(f"   DAILY LIVE SIGNAL SCANNER — {latest_date.strftime('%d-%b-%Y').upper()}   ")
    print("=" * 80)

    # 1. Macro Market Breadth Gate
    print("\n[STEP 1/3] Assessing Macro Market Breadth Regime...")
    daily_breadth = compute_market_breadth(df)
    current_breadth = float(daily_breadth.get(latest_date, 0.50))
    breadth_pct = current_breadth * 100.0

    is_regime_bullish = current_breadth >= MARKET_BREADTH_THRESHOLD
    status_str = "BULLISH / ENTRY PERMITTED" if is_regime_bullish else "DEFENSIVE / ENTRY BLOCKED"
    print(f"  - Nifty 500 Market Breadth:  {breadth_pct:.1f}% stocks > EMA 50")
    print(f"  - Breadth Gate Threshold:    {MARKET_BREADTH_THRESHOLD*100:.1f}%")
    print(f"  - Strategy Execution Regime: [{status_str}]")

    # 2. Candidate Evaluation
    print(f"\n[STEP 2/3] Evaluating 3-Day RSI Momentum Setup on Nifty 750 Close...")
    fresh_signals = get_live_signals_for_date(df, latest_date)
    print(f"  [OK] Found {len(fresh_signals)} qualifying breakout candidates.")

    # 3. Load or initialize consolidated signals
    consolidated_csv_path = LIVE_SIGNALS_OUTPUT_DIR / "consolidated_signals_history.csv"
    LIVE_SIGNALS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    existing_signals = []
    if consolidated_csv_path.exists():
        try:
            existing_df = pd.read_csv(consolidated_csv_path)
            existing_signals = existing_df.to_dict("records")
        except Exception:
            existing_signals = []

    # Merge fresh signals if not already present
    existing_keys = {(s["symbol"], str(s["signal_date"])) for s in existing_signals}
    for s in fresh_signals:
        if (s["symbol"], s["signal_date"]) not in existing_keys:
            existing_signals.append(s)

    # Save consolidated
    if existing_signals:
        cons_df = pd.DataFrame(existing_signals)
        safe_save_csv(cons_df, consolidated_csv_path)
        print(f"  [OK] Saved Consolidated Signals Log: output\\live_signals\\consolidated_signals_history.csv")

    # Active positions vs fresh
    active_positions = [s for s in existing_signals if "HOLD" in str(s.get("current_status", ""))]

    print(f"\n[STEP 3/3] Daily Actionable Plan:")
    if not is_regime_bullish:
        print(f"  [ALERT] Macro Breadth is {breadth_pct:.1f}% (< {MARKET_BREADTH_THRESHOLD*100:.0f}%). CASH PROTECTION ACTIVE — NO ENTRIES.")
    elif fresh_signals:
        print(f"  [ACTION: BUY] {len(fresh_signals)} Setup Triggers Detected (Top 5 Priority Allocated):")
        for s in fresh_signals[:5]:
            print(f"    * Rank #{s['rank_on_date']}: {s['symbol']} ({s['company_name'][:25]})")
            print(f"      - Day-3 Close: Rs. {s['signal_close']:,.2f} | Entry Trigger: Rs. {s['entry_trigger']:,.2f} | Trail SL: Rs. {s['trailing_sl']:,.2f}")
            print(f"      - RSI: {s['day3_rsi']} (+{s['day3_rsi_jump']}) | Vol Surge: {s['vol_multiple']}x | Size: {s['suggested_qty']} shares (~Rs. {s['allocated_capital']:,.0f})")
    else:
        print("  - Fresh Signals Today: 0 (No breakout setups met strict 3-Day RSI + Volume criteria today)")

    # 4. Generate Interactive Dashboard
    generate_live_html_dashboard(existing_signals, fresh_signals, active_positions, latest_date, current_breadth)
    return fresh_signals

def generate_live_html_dashboard(all_signals, fresh_signals, active_positions, latest_date, current_breadth):
    """
    Generates an institutional dark-mode live screener dashboard HTML.
    """
    html_path = LIVE_SIGNALS_OUTPUT_DIR / "daily_signals_report.html"
    date_str = latest_date.strftime("%d-%b-%Y")
    breadth_pct = current_breadth * 100.0
    is_regime_bullish = current_breadth >= MARKET_BREADTH_THRESHOLD

    fresh_rows = []
    for s in fresh_signals:
        is_priority = s.get("is_top5_priority", False)
        badge = "bg-amber-500/10 text-amber-400 border border-amber-500/20" if is_priority else "bg-slate-700 text-slate-300"
        fresh_rows.append(f"""
        <tr class="hover:bg-slate-800/50">
            <td class="py-3 px-3 text-center"><span class="px-2 py-0.5 rounded text-xs font-bold {badge}">#{s['rank_on_date']}</span></td>
            <td class="py-3 px-3 font-bold text-white text-sm">{s['symbol']}<div class="text-[10px] text-slate-400 font-normal">{s['company_name']}</div></td>
            <td class="py-3 px-3 text-slate-400 text-xs">{s['industry']}</td>
            <td class="py-3 px-3 text-right font-semibold text-slate-200">₹{s['signal_close']:,.2f}</td>
            <td class="py-3 px-3 text-right font-bold text-emerald-400">₹{s['entry_trigger']:,.2f}</td>
            <td class="py-3 px-3 text-right font-semibold text-rose-400">₹{s['trailing_sl']:,.2f}</td>
            <td class="py-3 px-3 text-center font-bold text-sky-400">{s['day3_rsi']} <span class="text-xs text-emerald-400">(+{s['day3_rsi_jump']})</span></td>
            <td class="py-3 px-3 text-center font-bold text-amber-400">{s['vol_multiple']}x</td>
            <td class="py-3 px-3 text-right text-slate-300">{s['suggested_qty']} shs</td>
            <td class="py-3 px-3 text-center"><span class="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold">BUY</span></td>
        </tr>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Champion 3-Day RSI Momentum - Daily Live Screener ({date_str})</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body {{ font-family: 'Inter', sans-serif; background-color: #0b0f19; color: #f8fafc; }}
        .glass-card {{ background: rgba(17, 24, 39, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }}
        .metric-card:hover {{ transform: translateY(-2px); }}
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">

    <!-- Header Section -->
    <div class="max-w-7xl mx-auto mb-8">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6">
            <div>
                <div class="flex items-center gap-2 mb-2">
                    <span class="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-semibold uppercase">Daily Live Execution</span>
                    <span class="px-3 py-1 bg-sky-500/10 text-sky-400 border border-sky-500/20 rounded-full text-xs font-semibold">Nifty 750 Universe</span>
                </div>
                <h1 class="text-3xl md:text-4xl font-extrabold text-white">Daily Breakout Signals & Market Regime</h1>
                <p class="text-slate-400 text-sm mt-1">Generated for Close: <span class="text-slate-200 font-semibold">{date_str}</span> &bull; Strategy: 3-Day RSI + Volume Surge + 52W High</p>
            </div>
            <div class="flex items-center gap-3">
                <div class="glass-card p-3 rounded-xl border border-slate-800 text-right">
                    <div class="text-xs text-slate-400">Macro Market Breadth</div>
                    <div class="text-lg font-bold {'text-emerald-400' if is_regime_bullish else 'text-rose-400'}">{breadth_pct:.1f}% ({'BULLISH' if is_regime_bullish else 'DEFENSIVE'})</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Market Regime Alert Banner -->
    <div class="max-w-7xl mx-auto mb-8">
        <div class="glass-card p-4 rounded-xl border-l-4 {'border-emerald-500 bg-emerald-950/20' if is_regime_bullish else 'border-rose-500 bg-rose-950/20'} flex items-center justify-between">
            <div>
                <div class="font-bold text-sm {'text-emerald-300' if is_regime_bullish else 'text-rose-300'}">
                    {'Market Breadth Health: Optimal (Entries Permitted)' if is_regime_bullish else f'Market Breadth Health: Below Threshold (< {MARKET_BREADTH_THRESHOLD*100:.0f}%) - Cash Protection Active'}
                </div>
                <div class="text-xs text-slate-400 mt-0.5">
                    {f'Nifty 500 breadth is above the {MARKET_BREADTH_THRESHOLD*100:.0f}% threshold. Qualifying momentum breakouts are eligible for 20% slot allocation.' if is_regime_bullish else 'Market wide participation is weak. The strategy mechanically blocks new entries to protect capital from correlated drawdowns.'}
                </div>
            </div>
            <div class="text-right">
                <span class="px-3 py-1 rounded-full text-xs font-bold {'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' if is_regime_bullish else 'bg-rose-500/20 text-rose-300 border border-rose-500/40'}">
                    {'GATE: OPEN' if is_regime_bullish else 'GATE: CLOSED'}
                </span>
            </div>
        </div>
    </div>

    <!-- Fresh Signals Table -->
    <div class="max-w-7xl mx-auto glass-card p-6 rounded-2xl mb-8">
        <div class="flex items-center justify-between mb-4">
            <div>
                <h3 class="text-lg font-semibold text-white">Fresh Breakout Triggers ({len(fresh_signals)} Stocks)</h3>
                <p class="text-xs text-slate-400">Order execution trigger: Buy above Day-3 High with Trailing SuperTrend Stop</p>
            </div>
        </div>

        <div class="overflow-x-auto border border-slate-800 rounded-xl">
            <table class="w-full text-left text-xs text-slate-300">
                <thead class="bg-slate-800/80 uppercase tracking-wider text-slate-400">
                    <tr>
                        <th class="py-3 px-3 text-center">Rank</th>
                        <th class="py-3 px-3">Symbol</th>
                        <th class="py-3 px-3">Industry</th>
                        <th class="py-3 px-3 text-right">Close (₹)</th>
                        <th class="py-3 px-3 text-right">Entry Trigger (₹)</th>
                        <th class="py-3 px-3 text-right">Trail SL (₹)</th>
                        <th class="py-3 px-3 text-center">RSI (Jump)</th>
                        <th class="py-3 px-3 text-center">Vol Surge</th>
                        <th class="py-3 px-3 text-right">Slot Sizing</th>
                        <th class="py-3 px-3 text-center">Action</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-800">
                    {"".join(fresh_rows) if fresh_rows else '<tr><td colspan="10" class="py-8 text-center text-slate-500">No qualifying breakout signals detected on this date. Market is in consolidation.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Historical Log & Instructions -->
    <div class="max-w-7xl mx-auto glass-card p-6 rounded-2xl border-l-4 border-sky-500">
        <h4 class="text-sm font-bold text-white mb-2 uppercase tracking-wider">Trading Execution Instructions</h4>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-400">
            <div>
                <span class="text-slate-200 font-semibold block mb-1">1. Order Placement</span>
                Place GTT / Limit Buy order at Day-3 High at 09:15 AM market open. If triggered, buy 1 slot (20% of current equity).
            </div>
            <div>
                <span class="text-slate-200 font-semibold block mb-1">2. Risk Management</span>
                Initial stop loss is the Trailing SL (Max of SuperTrend and High - 1.5*ATR). Update SL daily as SuperTrend moves up.
            </div>
            <div>
                <span class="text-slate-200 font-semibold block mb-1">3. Stagnation Cutoff</span>
                If position return is &le; 2% after 15 trading days, exit on Day 16 open to recycle capital into higher-velocity momentum.
            </div>
        </div>
    </div>

</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  [OK] Saved Live Screener Report: {html_path}")

    # Sync to root Daily_Signals_Report.html
    root_signals_path = BASE_DIR / "Daily_Signals_Report.html"
    try:
        shutil.copyfile(html_path, root_signals_path)
        print(f"  [OK] Synced root convenience file:     {root_signals_path.name}")
    except Exception as e:
        print(f"  [WARN] Could not sync root Daily_Signals_Report.html: {e}")

    return html_path

if __name__ == "__main__":
    run_live_screener()
