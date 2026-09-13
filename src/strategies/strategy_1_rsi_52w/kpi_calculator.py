import pandas as pd
import numpy as np
import math
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import RISK_FREE_RATE


def calculate_kpis(trades, daily_portfolio_history, initial_capital, final_equity=None):
    """
    Computes complete industry-standard quantitative performance KPIs.
    Compatible with dictionary or DataFrame inputs.
    """
    trades_df = pd.DataFrame(trades) if not isinstance(trades, pd.DataFrame) else trades.copy()
    hist_df = pd.DataFrame(daily_portfolio_history) if not isinstance(daily_portfolio_history, pd.DataFrame) else daily_portfolio_history.copy()

    total_trades = len(trades_df)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "cumulative_return_pct": 0.0,
            "cagr_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
        }

    # Normalize column names if needed
    ret_col = "Return_Pct" if "Return_Pct" in trades_df.columns else "net_return_pct"
    pnl_col = "Net_PnL_INR" if "Net_PnL_INR" in trades_df.columns else "pnl_amount"
    hold_col = "Holding_Days" if "Holding_Days" in trades_df.columns else "holding_days"

    wins = trades_df[trades_df[ret_col] > 0]
    losses = trades_df[trades_df[ret_col] <= 0]

    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_trades) * 100.0
    loss_rate = (loss_count / total_trades) * 100.0

    gross_profit = float(wins[pnl_col].sum()) if not wins.empty else 0.0
    gross_loss = abs(float(losses[pnl_col].sum())) if not losses.empty else 0.0
    net_pnl = gross_profit - gross_loss

    if final_equity is None:
        if not hist_df.empty:
            eq_col = "Total_Equity" if "Total_Equity" in hist_df.columns else "portfolio_value"
            final_equity = float(hist_df[eq_col].iloc[-1])
        else:
            final_equity = initial_capital + net_pnl

    cum_return_pct = ((final_equity - initial_capital) / initial_capital) * 100.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

    avg_win_pct = float(wins[ret_col].mean()) if not wins.empty else 0.0
    avg_loss_pct = float(losses[ret_col].mean()) if not losses.empty else 0.0

    avg_win_amt = (gross_profit / win_count) if win_count > 0 else 0.0
    avg_loss_amt = (gross_loss / loss_count) if loss_count > 0 else 0.0
    realized_rr = (avg_win_amt / avg_loss_amt) if avg_loss_amt > 0 else 0.0

    expectancy_pct = (win_rate / 100.0 * avg_win_pct) + (loss_rate / 100.0 * avg_loss_pct)
    expectancy_amt = net_pnl / total_trades

    avg_hold_days = float(trades_df[hold_col].mean()) if not trades_df.empty else 0.0
    avg_win_hold_days = float(wins[hold_col].mean()) if not wins.empty else 0.0
    avg_loss_hold_days = float(losses[hold_col].mean()) if not losses.empty else 0.0

    # Drawdown & Timeline Metrics
    eq_col = "Total_Equity" if "Total_Equity" in hist_df.columns else "portfolio_value"
    if not hist_df.empty and eq_col in hist_df.columns:
        hist_df["peak"] = hist_df[eq_col].cummax()
        hist_df["drawdown_pct"] = (hist_df[eq_col] - hist_df["peak"]) / hist_df["peak"] * 100.0
        hist_df["drawdown_inr"] = hist_df["peak"] - hist_df[eq_col]
        max_drawdown_pct = abs(float(hist_df["drawdown_pct"].min()))
        max_drawdown_inr = float(hist_df["drawdown_inr"].max())

        # Max Drawdown Duration
        is_in_dd = hist_df["drawdown_pct"] < 0
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

        # Time Horizon for CAGR
        date_col = "Date" if "Date" in hist_df.columns else "date"
        d_min = pd.to_datetime(hist_df[date_col].min())
        d_max = pd.to_datetime(hist_df[date_col].max())
        days_span = (d_max - d_min).days
        years_span = max(0.5, days_span / 365.25)

        cagr_pct = ((final_equity / initial_capital) ** (1.0 / years_span) - 1.0) * 100.0 if final_equity > 0 else -100.0

        # Daily Returns & Risk Ratios
        hist_df["daily_return"] = hist_df[eq_col].pct_change().fillna(0)
        rf_daily = (1.0 + RISK_FREE_RATE) ** (1.0 / 252.0) - 1.0
        excess_returns = hist_df["daily_return"] - rf_daily

        std_dev = excess_returns.std()
        sharpe_ratio = (excess_returns.mean() / std_dev * math.sqrt(252)) if std_dev > 0 else 0.0

        downside_returns = excess_returns[excess_returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0.0
        sortino_ratio = (excess_returns.mean() / downside_std * math.sqrt(252)) if downside_std > 0 else 0.0

        calmar_ratio = (cagr_pct / max_drawdown_pct) if max_drawdown_pct > 0 else 0.0
    else:
        max_drawdown_pct = 0.0
        max_drawdown_inr = 0.0
        max_dd_duration_days = 0
        cagr_pct = 0.0
        sharpe_ratio = 0.0
        sortino_ratio = 0.0
        calmar_ratio = 0.0

    # Consecutive Streaks
    max_consec_wins = 0
    max_consec_losses = 0
    cur_w = 0
    cur_l = 0
    for r in trades_df[ret_col]:
        if r > 0:
            cur_w += 1
            cur_l = 0
            if cur_w > max_consec_wins:
                max_consec_wins = cur_w
        else:
            cur_l += 1
            cur_w = 0
            if cur_l > max_consec_losses:
                max_consec_losses = cur_l

    return {
        "initial_capital": round(initial_capital, 2),
        "final_equity": round(final_equity, 2),
        "total_pnl": round(net_pnl, 2),
        "cumulative_return_pct": round(cum_return_pct, 2),
        "cagr_pct": round(cagr_pct, 2),
        "total_trades": int(total_trades),
        "win_trades": int(win_count),
        "loss_trades": int(loss_count),
        "win_rate_pct": round(win_rate, 1),
        "loss_rate_pct": round(loss_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "realized_rr": round(realized_rr, 2),
        "avg_win_pct": round(avg_win_pct, 2),
        "avg_loss_pct": round(avg_loss_pct, 2),
        "avg_win_amt": round(avg_win_amt, 2),
        "avg_loss_amt": round(avg_loss_amt, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "expectancy_pct": round(expectancy_pct, 2),
        "expectancy_amt": round(expectancy_amt, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "max_drawdown_amount": round(max_drawdown_inr, 2),
        "max_dd_duration_days": int(max_dd_duration_days),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "sortino_ratio": round(sortino_ratio, 2),
        "calmar_ratio": round(calmar_ratio, 2),
        "avg_hold_days": round(avg_hold_days, 1),
        "avg_win_hold_days": round(avg_win_hold_days, 1),
        "avg_loss_hold_days": round(avg_loss_hold_days, 1),
        "max_consecutive_wins": int(max_consec_wins),
        "max_consecutive_losses": int(max_consec_losses),
    }
