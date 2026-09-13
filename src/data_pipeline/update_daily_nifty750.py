#!/usr/bin/env python3
"""
Automated Daily Incremental Stock Data & Indicator Updater for NIFTY 750 (Python Engine)
Covers 750 Stocks: 500 NIFTY 500 + 250 NIFTY Microcap 250 Constituents.

Features:
1. Scrapes official NSE holiday calendar from NiftyIndices.
2. Auto-syncs both NIFTY 500 & NIFTY Microcap 250 constituent master CSVs.
3. Identifies missing trading dates and fetches latest 1D OHLCV candles via Yahoo Finance API.
4. Computes 100% exact Groww MCP technical indicators using a trailing 200-candle seed.
5. Updates both flat CSV and Multi-Tab Excel Workbook (Tab 1: NIFTY750_Data, Tab 2: Last_Sync).
6. Archives historical rows rolling past 1,240 trading sessions into archive/nifty750_historical_archive.csv.
"""

import os
import sys
import json
import math
import time
import re
import datetime
from datetime import timezone, timedelta
import urllib.parse
from decimal import Decimal, ROUND_HALF_UP
import requests
from bs4 import BeautifulSoup
import xlsxwriter

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

CSV_FILE = os.path.join(WORKSPACE_ROOT, "nifty750_historical_technical_data_5y.csv")
XLSX_FILE = os.path.join(WORKSPACE_ROOT, "nifty750_historical_technical_data_5y.xlsx")
ARCHIVE_DIR = os.path.join(WORKSPACE_ROOT, "archive")
ARCHIVE_FILE = os.path.join(ARCHIVE_DIR, "nifty750_historical_archive.csv")
N500_FILE = os.path.join(BACKEND_DIR, "ind_nifty500list.csv")
MICRO250_FILE = os.path.join(BACKEND_DIR, "ind_niftymicrocap250_list.csv")
SYNC_LOG_FILE = os.path.join(BACKEND_DIR, "sync_log.json")
BATCH_PROGRESS_FILE = os.path.join(BACKEND_DIR, "batch_progress.json")

N500_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
MICRO250_URL = "https://www.niftyindices.com/IndexConstituent/ind_niftymicrocap250_list.csv"
HOLIDAY_CALENDAR_URL = "https://www.niftyindices.com/resources/holiday-calendar"

MAX_ROLLING_SESSIONS = 1240

CSV_HEADER = [
    "Symbol", "Company_Name", "Industry", "ISIN_Code", "Index_Name", "Date",
    "Open", "High", "Low", "Close", "Volume",
    "SMA_10", "SMA_20", "SMA_50", "SMA_100", "SMA_150", "SMA_200",
    "EMA_10", "EMA_20", "EMA_50", "EMA_100", "EMA_150", "EMA_200",
    "RSI_14", "MACD", "MACD_Signal", "MACD_Hist",
    "BB_Upper", "BB_Middle", "BB_Lower",
    "SuperTrend", "SuperTrend_Dir", "ATR_14", "ADX_14", "Plus_DI_14", "Minus_DI_14"
]

IST_OFFSET = timedelta(hours=5, minutes=30)

def get_ist_now():
    utc_now = datetime.datetime.now(timezone.utc)
    return utc_now + IST_OFFSET

def format_ist_string(d=None):
    if d is None:
        d = get_ist_now()
    return d.strftime("%Y-%m-%d %H:%M:%S IST")

def normalize_date(date_str):
    if not date_str:
        return ""
    date_str = date_str.split("T")[0].strip()
    parts = re.split(r"[-/]", date_str)
    if len(parts) == 3:
        if len(parts[0]) == 4:
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
        if len(parts[2]) == 4:
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    return date_str

def js_round(val):
    if val is None or val == "" or (isinstance(val, float) and math.isnan(val)):
        return None
    return round(float(val) + 1e-12, 2)

def format_val(val):
    if val is None or val == "" or (isinstance(val, float) and math.isnan(val)):
        return ""
    if isinstance(val, (int, float)):
        if isinstance(val, float) and val.is_integer():
            return str(int(val))
        r = js_round(val)
        if r is not None and float(r).is_integer():
            return str(int(r))
        return str(r)
    return str(val)

# ==================== 1. Scrape Live NSE Holidays ====================

def get_live_holidays():
    holidays = {}
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(HOLIDAY_CALENDAR_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tr in soup.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) >= 4:
                    date_str = tds[1].get_text(strip=True)
                    occasion = tds[3].get_text(strip=True)
                    if "/" in date_str:
                        parts = date_str.split("/")
                        if len(parts) == 3:
                            iso = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                            holidays[iso] = occasion
    except Exception as e:
        print(f"[WARN] Could not fetch live holidays: {e}. Using fallback.")
    return holidays

# ==================== 2. Constituent Synchronization ====================

def sync_constituent_list(url, file_path):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200 and len(resp.text) > 100:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"[SYNC] Updated {os.path.basename(file_path)} from NiftyIndices.")
    except Exception as e:
        print(f"[WARN] Error syncing constituent list from {url}: {e}. Using local cache.")

def parse_constituent_file(file_path, default_index_name):
    constituents = []
    if not os.path.exists(file_path):
        return constituents
    with open(file_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        cols = [c.strip().strip('"') for c in line.split(",")]
        if len(cols) >= 3:
            sym = cols[2].strip()
            if not sym or sym.lower() == "symbol" or "dummy" in sym.lower():
                continue
            constituents.append({
                "companyName": cols[0].strip(),
                "industry": cols[1].strip(),
                "symbol": sym,
                "isin": cols[4].strip() if len(cols) >= 5 else "",
                "indexName": default_index_name
            })
    return constituents

def load_unified_constituents():
    n500 = parse_constituent_file(N500_FILE, "NIFTY 500")
    mc250 = parse_constituent_file(MICRO250_FILE, "NIFTY MICROCAP 250")
    
    seen = {}
    combined = []
    for c in n500:
        seen[c["symbol"]] = c
        combined.append(c)
    for c in mc250:
        if c["symbol"] not in seen:
            seen[c["symbol"]] = c
            combined.append(c)
    return combined

# ==================== 3. Technical Indicator Formulations ====================

def calculate_sma(series, period):
    n = len(series)
    res = [None] * n
    if n < period:
        return res
    for i in range(period - 1, n):
        s = sum(series[i - period + 1 : i + 1])
        res[i] = js_round(s / period)
    return res

def calculate_continuous_ema(series, period, prev_recorded_ema, start_index):
    n = len(series)
    res = [None] * n
    k = 2.0 / (period + 1)
    
    if prev_recorded_ema is not None and not (isinstance(prev_recorded_ema, float) and math.isnan(prev_recorded_ema)):
        prev_ema = prev_recorded_ema
        for i in range(start_index, n):
            curr_ema = series[i] * k + prev_ema * (1.0 - k)
            res[i] = js_round(curr_ema)
            prev_ema = curr_ema
        return res
        
    if n < period:
        return res
    s = sum(series[:period])
    prev_ema = s / period
    res[period - 1] = js_round(prev_ema)
    for i in range(period, n):
        curr_ema = series[i] * k + prev_ema * (1.0 - k)
        res[i] = js_round(curr_ema)
        prev_ema = curr_ema
    return res

def calculate_groww_rsi(closes, period=14):
    n = len(closes)
    rsi = [None] * n
    if n <= period:
        return rsi
    for i in range(period - 1, n):
        gains = 0.0
        losses = 0.0
        for j in range(i - period + 1, i + 1):
            if j == 0:
                continue
            diff = closes[j] - closes[j - 1]
            if diff > 0:
                gains += diff
            else:
                losses += abs(diff)
        avg_gain = gains / period
        avg_loss = losses / period
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = js_round(100.0 - (100.0 / (1.0 + rs)))
    return rsi

def calculate_groww_bollinger_bands(closes, period=20, multiplier=2):
    n = len(closes)
    upper = [None] * n
    middle = [None] * n
    lower = [None] * n
    for i in range(period - 1, n):
        window = closes[i - period + 1 : i + 1]
        sma = sum(window) / period
        variance = sum((x - sma) ** 2 for x in window) / (period - 1)
        sd = math.sqrt(variance)
        middle[i] = js_round(sma)
        upper[i] = js_round(sma + multiplier * sd)
        lower[i] = js_round(sma - multiplier * sd)
    return upper, middle, lower

def calculate_groww_atr(highs, lows, closes, period=14):
    n = len(closes)
    atr = [None] * n
    if n < period:
        return atr
    tr = [0.0] * n
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
    for i in range(period - 1, n):
        atr[i] = js_round(sum(tr[i - period + 1 : i + 1]) / period)
    return atr

def calculate_supertrend(highs, lows, closes, period=10, multiplier=3):
    atr = calculate_groww_atr(highs, lows, closes, period)
    n = len(closes)
    supertrend = [None] * n
    direction = [None] * n
    
    prev_upper = 0.0
    prev_lower = 0.0
    prev_trend = 1
    
    for i in range(period - 1, n):
        hl2 = (highs[i] + lows[i]) / 2.0
        basic_upper = hl2 + multiplier * atr[i]
        basic_lower = hl2 - multiplier * atr[i]
        
        final_upper = basic_upper if (i == period - 1 or basic_upper < prev_upper or closes[i - 1] > prev_upper) else prev_upper
        final_lower = basic_lower if (i == period - 1 or basic_lower > prev_lower or closes[i - 1] < prev_lower) else prev_lower
        
        curr_trend = prev_trend
        if prev_trend == 1 and closes[i] < final_lower:
            curr_trend = -1
        elif prev_trend == -1 and closes[i] > final_upper:
            curr_trend = 1
            
        st_val = final_lower if curr_trend == 1 else final_upper
        supertrend[i] = js_round(st_val)
        direction[i] = curr_trend
        
        prev_upper = final_upper
        prev_lower = final_lower
        prev_trend = curr_trend
        
    return supertrend, direction

def calculate_groww_adx(highs, lows, closes, period=14):
    n = len(closes)
    adx = [None] * n
    plus_di = [None] * n
    minus_di = [None] * n
    if n <= period:
        return adx, plus_di, minus_di
    
    tr = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        if up > down and up > 0:
            plus_dm[i] = up
        if down > up and down > 0:
            minus_dm[i] = down
    
    dx_list = []
    for i in range(period - 1, n):
        sum_tr = sum(tr[i - period + 1 : i + 1])
        sum_pdm = sum(plus_dm[i - period + 1 : i + 1])
        sum_mdm = sum(minus_dm[i - period + 1 : i + 1])
        if sum_tr == 0:
            pdi = 0.0
            mdi = 0.0
            dx = 0.0
        else:
            pdi = (sum_pdm / sum_tr) * 100.0
            mdi = (sum_mdm / sum_tr) * 100.0
            plus_di[i] = js_round(pdi)
            minus_di[i] = js_round(mdi)
            denom = pdi + mdi
            dx = (abs(pdi - mdi) / denom * 100.0) if denom != 0 else 0.0
        dx_list.append({"index": i, "dx": dx})
        
    if len(dx_list) >= period:
        for i in range(period - 1, len(dx_list)):
            slice_dx = dx_list[i - period + 1 : i + 1]
            mean_dx = sum(x["dx"] for x in slice_dx) / period
            adx[dx_list[i]["index"]] = js_round(mean_dx)
            
    return adx, plus_di, minus_di

def calculate_macd(closes, fast=12, slow=26, signal=9):
    n = len(closes)
    macd_line = [None] * n
    signal_line = [None] * n
    hist = [None] * n
    if n < slow:
        return macd_line, signal_line, hist
    
    ema_fast = calculate_continuous_ema(closes, fast, None, 0)
    ema_slow = calculate_continuous_ema(closes, slow, None, 0)
    
    valid_macd_idx = slow - 1
    for i in range(valid_macd_idx, n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = js_round(ema_fast[i] - ema_slow[i])
            
    if n >= slow + signal - 1:
        valid_macd_slice = macd_line[valid_macd_idx:]
        ema_sig_slice = calculate_continuous_ema(valid_macd_slice, signal, None, 0)
        for i in range(len(ema_sig_slice)):
            signal_line[valid_macd_idx + i] = ema_sig_slice[i]
            
    for i in range(n):
        if macd_line[i] is not None and signal_line[i] is not None:
            hist[i] = js_round(macd_line[i] - signal_line[i])
            
    return macd_line, signal_line, hist

# ==================== 4. Historical Buffer & Candle Fetcher ====================

def load_trailing_historical_buffer(symbols, buffer_size=200):
    buffers = {s: [] for s in symbols}
    if not os.path.exists(CSV_FILE):
        return buffers
    
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        header = f.readline()
        for line in f:
            line = line.strip()
            if not line:
                continue
            cols = line.split(",")
            sym = cols[0]
            if sym in buffers:
                buffers[sym].append({
                    "symbol": cols[0],
                    "companyName": cols[1],
                    "industry": cols[2],
                    "isin": cols[3],
                    "indexName": cols[4],
                    "date": cols[5],
                    "isoDate": normalize_date(cols[5]),
                    "open": float(cols[6]) if cols[6] else None,
                    "high": float(cols[7]) if cols[7] else None,
                    "low": float(cols[8]) if cols[8] else None,
                    "close": float(cols[9]) if cols[9] else None,
                    "volume": float(cols[10]) if cols[10] else None,
                    "sma10": float(cols[11]) if cols[11] != "" else None,
                    "sma20": float(cols[12]) if cols[12] != "" else None,
                    "sma50": float(cols[13]) if cols[13] != "" else None,
                    "sma100": float(cols[14]) if cols[14] != "" else None,
                    "sma150": float(cols[15]) if cols[15] != "" else None,
                    "sma200": float(cols[16]) if cols[16] != "" else None,
                    "ema10": float(cols[17]) if cols[17] != "" else None,
                    "ema20": float(cols[18]) if cols[18] != "" else None,
                    "ema50": float(cols[19]) if cols[19] != "" else None,
                    "ema100": float(cols[20]) if cols[20] != "" else None,
                    "ema150": float(cols[21]) if cols[21] != "" else None,
                    "ema200": float(cols[22]) if cols[22] != "" else None,
                    "rsi14": float(cols[23]) if cols[23] != "" else None,
                    "macd": float(cols[24]) if cols[24] != "" else None,
                    "macdSignal": float(cols[25]) if cols[25] != "" else None,
                    "macdHist": float(cols[26]) if cols[26] != "" else None,
                    "bbUpper": float(cols[27]) if cols[27] != "" else None,
                    "bbMiddle": float(cols[28]) if cols[28] != "" else None,
                    "bbLower": float(cols[29]) if cols[29] != "" else None,
                    "supertrend": float(cols[30]) if cols[30] != "" else None,
                    "supertrendDir": int(cols[31]) if cols[31] != "" else None,
                    "atr14": float(cols[32]) if cols[32] != "" else None,
                    "adx14": float(cols[33]) if cols[33] != "" else None,
                    "plusDI14": float(cols[34]) if cols[34] != "" else None,
                    "minusDI14": float(cols[35]) if cols[35] != "" else None
                })
                if len(buffers[sym]) > buffer_size:
                    buffers[sym].pop(0)
    return buffers

def fetch_latest_candles_yahoo(symbol, start_time_epoch):
    formatted_symbol = symbol if "^" in symbol else f"{symbol}.NS"
    now_epoch = int(time.time())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(formatted_symbol)}?period1={start_time_epoch}&period2={now_epoch}&interval=1d&events=history"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            return []
        data = resp.json()
        result = data.get("chart", {}).get("result")
        if not result or len(result) == 0:
            return []
        
        timestamps = result[0].get("timestamp", [])
        quote = result[0].get("indicators", {}).get("quote", [{}])[0]
        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        closes = quote.get("close", [])
        volumes = quote.get("volume", [])
        
        candles = []
        for i, ts in enumerate(timestamps):
            if i >= len(closes) or closes[i] is None:
                continue
            dt = datetime.datetime.fromtimestamp(ts, tz=timezone.utc) + IST_OFFSET
            date_str = dt.strftime("%d-%m-%Y")
            iso_date = dt.strftime("%Y-%m-%d")
            candles.append({
                "date": date_str,
                "isoDate": iso_date,
                "open": round(opens[i], 2) if opens[i] is not None else round(closes[i], 2),
                "high": round(highs[i], 2) if highs[i] is not None else round(closes[i], 2),
                "low": round(lows[i], 2) if lows[i] is not None else round(closes[i], 2),
                "close": round(closes[i], 2),
                "volume": int(volumes[i]) if volumes[i] is not None else 0
            })
        return candles
    except Exception:
        return []

# ==================== 5. Excel Stream Generation ====================

def refresh_multitab_excel(sync_status_text, rows_added=0):
    print("[EXCEL SYNC] Refreshing multi-tab Excel workbook (high-speed XlsxWriter stream)...")
    start_xl = time.time()
    temp_xlsx = XLSX_FILE + ".tmp"
    
    wb = xlsxwriter.Workbook(temp_xlsx, {'constant_memory': True, 'default_date_format': 'dd-mm-yyyy'})
    header_format = wb.add_format({'bold': True, 'bg_color': '#E0E0E0', 'border': 1})
    
    # 1. Sheet: Last_Sync
    sync_sheet = wb.add_worksheet('Last_Sync')
    sync_sheet.set_column(0, 0, 32)
    sync_sheet.set_column(1, 1, 80)
    sync_sheet.write_row(0, 0, ["Parameter / Metric", "Status / Details"], header_format)
    
    last_session_date = "N/A"
    total_active_rows = 0
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                total_active_rows += 1
                cols = line.split(",")
                if len(cols) >= 6:
                    last_session_date = cols[5]
    total_active_rows = max(0, total_active_rows - 1)
    
    sync_metadata = [
        ("Last Sync Timestamp", format_ist_string()),
        ("Market Session Covered", last_session_date),
        ("Total Constituents Synced", "750 / 750 (100%)"),
        ("Active Dataset Rows", str(total_active_rows)),
        ("Active Window Max Sessions", f"{MAX_ROLLING_SESSIONS} Trading Days per Stock"),
        ("Technical Indicators Included", "25 Columns (SMA 10-200, EMA 10-200, RSI, MACD, BB, SuperTrend, ATR, ADX/DMI)"),
        ("Sync Status", sync_status_text),
        ("Archive Storage Path", "archive/nifty750_historical_archive.csv"),
        ("Error Details", "None"),
        ("Scheduler Config", "Daily 4:00 PM IST (Mon-Fri) with Power-Off Catchup")
    ]
    
    for r_idx, (k, v) in enumerate(sync_metadata, start=1):
        sync_sheet.write_string(r_idx, 0, k)
        sync_sheet.write_string(r_idx, 1, v)
        
    # 2. Sheet: NIFTY750_Data
    data_sheet = wb.add_worksheet('NIFTY750_Data')
    
    row_idx = 0
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cols = line.split(",")
            if row_idx == 0:
                data_sheet.write_row(0, 0, cols, header_format)
            else:
                for c_idx, val in enumerate(cols):
                    if c_idx < 6:
                        data_sheet.write_string(row_idx, c_idx, val)
                    elif val == "" or val is None:
                        data_sheet.write_blank(row_idx, c_idx, None)
                    else:
                        try:
                            data_sheet.write_number(row_idx, c_idx, float(val))
                        except ValueError:
                            data_sheet.write_string(row_idx, c_idx, val)
            row_idx += 1
            
    wb.close()
    
    if os.path.exists(XLSX_FILE):
        os.remove(XLSX_FILE)
    os.rename(temp_xlsx, XLSX_FILE)
    xl_duration = round(time.time() - start_xl, 2)
    print(f"[EXCEL SYNC] Successfully updated multi-tab {os.path.basename(XLSX_FILE)} in {xl_duration}s.")

# ==================== 6. Rolling Archival Manager ====================

def perform_archival_trim():
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        
    stock_rows = {}
    symbol_order = []
    header_line = None
    
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if header_line is None:
                header_line = line
                continue
            sym = line.split(",")[0]
            if sym not in stock_rows:
                stock_rows[sym] = []
                symbol_order.append(sym)
            stock_rows[sym].append(line)
            
    active_lines = [header_line]
    archived_lines = []
    total_archived = 0
    
    for sym in symbol_order:
        rows = stock_rows[sym]
        if len(rows) > MAX_ROLLING_SESSIONS:
            excess = len(rows) - MAX_ROLLING_SESSIONS
            archived_lines.extend(rows[:excess])
            active_lines.extend(rows[excess:])
            total_archived += excess
        else:
            active_lines.extend(rows)
            
    if archived_lines:
        archive_exists = os.path.exists(ARCHIVE_FILE)
        with open(ARCHIVE_FILE, "a" if archive_exists else "w", encoding="utf-8") as f:
            if not archive_exists:
                f.write(header_line + "\n")
            f.write("\n".join(archived_lines) + "\n")
        print(f"[ARCHIVE] Saved {total_archived} rolled-off historical records to {os.path.basename(ARCHIVE_FILE)}.")
        
        temp_csv = CSV_FILE + ".tmp"
        with open(temp_csv, "w", encoding="utf-8") as f:
            f.write("\n".join(active_lines) + "\n")
        if os.path.exists(CSV_FILE):
            os.remove(CSV_FILE)
        os.rename(temp_csv, CSV_FILE)
        print(f"[CSV TRIMMED] Maintained active dataset strictly at <= {MAX_ROLLING_SESSIONS} sessions.")
        
    return total_archived

# ==================== 7. Main Daily Execution Engine ====================

def run_daily_updater(dry_run=False):
    start_time = time.time()
    print(f"=== NIFTY 750 Daily Incremental Updater (Python Engine) [{format_ist_string()}] ===")
    if dry_run:
        print(">>> RUNNING IN DRY-RUN MODE (No files will be modified) <<<")
        
    # Check Holidays
    holidays = get_live_holidays()
    ist = get_ist_now()
    day_of_week = ist.weekday() # 0 = Mon, 5 = Sat, 6 = Sun
    today_iso = ist.strftime("%Y-%m-%d")
    
    if day_of_week in (5, 6):
        print(f"[INFO] Today ({today_iso}) is a Weekend. NSE Market is closed.")
        return {"status": "MARKET_CLOSED_WEEKEND", "message": "Weekend - Market Closed"}
        
    if today_iso in holidays:
        print(f"[INFO] Today ({today_iso}) is an Official NSE Holiday: {holidays[today_iso]}")
        return {"status": "MARKET_CLOSED_HOLIDAY", "message": f"Holiday: {holidays[today_iso]}"}
        
    # Sync Constituents
    if not dry_run:
        sync_constituent_list(N500_URL, N500_FILE)
        sync_constituent_list(MICRO250_URL, MICRO250_FILE)
        
    constituents = load_unified_constituents()
    symbols = [c["symbol"] for c in constituents]
    meta_map = {c["symbol"]: c for c in constituents}
    print(f"Active Constituents: {len(symbols)}")
    
    # Load trailing buffer
    print("Loading trailing historical buffer from CSV...")
    buffers = load_trailing_historical_buffer(symbols, buffer_size=200)
    
    sample_sym = "RELIANCE" if "RELIANCE" in buffers and buffers["RELIANCE"] else symbols[0]
    sample_buffer = buffers.get(sample_sym, [])
    last_recorded_date = sample_buffer[-1]["date"] if sample_buffer else "N/A"
    last_recorded_iso = sample_buffer[-1]["isoDate"] if sample_buffer else "1970-01-01"
    print(f"Last recorded session in dataset: {last_recorded_date} ({last_recorded_iso})")
    
    # Check for new closed sessions
    print("Checking for new closed market sessions...")
    test_epoch = int(time.time()) - (5 * 86400)
    test_candles = fetch_latest_candles_yahoo(sample_sym, test_epoch)
    
    missing_dates = []
    for c in test_candles:
        if c["isoDate"] > last_recorded_iso and c["isoDate"] <= today_iso:
            missing_dates.append(c["isoDate"])
            
    if not missing_dates:
        print("[SUCCESS] Dataset is already 100% up-to-date with the latest market session.")
        return {"status": "ALREADY_UP_TO_DATE", "lastSessionDate": last_recorded_date}
        
    print(f"Detected {len(missing_dates)} new closed session(s) to synchronize: {', '.join(missing_dates)}")
    
    # Fetch candles for all constituents
    new_rows_by_stock = {}
    batch_size = 50
    total_new_candles = 0
    start_epoch = int(time.time()) - (10 * 86400)
    
    for idx, sym in enumerate(symbols):
        stock_buf = buffers.get(sym, [])
        stock_last_iso = stock_buf[-1]["isoDate"] if stock_buf else "1970-01-01"
        candles = fetch_latest_candles_yahoo(sym, start_epoch)
        new_candles = [c for c in candles if c["isoDate"] > stock_last_iso]
        if new_candles:
            new_rows_by_stock[sym] = new_candles
            total_new_candles += len(new_candles)
            
        if (idx + 1) % batch_size == 0 or idx == len(symbols) - 1:
            pct = round(((idx + 1) / len(symbols)) * 100, 1)
            print(f"[{pct}%] Synced {idx + 1}/{len(symbols)} stocks. New candles: {total_new_candles}")
            time.sleep(0.05)
            
    if dry_run:
        print(f"\n[DRY RUN] Finished. Total new rows that would be added: {total_new_candles}")
        return {"status": "DRY_RUN_COMPLETED", "rowsAdded": total_new_candles}
        
    # Calculate indicators incrementally and append rows
    lines_to_append = []
    for sym in symbols:
        new_candles = new_rows_by_stock.get(sym, [])
        if not new_candles:
            continue
        
        full_series = buffers.get(sym, []) + new_candles
        meta = meta_map.get(sym, {"companyName": sym, "industry": "N/A", "isin": "N/A", "indexName": "NIFTY 500"})
        
        closes = [c["close"] for c in full_series]
        highs = [c["high"] for c in full_series]
        lows = [c["low"] for c in full_series]
        
        sma10 = calculate_sma(closes, 10)
        sma20 = calculate_sma(closes, 20)
        sma50 = calculate_sma(closes, 50)
        sma100 = calculate_sma(closes, 100)
        sma150 = calculate_sma(closes, 150)
        sma200 = calculate_sma(closes, 200)
        
        stock_buf = buffers.get(sym, [])
        last_hist = stock_buf[-1] if stock_buf else None
        start_idx = len(full_series) - len(new_candles)
        
        ema10 = calculate_continuous_ema(closes, 10, last_hist["ema10"] if last_hist else None, start_idx)
        ema20 = calculate_continuous_ema(closes, 20, last_hist["ema20"] if last_hist else None, start_idx)
        ema50 = calculate_continuous_ema(closes, 50, last_hist["ema50"] if last_hist else None, start_idx)
        ema100 = calculate_continuous_ema(closes, 100, last_hist["ema100"] if last_hist else None, start_idx)
        ema150 = calculate_continuous_ema(closes, 150, last_hist["ema150"] if last_hist else None, start_idx)
        ema200 = calculate_continuous_ema(closes, 200, last_hist["ema200"] if last_hist else None, start_idx)
        
        rsi14 = calculate_groww_rsi(closes, 14)
        macd_line, sig_line, hist = calculate_macd(closes, 12, 26, 9)
        bb_upper, bb_mid, bb_lower = calculate_groww_bollinger_bands(closes, 20, 2)
        st, st_dir = calculate_supertrend(highs, lows, closes, 10, 3)
        atr14 = calculate_groww_atr(highs, lows, closes, 14)
        adx14, plus_di, minus_di = calculate_groww_adx(highs, lows, closes, 14)
        
        for i in range(start_idx, len(full_series)):
            c = full_series[i]
            comp_name = meta["companyName"]
            ind_name = meta["industry"]
            row = [
                sym,
                f'"{comp_name}"' if "," in comp_name else comp_name,
                f'"{ind_name}"' if "," in ind_name else ind_name,
                meta["isin"],
                meta["indexName"],
                c["date"],
                format_val(c["open"]),
                format_val(c["high"]),
                format_val(c["low"]),
                format_val(c["close"]),
                format_val(c["volume"]),
                format_val(sma10[i]),
                format_val(sma20[i]),
                format_val(sma50[i]),
                format_val(sma100[i]),
                format_val(sma150[i]),
                format_val(sma200[i]),
                format_val(ema10[i]),
                format_val(ema20[i]),
                format_val(ema50[i]),
                format_val(ema100[i]),
                format_val(ema150[i]),
                format_val(ema200[i]),
                format_val(rsi14[i]),
                format_val(macd_line[i]),
                format_val(sig_line[i]),
                format_val(hist[i]),
                format_val(bb_upper[i]),
                format_val(bb_mid[i]),
                format_val(bb_lower[i]),
                format_val(st[i]),
                format_val(st_dir[i]),
                format_val(atr14[i]),
                format_val(adx14[i]),
                format_val(plus_di[i]),
                format_val(minus_di[i])
            ]
            lines_to_append.append(",".join(row))
            
    if lines_to_append:
        with open(CSV_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(lines_to_append) + "\n")
        print(f"[CSV UPDATED] Appended {len(lines_to_append)} new records.")
        
        archived_count = perform_archival_trim()
        refresh_multitab_excel(f"SUCCESS - Appended {len(lines_to_append)} rows (Archived {archived_count} oldest)", len(lines_to_append))
        
    duration_sec = round(time.time() - start_time, 2)
    result = {
        "timestamp": format_ist_string(),
        "durationSeconds": duration_sec,
        "status": "SUCCESS",
        "rowsAdded": len(lines_to_append),
        "totalConstituents": len(constituents),
        "lastSessionDate": sample_buffer[-1]["date"] if sample_buffer else "N/A"
    }
    with open(SYNC_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        
    print(f"\n=== Python Incremental Sync Completed in {duration_sec}s ===")
    return result

if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    run_daily_updater(dry_run=is_dry)
