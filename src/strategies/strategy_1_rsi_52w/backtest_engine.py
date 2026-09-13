import pandas as pd
import numpy as np
import math
import json
from pathlib import Path
import sys

# Ensure UTF-8 output on Windows console if available
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    INITIAL_CAPITAL,
    MAX_OPEN_POSITIONS,
    USE_COMPOUNDING,
    ENTRY_MODE,
    ATR_SL_MULTIPLIER,
    TRAIL_EXIT_MODE,
    STAGNATION_EXIT_DAYS,
    STAGNATION_MIN_GAIN,
    USE_MARKET_BREADTH,
    MARKET_BREADTH_THRESHOLD,
    COST_PER_ROUND_TRIP,
    BACKTEST_OUTPUT_DIR,
)
from src.data_loader import load_data
from .strategy_rules import scan_candidate_signals, compute_market_breadth
from .kpi_calculator import calculate_kpis


def print_executive_scorecard(kpis: dict):
    """
    Prints a clear, beautifully aligned executive performance scorecard to the console.
    """
    pnl_sign = "+" if kpis["total_pnl"] >= 0 else ""
    print("\n" + "=" * 80)
    print("      CHAMPION INSTITUTIONAL 3-DAY RSI & 52W HIGH BREAKOUT SCORECARD            ")
    print("=" * 80)
    print(f"  Starting Capital:            INR {kpis['initial_capital']:,.2f}")
    print(f"  Final Portfolio Equity:      INR {kpis['final_equity']:,.2f}")
    print(f"  Total Net Profit:            {pnl_sign}INR {kpis['total_pnl']:,.2f} ({kpis['cumulative_return_pct']:+.2f}%)")
    print(f"  Annualized Return (CAGR):    {kpis['cagr_pct']:+.2f}% (5-Year Nifty 750 Horizon)")
    print("-" * 80)
    print(f"  Total Trades Executed:       {kpis['total_trades']} trades")
    print(f"  Win Rate:                    {kpis['win_rate_pct']}% ({kpis['win_trades']} Wins / {kpis['loss_trades']} Losses)")
    print(f"  Profit Factor:               {kpis['profit_factor']:.2f} (Gross Win INR {kpis['gross_profit']/100000:.2f}L / Gross Loss INR {kpis['gross_loss']/100000:.2f}L)")
    print(f"  Realized Risk-to-Reward:     1 : {kpis['realized_rr']:.2f} (Avg Win: +{kpis['avg_win_pct']:.2f}% / Avg Loss: {kpis['avg_loss_pct']:.2f}%)")
    print(f"  Trade Expectancy:            {kpis['expectancy_pct']:+.2f}% ({pnl_sign}INR {kpis['expectancy_amt']:,.2f} per trade)")
    print("-" * 80)
    print(f"  Maximum Drawdown (MDD):      -{kpis['max_drawdown_pct']:.2f}% (INR {kpis['max_drawdown_amount']:,.2f})")
    print(f"  Max Drawdown Duration:       {kpis['max_dd_duration_days']} trading days")
    print(f"  Sharpe Ratio (Rf=6.5%):      {kpis['sharpe_ratio']:.2f} (Risk-Adjusted Efficiency)")
    print(f"  Sortino Ratio:               {kpis['sortino_ratio']:.2f} (Downside Volatility Protection)")
    print(f"  Calmar Ratio:                {kpis['calmar_ratio']:.2f} (CAGR-to-Drawdown Quality)")
    print("-" * 80)
    print(f"  Average Holding Period:      {kpis['avg_hold_days']:.1f} days (Wins: {kpis['avg_win_hold_days']:.1f}d | Losses: {kpis['avg_loss_hold_days']:.1f}d)")
    print(f"  Max Consecutive Streaks:     {kpis['max_consecutive_wins']} wins / {kpis['max_consecutive_losses']} losses")
    print("=" * 80)


def run_backtest(
    df=None,
    initial_capital=INITIAL_CAPITAL,
    max_positions=MAX_OPEN_POSITIONS,
    output_dir=BACKTEST_OUTPUT_DIR,
):
    """
    Runs the full institutional backtest across all 750 stocks on 5-year daily candles.
    """
    if df is None:
        df = load_data()

    print("\n[STEP 2/4] Scanning Setup Signals & Computing Macro Market Breadth...")
    print("  - Rule 1: 3-Day Strictly Rising RSI (Day 1 < Day 2 < Day 3 and Day 3 RSI >= 60)")
    print("  - Rule 2: Volume Surge (Day 3 Volume >= 2.5x SMA10 and 3-Day Avg >= 2.5x SMA10)")
    print("  - Rule 3: 52-Week High Proximity (Day 3 Close within 10% of rolling 252-day high)")
    print("  - Rule 4: Trend Alignment (SuperTrend Bullish & Close > EMA 20 > EMA 50)")
    print("  - Rule 5: Macro Market Breadth Gating (% Nifty 500 stocks > EMA 50 >= 50%)")

    # Precompute Market Breadth
    market_breadth = compute_market_breadth(df)
    market_regime_dict = market_breadth.to_dict()
    print(f"  [OK] Computed Macro Market Breadth across {len(market_breadth):,} trading days.")

    # Scan Candidate Setups
    signals_df = scan_candidate_signals(df, variant="champion")
    print(f"  [OK] Identified {len(signals_df):,} Qualifying Day-3 Setup Candidates.")

    print("\n[STEP 3/4] Simulating Event-Driven Dynamic Compounding Portfolio...")
    print(f"  - Starting Capital: INR {initial_capital:,.2f}")
    print(f"  - Concurrent Positions: {max_positions} slots (20% Target Compounding Allocation)")
    print("  - Execution: Day 4 Breakout Confirmation at max(Open, Day 3 High)")
    print("  - Initial Stop Loss: Dynamic 1.5x ATR(14)")
    print("  - Capital Velocity: 15-Day Stagnation Exit if return < +3.0%")
    print("  - Trailing Exit: Ride momentum until Daily Close < SuperTrend")

    stock_history = {
        sym: data.set_index("Date").sort_index()
        for sym, data in df.groupby("Symbol")
    }

    all_trading_dates = sorted(df["Date"].dropna().unique())
    total_dates = len(all_trading_dates)

    signals_by_date = {d: grp for d, grp in signals_df.groupby("Date")}

    available_cash = initial_capital
    active_positions = []
    completed_trades = []
    daily_timeline = []

    for d_idx in range(total_dates):
        current_date = all_trading_dates[d_idx]
        prev_date = all_trading_dates[d_idx - 1] if d_idx > 0 else None

        # -------------------------------------------------------------
        # Step A: Enter new positions on Day 4 (Gated by Market Breadth)
        # -------------------------------------------------------------
        allow_new_entries = True
        if USE_MARKET_BREADTH and prev_date is not None:
            breadth_val = market_regime_dict.get(prev_date, 1.0)
            if breadth_val < MARKET_BREADTH_THRESHOLD:
                allow_new_entries = False

        if allow_new_entries and prev_date is not None and prev_date in signals_by_date:
            day_candidates = signals_by_date[prev_date].copy()
            day_candidates.sort_values(by=["Vol_Multiple_Day3", "RSI_Jump"], ascending=[False, False], inplace=True)

            for _, candidate in day_candidates.iterrows():
                sym = candidate["Symbol"]

                if any(p["symbol"] == sym for p in active_positions):
                    continue

                if len(active_positions) >= max_positions:
                    continue

                if available_cash < 5000.0:
                    continue

                sym_df = stock_history[sym]
                if current_date not in sym_df.index:
                    continue

                entry_bar = sym_df.loc[current_date]
                c_open = float(entry_bar["Open"])
                c_high = float(entry_bar["High"])
                c_close = float(entry_bar["Close"])

                day3_high = float(candidate["High"])
                day3_atr = float(candidate["ATR_14"]) if ("ATR_14" in candidate and not np.isnan(candidate["ATR_14"])) else (0.03 * c_open)

                # Breakout Confirmation Check on Day 4
                if ENTRY_MODE == "breakout_high":
                    if c_high < day3_high:
                        continue
                    entry_price = max(c_open, day3_high)
                else:
                    entry_price = c_open

                if entry_price <= 0 or np.isnan(entry_price):
                    continue

                # Dynamic 1.5x ATR Stop Loss
                sl_price = entry_price - (ATR_SL_MULTIPLIER * day3_atr)
                if sl_price <= 0:
                    sl_price = entry_price * 0.95

                # Dynamic Compounding Sizing (Equity / 5 slots)
                if USE_COMPOUNDING:
                    current_equity = available_cash + sum(p["quantity"] * p["last_close"] for p in active_positions)
                    target_slot_val = current_equity / max_positions
                    allocation = min(target_slot_val, available_cash)
                else:
                    allocation = min(initial_capital / max_positions, available_cash)

                qty = int(allocation // entry_price)
                if qty <= 0:
                    continue

                invested_amount = qty * entry_price
                available_cash -= invested_amount

                active_positions.append({
                    "symbol": sym,
                    "company_name": candidate.get("Company_Name", ""),
                    "signal_date": prev_date,
                    "entry_date": current_date,
                    "entry_price": entry_price,
                    "day3_high": day3_high,
                    "day3_atr": day3_atr,
                    "sl_price": sl_price,
                    "quantity": qty,
                    "invested_amount": invested_amount,
                    "holding_days": 1,
                    "last_close": c_close,
                    "day3_rsi": float(candidate["RSI_14"]),
                    "day3_rsi_jump": float(candidate["RSI_Jump"]),
                    "day3_vol_mult": float(candidate["Vol_Multiple_Day3"]),
                    "entered_today": True,
                })

        # -------------------------------------------------------------
        # Step B: Monitor Exits for Active Positions on current_date
        # -------------------------------------------------------------
        surviving_positions = []
        for pos in active_positions:
            sym = pos["symbol"]
            sym_df = stock_history[sym]

            if current_date not in sym_df.index:
                if not pos.get("entered_today", False):
                    pos["holding_days"] += 1
                pos["entered_today"] = False
                surviving_positions.append(pos)
                continue

            day_bar = sym_df.loc[current_date]
            c_open = float(day_bar["Open"])
            c_high = float(day_bar["High"])
            c_low = float(day_bar["Low"])
            c_close = float(day_bar["Close"])

            if not pos.get("entered_today", False):
                pos["holding_days"] += 1
            pos["entered_today"] = False

            entry_price = pos["entry_price"]
            sl_price = pos["sl_price"]
            qty = pos["quantity"]

            exited = False
            exit_price = 0.0
            exit_reason = ""

            # 1. Stop Loss Checks (Gap Down or Intraday Low Breach)
            if c_open <= sl_price:
                exit_price = c_open
                exit_reason = "StopLoss_GapDown"
                exited = True
            elif c_low <= sl_price:
                exit_price = sl_price
                exit_reason = "StopLoss_ATR"
                exited = True

            # 2. Capital Velocity: Stagnation Exit (Recycle Sluggish Trades)
            if not exited and STAGNATION_EXIT_DAYS is not None and pos["holding_days"] >= STAGNATION_EXIT_DAYS:
                unrealized_gain = (c_close - entry_price) / entry_price
                if unrealized_gain < STAGNATION_MIN_GAIN:
                    exit_price = c_close
                    exit_reason = "Stagnation_Exit"
                    exited = True

            # 3. SuperTrend Trailing Exit on Daily Close
            if not exited and pos["holding_days"] > 1:
                st_dir = float(day_bar.get("SuperTrend_Dir", 1))
                st_val = float(day_bar.get("SuperTrend", 0.0))

                if TRAIL_EXIT_MODE == "supertrend":
                    if st_dir == -1 or (st_val > 0 and c_close < st_val):
                        exit_price = c_close
                        exit_reason = "SuperTrend_Exit"
                        exited = True

            if exited:
                proceeds = exit_price * qty
                cost = pos["invested_amount"]
                friction = proceeds * COST_PER_ROUND_TRIP
                net_pnl = proceeds - cost - friction
                ret_pct = ((exit_price - entry_price) / entry_price - COST_PER_ROUND_TRIP) * 100.0
                available_cash += (proceeds - friction)

                completed_trades.append({
                    "symbol": sym,
                    "company_name": pos.get("company_name", ""),
                    "signal_date": pd.Timestamp(pos["signal_date"]).strftime("%Y-%m-%d"),
                    "entry_date": pd.Timestamp(pos["entry_date"]).strftime("%Y-%m-%d"),
                    "entry_price": round(entry_price, 2),
                    "exit_date": pd.Timestamp(current_date).strftime("%Y-%m-%d"),
                    "exit_price": round(exit_price, 2),
                    "quantity": qty,
                    "allocated_capital": round(cost, 2),
                    "proceeds_amount": round(proceeds, 2),
                    "pnl_amount": round(net_pnl, 2),
                    "net_return_pct": round(ret_pct, 2),
                    "exit_reason": exit_reason,
                    "holding_days": pos["holding_days"],
                    "day3_rsi": round(pos["day3_rsi"], 2),
                    "day3_rsi_jump": round(pos["day3_rsi_jump"], 2),
                    "day3_vol_mult": round(pos["day3_vol_mult"], 2),
                })
            else:
                pos["last_close"] = c_close
                surviving_positions.append(pos)

        active_positions = surviving_positions

        market_value_holdings = sum(p["quantity"] * p["last_close"] for p in active_positions)
        total_equity = available_cash + market_value_holdings

        daily_timeline.append({
            "date": pd.Timestamp(current_date).strftime("%Y-%m-%d"),
            "portfolio_value": round(total_equity, 2),
            "cash": round(available_cash, 2),
            "holdings_value": round(market_value_holdings, 2),
            "open_positions": len(active_positions),
        })

    # Close any open positions on final date
    if len(active_positions) > 0:
        final_date = all_trading_dates[-1]
        for pos in active_positions:
            exit_price = pos["last_close"]
            qty = pos["quantity"]
            cost = pos["invested_amount"]
            proceeds = exit_price * qty
            friction = proceeds * COST_PER_ROUND_TRIP
            net_pnl = proceeds - cost - friction
            ret_pct = ((exit_price - pos["entry_price"]) / pos["entry_price"] - COST_PER_ROUND_TRIP) * 100.0

            completed_trades.append({
                "symbol": pos["symbol"],
                "company_name": pos.get("company_name", ""),
                "signal_date": pd.Timestamp(pos["signal_date"]).strftime("%Y-%m-%d"),
                "entry_date": pd.Timestamp(pos["entry_date"]).strftime("%Y-%m-%d"),
                "entry_price": round(pos["entry_price"], 2),
                "exit_date": pd.Timestamp(final_date).strftime("%Y-%m-%d"),
                "exit_price": round(exit_price, 2),
                "quantity": qty,
                "allocated_capital": round(cost, 2),
                "proceeds_amount": round(proceeds, 2),
                "pnl_amount": round(net_pnl, 2),
                "net_return_pct": round(ret_pct, 2),
                "exit_reason": "FinalDate_Close",
                "holding_days": pos["holding_days"],
                "day3_rsi": round(pos["day3_rsi"], 2),
                "day3_rsi_jump": round(pos["day3_rsi_jump"], 2),
                "day3_vol_mult": round(pos["day3_vol_mult"], 2),
            })

    print(f"  [OK] Completed Portfolio Simulation: {len(completed_trades)} Total Trades Executed.")

    print("\n[STEP 4/4] Computing Quantitative KPIs & Exporting Files...")
    kpis = calculate_kpis(completed_trades, daily_timeline, initial_capital)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    trades_df = pd.DataFrame(completed_trades)
    trades_csv_path = output_dir / "trade_log.csv"
    trades_df.to_csv(trades_csv_path, index=False)
    print(f"  [OK] Saved Trade Log:        output\\backtest_results\\trade_log.csv")

    hist_df = pd.DataFrame(daily_timeline)
    hist_csv_path = output_dir / "equity_curve.csv"
    hist_df.to_csv(hist_csv_path, index=False)
    print(f"  [OK] Saved Equity Curve:     output\\backtest_results\\equity_curve.csv")

    kpi_json_path = output_dir / "kpi_summary.json"
    with open(kpi_json_path, "w", encoding="utf-8") as f:
        json.dump(kpis, f, indent=2)
    print(f"  [OK] Saved KPI Summary:      output\\backtest_results\\kpi_summary.json")

    print_executive_scorecard(kpis)
    return kpis, completed_trades, daily_timeline


if __name__ == "__main__":
    kpis, trades, history = run_backtest()
