import pandas as pd
import numpy as np
import math
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import RISK_FREE_RATE

def calculate_kpis(trades, daily_portfolio_history, initial_capital, final_equity):
    """
    Computes complete industry-standard quantitative performance KPIs.
    """
    total_trades = len(trades)
    if total_trades == 0:
        return {'total_trades': 0, 'cumulative_return_pct': 0.0}
        
    trades_df = pd.DataFrame(trades)
    hist_df = pd.DataFrame(daily_portfolio_history)
    
    wins = trades_df[trades_df['net_return_pct'] > 0]
    losses = trades_df[trades_df['net_return_pct'] <= 0]
    
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_trades) * 100.0
    loss_rate = (loss_count / total_trades) * 100.0
    
    total_pnl = final_equity - initial_capital
    cum_return_pct = (total_pnl / initial_capital) * 100.0
    
    gross_profit = wins['pnl_amount'].sum() if not wins.empty else 0.0
    gross_loss = abs(losses['pnl_amount'].sum()) if not losses.empty else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    
    avg_win_pct = wins['net_return_pct'].mean() if not wins.empty else 0.0
    avg_loss_pct = losses['net_return_pct'].mean() if not losses.empty else 0.0
    
    avg_win_amt = wins['pnl_amount'].mean() if not wins.empty else 0.0
    avg_loss_amt = abs(losses['pnl_amount'].mean()) if not losses.empty else 0.0
    
    realized_rr = (avg_win_amt / avg_loss_amt) if avg_loss_amt > 0 else 0.0
    
    # Expectancy
    expectancy_pct = (win_rate / 100.0 * avg_win_pct) + (loss_rate / 100.0 * avg_loss_pct)
    expectancy_amount = (total_pnl / total_trades)
    avg_realized_r = trades_df['realized_r'].mean() if 'realized_r' in trades_df else 0.0
    
    max_win_pct = trades_df['net_return_pct'].max()
    max_loss_pct = trades_df['net_return_pct'].min()
    avg_hold_days = trades_df['holding_days'].mean()
    
    # Drawdown & Recovery
    hist_df['peak'] = hist_df['portfolio_value'].cummax()
    hist_df['drawdown_pct'] = (hist_df['portfolio_value'] - hist_df['peak']) / hist_df['peak'] * 100.0
    max_drawdown = abs(hist_df['drawdown_pct'].min())
    
    # Max Drawdown Duration (days)
    is_in_dd = hist_df['drawdown_pct'] < 0
    dd_durations = []
    cur_dd_len = 0
    for in_dd in is_in_dd:
        if in_dd:
            cur_dd_len += 1
        else:
            if cur_dd_len > 0:
                dd_durations.append(cur_dd_len)
                cur_dd_len = 0
    if cur_dd_len > 0:
        dd_durations.append(cur_dd_len)
    max_dd_duration_days = max(dd_durations) if dd_durations else 0
    
    # CAGR (2 Years)
    years = 2.0
    cagr = ((final_equity / initial_capital) ** (1.0 / years) - 1.0) * 100.0 if final_equity > 0 else -100.0
    
    # Sharpe & Sortino (Daily returns approximation)
    hist_df['daily_return'] = hist_df['portfolio_value'].pct_change().fillna(0)
    rf_daily = (1.0 + RISK_FREE_RATE) ** (1.0 / 252.0) - 1.0
    excess_returns = hist_df['daily_return'] - rf_daily
    
    sharpe = (excess_returns.mean() / excess_returns.std() * math.sqrt(252)) if excess_returns.std() > 0 else 0.0
    
    downside_returns = excess_returns[excess_returns < 0]
    downside_std = downside_returns.std() if len(downside_returns) > 0 else 0.0
    sortino = (excess_returns.mean() / downside_std * math.sqrt(252)) if downside_std > 0 else 0.0
    
    calmar = (cagr / max_drawdown) if max_drawdown > 0 else 0.0
    
    # Consecutive streaks
    max_consec_wins = 0
    max_consec_losses = 0
    cur_w = 0
    cur_l = 0
    for r in trades_df['net_return_pct']:
        if r > 0:
            cur_w += 1
            cur_l = 0
            max_consec_wins = max(max_consec_wins, cur_w)
        else:
            cur_l += 1
            cur_w = 0
            max_consec_losses = max(max_consec_losses, cur_l)
            
    # Exit reasons breakdown
    exit_reasons = trades_df['exit_reason'].value_counts().to_dict()
    
    # Sector Breakdown
    sector_summary = {}
    if 'industry' in trades_df.columns:
        sec_grouped = trades_df.groupby('industry')
        for ind, g in sec_grouped:
            sector_summary[ind] = {
                'trades': int(len(g)),
                'win_rate': round((g['net_return_pct'] > 0).mean() * 100, 1),
                'total_pnl': round(g['pnl_amount'].sum(), 2),
                'avg_return': round(g['net_return_pct'].mean(), 2)
            }
            
    # Index Breakdown
    index_summary = {}
    if 'index_name' in trades_df.columns:
        idx_grouped = trades_df.groupby('index_name')
        for idx, g in idx_grouped:
            index_summary[idx] = {
                'trades': int(len(g)),
                'win_rate': round((g['net_return_pct'] > 0).mean() * 100, 1),
                'total_pnl': round(g['pnl_amount'].sum(), 2),
                'avg_return': round(g['net_return_pct'].mean(), 2)
            }
            
    # Monthly P&L Breakdown
    monthly_summary = {}
    trades_df['entry_month'] = pd.to_datetime(trades_df['entry_date']).dt.strftime('%Y-%m')
    for m, g in trades_df.groupby('entry_month'):
        monthly_summary[m] = {
            'trades': int(len(g)),
            'win_rate': round((g['net_return_pct'] > 0).mean() * 100, 1),
            'total_pnl': round(g['pnl_amount'].sum(), 2),
        }
        
    return {
        'total_trades': total_trades,
        'win_trades': win_count,
        'loss_trades': loss_count,
        'win_rate_pct': round(win_rate, 2),
        'loss_rate_pct': round(loss_rate, 2),
        'initial_capital': initial_capital,
        'final_equity': round(final_equity, 2),
        'total_pnl': round(total_pnl, 2),
        'gross_profit': round(gross_profit, 2),
        'gross_loss': round(gross_loss, 2),
        'cumulative_return_pct': round(cum_return_pct, 2),
        'cagr_pct': round(cagr, 2),
        'profit_factor': round(profit_factor, 2),
        'realized_rr': round(realized_rr, 2),
        'expectancy_pct': round(expectancy_pct, 2),
        'expectancy_amount': round(expectancy_amount, 2),
        'avg_realized_r': round(avg_realized_r, 2),
        'avg_win_pct': round(avg_win_pct, 2),
        'avg_loss_pct': round(avg_loss_pct, 2),
        'avg_win_amt': round(avg_win_amt, 2),
        'avg_loss_amt': round(avg_loss_amt, 2),
        'max_win_pct': round(max_win_pct, 2),
        'max_loss_pct': round(max_loss_pct, 2),
        'avg_hold_days': round(avg_hold_days, 1),
        'max_drawdown_pct': round(max_drawdown, 2),
        'max_dd_duration_days': max_dd_duration_days,
        'sharpe_ratio': round(sharpe, 2),
        'sortino_ratio': round(sortino, 2),
        'calmar_ratio': round(calmar, 2),
        'max_consec_wins': max_consec_wins,
        'max_consec_losses': max_consec_losses,
        'exit_reasons': exit_reasons,
        'sector_summary': sector_summary,
        'index_summary': index_summary,
        'monthly_summary': monthly_summary
    }
