import React, { useState, useEffect, useCallback } from 'react';
import { AppLayout } from './components/layout/AppLayout';
import { ActiveTab } from './components/layout/MobileDock';
import { MasterStage } from './views/MasterStage';
import { StrategyDashboard } from './views/StrategyDashboard';
import { SystemHealth } from './views/SystemHealth';
import {
  ConsolidatedSignalsPayload,
  BacktestDataPayload,
  SystemHealthData
} from './types';
import {
  fetchSignals,
  fetchBacktestData,
  fetchSystemHealth,
  triggerRefresh,
  isStaticCloudDeployment
} from './services/api';
import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { CloudSyncModal } from './components/ui/CloudSyncModal';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('nexus');
  const [signalsData, setSignalsData] = useState<ConsolidatedSignalsPayload | null>(null);
  const [backtestData, setBacktestData] = useState<BacktestDataPayload | null>(null);
  const [healthData, setHealthData] = useState<SystemHealthData | null>(null);
  
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isRefreshingBacktest, setIsRefreshingBacktest] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Cloud Sync Modal state
  const [isCloudModalOpen, setIsCloudModalOpen] = useState(false);
  const [cloudModalMode, setCloudModalMode] = useState<'screener' | 'backtest'>('screener');

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
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

  // Handle Screener Refresh / Cloud Hub Open
  const handleRefreshSignals = async () => {
    if (isStaticCloudDeployment()) {
      setCloudModalMode('screener');
      setIsCloudModalOpen(true);
      return;
    }

    setIsRefreshing(true);
    try {
      const res = await triggerRefresh('screener');
      if (res.success) {
        showToast(res.message || 'Daily breakout signals refreshed successfully!', 'success');
        await loadData();
      } else {
        showToast(`Refresh failed: ${res.error || 'Unknown error'}`, 'error');
      }
    } catch (err: any) {
      showToast(`Refresh error: ${err.message}`, 'error');
    } finally {
      setIsRefreshing(false);
    }
  };

  // Handle Backtest Refresh / Cloud Hub Open
  const handleRefreshBacktest = async (strategyId: string) => {
    if (isStaticCloudDeployment()) {
      setCloudModalMode('backtest');
      setIsCloudModalOpen(true);
      return;
    }

    setIsRefreshingBacktest(true);
    try {
      const res = await triggerRefresh('backtest');
      if (res.success) {
        showToast(res.message || `Backtest simulation complete for ${strategyId}`, 'success');
        const updatedBt = await fetchBacktestData(strategyId);
        setBacktestData(updatedBt);
      } else {
        showToast(`Backtest failed: ${res.error || 'Unknown error'}`, 'error');
      }
    } catch (err: any) {
      showToast(`Backtest error: ${err.message}`, 'error');
    } finally {
      setIsRefreshingBacktest(false);
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
    <AppLayout
      activeTab={activeTab}
      setActiveTab={setActiveTab}
      onRefresh={handleRefreshSignals}
      isRefreshing={isRefreshing}
      lastSyncTime={signalsData?.generated_at}
      triggerCount={signalsData?.total_triggers || 0}
      gateOpen={safeSignalsData.market_regime.gate_open}
    >
      {/* Dynamic Toast Feedback */}
      {toastMessage && (
        <div
          className={`fixed top-4 right-4 z-50 flex items-center gap-2.5 px-4 py-3 rounded-2xl shadow-2xl border text-xs font-bold font-sans backdrop-blur-xl transition-all ${
            toastMessage.type === 'success'
              ? 'bg-slate-950/95 text-emerald-300 border-emerald-500/40 shadow-[0_0_20px_rgba(0,255,157,0.25)]'
              : 'bg-slate-950/95 text-rose-300 border-rose-500/40 shadow-[0_0_20px_rgba(255,51,102,0.25)]'
          }`}
        >
          {toastMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-400" />
          )}
          <span>{toastMessage.text}</span>
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
          onRefreshHealth={loadData}
        />
      )}

      {/* Interactive Cloud Sync & Action Hub Modal */}
      <CloudSyncModal
        isOpen={isCloudModalOpen}
        onClose={() => setIsCloudModalOpen(false)}
        mode={cloudModalMode}
        lastSyncTime={signalsData?.generated_at}
        onRefreshData={loadData}
      />
    </AppLayout>
  );
};
export default App;
