"""
KPI Analytics Engine for Multi-Timeframe RSI Swing Trading Strategy.

Computes comprehensive, publication-grade quantitative performance metrics:
1. Trade Counts & Win/Loss Ratios
2. Realized Risk-to-Reward and Planned R:R (R-Multiples)
3. Return Statistics (Mean, Median, Min, Max, Standard Deviation)
4. Holding Period / Investment Span Statistics (Trading Days & Calendar Days)
5. Profit Factor & Strategy Expectancy (Percentage & R-Multiple)
6. Equity Curve Compounding & Maximum Peak-to-Trough Drawdown
7. Consecutive Streak Analysis (Wins / Losses)
8. Exit Reason Breakdown (Intraday Stop Loss vs Market Close Target)
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Union
import numpy as np
import pandas as pd

from src.strategies.strategy_3_gfs_mtf.simulator.order_engine import TradeRecord, ExitReason


@dataclass
class StrategyKPIs:
    """
    Comprehensive strategy performance scorecard data structure.
    """
    # Core Counts
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0

    # Ratios (%)
    win_ratio: float = 0.0
    loss_ratio: float = 0.0
    breakeven_ratio: float = 0.0

    # Return Metrics (%)
    avg_return_pct: float = 0.0
    median_return_pct: float = 0.0
    lowest_return_pct: float = 0.0
    highest_return_pct: float = 0.0
    std_return_pct: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    avg_loss_magnitude_pct: float = 0.0

    # Risk & Expectancy
    realized_risk_reward_ratio: float = 0.0
    avg_planned_risk_pct: float = 0.0
    avg_r_multiple: float = 0.0
    avg_win_r_multiple: float = 0.0
    avg_loss_r_multiple: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0
    strategy_expectancy_pct: float = 0.0
    strategy_expectancy_r: float = 0.0

    # Investment Span (Trading Days)
    avg_holding_days: float = 0.0
    median_holding_days: float = 0.0
    min_holding_days: int = 0
    max_holding_days: int = 0
    avg_win_holding_days: float = 0.0
    avg_loss_holding_days: float = 0.0

    # Investment Span (Calendar Days)
    avg_holding_calendar_days: float = 0.0
    min_holding_calendar_days: int = 0
    max_holding_calendar_days: int = 0

    # Portfolio & Curve Metrics
    total_return_pct: float = 0.0
    compounded_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

    # Exit Reason Diagnostics
    sl_trades_count: int = 0
    sl_trades_avg_return: float = 0.0
    sl_trades_win_ratio: float = 0.0
    target_trades_count: int = 0
    target_trades_avg_return: float = 0.0
    target_trades_win_ratio: float = 0.0
    end_of_data_trades_count: int = 0
    end_of_data_trades_avg_return: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to plain dictionary."""
        return asdict(self)


def _find_column(df: pd.DataFrame, *candidate_names: str) -> Optional[str]:
    """Finds matching column in DataFrame case-insensitively."""
    for cand in candidate_names:
        if cand in df.columns:
            return cand
    for cand in candidate_names:
        cand_lower = cand.lower()
        for col in df.columns:
            if col.lower() == cand_lower:
                return col
    return None


def calculate_strategy_kpis(
    trades: Union[List[TradeRecord], pd.DataFrame]
) -> StrategyKPIs:
    """
    Computes all quantitative performance KPIs from a collection of trade records.

    Handles edge cases gracefully (zero trades, 100% win rate, 100% loss rate,
    division by zero, open trades filtering, case-insensitive column names).

    Args:
        trades: List of TradeRecord instances OR a pandas DataFrame of trades.

    Returns:
        StrategyKPIs: Fully populated scorecard object.
    """
    # 1. Normalize input to a DataFrame of closed trades
    if isinstance(trades, pd.DataFrame):
        df = trades.copy()
    elif isinstance(trades, list):
        if not trades:
            return StrategyKPIs()
        records = [t.to_dict() if hasattr(t, "to_dict") else asdict(t) for t in trades]
        df = pd.DataFrame(records)
    else:
        raise TypeError(f"Unsupported trades type: {type(trades)}. Expected list or DataFrame.")

    if df.empty:
        return StrategyKPIs()

    # Identify relevant columns case-insensitively
    closed_col = _find_column(df, "is_closed", "Is_Closed")
    ret_col = _find_column(df, "return_pct", "Return_Pct", "return", "Return")
    holding_col = _find_column(df, "holding_days", "Holding_Days", "span")
    cal_col = _find_column(df, "holding_calendar_days", "Holding_Calendar_Days")
    r_col = _find_column(df, "r_multiple", "R_Multiple", "r_mult")
    risk_col = _find_column(df, "planned_risk_pct", "Planned_Risk_Pct")
    exit_col = _find_column(df, "exit_reason", "Exit_Reason")

    # Filter strictly closed trades with non-null return_pct
    if closed_col:
        df = df[df[closed_col] == True].copy()
    if ret_col:
        df = df[df[ret_col].notnull()].copy()
    else:
        return StrategyKPIs()

    total_trades = len(df)
    if total_trades == 0:
        return StrategyKPIs()

    # Ensure required numeric columns are float
    returns = df[ret_col].astype(float).values
    holding_days = df[holding_col].astype(int).values if holding_col else np.ones(total_trades, dtype=int)
    cal_days = df[cal_col].astype(int).values if cal_col else np.zeros(total_trades, dtype=int)
    r_multiples = df[r_col].fillna(0.0).astype(float).values if r_col else np.zeros(total_trades, dtype=float)
    planned_risks = df[risk_col].fillna(0.0).astype(float).values if risk_col else np.zeros(total_trades, dtype=float)

    # Trade outcomes
    win_mask = returns > 0.0
    loss_mask = returns < 0.0
    be_mask = returns == 0.0

    winning_trades = int(np.sum(win_mask))
    losing_trades = int(np.sum(loss_mask))
    breakeven_trades = int(np.sum(be_mask))

    win_ratio = float((winning_trades / total_trades) * 100.0)
    loss_ratio = float((losing_trades / total_trades) * 100.0)
    breakeven_ratio = float((breakeven_trades / total_trades) * 100.0)

    # Return statistics
    avg_return_pct = float(np.mean(returns))
    median_return_pct = float(np.median(returns))
    lowest_return_pct = float(np.min(returns))
    highest_return_pct = float(np.max(returns))
    std_return_pct = float(np.std(returns, ddof=1)) if total_trades > 1 else 0.0

    # Win / Loss segmented returns
    win_returns = returns[win_mask]
    loss_returns = returns[loss_mask]

    avg_win_pct = float(np.mean(win_returns)) if winning_trades > 0 else 0.0
    avg_loss_pct = float(np.mean(loss_returns)) if losing_trades > 0 else 0.0
    avg_loss_magnitude_pct = float(abs(avg_loss_pct))

    # Realized Risk to Reward: Avg Win Return % / Avg Loss Return %
    if avg_loss_magnitude_pct > 1e-6:
        realized_risk_reward_ratio = float(avg_win_pct / avg_loss_magnitude_pct)
    else:
        realized_risk_reward_ratio = float("inf") if avg_win_pct > 0 else 0.0

    # Planned Risk & R-Multiples
    avg_planned_risk_pct = float(np.mean(planned_risks))
    avg_r_multiple = float(np.mean(r_multiples))
    avg_win_r_multiple = float(np.mean(r_multiples[win_mask])) if winning_trades > 0 else 0.0
    avg_loss_r_multiple = float(np.mean(r_multiples[loss_mask])) if losing_trades > 0 else 0.0

    # Profit Factor
    gross_profit = float(np.sum(win_returns)) if winning_trades > 0 else 0.0
    gross_loss = float(np.sum(np.abs(loss_returns))) if losing_trades > 0 else 0.0

    if gross_loss > 1e-6:
        profit_factor = float(gross_profit / gross_loss)
    else:
        profit_factor = float("inf") if gross_profit > 0 else 0.0

    # Strategy Expectancy
    w_rate = winning_trades / total_trades
    l_rate = losing_trades / total_trades
    strategy_expectancy_pct = float((w_rate * avg_win_pct) - (l_rate * avg_loss_magnitude_pct))
    strategy_expectancy_r = float((w_rate * avg_win_r_multiple) + (l_rate * avg_loss_r_multiple))

    # Investment Span (Trading Days)
    avg_holding_days = float(np.mean(holding_days))
    median_holding_days = float(np.median(holding_days))
    min_holding_days = int(np.min(holding_days))
    max_holding_days = int(np.max(holding_days))
    avg_win_holding_days = float(np.mean(holding_days[win_mask])) if winning_trades > 0 else 0.0
    avg_loss_holding_days = float(np.mean(holding_days[loss_mask])) if losing_trades > 0 else 0.0

    # Investment Span (Calendar Days)
    avg_holding_calendar_days = float(np.mean(cal_days))
    min_holding_calendar_days = int(np.min(cal_days))
    max_holding_calendar_days = int(np.max(cal_days))

    # Cumulative & Compounded Returns
    total_return_pct = float(np.sum(returns))
    compounded_equity = np.cumprod(1.0 + returns / 100.0)
    compounded_return_pct = float((compounded_equity[-1] - 1.0) * 100.0)

    # Maximum Drawdown calculation on sequential trade curve
    running_max = np.maximum.accumulate(compounded_equity)
    drawdowns = (compounded_equity - running_max) / running_max * 100.0
    max_drawdown_pct = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

    # Consecutive Streaks (Wins / Losses)
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_win_streak = 0
    current_loss_streak = 0

    for r in returns:
        if r > 0:
            current_win_streak += 1
            current_loss_streak = 0
            if current_win_streak > max_consecutive_wins:
                max_consecutive_wins = current_win_streak
        elif r < 0:
            current_loss_streak += 1
            current_win_streak = 0
            if current_loss_streak > max_consecutive_losses:
                max_consecutive_losses = current_loss_streak
        else:
            current_win_streak = 0
            current_loss_streak = 0

    # Exit Reason Diagnostics
    sl_trades_count = 0
    sl_trades_avg_return = 0.0
    sl_trades_win_ratio = 0.0

    target_trades_count = 0
    target_trades_avg_return = 0.0
    target_trades_win_ratio = 0.0

    end_of_data_trades_count = 0
    end_of_data_trades_avg_return = 0.0

    if exit_col:
        sl_df = df[df[exit_col] == ExitReason.STOP_LOSS.value]
        if len(sl_df) > 0:
            sl_trades_count = len(sl_df)
            sl_trades_avg_return = float(sl_df[ret_col].mean())
            sl_trades_win_ratio = float((sl_df[ret_col] > 0).mean() * 100.0)

        target_reasons = [
            ExitReason.TARGET_RSI_60.value,
            ExitReason.TARGET_RSI_BELOW_60.value,
            ExitReason.TARGET_2DOWN_RED_CANDLE.value,
        ]
        target_df = df[df[exit_col].isin(target_reasons)]
        if len(target_df) > 0:
            target_trades_count = len(target_df)
            target_trades_avg_return = float(target_df[ret_col].mean())
            target_trades_win_ratio = float((target_df[ret_col] > 0).mean() * 100.0)

        eod_df = df[df[exit_col] == ExitReason.END_OF_DATA.value]
        if len(eod_df) > 0:
            end_of_data_trades_count = len(eod_df)
            end_of_data_trades_avg_return = float(eod_df[ret_col].mean())

    return StrategyKPIs(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        breakeven_trades=breakeven_trades,
        win_ratio=win_ratio,
        loss_ratio=loss_ratio,
        breakeven_ratio=breakeven_ratio,
        avg_return_pct=avg_return_pct,
        median_return_pct=median_return_pct,
        lowest_return_pct=lowest_return_pct,
        highest_return_pct=highest_return_pct,
        std_return_pct=std_return_pct,
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        avg_loss_magnitude_pct=avg_loss_magnitude_pct,
        realized_risk_reward_ratio=realized_risk_reward_ratio,
        avg_planned_risk_pct=avg_planned_risk_pct,
        avg_r_multiple=avg_r_multiple,
        avg_win_r_multiple=avg_win_r_multiple,
        avg_loss_r_multiple=avg_loss_r_multiple,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
        strategy_expectancy_pct=strategy_expectancy_pct,
        strategy_expectancy_r=strategy_expectancy_r,
        avg_holding_days=avg_holding_days,
        median_holding_days=median_holding_days,
        min_holding_days=min_holding_days,
        max_holding_days=max_holding_days,
        avg_win_holding_days=avg_win_holding_days,
        avg_loss_holding_days=avg_loss_holding_days,
        avg_holding_calendar_days=avg_holding_calendar_days,
        min_holding_calendar_days=min_holding_calendar_days,
        max_holding_calendar_days=max_holding_calendar_days,
        total_return_pct=total_return_pct,
        compounded_return_pct=compounded_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        max_consecutive_wins=max_consecutive_wins,
        max_consecutive_losses=max_consecutive_losses,
        sl_trades_count=sl_trades_count,
        sl_trades_avg_return=sl_trades_avg_return,
        sl_trades_win_ratio=sl_trades_win_ratio,
        target_trades_count=target_trades_count,
        target_trades_avg_return=target_trades_avg_return,
        target_trades_win_ratio=target_trades_win_ratio,
        end_of_data_trades_count=end_of_data_trades_count,
        end_of_data_trades_avg_return=end_of_data_trades_avg_return,
    )
