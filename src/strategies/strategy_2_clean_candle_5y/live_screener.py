import pandas as pd
import numpy as np
from pathlib import Path
import sys
import time

# Ensure UTF-8 output on Windows console if available
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    LIVE_SIGNALS_OUTPUT_DIR,
    PROFIT_TARGET_PCT,
    MAX_HOLDING_DAYS,
    COST_PER_ROUND_TRIP
)
from src.data_loader import load_data
from .strategy_rules import evaluate_candle_signal

def safe_save_csv(dataframe, filepath):
    """
    Saves a DataFrame to CSV safely. If the file is locked by Excel,
    it attempts retries and falls back to a temporary update file if necessary.
    """
    filepath = Path(filepath)
    try:
        dataframe.to_csv(filepath, index=False)
        return filepath
    except PermissionError:
        print(f"\n[NOTICE] '{filepath.name}' is currently open in Excel.")
        for attempt in range(1, 3):
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
            print(f"[TIP] Close '{filepath.name}' in Excel to allow direct overwrites next time.\n")
            return fallback_path
        except Exception as e:
            print(f"[ERROR] Could not write fallback CSV: {e}")
            return filepath

def get_live_signals_for_date(df, target_date):
    """
    Scans all 750 stocks on a specific target date and returns confirmed breakout signals.
    """
    signals = []
    
    for symbol, group in df.groupby('Symbol'):
        group = group.reset_index(drop=True)
        n = len(group)
        if n < 50:
            continue
            
        group_sub = group[group['Date'] <= target_date].reset_index(drop=True)
        n_sub = len(group_sub)
        if n_sub < 50 or group_sub['Date'].iloc[-1] != target_date:
            continue
            
        t = n_sub - 1
        
        company_name = group_sub['Company_Name'].iloc[0] if 'Company_Name' in group_sub.columns else symbol
        industry = group_sub['Industry'].iloc[0] if 'Industry' in group_sub.columns else 'Unknown'
        index_name = group_sub['Index_Name'].iloc[0] if 'Index_Name' in group_sub.columns else 'Unknown'
        
        closes = group_sub['Close'].values
        highs = group_sub['High'].values
        lows = group_sub['Low'].values
        opens = group_sub['Open'].values
        vols = group_sub['Volume'].values
        sma10s = group_sub['SMA_10'].values
        sma20s = group_sub['SMA_20'].values
        rsi14s = group_sub['RSI_14'].values
        
        cum_max_close = np.maximum.accumulate(closes)
        cum_max_high = np.maximum.accumulate(highs)
        
        p_close = cum_max_close[t-1]
        p_high = cum_max_high[t-1]
        
        is_sig, m = evaluate_candle_signal(
            closes[t], highs[t], lows[t], opens[t], vols[t], vols[t-1],
            p_close, p_high, sma10s[t], sma20s[t], rsi14s[t], rsi14s[t-1]
        )
        
        if is_sig:
            signals.append({
                'signal_date': target_date.strftime('%Y-%m-%d'),
                'symbol': symbol,
                'company_name': company_name,
                'industry': industry,
                'index_name': index_name,
                'signal_close': round(closes[t], 2),
                'breakout_high': round(highs[t], 2),
                'stop_loss_price': round(m['sl_price'], 2),
                'target_price': round(closes[t] * (1.0 + PROFIT_TARGET_PCT), 2),
                'risk_pct': round(((closes[t] - m['sl_price']) / closes[t]) * 100, 2),
                'vol_ratio': m['vol_ratio'],
                'rsi_today': m['rsi_t'],
                'rsi_jump': m['rsi_delta'],
                'body_ratio_pct': m['body_ratio'],
                'momentum_score': m['momentum_score'],
                'current_status': 'BUY (Tomorrow Open)',
                'current_market_price': round(closes[t], 2),
                'holding_days': 0,
                'unrealized_pnl_pct': 0.0,
                'exit_date': None,
                'exit_price': None,
                'exit_reason': None
            })
            
    signals.sort(key=lambda x: x['momentum_score'], reverse=True)
    total_on_day = len(signals)
    for i, s in enumerate(signals):
        s['total_signals_on_date'] = total_on_day
        s['rank_on_date'] = i + 1
        s['is_top5_priority'] = (i < 5) if total_on_day > 5 else True
        s['priority_label'] = f"Top 5 Priority (Rank #{i+1})" if (total_on_day > 5 and i < 5) else (f"Active Candidate (Rank #{i+1})" if total_on_day <= 5 else f"Alternate (Rank #{i+1})")
        
    return signals

def update_live_signal_tracking(persisted_signals, df, latest_date):
    """
    Updates the live trade status (BUY, HOLD, SELL) of all previously tracked live signals.
    """
    stock_groups = {symbol: group.sort_values('Date').reset_index(drop=True) for symbol, group in df.groupby('Symbol')}
    updated_list = []
    
    for s in persisted_signals:
        sig_date = pd.to_datetime(s['signal_date'])
        symbol = s['symbol']
        
        if sig_date == latest_date:
            s['current_status'] = "BUY (Tomorrow Open)"
            s['holding_days'] = 0
            s['unrealized_pnl_pct'] = 0.0
            updated_list.append(s)
            continue
            
        if s.get('exit_reason') and str(s['exit_reason']) not in ['None', '', 'nan']:
            updated_list.append(s)
            continue
            
        if symbol not in stock_groups:
            updated_list.append(s)
            continue
            
        group = stock_groups[symbol]
        f_bars = group[(group['Date'] > sig_date) & (group['Date'] <= latest_date)].reset_index(drop=True)
        
        if len(f_bars) == 0:
            s['current_status'] = "BUY (Tomorrow Open)"
            s['holding_days'] = 0
            s['unrealized_pnl_pct'] = 0.0
            updated_list.append(s)
            continue
            
        entry_open = f_bars['Open'].iloc[0]
        sl_price = float(s['stop_loss_price'])
        target_price = float(s['target_price'])
        
        holding_days = 0
        is_closed = False
        exit_date = None
        exit_price = None
        exit_reason = None
        
        for idx, row in f_bars.iterrows():
            holding_days += 1
            b_open = row['Open']
            b_high = row['High']
            b_low = row['Low']
            b_close = row['Close']
            b_date = row['Date']
            
            # 1. Stop Loss Check
            if b_low <= sl_price:
                exit_price = min(b_open, sl_price)
                exit_date = b_date
                exit_reason = "Stop Loss Hit"
                is_closed = True
                break
                
            # 2. Target Check
            if b_high >= target_price:
                exit_price = max(b_open, target_price)
                exit_date = b_date
                exit_reason = "Target Hit (+8%)"
                is_closed = True
                break
                
            # 3. Time Stop (10 Days)
            if holding_days >= MAX_HOLDING_DAYS:
                exit_price = b_close
                exit_date = b_date
                exit_reason = f"Time Stop (Day {MAX_HOLDING_DAYS})"
                is_closed = True
                break
                
        if is_closed:
            s['current_status'] = f"SELL ({exit_reason})"
            s['current_market_price'] = round(exit_price, 2)
            s['exit_date'] = exit_date.strftime('%Y-%m-%d')
            s['exit_price'] = round(exit_price, 2)
            s['exit_reason'] = exit_reason
            s['holding_days'] = holding_days
            s['unrealized_pnl_pct'] = round(((exit_price - entry_open) / entry_open) * 100 - (COST_PER_ROUND_TRIP * 100), 2)
        else:
            current_close = f_bars['Close'].iloc[-1]
            s['current_status'] = f"HOLD (Day {holding_days}/{MAX_HOLDING_DAYS})"
            s['current_market_price'] = round(current_close, 2)
            s['holding_days'] = holding_days
            s['unrealized_pnl_pct'] = round(((current_close - entry_open) / entry_open) * 100 - (COST_PER_ROUND_TRIP * 100), 2)
            
        updated_list.append(s)
        
    return updated_list

def run_live_screener(df=None):
    """
    Main Live Screener with enhanced console formatting.
    """
    if df is None:
        df = load_data()
        
    latest_date = df['Date'].max()
    latest_date_str = latest_date.strftime('%Y-%m-%d')
    
    print(f"\n[STEP 2/3] Evaluating Clean Candle Breakout Rules on Latest Close ({latest_date.strftime('%d-%b-%Y')})...")
    print("  - 5-Year High Breakout Lookback: Checked")
    print("  - Volume Explosion Multiplier (>= 3.0x): Checked")
    print("  - 10 & 20 SMA Bullish Alignment: Checked")
    print("  - RSI Impulse Jump (>= +8.0): Checked")
    print("  - Clean Green Body Ratio (>= 40%): Checked")
    
    # 1. Scan fresh signals on the latest date
    today_signals = get_live_signals_for_date(df, latest_date)
    print(f"  [OK] Fresh Breakout Signals Found Today: {len(today_signals)} stock(s)")
    
    # 2. Load existing live-only consolidated history
    consolidated_csv_path = LIVE_SIGNALS_OUTPUT_DIR / "consolidated_signals_history.csv"
    existing_records = []
    
    if consolidated_csv_path.exists():
        try:
            existing_df = pd.read_csv(consolidated_csv_path)
            existing_records = existing_df.to_dict('records')
        except Exception:
            existing_records = []
            
    # Merge today's signals into existing history
    existing_keys = {(str(r['signal_date']), str(r['symbol'])) for r in existing_records}
    for s in today_signals:
        if (s['signal_date'], s['symbol']) not in existing_keys:
            existing_records.append(s)
            existing_keys.add((s['signal_date'], s['symbol']))
            
    # 3. Update real-time forward tracking (BUY, HOLD, SELL)
    all_live_signals = update_live_signal_tracking(existing_records, df, latest_date)
    all_live_signals.sort(key=lambda x: (str(x['signal_date']), float(x.get('momentum_score', 0))), reverse=True)
    
    # Save Consolidated CSV
    consolidated_df = pd.DataFrame(all_live_signals)
    saved_path = safe_save_csv(consolidated_df, consolidated_csv_path)
    
    fresh_signals = [s for s in all_live_signals if s['signal_date'] == latest_date_str]
    active_positions = [s for s in all_live_signals if 'HOLD' in str(s['current_status'])]
    
    print("\n[STEP 3/3] Live Trade Tracking & Status Overview:")
    if fresh_signals:
        print(f"\n  [ACTION: BUY @ 9:15 AM TOMORROW] Fresh Breakout Signals ({len(fresh_signals)} Stock):")
        for s in fresh_signals:
            p_badge = " [TOP 5 PRIORITY]" if s.get('is_top5_priority', False) else ""
            print(f"    * [Rank #{s['rank_on_date']}] {s['symbol']} ({s['company_name']}){p_badge}")
            print(f"      - Close: Rs. {s['signal_close']:,.2f} | Stop Loss: Rs. {s['stop_loss_price']:,.2f} | Target (+8%): Rs. {s['target_price']:,.2f}")
            print(f"      - Vol Surge: {s['vol_ratio']}x | RSI Jump: +{s['rsi_jump']} | Momentum Score: {s['momentum_score']}")
    else:
        print("  - Fresh Signals Today: 0 (Market is consolidating - No breakout matches)")
        
    print(f"\n  [ACTION: HOLD] Active Open Positions: {len(active_positions)} stock(s)")
    for p in active_positions:
        pnl_str = f"+{p['unrealized_pnl_pct']}%" if p['unrealized_pnl_pct'] >= 0 else f"{p['unrealized_pnl_pct']}%"
        print(f"    * {p['symbol']} | Status: {p['current_status']} | CMP: Rs. {p['current_market_price']:,.2f} | P&L: {pnl_str}")
        
    print(f"\n  📁 Master Consolidated Signals Logged: {len(all_live_signals)} total historical live triggers")
    print(f"  [OK] Saved Consolidated CSV:    output\\live_signals\\consolidated_signals_history.csv")
    
    # Save HTML Report
    generate_live_html_dashboard(all_live_signals, fresh_signals, active_positions, latest_date)
    return fresh_signals

def generate_live_html_dashboard(all_signals, fresh_signals, active_positions, latest_date):
    """
    Generates a single comprehensive interactive HTML dashboard.
    """
    html_path = LIVE_SIGNALS_OUTPUT_DIR / "daily_signals_report.html"
    date_str = latest_date.strftime('%d-%b-%Y')
    
    buy_count = len(fresh_signals)
    hold_count = len(active_positions)
    closed_trades = [s for s in all_signals if 'SELL' in str(s.get('current_status', ''))]
    sell_count = len(closed_trades)
    
    has_more_than_5_today = len(fresh_signals) > 5
    fresh_rows_html = []
    for s in fresh_signals:
        is_priority = s.get('is_top5_priority', False) and has_more_than_5_today
        if is_priority:
            symbol_badge = f"""
            <div class="inline-flex items-center gap-1.5 bg-yellow-400 text-black px-2.5 py-1 rounded-md shadow-md border border-yellow-300">
                <span class="text-sm font-black tracking-wide">{s['symbol']}</span>
                <span class="text-[10px] bg-black text-yellow-300 font-bold px-1.5 py-0.5 rounded">TOP #{s['rank_on_date']} PRIORITY</span>
            </div>
            <div class="text-[11px] text-slate-300 font-medium mt-0.5">{s['company_name']}</div>
            """
            row_class = "bg-yellow-500/10 hover:bg-yellow-500/20 border-l-4 border-yellow-400"
            rank_display = f"<span class='text-yellow-400 font-black text-sm'>#{s['rank_on_date']} ⭐</span>"
        elif not has_more_than_5_today:
            symbol_badge = f"""
            <div class="inline-flex items-center gap-1.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded">
                <span class="text-sm font-bold">{s['symbol']}</span>
            </div>
            <div class="text-[10px] text-slate-400 font-normal">{s['company_name']}</div>
            """
            row_class = "hover:bg-slate-800/50"
            rank_display = f"<span class='text-slate-400 font-bold'>#{s['rank_on_date']}</span>"
        else:
            symbol_badge = f"""
            <div class="font-semibold text-slate-300 text-sm">{s['symbol']}</div>
            <div class="text-[10px] text-slate-400 font-normal">{s['company_name']}</div>
            """
            row_class = "hover:bg-slate-800/30 opacity-80"
            rank_display = f"<span class='text-slate-500 font-medium'>#{s['rank_on_date']}</span>"
            
        fresh_rows_html.append(f"""
        <tr class="{row_class}">
            <td class="py-3 px-3">{rank_display}</td>
            <td class="py-3 px-3">{symbol_badge}</td>
            <td class="py-3 px-3 text-slate-400">{s['industry']}</td>
            <td class="py-3 px-3 text-right font-semibold text-slate-100">₹{s['signal_close']:,.2f}</td>
            <td class="py-3 px-3 text-right text-rose-400 font-semibold">₹{s['stop_loss_price']:,.2f}</td>
            <td class="py-3 px-3 text-right text-emerald-400 font-bold">₹{s['target_price']:,.2f}</td>
            <td class="py-3 px-3 text-center"><span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold text-xs">BUY @ OPEN</span></td>
            <td class="py-3 px-3 text-center font-bold text-sky-400">{s['vol_ratio']}x</td>
            <td class="py-3 px-3 text-center font-bold text-emerald-400">+{s['rsi_jump']}</td>
            <td class="py-3 px-3 text-center">{s['body_ratio_pct']}%</td>
        </tr>
        """)
        
    hold_rows_html = []
    for s in active_positions:
        pnl = float(s.get('unrealized_pnl_pct', 0))
        pnl_class = "text-emerald-400 font-bold" if pnl >= 0 else "text-rose-400 font-bold"
        hold_rows_html.append(f"""
        <tr class="hover:bg-slate-800/50">
            <td class="py-3 px-3 font-bold text-white text-sm">{s['symbol']}<div class="text-[10px] text-slate-400">{s['company_name']}</div></td>
            <td class="py-3 px-3 text-center text-slate-400">{s['signal_date']}</td>
            <td class="py-3 px-3 text-right font-semibold text-slate-200">₹{s['current_market_price']:,.2f}</td>
            <td class="py-3 px-3 text-right text-rose-400">₹{s['stop_loss_price']:,.2f}</td>
            <td class="py-3 px-3 text-right text-emerald-400 font-semibold">₹{s['target_price']:,.2f}</td>
            <td class="py-3 px-3 text-center"><span class="px-2.5 py-1 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold text-xs">HOLD ({s['holding_days']}/10d)</span></td>
            <td class="py-3 px-3 text-right {pnl_class}">{'+' if pnl >= 0 else ''}{pnl}%</td>
        </tr>
        """)
        
    consolidated_rows_html = []
    for s in all_signals:
        is_highlighted = s.get('is_top5_priority', False) and s.get('total_signals_on_date', 1) > 5
        row_bg = "bg-yellow-500/5 hover:bg-yellow-500/15" if is_highlighted else "hover:bg-slate-800/40"
        
        if is_highlighted:
            sym_display = f"<span class='bg-yellow-400 text-black font-extrabold px-1.5 py-0.5 rounded text-xs'>{s['symbol']} ⭐</span>"
        else:
            sym_display = f"<span class='font-bold text-white'>{s['symbol']}</span>"
            
        status = str(s.get('current_status', ''))
        status_badge = "bg-emerald-500/20 text-emerald-300" if "BUY" in status else ("bg-cyan-500/20 text-cyan-300" if "HOLD" in status else "bg-slate-700 text-slate-300")
        pnl = float(s.get('unrealized_pnl_pct', 0))
        
        consolidated_rows_html.append(f"""
        <tr class="{row_bg}">
            <td class="py-2.5 px-3 font-medium text-slate-300">{s['signal_date']}</td>
            <td class="py-2.5 px-3">{sym_display}</td>
            <td class="py-2.5 px-3 text-slate-400">{s['industry']}</td>
            <td class="py-2.5 px-3 text-right">₹{s['signal_close']:,.2f}</td>
            <td class="py-2.5 px-3 text-right text-rose-400">₹{s['stop_loss_price']:,.2f}</td>
            <td class="py-2.5 px-3 text-right text-emerald-400 font-semibold">₹{s['target_price']:,.2f}</td>
            <td class="py-2.5 px-3 text-center"><span class="px-2 py-0.5 rounded text-[11px] font-semibold {status_badge}">{status}</span></td>
            <td class="py-2.5 px-3 text-center font-bold text-sky-400">{s['vol_ratio']}x</td>
            <td class="py-2.5 px-3 text-center">{s['body_ratio_pct']}%</td>
            <td class="py-2.5 px-3 text-right font-bold {('text-emerald-400' if pnl >= 0 else 'text-rose-400')}">{'+' if pnl >= 0 else ''}{pnl}%</td>
        </tr>
        """)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Live Signals & Trade Status Report - {date_str}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
        body {{ font-family: 'Inter', sans-serif; background-color: #0b1329; color: #f8fafc; }}
        .glass-card {{ background: rgba(30, 41, 59, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }}
        .table-container {{ max-height: 480px; overflow-y: auto; }}
        ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        ::-webkit-scrollbar-track {{ background: #1e293b; }}
        ::-webkit-scrollbar-thumb {{ background: #475569; border-radius: 3px; }}
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">
    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6 mb-8">
            <div>
                <div class="flex items-center gap-2 mb-2">
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Live Screener Output</span>
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-500/20 text-sky-400 border border-sky-500/30">Nifty 750</span>
                </div>
                <h1 class="text-3xl font-bold text-white">Daily Live Signals & Trade Status Report</h1>
                <p class="text-slate-400 text-sm mt-1">Single Consolidated Live Signals & Real-Time Actionable Buy, Hold, and Sell Status</p>
            </div>
            <div class="glass-card p-3.5 rounded-xl text-right">
                <div class="text-xs text-slate-400 font-medium">Market Data Date</div>
                <div class="text-base font-bold text-emerald-400">{date_str}</div>
                <div class="text-[11px] text-slate-400">Next Action: Market Open Tomorrow</div>
            </div>
        </div>

        <!-- Action Status KPI Scorecards -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <!-- BUY Scorecard -->
            <div class="glass-card p-5 rounded-2xl border-l-4 border-emerald-500">
                <div class="flex items-center justify-between">
                    <span class="text-xs text-slate-400 font-semibold uppercase tracking-wider">Action: BUY</span>
                    <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[11px] font-bold">Tomorrow Open</span>
                </div>
                <div class="text-3xl font-black text-emerald-400 mt-2">{buy_count} Candidates</div>
                <p class="text-[11px] text-slate-400 mt-1">Fresh 5-Year Breakouts with 3x Volume & Clean Candle</p>
            </div>

            <!-- HOLD Scorecard -->
            <div class="glass-card p-5 rounded-2xl border-l-4 border-cyan-500">
                <div class="flex items-center justify-between">
                    <span class="text-xs text-slate-400 font-semibold uppercase tracking-wider">Action: HOLD</span>
                    <span class="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 text-[11px] font-bold">Within 10 Days</span>
                </div>
                <div class="text-3xl font-black text-cyan-400 mt-2">{hold_count} Positions</div>
                <p class="text-[11px] text-slate-400 mt-1">Active open swing trades progressing toward +8% target</p>
            </div>

            <!-- SELL Scorecard -->
            <div class="glass-card p-5 rounded-2xl border-l-4 border-rose-500">
                <div class="flex items-center justify-between">
                    <span class="text-xs text-slate-400 font-semibold uppercase tracking-wider">Action: SELL</span>
                    <span class="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 text-[11px] font-bold">Exit Executed</span>
                </div>
                <div class="text-3xl font-black text-rose-400 mt-2">{sell_count} Closed</div>
                <p class="text-[11px] text-slate-400 mt-1">Exits triggered by Target Hit (+8%), Stop Loss, or Day 10 Time-Stop</p>
            </div>
        </div>

        <!-- Section 1: Fresh Signals for Tomorrow (BUY) -->
        <div class="glass-card rounded-2xl p-6 mb-8">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
                <div>
                    <h3 class="text-lg font-bold text-white flex items-center gap-2">
                        <span class="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span>
                        Fresh Breakout Signals (Action: BUY at Market Open)
                    </h3>
                    <p class="text-xs text-slate-400">Triggered on {date_str} close &bull; Allocate to Top 5 Priority candidates (20% per slot)</p>
                </div>
                {"<span class='text-xs font-semibold text-yellow-400 bg-yellow-400/10 border border-yellow-400/20 px-3 py-1 rounded-full flex items-center gap-1.5'>⭐ Top 5 Priority Highlighted in Bold Yellow</span>" if has_more_than_5_today else ""}
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-left text-xs text-slate-300">
                    <thead class="bg-slate-800/80 uppercase tracking-wider text-slate-400">
                        <tr>
                            <th class="py-3 px-3 rounded-l-lg">Rank</th>
                            <th class="py-3 px-3">Symbol</th>
                            <th class="py-3 px-3">Industry</th>
                            <th class="py-3 px-3 text-right">Close (₹)</th>
                            <th class="py-3 px-3 text-right">Stop Loss (₹)</th>
                            <th class="py-3 px-3 text-right">Target (+8%)</th>
                            <th class="py-3 px-3 text-center">Action Status</th>
                            <th class="py-3 px-3 text-center">Vol Multiplier</th>
                            <th class="py-3 px-3 text-center">RSI Jump</th>
                            <th class="py-3 px-3 text-center rounded-r-lg">Body %</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800">
                        {"".join(fresh_rows_html) if fresh_rows_html else '''
                        <tr>
                            <td colspan="10" class="py-8 text-center text-slate-400 text-sm">No new breakout signals triggered on this trading date. The market is consolidating.</td>
                        </tr>
                        '''}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Section 2: Active Positions Tracker (HOLD) -->
        <div class="glass-card rounded-2xl p-6 mb-8">
            <h3 class="text-lg font-bold text-white flex items-center gap-2 mb-1">
                <span class="w-3 h-3 rounded-full bg-cyan-500 inline-block"></span>
                Active Swing Positions Tracker (Action: HOLD)
            </h3>
            <p class="text-xs text-slate-400 mb-4">Open positions triggered by screener currently being monitored for +8% target or Stop Loss</p>

            <div class="overflow-x-auto">
                <table class="w-full text-left text-xs text-slate-300">
                    <thead class="bg-slate-800/80 uppercase tracking-wider text-slate-400">
                        <tr>
                            <th class="py-3 px-3 rounded-l-lg">Symbol</th>
                            <th class="py-3 px-3 text-center">Signal Date</th>
                            <th class="py-3 px-3 text-right">Current Market Price (₹)</th>
                            <th class="py-3 px-3 text-right">Stop Loss (₹)</th>
                            <th class="py-3 px-3 text-right">Target (₹)</th>
                            <th class="py-3 px-3 text-center">Current Status</th>
                            <th class="py-3 px-3 text-right rounded-r-lg">Unrealized P&L %</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800">
                        {"".join(hold_rows_html) if hold_rows_html else '''
                        <tr>
                            <td colspan="7" class="py-6 text-center text-slate-400 text-xs">No active positions currently in HOLD status.</td>
                        </tr>
                        '''}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Section 3: Master Consolidated Signals Archive -->
        <div class="glass-card rounded-2xl p-6">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
                <div>
                    <h3 class="text-lg font-bold text-white">Consolidated Live Signals History ({len(all_signals)} Total Screener Signals)</h3>
                    <p class="text-xs text-slate-400">Complete consolidated historical record of signals triggered via daily screener runs</p>
                </div>
                <input type="text" id="archiveSearch" placeholder="Search Date, Symbol, or Status..." class="bg-slate-900/80 border border-slate-700 text-xs text-white rounded-lg px-3 py-2 focus:outline-none focus:border-sky-500 w-full sm:w-64">
            </div>

            <div class="table-container border border-slate-800 rounded-xl">
                <table class="w-full text-left text-xs text-slate-300" id="archiveTable">
                    <thead class="bg-slate-800/90 sticky top-0 uppercase tracking-wider text-slate-400 z-10">
                        <tr>
                            <th class="py-2.5 px-3">Date</th>
                            <th class="py-2.5 px-3">Symbol</th>
                            <th class="py-2.5 px-3">Industry</th>
                            <th class="py-2.5 px-3 text-right">Close (₹)</th>
                            <th class="py-2.5 px-3 text-right">Stop Loss (₹)</th>
                            <th class="py-2.5 px-3 text-right">Target (₹)</th>
                            <th class="py-2.5 px-3 text-center">Status</th>
                            <th class="py-2.5 px-3 text-center">Vol Multiplier</th>
                            <th class="py-2.5 px-3 text-center">Body %</th>
                            <th class="py-2.5 px-3 text-right">Return %</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800">
                        {"".join(consolidated_rows_html) if consolidated_rows_html else '''
                        <tr>
                            <td colspan="10" class="py-6 text-center text-slate-400 text-xs">No historical live screener signals logged yet. Run RUN_DAILY_SCREENER to log today's signals.</td>
                        </tr>
                        '''}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('archiveSearch').addEventListener('keyup', function() {{
            const filter = this.value.toLowerCase();
            const rows = document.querySelectorAll('#archiveTable tbody tr');
            rows.forEach(row => {{
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            }});
        }});
    </script>
</body>
</html>"""
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  [OK] Generated Interactive Dashboard: output\\live_signals\\daily_signals_report.html")

if __name__ == "__main__":
    run_live_screener()
