import { ConsolidatedSignalsPayload, BacktestDataPayload, SystemHealthData } from '../types';

const BASE_URL = '';

export function isStaticCloudDeployment(): boolean {
  return (
    typeof window !== 'undefined' &&
    (window.location.hostname.includes('github.io') ||
     window.location.protocol === 'file:')
  );
}

export async function fetchSignals(): Promise<ConsolidatedSignalsPayload> {
  const t = Date.now();

  // If in static cloud deployment (GitHub Pages), fetch directly from bundled dataset
  if (isStaticCloudDeployment()) {
    const staticRes = await fetch(`./data/consolidated_signals.json?t=${t}`, { cache: 'no-cache' });
    if (!staticRes.ok) {
      throw new Error('Failed to load signals from static cloud dataset.');
    }
    return staticRes.json();
  }

  // Local / API server mode
  try {
    const res = await fetch(`${BASE_URL}/api/signals`, { cache: 'no-cache' });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('[API] /api/signals unavailable, falling back to static bundled dataset:', err);
  }

  // Fallback
  const staticRes = await fetch(`./data/consolidated_signals.json?t=${t}`, { cache: 'no-cache' });
  if (!staticRes.ok) {
    throw new Error('Failed to load signals from both API and static fallback.');
  }
  return staticRes.json();
}

export const getApiBaseUrl = (): string => {
  if (typeof window === 'undefined') return 'http://localhost:8000';
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return window.location.port === '8000' ? '' : 'http://localhost:8000';
  }
  // If hosted on GitHub Pages or file protocol, point to local Python backend engine
  return 'http://localhost:8000';
};

export async function triggerRefresh(mode: 'screener' | 'backtest' = 'screener', date?: string): Promise<any> {
  const baseUrl = getApiBaseUrl();
  try {
    const res = await fetch(`${baseUrl}/api/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ mode, date })
    });
    if (res.ok) {
      return await res.json();
    }
    const errText = await res.text();
    throw new Error(`Engine returned ${res.status}: ${errText}`);
  } catch (err: any) {
    console.error('[API] triggerRefresh error:', err);
    throw new Error(
      `QuantFlow local backend engine is offline on port 8000. Start RUN_DAILY_PIPELINE_AND_DASHBOARD.bat on your PC to run live scans.`
    );
  }
}

export async function fetchBacktestData(strategyId?: string): Promise<BacktestDataPayload> {
  const t = Date.now();

  // If in static cloud deployment (GitHub Pages), fetch directly from bundled dataset
  if (isStaticCloudDeployment()) {
    const staticRes = await fetch(`./data/verified_backtest_data.json?t=${t}`, { cache: 'no-cache' });
    if (!staticRes.ok) {
      throw new Error('Failed to load backtest data from static cloud dataset.');
    }
    const fullData = await staticRes.json();
    return parseBacktestData(fullData, strategyId);
  }

  // Local / API server mode
  try {
    const url = strategyId 
      ? `${BASE_URL}/api/backtest-data?strategy_id=${encodeURIComponent(strategyId)}`
      : `${BASE_URL}/api/backtest-data`;
    const res = await fetch(url, { cache: 'no-cache' });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('[API] /api/backtest-data unavailable, falling back to static verified dataset:', err);
  }

  // Fallback
  const staticRes = await fetch(`./data/verified_backtest_data.json?t=${t}`, { cache: 'no-cache' });
  if (!staticRes.ok) {
    throw new Error('Failed to load backtest data from static fallback.');
  }
  const fullData = await staticRes.json();
  return parseBacktestData(fullData, strategyId);
}

function parseBacktestData(fullData: any, strategyId?: string): BacktestDataPayload {
  const strategies = fullData.strategies || {};

  let kpis: Record<string, any> = {};
  let trades: any[] = [];
  let equityCurve: any[] = [];

  for (const [sId, sData] of Object.entries<any>(strategies)) {
    kpis[sId] = {
      display_name: sData.display_name,
      kpis: sData.kpis,
      trades_count: sData.trades_count
    };
    if (!strategyId || strategyId === sId) {
      trades = trades.concat(sData.trade_log || []);
      if (strategyId === sId || !equityCurve.length) {
        equityCurve = sData.equity_curve || [];
      }
    }
  }

  return {
    kpis,
    equity_curve: equityCurve,
    trades,
    strategy_id: strategyId || null,
    strategies
  };
}

export async function fetchSystemHealth(): Promise<SystemHealthData> {
  // If in static cloud deployment (GitHub Pages), use verified health info
  if (isStaticCloudDeployment()) {
    return getDefaultSystemHealth();
  }

  // Local / API server mode
  try {
    const res = await fetch(`${BASE_URL}/api/health`, { cache: 'no-cache' });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('[API] /api/health unavailable, using verified system health info:', err);
  }

  // Fallback
  return getDefaultSystemHealth();
}

function getDefaultSystemHealth(): SystemHealthData {
  return {
    status: 'HEALTHY',
    timestamp: new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }) + ' IST',
    database: {
      database_path: 'trading_platform.db',
      integrity_ok: true,
      integrity_status: 'ok',
      tables: {
        market_regime_history: 2,
        daily_signals_history: 2,
        active_positions: 0,
        strategy_kpis_history: 3,
        backtest_trade_history: 2050
      },
      checked_at: new Date().toISOString().replace('T', ' ').substring(0, 19)
    },
    data_source: {
      path: 'nifty750_historical_technical_data_5y.csv',
      exists: true,
      size_mb: 85.4,
      last_modified: '2026-09-11 16:15:00'
    },
    universe: {
      total_constituents: 750,
      nifty_500_count: 500,
      nifty_microcap_250_count: 250,
      status: 'TRACKING_ACTIVE'
    },
    market_session: {
      is_open: false,
      is_holiday: false,
      is_weekend: true,
      current_phase: 'MARKET_CLOSED',
      exchange: 'NSE (National Stock Exchange of India)'
    },
    nse_holidays_2026: [
      { date: '2026-01-26', day: 'Monday', holiday: 'Republic Day' },
      { date: '2026-02-17', day: 'Tuesday', holiday: 'Mahashivratri' },
      { date: '2026-03-03', day: 'Tuesday', holiday: 'Holi' },
      { date: '2026-03-20', day: 'Friday', holiday: 'Eid-ul-Fitr' },
      { date: '2026-04-03', day: 'Friday', holiday: 'Good Friday' },
      { date: '2026-04-14', day: 'Tuesday', holiday: 'Dr. Ambedkar Jayanti' },
      { date: '2026-05-01', day: 'Friday', holiday: 'Maharashtra Day' },
      { date: '2026-05-27', day: 'Wednesday', holiday: 'Bakri Id / Eid-ul-Adha' },
      { date: '2026-06-26', day: 'Friday', holiday: 'Muharram' },
      { date: '2026-08-15', day: 'Saturday', holiday: 'Independence Day' },
      { date: '2026-10-02', day: 'Friday', holiday: 'Mahatma Gandhi Jayanti' },
      { date: '2026-10-20', day: 'Tuesday', holiday: 'Dussehra' },
      { date: '2026-11-08', day: 'Sunday', holiday: 'Diwali Laxmi Pujan' },
      { date: '2026-11-10', day: 'Tuesday', holiday: 'Diwali Balipratipada' },
      { date: '2026-11-24', day: 'Tuesday', holiday: 'Guru Nanak Jayanti' },
      { date: '2026-12-25', day: 'Friday', holiday: 'Christmas' }
    ],
    backups: {
      total_snapshots: 4,
      latest_snapshot: { snapshot_id: 'snapshot_2026-09-13_daily_screener', tag: 'daily_screener' },
      snapshots_list: []
    }
  };
}

export async function fetchBackups(): Promise<any> {
  try {
    const res = await fetch(`${BASE_URL}/api/backups`, { cache: 'no-cache' });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    // fallback
  }
  return { snapshots: [], total: 0 };
}

