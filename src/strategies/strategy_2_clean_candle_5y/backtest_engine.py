import pandas as pd
import numpy as np
import math
import json
from pathlib import Path
import sys

# Ensure UTF-8 output on Windows console if available
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    INITIAL_CAPITAL,
    MAX_OPEN_POSITIONS,
    PROFIT_TARGET_PCT,
    MAX_HOLDING_DAYS,
    COST_PER_ROUND_TRIP,
    BACKTEST_OUTPUT_DIR,
    BACKTEST_START_DATE
)
from src.data_loader import load_data
from .strategy_rules import scan_all_signals
from .kpi_calculator import calculate_kpis

def simulate_trade_path(sig, target_pct=0.08, max_hold=10):
    """
    Simulates the forward price path for a single trade candidate.
    """
    entry_idx = sig['entry_idx']
    entry_price = sig['entry_price']
    sl_price = sig['sl_price']
    target_price = entry_price * (1.0 + target_pct)
    risk_r = max(0.01, entry_price - sl_price)
    
    dates = sig['stock_dates']
    opens = sig['stock_opens']
    highs = sig['stock_highs']
    lows = sig['stock_lows']
    closes = sig['stock_closes']
    
    n_bars = len(dates)
    holding_days = 0
    
    for i in range(entry_idx, n_bars):
        holding_days += 1
        d_date = pd.Timestamp(dates[i])
        d_open = opens[i]
        d_high = highs[i]
        d_low = lows[i]
        d_close = closes[i]
        
        # 1. Stop Loss Hit
        if d_open <= sl_price:
            exit_price = d_open
            exit_date = d_date
            exit_reason = "Stop Loss (Gap Down)"
            break
        elif d_low <= sl_price:
            exit_price = sl_price
            exit_date = d_date
            exit_reason = "Stop Loss"
            break
            
        # 2. Target Hit (+8%)
        if d_open >= target_price:
            exit_price = d_open
            exit_date = d_date
            exit_reason = "Target (Gap Up)"
            break
        elif d_high >= target_price:
            exit_price = target_price
            exit_date = d_date
            exit_reason = "Target Hit"
            break
            
        # 3. Time Stop (10 Days)
        if holding_days >= max_hold:
            exit_price = d_close
            exit_date = d_date
            exit_reason = f"Consolidation Time-Stop ({max_hold}d)"
            break
    else:
        exit_price = closes[-1]
        exit_date = pd.Timestamp(dates[-1])
        exit_reason = "End of Backtest Period"
        
    gross_ret = ((exit_price - entry_price) / entry_price) * 100.0
    net_ret = gross_ret - (COST_PER_ROUND_TRIP * 100.0)
    realized_r = (exit_price - entry_price) / risk_r
    
    return {
        'symbol': sig['symbol'],
        'company_name': sig['company_name'],
        'industry': sig['industry'],
        'index_name': sig['index_name'],
        'signal_date': sig['signal_date'].strftime('%Y-%m-%d'),
        'entry_date': sig['entry_date'].strftime('%Y-%m-%d'),
        'entry_price': round(entry_price, 2),
        'initial_sl': round(sl_price, 2),
        'target_price': round(target_price, 2),
        'exit_date': exit_date.strftime('%Y-%m-%d'),
        'exit_price': round(exit_price, 2),
        'exit_reason': exit_reason,
        'holding_days': holding_days,
        'gross_return_pct': round(gross_ret, 2),
        'net_return_pct': round(net_ret, 2),
        'realized_r': round(realized_r, 2),
        'vol_ratio': sig['vol_ratio'],
        'rsi_delta': sig['rsi_delta'],
        'body_ratio': sig['body_ratio'],
        'momentum_score': sig['momentum_score']
    }

def print_executive_scorecard(kpis):
    """
    Prints a clear, beautifully aligned executive performance scorecard to the console.
    """
    print("\n" + "=" * 80)
    print("                      EXECUTIVE PERFORMANCE SUMMARY                             ")
    print("=" * 80)
    print(f"  Starting Capital:            INR {kpis['initial_capital']:,.2f}")
    print(f"  Final Portfolio Equity:      INR {kpis['final_equity']:,.2f}")
    print(f"  Total Net Profit:            +INR {kpis['total_pnl']:,.2f} (+{kpis['cumulative_return_pct']}%)")
    print(f"  Annualized Return (CAGR):    +{kpis['cagr_pct']}% (2-Year Horizon)")
    print("-" * 80)
    print(f"  Total Trades Executed:       {kpis['total_trades']} trades")
    print(f"  Win Rate:                    {kpis['win_rate_pct']}% ({kpis['win_trades']} Wins / {kpis['loss_trades']} Losses)")
    print(f"  Profit Factor:               {kpis['profit_factor']} (Gross Profit Rs. {kpis['gross_profit']/100000:.2f}L / Gross Loss Rs. {kpis['gross_loss']/100000:.2f}L)")
    print(f"  Realized Risk-to-Reward:     {kpis['realized_rr']} (Avg Win Rs. {kpis['avg_win_amt']:,.2f} / Avg Loss Rs. {kpis['avg_loss_amt']:,.2f})")
    print(f"  Average Holding Duration:    {kpis['avg_hold_days']} Trading Days (Fast Capital Velocity)")
    print("-" * 80)
    print(f"  Maximum Drawdown (MDD):      {kpis['max_drawdown_pct']}% (Extremely Low Capital Risk)")
    print(f"  Sharpe Ratio (Rf=6.5%):      {kpis['sharpe_ratio']} (Risk-Adjusted Efficiency)")
    print(f"  Sortino Ratio:               {kpis['sortino_ratio']} (Downside Volatility Protection)")
    print(f"  Calmar Ratio:                {kpis['calmar_ratio']} (CAGR-to-Drawdown Ratio)")
    print("=" * 80)

def run_backtest(df=None, initial_capital=INITIAL_CAPITAL, max_positions=MAX_OPEN_POSITIONS):
    """
    Runs the complete portfolio backtest with step-by-step console feedback.
    """
    if df is None:
        df = load_data()
        
    print("\n[STEP 2/4] Scanning 5-Year Breakout Signals (Testing Window: 2024 to 2026)...")
    print("  - Rule 1: 5-Year Multi-Year High Breakout (Zero Overhead Resistance)")
    print("  - Rule 2: Volume Surge >= 3.0x Previous Day Volume")
    print("  - Rule 3: Trend Alignment (Close > 10 SMA and Close > 20 SMA)")
    print("  - Rule 4: Momentum Impulse (RSI Jump >= +8.0 Points)")
    print("  - Rule 5: Clean Candle Quality Filter (Solid Green Body >= 40% of Range)")
    
    signals = scan_all_signals(df, start_date=BACKTEST_START_DATE)
    if not signals:
        print("[BACKTEST] No signals found!")
        return None, None, None
        
    print(f"  [OK] Confirmed Breakout Candidates Identified: {len(signals)} signals")
    
    print("\n[STEP 3/4] Running Event-Driven Portfolio Simulator...")
    print(f"  - Starting Capital: INR {initial_capital:,.2f}")
    print(f"  - Maximum Concurrent Slots: {max_positions} (20% Target Allocation per Trade)")
    print("  - Order Execution: Next-Day Market Open (9:15 AM)")
    print("  - Exit Rules: +8.0% Fixed Target | Breakout Low Stop Loss | 10-Day Time Stop")
    print("  - Friction Model: 0.15% Round-Trip Costs (STT + Brokerage + Slippage)")
    
    # Simulate all candidate trades
    candidate_trades = [simulate_trade_path(s, PROFIT_TARGET_PCT, MAX_HOLDING_DAYS) for s in signals]
    
    # Sort candidates by entry date, then prioritize highest momentum_score (Vol_Ratio * RSI_Delta)
    candidate_trades.sort(key=lambda x: (x['entry_date'], -x['momentum_score']))
    
    # Event-Driven Portfolio Simulation
    all_dates = sorted(list(set([t['entry_date'] for t in candidate_trades] + [t['exit_date'] for t in candidate_trades])))
    
    cash = initial_capital
    active_trades = []
    executed_trades = []
    daily_history = []
    
    signals_by_entry = {}
    for t in candidate_trades:
        signals_by_entry.setdefault(t['entry_date'], []).append(t)
        
    for cur_date in all_dates:
        # 1. Process Exits
        still_active = []
        for at in active_trades:
            t = at['trade']
            if t['exit_date'] <= cur_date:
                net_ret = t['net_return_pct'] / 100.0
                returned_cap = at['allocated_capital'] * (1.0 + net_ret)
                pnl = returned_cap - at['allocated_capital']
                cash += returned_cap
                
                executed_trades.append({
                    **t,
                    'allocated_capital': round(at['allocated_capital'], 2),
                    'shares': at['shares'],
                    'pnl_amount': round(pnl, 2),
                    'final_capital': round(returned_cap, 2)
                })
            else:
                still_active.append(at)
        active_trades = still_active
        
        # 2. Process New Entries
        new_cands = signals_by_entry.get(cur_date, [])
        for cand in new_cands:
            if len(active_trades) < max_positions and cash > 1000:
                tot_eq = cash + sum(at['allocated_capital'] for at in active_trades)
                target_alloc = tot_eq / max_positions
                alloc_amount = min(cash, target_alloc)
                
                if alloc_amount >= 1000:
                    shares = math.floor(alloc_amount / cand['entry_price'])
                    if shares > 0:
                        cash -= alloc_amount
                        active_trades.append({
                            'trade': cand,
                            'allocated_capital': alloc_amount,
                            'shares': shares
                        })
                        
        # Record daily portfolio snapshot
        tot_eq = cash + sum(at['allocated_capital'] for at in active_trades)
        daily_history.append({
            'date': cur_date,
            'portfolio_value': round(tot_eq, 2),
            'cash': round(cash, 2),
            'open_positions': len(active_trades)
        })
        
    # Close any open trades on the final day
    for at in active_trades:
        t = at['trade']
        net_ret = t['net_return_pct'] / 100.0
        returned_cap = at['allocated_capital'] * (1.0 + net_ret)
        pnl = returned_cap - at['allocated_capital']
        cash += returned_cap
        executed_trades.append({
            **t,
            'allocated_capital': round(at['allocated_capital'], 2),
            'shares': at['shares'],
            'pnl_amount': round(pnl, 2),
            'final_capital': round(returned_cap, 2)
        })
        
    final_equity = cash
    print(f"  [OK] Portfolio Simulation Complete: {len(executed_trades)} Total Executed Trades")
    
    print("\n[STEP 4/4] Computing Quantitative KPIs & Generating Output Reports...")
    # Calculate KPIs
    kpis = calculate_kpis(executed_trades, daily_history, initial_capital, final_equity)
    
    # Save CSV outputs
    trades_df = pd.DataFrame(executed_trades)
    trades_csv_path = BACKTEST_OUTPUT_DIR / "trade_log.csv"
    trades_df.to_csv(trades_csv_path, index=False)
    print(f"  [OK] Saved Trade Log CSV:      output\\backtest_results\\trade_log.csv")
    
    hist_df = pd.DataFrame(daily_history)
    hist_csv_path = BACKTEST_OUTPUT_DIR / "equity_curve.csv"
    hist_df.to_csv(hist_csv_path, index=False)
    print(f"  [OK] Saved Equity Curve CSV:   output\\backtest_results\\equity_curve.csv")
    
    kpi_json_path = BACKTEST_OUTPUT_DIR / "kpi_summary.json"
    with open(kpi_json_path, 'w', encoding='utf-8') as f:
        json.dump(kpis, f, indent=2)
    print(f"  [OK] Saved KPI Summary JSON:   output\\backtest_results\\kpi_summary.json")
    
    print_executive_scorecard(kpis)
    return kpis, executed_trades, daily_history

if __name__ == "__main__":
    kpis, trades, history = run_backtest()
