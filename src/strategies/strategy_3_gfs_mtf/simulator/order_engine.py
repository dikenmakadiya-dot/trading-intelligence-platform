"""
Deterministic Trade Execution State Machine and Order Engine.

Implements strict 5-state trade lifecycle management:
1. Day T Signal: Identifies Signal Candle and sets Buy Stop at Signal_High.
2. Day T+1 Entry: Executes Buy Stop at max(Signal_High, Open_{T+1}) if High_{T+1} >= Signal_High.
   Cancels signal if High_{T+1} < Signal_High.
3. Intraday Stop Loss: Exits at min(Signal_Low, Open_t) if Low_t <= Signal_Low.
4. Target Exit: Exits at Close_t if Daily_RSI_14 >= 60.0 at Market Close.
5. Strict Priority Rule: Intraday Stop Loss takes 100% precedence over Target Exit on same bar.
6. Non-Pyramiding: Suppresses new signal generation while actively in position for a stock.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
import pandas as pd
import numpy as np


class OrderState(Enum):
    OUT_OF_MARKET = "OUT_OF_MARKET"
    PENDING_ENTRY = "PENDING_ENTRY"
    IN_POSITION = "IN_POSITION"


class ExitReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TARGET_RSI_60 = "TARGET_RSI_60"
    TARGET_RSI_BELOW_60 = "TARGET_RSI_BELOW_60"
    TARGET_2DOWN_RED_CANDLE = "TARGET_2DOWN_RED_CANDLE"
    END_OF_DATA = "END_OF_DATA"


@dataclass
class TradeRecord:
    """
    Typed data structure representing an individual trade lifecycle.
    """
    symbol: str
    signal_date: pd.Timestamp
    signal_high: float
    signal_low: float
    signal_close: float
    entry_date: pd.Timestamp
    entry_price: float
    stop_loss: float
    exit_date: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    return_pct: Optional[float] = None
    holding_days: Optional[int] = None
    holding_calendar_days: Optional[int] = None
    planned_risk_pct: Optional[float] = None
    r_multiple: Optional[float] = None
    is_closed: bool = False
    entry_bar_idx: Optional[int] = None
    exit_bar_idx: Optional[int] = None

    def close_trade(
        self,
        exit_date: pd.Timestamp,
        exit_price: float,
        exit_reason: str,
        exit_bar_idx: int,
        entry_bar_idx: Optional[int] = None,
    ) -> None:
        """
        Closes the active trade and computes return metrics.
        """
        self.exit_date = exit_date
        self.exit_price = float(exit_price)
        self.exit_reason = str(exit_reason)
        self.exit_bar_idx = exit_bar_idx
        if entry_bar_idx is not None:
            self.entry_bar_idx = entry_bar_idx

        # Calculate holding span in trading days (inclusive)
        if self.entry_bar_idx is not None:
            self.holding_days = int(exit_bar_idx - self.entry_bar_idx + 1)
        else:
            self.holding_days = 1

        # Calculate calendar days
        if self.entry_date is not None and self.exit_date is not None:
            self.holding_calendar_days = int((self.exit_date - self.entry_date).days)
        else:
            self.holding_calendar_days = 0

        # Calculate percentage return
        if self.entry_price > 0:
            self.return_pct = float(((self.exit_price - self.entry_price) / self.entry_price) * 100.0)
            self.planned_risk_pct = float(((self.entry_price - self.stop_loss) / self.entry_price) * 100.0)
        else:
            self.return_pct = 0.0
            self.planned_risk_pct = 0.0

        # Calculate R-Multiple: (Exit - Entry) / (Entry - StopLoss)
        risk_per_share = self.entry_price - self.stop_loss
        if abs(risk_per_share) > 1e-6:
            self.r_multiple = float((self.exit_price - self.entry_price) / risk_per_share)
        else:
            self.r_multiple = 0.0

        self.is_closed = True

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the trade record to a flat dictionary.
        """
        return asdict(self)


class OrderEngine:
    """
    Deterministic Order Execution State Machine.
    Processes OHLCV and RSI price series for a single ticker.
    """

    def __init__(
        self,
        exit_mode: str = "hard_rsi_60",
        sl_atr_buffer: float = 0.0,
        target_rsi_threshold: float = 60.0,
        trail_sl_to_cost: bool = False,
        include_open_trades: bool = False,
    ):
        self.exit_mode = exit_mode
        self.sl_atr_buffer = sl_atr_buffer
        self.target_rsi_threshold = target_rsi_threshold
        self.trail_sl_to_cost = trail_sl_to_cost
        self.include_open_trades = include_open_trades

    def simulate(self, df_stock: pd.DataFrame) -> List[TradeRecord]:
        """
        Executes trade simulation for a single stock DataFrame.
        """
        if df_stock.empty:
            return []

        # Ensure sorted by Date
        if not df_stock["Date"].is_monotonic_increasing:
            df_stock = df_stock.sort_values(by="Date", ascending=True).reset_index(drop=True)

        n = len(df_stock)
        if n == 0:
            return []

        # Extract NumPy arrays for fast vectorized access
        dates = pd.to_datetime(df_stock["Date"]).values
        symbol = str(df_stock["Symbol"].iloc[0]) if "Symbol" in df_stock.columns else "UNKNOWN"
        opens = df_stock["Open"].to_numpy(dtype=np.float64)
        highs = df_stock["High"].to_numpy(dtype=np.float64)
        lows = df_stock["Low"].to_numpy(dtype=np.float64)
        closes = df_stock["Close"].to_numpy(dtype=np.float64)
        daily_rsi = df_stock["Daily_RSI_14"].to_numpy(dtype=np.float64) if "Daily_RSI_14" in df_stock.columns else np.full(n, np.nan)
        signals = df_stock["Signal_Candle"].to_numpy(dtype=bool) if "Signal_Candle" in df_stock.columns else np.zeros(n, dtype=bool)

        signal_highs = df_stock["Signal_High"].to_numpy(dtype=np.float64) if "Signal_High" in df_stock.columns else highs
        signal_lows = df_stock["Signal_Low"].to_numpy(dtype=np.float64) if "Signal_Low" in df_stock.columns else lows
        signal_atrs = df_stock["Signal_ATR"].to_numpy(dtype=np.float64) if "Signal_ATR" in df_stock.columns else (
            df_stock["ATR_14"].to_numpy(dtype=np.float64) if "ATR_14" in df_stock.columns else np.zeros(n)
        )

        trades: List[TradeRecord] = []
        state: OrderState = OrderState.OUT_OF_MARKET

        # State tracking variables
        pending_signal_date: Optional[pd.Timestamp] = None
        pending_signal_high: float = 0.0
        pending_signal_low: float = 0.0
        pending_signal_close: float = 0.0
        pending_signal_atr: float = 0.0
        pending_signal_bar_idx: int = -1

        active_trade: Optional[TradeRecord] = None
        active_entry_bar_idx: int = -1

        target_armed = False
        peak_rsi = 0.0
        down_count = 0

        for i in range(n):
            current_date = pd.Timestamp(dates[i])
            curr_open = opens[i]
            curr_high = highs[i]
            curr_low = lows[i]
            curr_close = closes[i]
            curr_rsi = daily_rsi[i]
            curr_signal = signals[i]

            # -------------------------------------------------------------
            # 1. EVALUATE PENDING ENTRY FROM PREVIOUS BAR (T+1 EXECUTION)
            # -------------------------------------------------------------
            if state == OrderState.PENDING_ENTRY:
                if curr_high >= pending_signal_high:
                    # Buy Stop Triggered: Fill price = max(Signal_High, Open_{T+1})
                    entry_price = max(pending_signal_high, curr_open)
                    
                    # Stop loss with optional ATR buffer
                    atr_val = pending_signal_atr if pending_signal_atr > 0 else 0.0
                    stop_loss_price = pending_signal_low - (self.sl_atr_buffer * atr_val)

                    active_trade = TradeRecord(
                        symbol=symbol,
                        signal_date=pending_signal_date,
                        signal_high=pending_signal_high,
                        signal_low=pending_signal_low,
                        signal_close=pending_signal_close,
                        entry_date=current_date,
                        entry_price=entry_price,
                        stop_loss=stop_loss_price,
                        entry_bar_idx=i,
                        is_closed=False,
                    )
                    active_entry_bar_idx = i
                    state = OrderState.IN_POSITION
                    target_armed = False
                    peak_rsi = curr_rsi if not np.isnan(curr_rsi) else 0.0
                    down_count = 0

                    # Clear pending signal
                    pending_signal_date = None
                    pending_signal_bar_idx = -1
                else:
                    # High < Signal_High: Order cancelled at T+1
                    pending_signal_date = None
                    pending_signal_bar_idx = -1
                    state = OrderState.OUT_OF_MARKET

            # -------------------------------------------------------------
            # 2. EVALUATE EXITS IF IN POSITION (SAME-BAR / INTRADAY)
            # -------------------------------------------------------------
            if state == OrderState.IN_POSITION and active_trade is not None:
                # Priority 1: Intraday Stop Loss Check (Strict Precedence)
                sl_hit = curr_low <= active_trade.stop_loss

                if sl_hit:
                    # SL Fill Price = min(Stop_Loss, Open_t)
                    exit_price = min(active_trade.stop_loss, curr_open)
                    active_trade.close_trade(
                        exit_date=current_date,
                        exit_price=exit_price,
                        exit_reason=ExitReason.STOP_LOSS.value,
                        exit_bar_idx=i,
                        entry_bar_idx=active_entry_bar_idx,
                    )
                    trades.append(active_trade)
                    active_trade = None
                    state = OrderState.OUT_OF_MARKET

                # Priority 2: Target Exit evaluation at Market Close
                elif not np.isnan(curr_rsi):
                    if self.exit_mode == "hard_rsi_60":
                        if curr_rsi >= self.target_rsi_threshold:
                            exit_price = curr_close
                            active_trade.close_trade(
                                exit_date=current_date,
                                exit_price=exit_price,
                                exit_reason=ExitReason.TARGET_RSI_60.value,
                                exit_bar_idx=i,
                                entry_bar_idx=active_entry_bar_idx,
                            )
                            trades.append(active_trade)
                            active_trade = None
                            state = OrderState.OUT_OF_MARKET

                    elif self.exit_mode == "user_momentum_exhaustion":
                        prev_rsi = daily_rsi[i - 1] if i > 0 and not np.isnan(daily_rsi[i - 1]) else curr_rsi
                        is_red_candle = curr_close < curr_open

                        if not target_armed:
                            if curr_rsi >= self.target_rsi_threshold:
                                target_armed = True
                                peak_rsi = curr_rsi
                                down_count = 0
                                if self.trail_sl_to_cost:
                                    active_trade.stop_loss = max(active_trade.stop_loss, active_trade.entry_price)
                        else:
                            # Target is armed (RSI previously reached >= 60)
                            if self.trail_sl_to_cost:
                                active_trade.stop_loss = max(active_trade.stop_loss, active_trade.entry_price)

                            # Condition A: Daily RSI dropped back below 60.0 (Immediate 100% exit)
                            if curr_rsi < self.target_rsi_threshold:
                                active_trade.close_trade(
                                    exit_date=current_date,
                                    exit_price=curr_close,
                                    exit_reason=ExitReason.TARGET_RSI_BELOW_60.value,
                                    exit_bar_idx=i,
                                    entry_bar_idx=active_entry_bar_idx,
                                    )
                                trades.append(active_trade)
                                active_trade = None
                                state = OrderState.OUT_OF_MARKET

                            # Condition B: 2 Consecutive Down RSI Days + Current Day Red Candle
                            elif down_count >= 2 and is_red_candle:
                                active_trade.close_trade(
                                    exit_date=current_date,
                                    exit_price=curr_close,
                                    exit_reason=ExitReason.TARGET_2DOWN_RED_CANDLE.value,
                                    exit_bar_idx=i,
                                    entry_bar_idx=active_entry_bar_idx,
                                )
                                trades.append(active_trade)
                                active_trade = None
                                state = OrderState.OUT_OF_MARKET

                            else:
                                # Update down_count tracker
                                if curr_rsi < prev_rsi:
                                    down_count += 1
                                else:
                                    down_count = 0

            # -------------------------------------------------------------
            # 3. EVALUATE NEW SIGNAL GENERATION ON DAY T CLOSE
            # -------------------------------------------------------------
            if state == OrderState.OUT_OF_MARKET:
                if curr_signal:
                    state = OrderState.PENDING_ENTRY
                    pending_signal_date = current_date
                    pending_signal_high = signal_highs[i] if not np.isnan(signal_highs[i]) else curr_high
                    pending_signal_low = signal_lows[i] if not np.isnan(signal_lows[i]) else curr_low
                    pending_signal_close = curr_close
                    pending_signal_atr = signal_atrs[i] if not np.isnan(signal_atrs[i]) else 0.0
                    pending_signal_bar_idx = i

        # Handle any trade that remains open at the end of the dataset
        if state == OrderState.IN_POSITION and active_trade is not None:
            if self.include_open_trades:
                trades.append(active_trade)

        return trades


def simulate_stock_trades(
    df_stock: pd.DataFrame,
    exit_mode: str = "hard_rsi_60",
    sl_atr_buffer: float = 0.0,
    target_rsi_threshold: float = 60.0,
    trail_sl_to_cost: bool = False,
    include_open_trades: bool = False,
) -> List[TradeRecord]:
    """
    Functional wrapper to simulate trades for a single stock DataFrame.
    """
    engine = OrderEngine(
        exit_mode=exit_mode,
        sl_atr_buffer=sl_atr_buffer,
        target_rsi_threshold=target_rsi_threshold,
        trail_sl_to_cost=trail_sl_to_cost,
        include_open_trades=include_open_trades,
    )
    return engine.simulate(df_stock)
