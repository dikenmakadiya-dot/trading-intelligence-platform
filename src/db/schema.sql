-- Quant Trading Intelligence Platform - Relational Database Schema
-- Supports SQLite and PostgreSQL syntax compatibility

-- 1. Market Regime & Breadth History
CREATE TABLE IF NOT EXISTS market_regime_history (
    date TEXT PRIMARY KEY,                       -- ISO YYYY-MM-DD or trading session date
    breadth_pct REAL NOT NULL,                   -- % of Nifty 500 stocks > EMA50
    gate_open INTEGER NOT NULL,                  -- 1 = Open (Aggressive), 0 = Closed (Defensive)
    status_label TEXT NOT NULL,                  -- Descriptive label
    total_stocks_evaluated INTEGER DEFAULT 0,
    stocks_above_ema50 INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 2. Consolidated Daily Signals History
CREATE TABLE IF NOT EXISTS daily_signals_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_date TEXT NOT NULL,                   -- ISO YYYY-MM-DD
    strategy_id TEXT NOT NULL,                   -- e.g. rsi_52w_breakout, clean_candle_5y, gfs_mtf_rsi
    strategy_name TEXT NOT NULL,                 -- Human-readable strategy name
    rank INTEGER DEFAULT 1,
    symbol TEXT NOT NULL,
    company_name TEXT NOT NULL,
    industry TEXT DEFAULT 'Diversified',
    index_name TEXT DEFAULT 'NIFTY 500',
    close_price REAL NOT NULL,
    entry_trigger REAL NOT NULL,
    trailing_sl REAL NOT NULL,
    target_price REAL,
    groww_chart_url TEXT NOT NULL,
    metrics_json TEXT,                           -- JSON encoded technical metrics (RSI, volume surge, etc.)
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(signal_date, strategy_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_signals_date ON daily_signals_history(signal_date);
CREATE INDEX IF NOT EXISTS idx_signals_strategy ON daily_signals_history(strategy_id);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON daily_signals_history(symbol);

-- 3. Active Portfolio Positions Tracker
CREATE TABLE IF NOT EXISTS active_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    company_name TEXT NOT NULL,
    entry_date TEXT NOT NULL,                    -- Date entered (YYYY-MM-DD)
    entry_price REAL NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    allocated_capital REAL NOT NULL DEFAULT 0.0,
    current_price REAL NOT NULL,
    trailing_sl REAL NOT NULL,
    target_price REAL,
    unrealized_pnl REAL DEFAULT 0.0,
    unrealized_pnl_pct REAL DEFAULT 0.0,
    days_held INTEGER DEFAULT 0,
    groww_chart_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',          -- 'OPEN' or 'CLOSED'
    exit_date TEXT,
    exit_price REAL,
    exit_reason TEXT,
    realized_pnl REAL,
    realized_pnl_pct REAL,
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(strategy_id, symbol, entry_date)
);

CREATE INDEX IF NOT EXISTS idx_positions_status ON active_positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_strat_sym ON active_positions(strategy_id, symbol);

-- 4. Strategy KPIs & Backtest History Summary
CREATE TABLE IF NOT EXISTS strategy_kpis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,                      -- ISO YYYY-MM-DD
    strategy_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    initial_capital REAL DEFAULT 1000000.0,
    final_equity REAL DEFAULT 0.0,
    total_pnl REAL DEFAULT 0.0,
    total_trades INTEGER DEFAULT 0,
    win_rate_pct REAL DEFAULT 0.0,
    profit_factor REAL DEFAULT 0.0,
    cagr_pct REAL DEFAULT 0.0,
    max_drawdown_pct REAL DEFAULT 0.0,
    sharpe_ratio REAL DEFAULT 0.0,
    sortino_ratio REAL DEFAULT 0.0,
    calmar_ratio REAL DEFAULT 0.0,
    expectancy_pct REAL DEFAULT 0.0,
    expectancy_amt REAL DEFAULT 0.0,
    raw_kpis_json TEXT,                          -- Complete JSON string of all KPI metrics
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(run_date, strategy_id)
);

CREATE INDEX IF NOT EXISTS idx_kpis_strategy ON strategy_kpis_history(strategy_id);

-- 5. Audited Backtest Trade History
CREATE TABLE IF NOT EXISTS backtest_trade_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    company_name TEXT DEFAULT '',
    signal_date TEXT,
    entry_date TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_date TEXT NOT NULL,
    exit_price REAL NOT NULL,
    quantity INTEGER DEFAULT 1,
    allocated_capital REAL DEFAULT 0.0,
    proceeds_amount REAL DEFAULT 0.0,
    pnl_amount REAL NOT NULL,
    net_return_pct REAL NOT NULL,
    exit_reason TEXT NOT NULL,
    holding_days INTEGER NOT NULL,
    groww_chart_url TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(strategy_id, symbol, entry_date, exit_date)
);

CREATE INDEX IF NOT EXISTS idx_btest_trades_strat ON backtest_trade_history(strategy_id);
CREATE INDEX IF NOT EXISTS idx_btest_trades_symbol ON backtest_trade_history(symbol);
