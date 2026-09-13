import pandas as pd
import numpy as np
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    VOLUME_SURGE_MULTIPLIER,
    RSI_INCREASE_MIN,
    CLEAN_CANDLE_BODY_RATIO
)

def evaluate_candle_signal(
    c_t, h_t, l_t, o_t, v_t, v_prev,
    prior_high_close, prior_high_price,
    sma10_t, sma20_t, rsi_t, rsi_prev
):
    """
    Evaluates whether bar t satisfies the 5-Year High Breakout + Clean Candle rules.
    Returns (is_signal, metrics_dict).
    """
    # 1. 5-Year High Breakout
    is_breakout = (c_t > prior_high_close) or (c_t >= prior_high_price)
    if not is_breakout:
        return False, None
        
    # 2. Volume Surge (>= 3.0x previous day)
    if v_prev <= 0 or (v_t < VOLUME_SURGE_MULTIPLIER * v_prev):
        return False, None
        
    # 3. Moving Average Alignment (Close > SMA 10 and Close > SMA 20)
    if np.isnan(sma10_t) or np.isnan(sma20_t) or not (c_t > sma10_t and c_t > sma20_t):
        return False, None
        
    # 4. RSI Momentum Impulse (RSI delta >= +8.0)
    if np.isnan(rsi_t) or np.isnan(rsi_prev) or ((rsi_t - rsi_prev) < RSI_INCREASE_MIN):
        return False, None
        
    # 5. Clean Candle Body Filter (Marubozu / Quality Filter)
    # Candle body must be solid green and >= 40% of the entire candle range
    candle_range = h_t - l_t
    if candle_range <= 0 or (c_t <= o_t):
        return False, None
        
    body_ratio = (c_t - o_t) / candle_range
    if body_ratio < CLEAN_CANDLE_BODY_RATIO:
        return False, None
        
    # Signal Confirmed!
    vol_ratio = v_t / v_prev
    rsi_delta = rsi_t - rsi_prev
    momentum_score = vol_ratio * rsi_delta  # For sorting/ranking candidates
    
    metrics = {
        'close': c_t,
        'open': o_t,
        'high': h_t,
        'low': l_t,
        'volume': v_t,
        'vol_ratio': round(vol_ratio, 2),
        'rsi_t': round(rsi_t, 2),
        'rsi_delta': round(rsi_delta, 2),
        'body_ratio': round(body_ratio * 100, 1),
        'momentum_score': round(momentum_score, 2),
        'prior_5y_high': round(max(prior_high_close, prior_high_price), 2),
        'sl_price': l_t # Breakout candle low
    }
    
    return True, metrics

def scan_all_signals(df, start_date="2024-08-25"):
    """
    Scans the entire dataset for all historical breakout signals from start_date onwards.
    """
    start_ts = pd.to_datetime(start_date)
    signals = []
    
    grouped = df.groupby('Symbol')
    print(f"[STRATEGY] Scanning 5-year high breakouts for {len(grouped)} symbols from {start_date}...")
    
    for symbol, group in grouped:
        group = group.reset_index(drop=True)
        n = len(group)
        if n < 50:
            continue
            
        company_name = group['Company_Name'].iloc[0] if 'Company_Name' in group.columns else symbol
        industry = group['Industry'].iloc[0] if 'Industry' in group.columns else 'Unknown'
        index_name = group['Index_Name'].iloc[0] if 'Index_Name' in group.columns else 'Unknown'
        
        dates = group['Date'].values
        opens = group['Open'].values
        highs = group['High'].values
        lows = group['Low'].values
        closes = group['Close'].values
        vols = group['Volume'].values
        sma10s = group['SMA_10'].values
        sma20s = group['SMA_20'].values
        rsi14s = group['RSI_14'].values
        
        # Cumulative max strictly prior to day t
        cum_max_close = np.maximum.accumulate(closes)
        cum_max_high = np.maximum.accumulate(highs)
        
        for t in range(1, n - 1):
            current_date = pd.Timestamp(dates[t])
            if current_date < start_ts:
                continue
                
            p_close = cum_max_close[t-1]
            p_high = cum_max_high[t-1]
            
            is_sig, m = evaluate_candle_signal(
                closes[t], highs[t], lows[t], opens[t], vols[t], vols[t-1],
                p_close, p_high, sma10s[t], sma20s[t], rsi14s[t], rsi14s[t-1]
            )
            
            if not is_sig:
                continue
                
            entry_open = opens[t+1]
            if entry_open <= 0 or m['sl_price'] <= 0:
                continue
                
            signals.append({
                'symbol': symbol,
                'company_name': company_name,
                'industry': industry,
                'index_name': index_name,
                'signal_idx': t,
                'signal_date': current_date,
                'entry_idx': t + 1,
                'entry_date': pd.Timestamp(dates[t+1]),
                'entry_price': entry_open,
                'sl_price': m['sl_price'],
                'target_price': round(entry_open * 1.08, 2),
                'risk_per_share': round(entry_open - m['sl_price'], 2),
                'risk_pct': round(((entry_open - m['sl_price']) / entry_open) * 100, 2),
                'vol_ratio': m['vol_ratio'],
                'rsi_delta': m['rsi_delta'],
                'rsi_t': m['rsi_t'],
                'body_ratio': m['body_ratio'],
                'momentum_score': m['momentum_score'],
                # Forward price series for backtest execution
                'stock_dates': dates,
                'stock_opens': opens,
                'stock_highs': highs,
                'stock_lows': lows,
                'stock_closes': closes,
            })
            
    print(f"[STRATEGY] Identified {len(signals)} confirmed high-quality breakout signals.")
    return signals
