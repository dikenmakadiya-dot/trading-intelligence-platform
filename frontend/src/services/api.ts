import { ConsolidatedSignalsPayload, BacktestDataPayload, SystemHealthData } from '../types';

const BASE_URL = '';

export async function fetchSignals(): Promise<ConsolidatedSignalsPayload> {
  const res = await fetch(`${BASE_URL}/api/signals`, { cache: 'no-cache' });
  if (!res.ok) {
    throw new Error(`Failed to fetch signals: ${res.statusText}`);
  }
  return res.json();
}

export async function triggerRefresh(mode: 'screener' | 'backtest' = 'screener', date?: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ mode, date })
  });
  if (!res.ok) {
    throw new Error(`Failed to trigger refresh: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchBacktestData(strategyId?: string): Promise<BacktestDataPayload> {
  const url = strategyId 
    ? `${BASE_URL}/api/backtest-data?strategy_id=${encodeURIComponent(strategyId)}`
    : `${BASE_URL}/api/backtest-data`;
  const res = await fetch(url, { cache: 'no-cache' });
  if (!res.ok) {
    throw new Error(`Failed to fetch backtest data: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSystemHealth(): Promise<SystemHealthData> {
  const res = await fetch(`${BASE_URL}/api/health`, { cache: 'no-cache' });
  if (!res.ok) {
    throw new Error(`Failed to fetch system health: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchBackups(): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/backups`, { cache: 'no-cache' });
  if (!res.ok) {
    throw new Error(`Failed to fetch backups: ${res.statusText}`);
  }
  return res.json();
}
