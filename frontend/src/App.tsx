import React, { useState } from 'react';
import { AppLayout } from './components/layout/AppLayout';
import { ActiveTab } from './components/layout/MobileDock';
import { LiveTrackerView } from './views/LiveTrackerView';
import { MasterBacktestingHub } from './views/MasterBacktestingHub';
import { SystemHealth } from './views/SystemHealth';
import { CloudConnectModal } from './components/CloudConnectModal';
import { ConsolidatedSignalsPayload, BacktestDataPayload, SystemHealthData } from './types';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('live_tracker');
  const [signalsData] = useState<ConsolidatedSignalsPayload | null>(null);
  const [backtestData] = useState<BacktestDataPayload | null>(null);
  const [healthData] = useState<SystemHealthData | null>(null);
  const [syncTimestamp, setSyncTimestamp] = useState<string>('22-Sep-2026 23:25:00 IST');
  
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

  // Safe fallback signals payload for Phase 1 UI mockup inspection
  const safeSignalsData: ConsolidatedSignalsPayload = signalsData || {
    generated_at: '22-Sep-2026 23:25:00 IST',
    as_of_date: '22-Sep-2026',
    market_regime: {
      breadth_pct: 48.6,
      gate_open: true,
      status_label: 'FAVORABLE (EXPANSION REGIME)',
      total_stocks_evaluated: 750,
      stocks_above_ema50: 365
    },
    total_triggers: 6,
    all_signals_unified: [],
    portfolio_summary: {
      total_open_positions: 3,
      max_slots: 5,
      available_slots: 2,
      slots_label: '3 / 5 Slots Filled',
      positions: []
    },
    active_positions: []
  };

  const handleRefreshSignals = () => {
    setIsRefreshing(true);
    showToast('Refreshing Live Signal Tracker & Drift Matrix...', 'info', 1500);
    setTimeout(() => {
      setIsRefreshing(false);
      const now = new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' });
      setSyncTimestamp(`22-Sep-2026 ${now} IST`);
      showToast('Live Tracker & Trailing SL Monitor Refreshed!', 'success', 3500);
    }, 1000);
  };

  const handleRefreshBacktest = (strategyId: string) => {
    setIsRefreshingBacktest(true);
    showToast(`Simulating 5-Year Walk Forward for ${strategyId}...`, 'info', 1500);
    setTimeout(() => {
      setIsRefreshingBacktest(false);
      showToast('Audited Walk Forward Simulation Refreshed (WAL Verified)!', 'success', 3500);
    }, 1000);
  };

  const handleRefreshHealth = () => {
    setIsRefreshingHealth(true);
    showToast('Inspecting SQLite WAL & System Architecture...', 'info', 1500);
    setTimeout(() => {
      setIsRefreshingHealth(false);
      showToast('System Health & ACID Database Status: ALL GREEN', 'success', 3500);
    }, 1000);
  };

  return (
    <>
      <AppLayout
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onRefresh={handleRefreshSignals}
        isRefreshing={isRefreshing}
        lastSyncTime={syncTimestamp}
        triggerCount={safeSignalsData.total_triggers}
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

        {/* 3 Master Views */}
        {activeTab === 'live_tracker' && (
          <LiveTrackerView
            data={safeSignalsData}
            onRefresh={handleRefreshSignals}
            isRefreshing={isRefreshing}
            lastSyncTime={syncTimestamp}
            onNavigateToBacktest={() => setActiveTab('backtesting')}
          />
        )}

        {activeTab === 'backtesting' && (
          <MasterBacktestingHub
            backtestData={backtestData}
            onRefreshBacktest={handleRefreshBacktest}
            isRefreshingBacktest={isRefreshingBacktest}
          />
        )}

        {activeTab === 'system_health' && (
          <SystemHealth
            healthData={healthData}
            onRefreshHealth={handleRefreshHealth}
            isRefreshingHealth={isRefreshingHealth}
          />
        )}
      </AppLayout>

      {/* Cloud Connector Modal */}
      <CloudConnectModal
        isOpen={isCloudModalOpen}
        onClose={() => setIsCloudModalOpen(false)}
        onConnected={() => handleRefreshSignals()}
      />
    </>
  );
};
export default App;
