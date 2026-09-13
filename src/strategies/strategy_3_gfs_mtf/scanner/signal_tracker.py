"""
Signal Tracker, Performance Efficacy & Warm HTML Report Generator.
Multi-Timeframe RSI Swing Trading Strategy (V3).

Consolidates all historical signals into a single master file with Signal_Date
as the first column, tracks actual trade execution and live efficacy against subsequent
market bars, and generates an executive warm-themed Signal Report HTML dashboard.
"""

import os
import sys
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.strategies.strategy_3_gfs_mtf.indicators.wilder_rsi import compute_wilder_rsi


def _format_pct(val: Optional[float], decimals: int = 2) -> str:
    if val is None or np.isnan(val):
        return "N/A"
    return f"{val:+.{decimals}f}%"


def _format_num(val: Optional[float], decimals: int = 2) -> str:
    if val is None or np.isnan(val):
        return "N/A"
    return f"{val:,.{decimals}f}"


def _format_date(val: Any) -> str:
    if val is None or pd.isnull(val):
        return "N/A"
    if isinstance(val, pd.Timestamp):
        return val.strftime("%Y-%m-%d")
    return str(val)[:10]


def _safe_write_text(file_path: str, content: str):
    """Safely writes text to a file, creating parent directories if needed."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def _safe_write_df_csv(df: pd.DataFrame, file_path: str):
    """Safely writes DataFrame to CSV."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    df.to_csv(file_path, index=False)


def consolidate_existing_signal_files(output_dir: str) -> pd.DataFrame:
    """
    Reads existing consolidated_signals.csv from outputs directory,
    deduplicating by (Signal_Date, Symbol).
    """
    if not os.path.exists(output_dir):
        return pd.DataFrame()

    all_dfs = []
    # Check direct outputs/consolidated_signals.csv
    cons_path = os.path.join(output_dir, "consolidated_signals.csv")
    if os.path.exists(cons_path):
        try:
            sub_df = pd.read_csv(cons_path)
            if not sub_df.empty:
                all_dfs.append(sub_df)
        except Exception:
            pass

    # Also check legacy outputs/signals/ folder if it exists
    legacy_dir = os.path.join(output_dir, "signals")
    if os.path.exists(legacy_dir):
        for fname in os.listdir(legacy_dir):
            if fname.endswith(".csv"):
                p = os.path.join(legacy_dir, fname)
                try:
                    sub_df = pd.read_csv(p)
                    if not sub_df.empty:
                        all_dfs.append(sub_df)
                except Exception:
                    pass

    if not all_dfs:
        return pd.DataFrame()

    merged = pd.concat(all_dfs, ignore_index=True)

    # Standardize column names
    if "Signal_Date" in merged.columns and "Symbol" in merged.columns:
        merged["Signal_Date"] = pd.to_datetime(merged["Signal_Date"]).dt.strftime("%Y-%m-%d")
        merged = merged.drop_duplicates(subset=["Signal_Date", "Symbol"]).reset_index(drop=True)

    return merged


def track_signal_performance(
    signals_df: pd.DataFrame,
    universe_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Simulates the actual post-signal price path for each signal in signals_df using universe_df.
    Computes:
      - Status: PENDING_T+1_ENTRY, ACTIVE_IN_TRADE, TRIGGERED_CLOSED, CANCELLED_NO_FILL
      - Entry_Date, Entry_Price
      - Exit_Date, Exit_Price, Exit_Reason
      - Current_Close, Current_Return_Pct, Realized_Return_Pct
      - Holding_Days
    """
    if signals_df.empty or universe_df.empty:
        return signals_df.copy()

    df_sig = signals_df.copy()
    universe_df = universe_df.sort_values(by=["Symbol", "Date"]).reset_index(drop=True)

    results = []
    for _, row in df_sig.iterrows():
        sig_date_str = str(row["Signal_Date"])[:10]
        sig_date = pd.to_datetime(sig_date_str)
        sym = str(row["Symbol"])
        buy_trigger = float(row.get("Buy_Trigger_Price", row.get("Current_Close", 0.0)))
        stop_loss = float(row.get("Stop_Loss_Price", 0.0))
        qty = int(row.get("Suggested_Quantity_1Lakh", 100))

        stock_bars = universe_df[universe_df["Symbol"] == sym].copy()
        if stock_bars.empty:
            rec = row.to_dict()
            rec["Execution_Status"] = "NO_DATA"
            results.append(rec)
            continue

        stock_bars["Date"] = pd.to_datetime(stock_bars["Date"])
        stock_bars = stock_bars.sort_values(by="Date").reset_index(drop=True)

        # Subsequent bars after Signal_Date
        subseq_bars = stock_bars[stock_bars["Date"] > sig_date].reset_index(drop=True)

        if subseq_bars.empty:
            # Signal generated on latest market date -> Pending next day entry
            rec = row.to_dict()
            rec["Execution_Status"] = "PENDING_T+1_ENTRY"
            rec["Entry_Date"] = "Pending T+1"
            rec["Entry_Price"] = np.nan
            rec["Exit_Date"] = "Open"
            rec["Exit_Price"] = np.nan
            rec["Exit_Reason"] = "Awaiting Market Open"
            rec["Return_Pct"] = 0.0
            rec["Holding_Days"] = 0
            rec["Current_Close"] = float(row.get("Current_Close", 0.0))
            rec["Current_Pnl_Rs"] = 0.0
            results.append(rec)
            continue

        # Day T+1 Bar
        bar_t1 = subseq_bars.iloc[0]
        t1_high = float(bar_t1["High"])
        t1_open = float(bar_t1["Open"])
        t1_low = float(bar_t1["Low"])
        t1_date = bar_t1["Date"].strftime("%Y-%m-%d")

        if t1_high < buy_trigger:
            # Order not triggered on T+1 -> Cancelled
            rec = row.to_dict()
            rec["Execution_Status"] = "CANCELLED_NO_FILL"
            rec["Entry_Date"] = "Not Triggered"
            rec["Entry_Price"] = np.nan
            rec["Exit_Date"] = t1_date
            rec["Exit_Price"] = np.nan
            rec["Exit_Reason"] = "High < Buy Trigger on T+1"
            rec["Return_Pct"] = 0.0
            rec["Holding_Days"] = 0
            rec["Current_Close"] = float(bar_t1["Close"])
            rec["Current_Pnl_Rs"] = 0.0
            results.append(rec)
            continue

        # Entry Filled!
        entry_price = max(buy_trigger, t1_open)
        entry_date = t1_date

        # Check if Stop Loss hit on Day T+1 itself
        if t1_low <= stop_loss:
            exit_price = min(stop_loss, t1_open)
            ret_pct = ((exit_price - entry_price) / entry_price) * 100.0
            rec = row.to_dict()
            rec["Execution_Status"] = "TRIGGERED_CLOSED"
            rec["Entry_Date"] = entry_date
            rec["Entry_Price"] = round(entry_price, 2)
            rec["Exit_Date"] = t1_date
            rec["Exit_Price"] = round(exit_price, 2)
            rec["Exit_Reason"] = "STOP_LOSS (Day T+1)"
            rec["Return_Pct"] = round(ret_pct, 2)
            rec["Holding_Days"] = 1
            rec["Current_Close"] = float(bar_t1["Close"])
            rec["Current_Pnl_Rs"] = round(ret_pct / 100.0 * entry_price * qty, 2)
            results.append(rec)
            continue

        # Simulate subsequent daily bars
        # Precompute RSI for the stock series
        if "Daily_RSI_14" in stock_bars.columns and not stock_bars["Daily_RSI_14"].isnull().all():
            rsi_series = stock_bars["Daily_RSI_14"].values
        else:
            rsi_series = compute_wilder_rsi(stock_bars["Close"], period=14).values
        stock_bars["_RSI"] = rsi_series

        # Find bar index in stock_bars corresponding to subseq_bars
        t1_idx = stock_bars[stock_bars["Date"] == bar_t1["Date"]].index[0]
        
        is_closed = False
        exit_date = None
        exit_price = None
        exit_reason = None
        holding_days = 0
        in_target_mode = False
        down_rsi_days = 0
        prev_rsi = None

        for curr_idx in range(t1_idx, len(stock_bars)):
            holding_days += 1
            curr_bar = stock_bars.iloc[curr_idx]
            curr_low = float(curr_bar["Low"])
            curr_open = float(curr_bar["Open"])
            curr_close = float(curr_bar["Close"])
            curr_date_str = curr_bar["Date"].strftime("%Y-%m-%d")
            curr_rsi = float(curr_bar["_RSI"]) if not np.isnan(curr_bar["_RSI"]) else 50.0

            # 1. Check Stop Loss (Intraday priority)
            if curr_low <= stop_loss:
                exit_price = min(stop_loss, curr_open)
                exit_date = curr_date_str
                exit_reason = "STOP_LOSS"
                is_closed = True
                break

            # 2. Check Momentum Exhaustion Exit
            if not in_target_mode:
                if curr_rsi >= 60.0:
                    in_target_mode = True
                    down_rsi_days = 0
                    prev_rsi = curr_rsi
            else:
                if curr_rsi < 60.0:
                    exit_price = curr_close
                    exit_date = curr_date_str
                    exit_reason = "TARGET_RSI_DROP_BELOW_60"
                    is_closed = True
                    break
                else:
                    if prev_rsi is not None and curr_rsi < prev_rsi:
                        down_rsi_days += 1
                    else:
                        down_rsi_days = 0
                    
                    is_red = curr_close < curr_open
                    if down_rsi_days >= 2 and is_red:
                        exit_price = curr_close
                        exit_date = curr_date_str
                        exit_reason = "TARGET_MOMENTUM_EXHAUSTION_2D_RED"
                        is_closed = True
                        break
                    
                    prev_rsi = curr_rsi

        rec = row.to_dict()
        latest_market_close = float(stock_bars.iloc[-1]["Close"])
        rec["Current_Close"] = round(latest_market_close, 2)

        if is_closed:
            ret_pct = ((exit_price - entry_price) / entry_price) * 100.0
            rec["Execution_Status"] = "TRIGGERED_CLOSED"
            rec["Entry_Date"] = entry_date
            rec["Entry_Price"] = round(entry_price, 2)
            rec["Exit_Date"] = exit_date
            rec["Exit_Price"] = round(exit_price, 2)
            rec["Exit_Reason"] = exit_reason
            rec["Return_Pct"] = round(ret_pct, 2)
            rec["Holding_Days"] = holding_days
            rec["Current_Pnl_Rs"] = round(ret_pct / 100.0 * entry_price * qty, 2)
        else:
            unrealized_ret = ((latest_market_close - entry_price) / entry_price) * 100.0
            rec["Execution_Status"] = "ACTIVE_IN_TRADE"
            rec["Entry_Date"] = entry_date
            rec["Entry_Price"] = round(entry_price, 2)
            rec["Exit_Date"] = "Active"
            rec["Exit_Price"] = round(latest_market_close, 2)
            rec["Exit_Reason"] = "In Progress (Riding Trend)" if in_target_mode else "In Progress"
            rec["Return_Pct"] = round(unrealized_ret, 2)
            rec["Holding_Days"] = holding_days
            rec["Current_Pnl_Rs"] = round(unrealized_ret / 100.0 * entry_price * qty, 2)

        results.append(rec)

    res_df = pd.DataFrame(results)

    # Put Signal_Date as the very FIRST column
    cols = ["Signal_Date", "Symbol", "Company_Name", "Industry", "Current_Close", "Buy_Trigger_Price", 
            "Stop_Loss_Price", "ATR_14", "Planned_Risk_Pct", "Daily_RSI_14", "Weekly_RSI_Completed", 
            "Monthly_RSI_Completed", "Suggested_Quantity_1Lakh", "Execution_Status", "Entry_Date", 
            "Entry_Price", "Exit_Date", "Exit_Price", "Exit_Reason", "Return_Pct", "Holding_Days", "Current_Pnl_Rs"]
    
    available_cols = [c for c in cols if c in res_df.columns]
    extra_cols = [c for c in res_df.columns if c not in available_cols]
    final_cols = available_cols + extra_cols
    res_df = res_df[final_cols].sort_values(by=["Signal_Date", "Symbol"], ascending=[True, True]).reset_index(drop=True)
    return res_df


def generate_signal_report_html(
    tracked_signals_df: pd.DataFrame,
    output_path: str,
    backtest_kpis: Optional[Any] = None,
) -> str:
    """
    Generates a publication-grade, interactive HTML report for live signal performance & efficacy,
    designed with a sophisticated warm color palette.
    """
    df = tracked_signals_df.copy()
    if df.empty:
        total_sigs = 0
        active_trades = pd.DataFrame()
        closed_trades = pd.DataFrame()
        pending_trades = pd.DataFrame()
        cancelled_trades = pd.DataFrame()
        win_rate = 0.0
        avg_ret = 0.0
        fill_rate = 0.0
    else:
        total_sigs = len(df)
        active_trades = df[df["Execution_Status"] == "ACTIVE_IN_TRADE"]
        closed_trades = df[df["Execution_Status"] == "TRIGGERED_CLOSED"]
        pending_trades = df[df["Execution_Status"] == "PENDING_T+1_ENTRY"]
        cancelled_trades = df[df["Execution_Status"] == "CANCELLED_NO_FILL"]

        triggered_count = len(active_trades) + len(closed_trades)
        fill_rate = (triggered_count / total_sigs * 100.0) if total_sigs > 0 else 0.0

        if not closed_trades.empty:
            wins = closed_trades[closed_trades["Return_Pct"] > 0]
            win_rate = (len(wins) / len(closed_trades) * 100.0)
            avg_ret = closed_trades["Return_Pct"].mean()
        else:
            win_rate = 0.0
            avg_ret = 0.0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>V3 MTF RSI Swing Strategy — Signal Report</title>
    <style>
        :root {{
            --bg: #181412;
            --surface: #231c18;
            --surface-card: #2c221d;
            --surface-hover: #382c26;
            --border: #44342c;
            --text-main: #fbf8f5;
            --text-muted: #b8a698;
            --primary: #f59e0b;
            --primary-light: #fbbf24;
            --accent-warm: #ea580c;
            --accent-green: #10b981;
            --accent-rose: #f43f5e;
            --accent-amber: #d97706;
            --accent-badge: rgba(245, 158, 11, 0.12);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            line-height: 1.6;
            padding: 2.5rem 1.5rem;
            max-width: 1280px;
            margin: 0 auto;
        }}
        header {{
            background: linear-gradient(135deg, #2c201a 0%, #1a1412 100%);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        }}
        h1 {{ font-size: 2.2rem; font-weight: 800; color: #ffffff; margin-bottom: 0.5rem; }}
        h1 span {{ color: var(--primary); }}
        .subtitle {{ font-size: 1.05rem; color: var(--text-muted); }}
        .badges-bar {{ display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 1.2rem; }}
        .badge {{
            display: inline-flex; align-items: center; padding: 0.3rem 0.8rem;
            border-radius: 9999px; font-size: 0.8rem; font-weight: 600; text-transform: uppercase;
        }}
        .badge-warm {{ background: rgba(234, 88, 12, 0.15); color: #fb923c; border: 1px solid rgba(234, 88, 12, 0.3); }}
        .badge-amber {{ background: rgba(245, 158, 11, 0.15); color: var(--primary); border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge-green {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.3); }}
        h2 {{
            font-size: 1.45rem; font-weight: 700; color: #ffffff; margin: 2.5rem 0 1.25rem 0;
            padding-bottom: 0.5rem; border-bottom: 2px solid var(--border); display: flex; align-items: center; gap: 0.5rem;
        }}
        h2::before {{ content: ''; display: inline-block; width: 8px; height: 1.2rem; background: var(--primary); border-radius: 4px; }}
        .grid-4 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }}
        .metric-card {{ background-color: var(--surface-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }}
        .metric-card:hover {{ border-color: var(--primary); background-color: var(--surface-hover); }}
        .metric-title {{ font-size: 0.82rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-bottom: 0.3rem; }}
        .metric-val {{ font-size: 1.6rem; font-weight: 700; color: #ffffff; }}
        .metric-val.positive {{ color: var(--accent-green); }}
        .metric-val.negative {{ color: var(--accent-rose); }}
        .metric-val.warm {{ color: var(--primary); }}
        .metric-sub {{ font-size: 0.82rem; color: var(--text-muted); margin-top: 0.2rem; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1.25rem 0; border-radius: 10px; overflow: hidden; border: 1px solid var(--border); background: var(--surface); }}
        th {{ background-color: #1a1411; color: #ffffff; font-weight: 600; text-align: left; padding: 0.8rem 0.9rem; font-size: 0.85rem; border-bottom: 1px solid var(--border); text-transform: uppercase; }}
        td {{ padding: 0.75rem 0.9rem; font-size: 0.9rem; border-bottom: 1px solid var(--border); color: var(--text-main); }}
        tr:hover td {{ background-color: rgba(245, 158, 11, 0.03); }}
        .pos {{ color: var(--accent-green); font-weight: 600; }}
        .neg {{ color: var(--accent-rose); font-weight: 600; }}
        .badge-status {{ padding: 0.2rem 0.5rem; border-radius: 6px; font-size: 0.75rem; font-weight: 700; display: inline-block; }}
        .status-active {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }}
        .status-closed {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }}
        .status-pending {{ background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }}
        .status-cancelled {{ background: rgba(148, 163, 184, 0.2); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.4); }}
        code {{ font-family: 'Consolas', monospace; background: rgba(24, 20, 18, 0.8); padding: 0.15rem 0.4rem; border-radius: 4px; color: var(--primary); font-size: 0.88em; }}
        footer {{ margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); text-align: center; color: var(--text-muted); font-size: 0.85rem; }}
    </style>
</head>
<body>
    <header>
        <h1>V3 MTF RSI Swing Strategy — <span>Signal Report</span></h1>
        <div class="subtitle">Live Signal Execution, Trade Efficacy & Active Position Tracking Dashboard</div>
        <div class="badges-bar">
            <span class="badge badge-warm">Live Efficacy Tracker</span>
            <span class="badge badge-amber">V3 Production Engine</span>
            <span class="badge badge-green">Consolidated Master Feed</span>
        </div>
    </header>

    <!-- Key Efficacy Metrics -->
    <div class="grid-4">
        <div class="metric-card">
            <div class="metric-title">Total Signals Tracked</div>
            <div class="metric-val warm">{total_sigs}</div>
            <div class="metric-sub">{len(active_trades)} Active • {len(closed_trades)} Closed • {len(pending_trades)} Pending</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Order Fill / Trigger Rate</div>
            <div class="metric-val">{fill_rate:.1f}%</div>
            <div class="metric-sub">{len(active_trades) + len(closed_trades)} of {total_sigs} breached T+1 High</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Closed Trades Win Rate</div>
            <div class="metric-val {'positive' if win_rate >= 35 else 'warm'}">{win_rate:.1f}%</div>
            <div class="metric-sub">{len(closed_trades[closed_trades['Return_Pct'] > 0]) if not closed_trades.empty else 0} Wins / {len(closed_trades[closed_trades['Return_Pct'] < 0]) if not closed_trades.empty else 0} Losses</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Avg Closed Trade Return</div>
            <div class="metric-val {'positive' if avg_ret >= 0 else 'negative'}">{avg_ret:+.2f}%</div>
            <div class="metric-sub">Target Exit vs Stop Loss</div>
        </div>
    </div>

    <!-- Active Open Positions -->
    <h2>1. Active Open Positions (In-Trade)</h2>
"""
    if active_trades.empty:
        html += """    <p style="color: var(--text-muted); padding: 1rem; background: var(--surface); border-radius: 8px;">No active open trades currently in progress.</p>"""
    else:
        html += """    <table>
        <thead>
            <tr><th>Signal Date</th><th>Symbol</th><th>Entry Date</th><th>Entry (₹)</th><th>Current (₹)</th><th>Unrealized (%)</th><th>SL (₹)</th><th>Days Held</th><th>Status / Mode</th></tr>
        </thead>
        <tbody>
"""
        for _, r in active_trades.iterrows():
            ret_cls = "pos" if r["Return_Pct"] >= 0 else "neg"
            html += f"""            <tr>
                <td><strong>{_format_date(r['Signal_Date'])}</strong></td>
                <td><code>{r['Symbol']}</code></td>
                <td>{_format_date(r['Entry_Date'])}</td>
                <td>{_format_num(r['Entry_Price'])}</td>
                <td>{_format_num(r['Current_Close'])}</td>
                <td class="{ret_cls}"><strong>{r['Return_Pct']:+.2f}%</strong></td>
                <td>{_format_num(r['Stop_Loss_Price'])}</td>
                <td>{int(r['Holding_Days'])} Days</td>
                <td><span class="badge-status status-active">{r['Exit_Reason']}</span></td>
            </tr>
"""
        html += """        </tbody>
    </table>
"""

    # Newly Generated / Pending Orders
    html += """    <h2>2. Pending Next-Day Orders (Awaiting T+1 Session)</h2>"""
    if pending_trades.empty:
        html += """    <p style="color: var(--text-muted); padding: 1rem; background: var(--surface); border-radius: 8px;">No pending orders awaiting next market session.</p>"""
    else:
        html += """    <table>
        <thead>
            <tr><th>Signal Date</th><th>Symbol</th><th>Company Name</th><th>Buy Trigger (₹)</th><th>Stop Loss (₹)</th><th>Risk %</th><th>Qty (1L)</th><th>Daily RSI</th><th>Order Action</th></tr>
        </thead>
        <tbody>
"""
        for _, r in pending_trades.iterrows():
            html += f"""            <tr>
                <td><strong>{_format_date(r['Signal_Date'])}</strong></td>
                <td><code>{r['Symbol']}</code></td>
                <td>{str(r.get('Company_Name', 'N/A'))[:25]}</td>
                <td><strong>{_format_num(r['Buy_Trigger_Price'])}</strong></td>
                <td class="neg">{_format_num(r['Stop_Loss_Price'])}</td>
                <td>{r.get('Planned_Risk_Pct', 0.0):.2f}%</td>
                <td>{int(r.get('Suggested_Quantity_1Lakh', 0))}</td>
                <td>{r.get('Daily_RSI_14', 0.0):.2f}</td>
                <td><span class="badge-status status-pending">BUY STOP AT OPEN</span></td>
            </tr>
"""
        html += """        </tbody>
    </table>
"""

    # Completed Trades Audit
    html += """    <h2>3. Completed Signal Trades (Realized Performance)</h2>"""
    if closed_trades.empty:
        html += """    <p style="color: var(--text-muted); padding: 1rem; background: var(--surface); border-radius: 8px;">No closed signal trades recorded yet.</p>"""
    else:
        html += """    <table>
        <thead>
            <tr><th>Signal Date</th><th>Symbol</th><th>Entry Date</th><th>Entry (₹)</th><th>Exit Date</th><th>Exit (₹)</th><th>Return (%)</th><th>Days</th><th>Exit Reason</th></tr>
        </thead>
        <tbody>
"""
        for _, r in closed_trades.iterrows():
            ret_cls = "pos" if r["Return_Pct"] >= 0 else "neg"
            html += f"""            <tr>
                <td><strong>{_format_date(r['Signal_Date'])}</strong></td>
                <td><code>{r['Symbol']}</code></td>
                <td>{_format_date(r['Entry_Date'])}</td>
                <td>{_format_num(r['Entry_Price'])}</td>
                <td>{_format_date(r['Exit_Date'])}</td>
                <td>{_format_num(r['Exit_Price'])}</td>
                <td class="{ret_cls}"><strong>{r['Return_Pct']:+.2f}%</strong></td>
                <td>{int(r['Holding_Days'])}</td>
                <td><span class="badge-status status-closed">{r['Exit_Reason']}</span></td>
            </tr>
"""
        html += """        </tbody>
    </table>
"""

    # Cancelled Orders Log
    if not cancelled_trades.empty:
        html += f"""    <h2>4. Unfulfilled / Cancelled Signals ({len(cancelled_trades)} Orders)</h2>
    <table>
        <thead>
            <tr><th>Signal Date</th><th>Symbol</th><th>Buy Trigger (₹)</th><th>Stop Loss (₹)</th><th>Status</th></tr>
        </thead>
        <tbody>
"""
        for _, r in cancelled_trades.iterrows():
            html += f"""            <tr>
                <td>{_format_date(r['Signal_Date'])}</td>
                <td><code>{r['Symbol']}</code></td>
                <td>{_format_num(r['Buy_Trigger_Price'])}</td>
                <td>{_format_num(r['Stop_Loss_Price'])}</td>
                <td><span class="badge-status status-cancelled">{r['Exit_Reason']}</span></td>
            </tr>
"""
        html += """        </tbody>
    </table>
"""

    html += """    <footer>
        V3 MTF RSI Swing Trading Strategy • Live Signal Efficacy & Performance Dashboard
    </footer>
</body>
</html>
"""
    _safe_write_text(output_path, html)
    return os.path.abspath(output_path)
