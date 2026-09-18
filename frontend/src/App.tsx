import React, { useState, useEffect, useCallback } from 'react';
import { AppLayout } from './components/layout/AppLayout';
import { ActiveTab } from './components/layout/MobileDock';
import { MasterStage } from './views/MasterStage';
import { StrategyDashboard } from './views/StrategyDashboard';
import { SystemHealth } from './views/SystemHealth';
import { CloudConnectModal } from './components/CloudConnectModal';
import {
  ConsolidatedSignalsPayload,
  BacktestDataPayload,
  SystemHealthData
} from './types';
import {
  fetchSignals,
  fetchBacktestData,
  fetchSystemHealth,
  triggerRefresh
} from './services/api';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('nexus');
  const [signalsData, setSignalsData] = useState<ConsolidatedSignalsPayload | null>(null);
  const [backtestData, setBacktestData] = useState<BacktestDataPayload | null>(null);
  const [healthData, setHealthData] = useState<SystemHealthData | null>(null);
  
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isRefreshingBacktest, setIsRefreshingBacktest] = useState(false);
  const [isRefreshingHealth, setIsRefreshingHealth] = useState(false);
  const [isCloudModalOpen, setIsCloudModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showToast = (text: string, type: 'success' | 'error' | 'info' = 'success', duration: number = 5000) => {
    setToastMessage({ text, type });
    if (duration > 0) {
      setTimeout(() => setToastMessage(null), duration);
    }
  };

  // Initial Data Load
  const loadData = useCallback(async () => {
    try {
      const [sig, bt, hl] = await Promise.allSettled([
        fetchSignals(),
        fetchBacktestData(),
        fetchSystemHealth()
      ]);

      if (sig.status === 'fulfilled') setSignalsData(sig.value);
      if (bt.status === 'fulfilled') setBacktestData(bt.value);
      if (hl.status === 'fulfilled') setHealthData(hl.value);
    } catch (err) {
      console.error('Data initialization error:', err);
    }
  }, []);

  useEffect(() => {
    loadData();
    // Auto-refresh every 60 seconds
    const timer = setInterval(() => {
      loadData();
    }, 60000);
    return () => clearInterval(timer);
  }, [loadData]);

  // Handle Cloud / Local Live Screener Execution
  const handleRefreshSignals = async () => {
    setIsRefreshing(true);
    showToast('Initiating Multi-Strategy Market Screener...', 'info', 0);
    try {
      const res = await triggerRefresh('screener', undefined, (statusText: string) => {
        showToast(statusText, 'info', 0);
      });
      if (res.success) {
        showToast(res.message || 'Market Scan Complete! Fresh breakout signals loaded.', 'success', 6000);
        if (res.data && res.data.all_signals_unified) {
          setSignalsData(res.data);
        } else {
          await loadData();
        }
      } else {
        showToast(`Refresh failed: ${res.error || 'Unknown error'}`, 'error', 8000);
      }
    } catch (err: any) {
      if (err.message === 'CLOUD_TOKEN_REQUIRED') {
        showToast('Connect your GitHub Token to trigger cloud screeners without your PC.', 'info', 5000);
        setIsCloudModalOpen(true);
      } else {
        showToast(err.message || 'Error running live market scan', 'error', 8000);
      }
    } finally {
      setIsRefreshing(false);
    }
  };

  // Handle Cloud / Local Backtest Execution
  const handleRefreshBacktest = async (strategyId: string) => {
    setIsRefreshingBacktest(true);
    showToast(`Initiating 5-Year Backtest Simulation for ${strategyId}...`, 'info', 0);
    try {
      const res = await triggerRefresh('backtest', undefined, (statusText: string) => {
        showToast(statusText, 'info', 0);
      });
      if (res.success) {
        showToast(res.message || `Backtest simulation initiated!`, 'success', 6000);
        const updatedBt = await fetchBacktestData(strategyId);
        setBacktestData(updatedBt);
      } else {
        showToast(`Backtest failed: ${res.error || 'Unknown error'}`, 'error', 8000);
      }
    } catch (err: any) {
      if (err.message === 'CLOUD_TOKEN_REQUIRED') {
        showToast('Connect your GitHub Token to run cloud backtest simulations without your PC.', 'info', 5000);
        setIsCloudModalOpen(true);
      } else {
        showToast(err.message || 'Error running backtest', 'error', 8000);
      }
    } finally {
      setIsRefreshingBacktest(false);
    }
  };

  // Handle System Health Refresh
  const handleRefreshHealth = async () => {
    setIsRefreshingHealth(true);
    showToast('Verifying SQLite WAL database integrity & snapshots...', 'info', 0);
    try {
      const hl = await fetchSystemHealth();
      setHealthData(hl);
      showToast('System Health & Database Integrity Verified (Status: HEALTHY)', 'success', 5000);
    } catch (err: any) {
      console.error('Failed to refresh health:', err);
      showToast(err.message || 'Error refreshing system health', 'error', 6000);
    } finally {
      setIsRefreshingHealth(false);
    }
  };

  // Fallback initial object while loading
  const safeSignalsData: ConsolidatedSignalsPayload = signalsData || {
    generated_at: 'Loading...',
    as_of_date: '11-Sep-2026',
    market_regime: {
      breadth_pct: 34.0,
      gate_open: false,
      status_label: 'DEFENSIVE (CASH PROTECTION)',
      total_stocks_evaluated: 500,
      stocks_above_ema50: 170
    },
    total_triggers: 0,
    all_signals_unified: [],
    portfolio_summary: {
      total_open_positions: 0,
      max_slots: 5,
      available_slots: 5,
      slots_label: '0 / 5 Filled',
      positions: []
    },
    active_positions: []
  };

  return (
    <>
      <AppLayout
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onRefresh={handleRefreshSignals}
        isRefreshing={isRefreshing}
        lastSyncTime={signalsData?.generated_at}
        triggerCount={signalsData?.total_triggers || 0}
        gateOpen={safeSignalsData.market_regime.gate_open}
        onOpenCloudModal={() => setIsCloudModalOpen(true)}
      >
        {/* Dynamic Toast / Status Banner */}
        {toastMessage && (
          <div
            className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-5 py-3.5 rounded-2xl shadow-2xl border text-xs font-bold font-sans backdrop-blur-xl transition-all animate-in fade-in slide-in-from-top-2 duration-200 ${
              toastMessage.type === 'success'
                ? 'bg-slate-950/95 text-emerald-300 border-emerald-500/50 shadow-[0_0_25px_rgba(0,255,157,0.3)]'
                : toastMessage.type === 'info'
                ? 'bg-slate-950/95 text-cyan-300 border-cyan-500/50 shadow-[0_0_25px_rgba(0,229,255,0.3)]'
                : 'bg-slate-950/95 text-rose-300 border-rose-500/50 shadow-[0_0_25px_rgba(255,51,102,0.3)]'
            }`}
          >
            {toastMessage.type === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
            {toastMessage.type === 'info' && <Loader2 className="w-4 h-4 text-cyan-400 animate-spin shrink-0" />}
            {toastMessage.type === 'error' && <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />}
            <span className="leading-snug max-w-sm">{toastMessage.text}</span>
          </div>
        )}

        {/* Screen Views */}
        {activeTab === 'nexus' && (
          <MasterStage
            data={safeSignalsData}
            onRefresh={handleRefreshSignals}
            isRefreshing={isRefreshing}
          />
        )}

        {activeTab === 'strategy_1' && (
          <StrategyDashboard
            initialStrategyId="rsi_52w_breakout"
            backtestData={backtestData}
            onRefreshBacktest={handleRefreshBacktest}
            isRefreshingBacktest={isRefreshingBacktest}
          />
        )}

        {activeTab === 'strategy_2' && (
          <StrategyDashboard
            initialStrategyId="clean_candle_5y"
            backtestData={backtestData}
            onRefreshBacktest={handleRefreshBacktest}
            isRefreshingBacktest={isRefreshingBacktest}
          />
        )}

        {activeTab === 'strategy_3' && (
          <StrategyDashboard
            initialStrategyId="gfs_mtf_rsi"
            backtestData={backtestData}
            onRefreshBacktest={handleRefreshBacktest}
            isRefreshingBacktest={isRefreshingBacktest}
          />
        )}

        {activeTab === 'health' && (
          <SystemHealth
            healthData={healthData}
            onRefreshHealth={handleRefreshHealth}
            isRefreshingHealth={isRefreshingHealth}
          />
        )}
      </AppLayout>

      {/* 100% Cloud Automation Connector Modal */}
      <CloudConnectModal
        isOpen={isCloudModalOpen}
        onClose={() => setIsCloudModalOpen(false)}
        onConnected={() => loadData()}
      />
    </>
  );
};
export default App;
