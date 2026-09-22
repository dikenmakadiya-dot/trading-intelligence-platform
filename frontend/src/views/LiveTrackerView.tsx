import React, { useState, useMemo } from 'react';
import { ConsolidatedSignalsPayload } from '../types';
import { mockLiveVsBacktestComparison, mockLiveSignalsTracker } from '../mocks/mockData';
import { GrowwLink } from '../components/ui/GrowwLink';
import {
  ShieldCheck,
  ShieldAlert,
  Search,
  Flame,
  Scale,
  Compass,
  Layers,
  RotateCcw,
  TrendingUp
} from 'lucide-react';

interface LiveTrackerViewProps {
  data: ConsolidatedSignalsPayload;
  onRefresh: () => void;
  onFastSync?: () => void;
  isRefreshing: boolean;
  lastSyncTime?: string;
  onNavigateToBacktest?: (stratId: string) => void;
}

export const LiveTrackerView: React.FC<LiveTrackerViewProps> = ({
  data,
  onRefresh,
  isRefreshing,
  lastSyncTime,
  onNavigateToBacktest
}) => {
  const [selectedStrategyFilter, setSelectedStrategyFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [driftCategory, setDriftCategory] = useState<'all' | 'returns' | 'risk' | 'consistency'>('all');

  // Filter comparison drift metrics
  const filteredMetrics = useMemo(() => {
    if (driftCategory === 'all') return mockLiveVsBacktestComparison;
    return mockLiveVsBacktestComparison.filter((m) => m.category === driftCategory);
  }, [driftCategory]);

  // Filter running signals
  const filteredRunningSignals = useMemo(() => {
    return mockLiveSignalsTracker.filter((item) => {
      const matchStrat = selectedStrategyFilter === 'all' || item.strategy_id === selectedStrategyFilter;
      const matchQuery =
        item.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.company_name.toLowerCase().includes(searchQuery.toLowerCase());
      return matchStrat && matchQuery;
    });
  }, [selectedStrategyFilter, searchQuery]);

  // Safe market regime values
  const regime = data.market_regime || {
    breadth_pct: 34.0,
    gate_open: false,
    status_label: 'DEFENSIVE (CASH PROTECTION)',
    total_stocks_evaluated: 500,
    stocks_above_ema50: 170
  };

  const portfolio = data.portfolio_summary || {
    total_open_positions: 3,
    max_slots: 5,
    available_slots: 2,
    slots_label: '3 / 5 Slots Filled',
    positions: []
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300 w-full">
      {/* 0. Top Control & Synchronization Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 sm:p-5 rounded-2xl bg-slate-900/90 border border-slate-800/80 shadow-2xl backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-black tracking-tight text-white">
                Live Portfolio & Forward Signal Tracker
              </h1>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                PHASE 1 MOCKUP
              </span>
            </div>
            <p className="text-xs text-slate-400 font-sans mt-0.5">
              Synced: <span className="font-mono text-slate-300">{lastSyncTime || '22-Sep-2026 23:25:00 IST'}</span> • Real-time Trailing SL Progression & Drift Matrix
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {onNavigateToBacktest && (
            <button
              onClick={() => onNavigateToBacktest('rsi_52w_breakout')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-cyan-500/40 text-xs font-bold font-sans text-slate-300 hover:text-white transition-all active:scale-95"
            >
              <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
              <span>Backtesting Hub</span>
            </button>
          )}

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500/20 to-emerald-500/20 hover:from-cyan-500/30 hover:to-emerald-500/30 border border-cyan-500/40 text-cyan-300 font-sans text-xs font-bold transition-all shadow-lg active:scale-95 disabled:opacity-50"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Syncing Signals...' : 'Refresh Tracker'}</span>
          </button>
        </div>
      </div>

      {/* 1. Header Section: Live Regime Gate & Portfolio Slots */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        {/* Market Regime Card (7 cols) */}
        <div className="xl:col-span-7 p-4 sm:p-5 rounded-2xl bg-gradient-to-br from-slate-900/90 via-slate-950/95 to-slate-900/90 border border-slate-800/80 shadow-2xl relative overflow-hidden backdrop-blur-xl">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2.5">
              <span className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <Compass className="w-5 h-5 animate-spin-slow" />
              </span>
              <div>
                <h1 className="text-base sm:text-lg font-black tracking-tight text-white flex items-center gap-2">
                  <span>Macro Regime Gate</span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                    NIFTY 500 BREADTH
                  </span>
                </h1>
                <p className="text-xs text-slate-400 font-sans">
                  50-EMA Breadth filter controlling all fresh breakout deployment
                </p>
              </div>
            </div>

            {/* Gate Status Pill */}
            <div className={`px-3 py-1.5 rounded-xl border flex items-center gap-2 font-mono text-xs font-black shadow-lg ${
              regime.gate_open
                ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400 shadow-emerald-950/40'
                : 'bg-rose-500/15 border-rose-500/40 text-rose-400 shadow-rose-950/40'
            }`}>
              {regime.gate_open ? (
                <>
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>GATE OPEN (RISK-ON)</span>
                </>
              ) : (
                <>
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                  <span>GATE CLOSED (PROTECT CASH)</span>
                </>
              )}
            </div>
          </div>

          {/* Breadth Progress Bar & Metrics */}
          <div className="space-y-2 mt-4 pt-3 border-t border-slate-800/70">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-slate-400">Breadth Ratio:</span>
              <span className="font-bold text-white">
                {regime.stocks_above_ema50 || 170} / {regime.total_stocks_evaluated || 500} stocks ({regime.breadth_pct?.toFixed(1) || '34.0'}%)
              </span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-700/50">
              <div
                className={`h-full rounded-full transition-all duration-700 ${
                  regime.gate_open
                    ? 'bg-gradient-to-r from-emerald-500 to-cyan-400 shadow-[0_0_10px_rgba(0,255,157,0.5)]'
                    : 'bg-gradient-to-r from-rose-500 to-amber-500 shadow-[0_0_10px_rgba(255,51,102,0.5)]'
                }`}
                style={{ width: `${Math.min(100, Math.max(5, regime.breadth_pct || 34))}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0% Defensive</span>
              <span className="text-amber-400/90 font-bold">40% Threshold</span>
              <span>100% Aggressive</span>
            </div>
          </div>
        </div>

        {/* Portfolio 5-Slot Allocation Deck (5 cols) */}
        <div className="xl:col-span-5 p-4 sm:p-5 rounded-2xl bg-gradient-to-br from-slate-900/90 via-slate-950/95 to-slate-900/90 border border-slate-800/80 shadow-2xl backdrop-blur-xl flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
                <Layers className="w-5 h-5" />
              </span>
              <div>
                <h2 className="text-sm font-bold text-white tracking-tight">Active Portfolio Slots</h2>
                <p className="text-[11px] text-slate-400 font-mono">Max 5 Concurrent Risk Buckets (20% Each)</p>
              </div>
            </div>
            <span className="text-xs font-mono font-black px-2.5 py-1 rounded-xl bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
              {portfolio.slots_label || '3 / 5 Filled'}
            </span>
          </div>

          {/* 5 Visual Slot Boxes */}
          <div className="grid grid-cols-5 gap-2 my-2">
            {[0, 1, 2, 3, 4].map((idx) => {
              const isFilled = idx < (portfolio.total_open_positions || 3);
              const symbolNames = ['YATHARTH', 'DIXON', 'TRENT', 'AVAILABLE', 'AVAILABLE'];
              const currentPnl = ['+3.8%', '+5.9%', '+6.1%', '--', '--'];

              return (
                <div
                  key={idx}
                  className={`p-2.5 rounded-xl border text-center transition-all ${
                    isFilled
                      ? 'bg-slate-900/90 border-cyan-500/30 text-white shadow-md shadow-cyan-950/30'
                      : 'bg-slate-950/40 border-dashed border-slate-800 text-slate-500'
                  }`}
                >
                  <div className="text-[9px] font-mono text-slate-400 uppercase">Slot {idx + 1}</div>
                  <div className="text-[11px] font-bold font-sans mt-0.5 truncate">
                    {symbolNames[idx]}
                  </div>
                  <div className={`text-[10px] font-mono font-bold mt-1 ${
                    isFilled ? 'text-emerald-400' : 'text-slate-600'
                  }`}>
                    {currentPnl[idx]}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-2 border-t border-slate-800/70">
            <span>Available Capacity: <strong className="text-white">2 Slots (40%)</strong></span>
            <span>Allocated Capital: <strong className="text-cyan-300">₹6,00,000 / ₹10,00,000</strong></span>
          </div>
        </div>
      </div>

      {/* 2. CORE REQUIREMENT: Live vs. Backtest Comparison & Performance Drift Matrix */}
      <div className="p-5 sm:p-6 rounded-3xl bg-slate-900/80 border border-cyan-500/30 shadow-2xl relative overflow-hidden backdrop-blur-xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none"></div>

        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                <Scale className="w-4 h-4" />
              </span>
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-cyan-400">
                Statistical Edge Verification Engine
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-black tracking-tight text-white flex items-center gap-2">
              <span>Live vs. Backtest Performance Drift</span>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                EDGE ALIGNED
              </span>
            </h2>
            <p className="text-xs text-slate-400 font-sans mt-0.5">
              Side-by-side empirical KPI benchmarking comparing real-time forward tracking against 5-year historical backtest baselines.
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 bg-slate-950/80 p-1 rounded-xl border border-slate-800 shrink-0">
            {(['all', 'returns', 'risk', 'consistency'] as const).map((cat) => (
              <button
                key={cat}
                onClick={() => setDriftCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold font-sans transition-all capitalize ${
                  driftCategory === cat
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {cat === 'all' ? 'All Metrics' : cat}
              </button>
            ))}
          </div>
        </div>

        {/* Comparison Metric Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {filteredMetrics.map((m, idx) => {
            const isOutperforming = m.status === 'OUTPERFORMING';
            const isAligned = m.status === 'ALIGNED';
            const isNormalRange = m.status === 'NORMAL_RANGE';

            return (
              <div
                key={idx}
                className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800/90 hover:border-cyan-500/40 transition-all group flex flex-col justify-between shadow-inner relative"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-slate-300 font-sans group-hover:text-cyan-300 transition-colors">
                      {m.metric_name}
                    </span>
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                      isOutperforming
                        ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                        : isAligned
                        ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                        : isNormalRange
                        ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                        : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                    }`}>
                      {m.status}
                    </span>
                  </div>

                  {/* Dual Values Comparison */}
                  <div className="grid grid-cols-2 gap-2 my-3 p-2.5 rounded-xl bg-slate-900/80 border border-slate-800/70">
                    <div>
                      <div className="text-[10px] font-mono text-slate-400 uppercase">5Y Backtest</div>
                      <div className="text-sm font-black font-mono text-slate-200 mt-0.5">
                        {m.backtest_value}
                      </div>
                    </div>
                    <div className="border-l border-slate-800 pl-2">
                      <div className="text-[10px] font-mono text-cyan-400 uppercase flex items-center gap-1">
                        <span>Live Forward</span>
                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>
                      </div>
                      <div className="text-sm font-black font-mono text-white mt-0.5">
                        {m.live_value}
                      </div>
                    </div>
                  </div>

                  {/* Variance Delta */}
                  <div className="flex items-center justify-between text-xs font-mono font-bold mb-2">
                    <span className="text-slate-400 text-[11px]">Variance Delta:</span>
                    <span className={
                      isOutperforming
                        ? 'text-emerald-400'
                        : isAligned
                        ? 'text-cyan-300'
                        : isNormalRange
                        ? 'text-amber-300'
                        : 'text-rose-400'
                    }>
                      {m.variance_label}
                    </span>
                  </div>
                </div>

                {/* Interpretation Note */}
                <p className="text-[11px] text-slate-400 font-sans leading-relaxed pt-2 border-t border-slate-900">
                  {m.interpretation}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Live Running Signals & Real-Time Trailing Stop-Loss Progress */}
      <div className="p-5 sm:p-6 rounded-3xl bg-slate-900/80 border border-slate-800/80 shadow-2xl backdrop-blur-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                <Flame className="w-4 h-4" />
              </span>
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-cyan-400">
                Active Execution Track
              </span>
            </div>
            <h2 className="text-base sm:text-lg font-black tracking-tight text-white flex items-center gap-2">
              <span>Live Signal Tracker & Trailing Stop-Loss Monitor</span>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                {filteredRunningSignals.length} POSITIONS
              </span>
            </h2>
            <p className="text-xs text-slate-400 font-sans">
              Daily forward tracking of live generated signals with dynamic ATR trailing stops, MTM returns, and Groww charts.
            </p>
          </div>

          {/* Strategy Filter and Search Controls */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Strategy Select Filter */}
            <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
              {[
                { id: 'all', label: 'All Strategies' },
                { id: 'rsi_52w_breakout', label: '3D-RSI' },
                { id: 'clean_candle_5y', label: '5Y Clean' },
                { id: 'gfs_mtf_rsi', label: 'GFS MTF' }
              ].map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedStrategyFilter(s.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold font-sans transition-all ${
                    selectedStrategyFilter === s.id
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search symbol..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 w-44 font-sans"
              />
            </div>
          </div>
        </div>

        {/* Signals Table */}
        <div className="overflow-x-auto rounded-2xl border border-slate-800/80 bg-slate-950/60">
          <table className="w-full text-left text-xs font-sans">
            <thead className="bg-slate-900/90 text-slate-400 font-mono text-[10px] uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Symbol / Company</th>
                <th className="py-3 px-3">Strategy</th>
                <th className="py-3 px-3">Signal Date</th>
                <th className="py-3 px-3 text-right">Trigger (₹)</th>
                <th className="py-3 px-3 text-right">LTP (₹)</th>
                <th className="py-3 px-3 text-right">Trailing SL</th>
                <th className="py-3 px-3 text-center">Distance to SL</th>
                <th className="py-3 px-3 text-right">MTM PnL</th>
                <th className="py-3 px-3 text-center">Held</th>
                <th className="py-3 px-3 text-center">Status</th>
                <th className="py-3 px-4 text-right">Chart</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredRunningSignals.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-8 text-center text-slate-500 font-sans">
                    No active positions matching current filter.
                  </td>
                </tr>
              ) : (
                filteredRunningSignals.map((item) => {
                  const isProfit = item.mtm_pnl_pct >= 0;

                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-900/50 transition-colors group"
                    >
                      {/* Symbol / Company */}
                      <td className="py-3 px-4">
                        <div className="font-bold text-white font-sans text-sm flex items-center gap-2">
                          <span>{item.symbol}</span>
                          <span className="text-[10px] font-mono font-normal text-slate-500">
                            {item.id}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 font-sans truncate max-w-xs">
                          {item.company_name}
                        </div>
                      </td>

                      {/* Strategy */}
                      <td className="py-3 px-3 font-sans text-[11px]">
                        <span className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700 font-semibold whitespace-nowrap">
                          {item.strategy_name}
                        </span>
                      </td>

                      {/* Signal Date */}
                      <td className="py-3 px-3 text-slate-400 text-xs">
                        {item.signal_date}
                      </td>

                      {/* Trigger Price */}
                      <td className="py-3 px-3 text-right font-bold text-slate-300">
                        ₹{item.entry_trigger.toFixed(2)}
                      </td>

                      {/* Current LTP */}
                      <td className="py-3 px-3 text-right font-bold text-white">
                        ₹{item.current_price.toFixed(2)}
                      </td>

                      {/* Trailing SL */}
                      <td className="py-3 px-3 text-right">
                        <div className="font-bold text-amber-400">
                          ₹{item.trailing_sl.toFixed(2)}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          Init: ₹{item.initial_sl.toFixed(2)}
                        </div>
                      </td>

                      {/* Distance to SL Gauge */}
                      <td className="py-3 px-3 text-center">
                        <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-bold text-[11px]">
                          {item.distance_to_sl_pct.toFixed(1)}% safe
                        </span>
                      </td>

                      {/* MTM PnL */}
                      <td className="py-3 px-3 text-right">
                        <span className={`px-2 py-1 rounded-lg font-black text-xs inline-flex items-center gap-1 ${
                          isProfit
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                            : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                        }`}>
                          {isProfit ? '+' : ''}{item.mtm_pnl_pct.toFixed(2)}%
                        </span>
                      </td>

                      {/* Holding Days */}
                      <td className="py-3 px-3 text-center text-slate-400 font-sans text-xs">
                        {item.holding_days} d
                      </td>

                      {/* Status */}
                      <td className="py-3 px-3 text-center">
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold font-mono border ${
                          item.status === 'TRAILING_ACTIVE'
                            ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                            : item.status === 'TARGET_REACHED'
                            ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                            : item.status === 'PENDING_TRIGGER'
                            ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}>
                          {item.status.replace('_', ' ')}
                        </span>
                      </td>

                      {/* Groww Link */}
                      <td className="py-3 px-4 text-right">
                        <GrowwLink
                          symbol={item.symbol}
                          url={item.groww_chart_url}
                          variant="compact"
                        />
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
export default LiveTrackerView;
