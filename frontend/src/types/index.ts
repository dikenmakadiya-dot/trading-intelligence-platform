export interface MarketRegime {
  breadth_pct: number;
  gate_open: boolean;
  status_label: string;
  total_stocks_evaluated: number;
  stocks_above_ema50: number;
}

export interface SignalItem {
  id?: number;
  strategy_id: string;
  strategy_name?: string;
  rank: number;
  symbol: string;
  company_name: string;
  industry: string;
  index_name: string;
  close?: number;
  close_price?: number;
  entry_trigger: number;
  trailing_sl: number;
  target_price?: number | null;
  daily_rsi?: number;
  weekly_rsi?: number;
  monthly_rsi?: number;
  vol_ratio?: number;
  as_of_date: string;
  groww_chart_url: string;
  metrics?: Record<string, any>;
  [key: string]: any;
}

export interface PositionItem {
  id: number;
  strategy_id: string;
  symbol: string;
  company_name: string;
  entry_date: string;
  entry_price: number;
  quantity: number;
  allocated_capital: number;
  current_price: number;
  trailing_sl: number;
  target_price?: number | null;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  days_held: number;
  groww_chart_url: string;
  status: 'OPEN' | 'CLOSED';
  exit_date?: string | null;
  exit_price?: number | null;
  exit_reason?: string | null;
  realized_pnl?: number | null;
  realized_pnl_pct?: number | null;
  updated_at?: string;
}

export interface PortfolioSummary {
  total_open_positions: number;
  max_slots: number;
  available_slots: number;
  slots_label: string;
  total_invested_capital?: number;
  total_current_value?: number;
  total_unrealized_pnl?: number;
  total_unrealized_pnl_pct?: number;
  positions: PositionItem[];
}

export interface ConsolidatedSignalsPayload {
  generated_at: string;
  as_of_date: string;
  market_regime: MarketRegime;
  total_triggers: number;
  all_signals_unified: SignalItem[];
  portfolio_summary: PortfolioSummary;
  active_positions: PositionItem[];
  backup_status?: Record<string, any>;
  strategies?: Record<string, any>;
}

export interface StrategyKPI {
  initial_capital: number;
  final_equity: number;
  total_pnl: number;
  cagr_pct: number;
  max_drawdown_pct: number;
  win_rate_pct: number;
  profit_factor: number;
  realized_rr?: number;
  expectancy_amt?: number;
  expectancy_pct?: number;
  total_trades: number;
  win_trades?: number;
  loss_trades?: number;
  sharpe_ratio?: number;
  sortino_ratio?: number;
  avg_hold_days?: number;
  [key: string]: any;
}

export interface BacktestTrade {
  id?: number;
  strategy_id: string;
  symbol: string;
  company_name: string;
  signal_date?: string;
  entry_date: string;
  entry_price: number;
  exit_date: string;
  exit_price: number;
  quantity?: number;
  allocated_capital?: number;
  proceeds_amount?: number;
  pnl_amount: number;
  net_return_pct: number;
  exit_reason: string;
  holding_days: number;
  groww_chart_url: string;
}

export interface EquityCurvePoint {
  date: string;
  portfolio_value: number;
  cash: number;
  open_positions: number;
}

export interface BacktestDataPayload {
  kpis: Record<string, { display_name: string; kpis: StrategyKPI; trades_count: number }>;
  equity_curve: EquityCurvePoint[];
  trades: BacktestTrade[];
  strategy_id?: string | null;
}

export interface SystemHealthData {
  status: 'HEALTHY' | 'DEGRADED';
  timestamp: string;
  database: {
    database_path: string;
    integrity_ok: boolean;
    integrity_status: string;
    tables: Record<string, number>;
    checked_at: string;
  };
  data_source: {
    path: string;
    exists: boolean;
    size_mb: number;
    last_modified: string | null;
  };
  universe: {
    total_constituents: number;
    nifty_500_count: number;
    nifty_microcap_250_count: number;
    status: string;
  };
  market_session: {
    is_open: boolean;
    is_holiday: boolean;
    is_weekend: boolean;
    current_phase: string;
    exchange: string;
  };
  nse_holidays_2026: Array<{
    date: string;
    day: string;
    holiday: string;
  }>;
  backups: {
    total_snapshots: number;
    latest_snapshot: any;
    snapshots_list: any[];
  };
}
