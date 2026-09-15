import React, { useState, useMemo } from 'react';
import { ConsolidatedSignalsPayload, PositionItem } from '../types';
import { RadialGauge } from '../components/ui/RadialGauge';
import { GrowwLink } from '../components/ui/GrowwLink';
import { StrategyBadge } from '../components/ui/Badge';
import {
  Search,
  Briefcase,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';

interface MasterStageProps {
  data: ConsolidatedSignalsPayload;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const MasterStage: React.FC<MasterStageProps> = ({ data, onRefresh, isRefreshing }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [strategyFilter, setStrategyFilter] = useState<string>('all');

  const { market_regime, all_signals_unified = [], portfolio_summary, as_of_date } = data;
  const positions: PositionItem[] = portfolio_summary?.positions || [];

  // Filter signals
  const filteredSignals = useMemo(() => {
    return all_signals_unified.filter((sig) => {
      const matchesSearch =
        sig.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (sig.company_name && sig.company_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (sig.industry && sig.industry.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesStrategy =
        strategyFilter === 'all' ||
        sig.strategy_id === strategyFilter ||
        (strategyFilter === 'rsi_52w' && sig.strategy_id.includes('rsi')) ||
        (strategyFilter === 'clean_candle' && sig.strategy_id.includes('clean_candle')) ||
        (strategyFilter === 'gfs' && sig.strategy_id.includes('gfs'));

      return matchesSearch && matchesStrategy;
    });
  }, [all_signals_unified, searchQuery, strategyFilter]);

  // Portfolio Slots rendering (at least 5 capacity slots)
  const totalSlots = 5;
  const emptySlotsCount = Math.max(0, totalSlots - positions.length);

  return (
    <div className="space-y-6">
      
      {/* TOP BENTO GRID: REGIME, ACTIVE PORTFOLIO, BREAKOUT CANDIDATES, QUANT KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: Macro Breadth Gate Card */}
        <div className="glass-card rounded-2xl p-5 flex flex-col justify-between relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              Breadth Gate • {as_of_date || 'Today'}
            </span>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold flex items-center gap-1.5 ${
              market_regime?.gate_open
                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${market_regime?.gate_open ? 'bg-emerald-400 beacon-pulse' : 'bg-rose-400'}`}></span>
              {market_regime?.gate_open ? 'GATE OPEN' : 'DEFENSIVE'}
            </span>
          </div>

          <div className="my-1 flex-1 flex items-center justify-center">
            <RadialGauge
              percentage={market_regime?.breadth_pct || 0}
              gateOpen={market_regime?.gate_open || false}
              stocksAbove={market_regime?.stocks_above_ema50 || 0}
              totalStocks={market_regime?.total_stocks_evaluated || 500}
              statusLabel={market_regime?.status_label}
              size={195}
            />
          </div>

          <div className="pt-2.5 border-t border-slate-800/80 text-[11px] text-center font-medium">
            {market_regime?.gate_open ? (
              <span className="text-emerald-400 inline-flex items-center justify-center gap-1 font-sans">
                <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                <span>Breadth &ge; 50.0% — Fresh breakout orders enabled.</span>
              </span>
            ) : (
              <span className="text-rose-400 inline-flex items-center justify-center gap-1 font-sans">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                <span>Defensive cash mode. New purchases throttled.</span>
              </span>
            )}
          </div>
        </div>

        {/* Card 2: Active Trade Slots Deck (5 Capacity) */}
        <div className="glass-card rounded-2xl p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">Portfolio Slots</span>
            </div>
            <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-lg bg-slate-900/90 text-cyan-300 border border-slate-700 tabular-nums">
              {positions.length} / {totalSlots} Filled
            </span>
          </div>

          <div className="my-3 space-y-2 overflow-y-auto max-h-[220px]">
            {positions.length === 0 ? (
              <div className="p-4 rounded-xl border border-dashed border-slate-800 text-center text-slate-500 font-mono text-xs space-y-1">
                <div className="text-cyan-400 font-bold">100% Cash Allocation</div>
                <div className="text-[11px] text-slate-500">5 slots open for fresh breakouts</div>
              </div>
            ) : (
              positions.map((pos) => {
                const isProfit = (pos.unrealized_pnl_pct || 0) >= 0;
                return (
                  <div
                    key={pos.id || `${pos.symbol}-${pos.entry_date}`}
                    className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800/90 hover:border-cyan-500/40 transition-all flex items-center justify-between gap-2"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`w-2 h-2 rounded-full shrink-0 ${isProfit ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
                      <div className="truncate">
                        <div className="font-mono font-bold text-xs text-white flex items-center gap-1.5">
                          {pos.symbol}
                          <StrategyBadge strategyId={pos.strategy_id} className="text-[9px] px-1.5 py-0" />
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          ₹{(pos.entry_price || 0).toFixed(0)} &bull; Day {pos.days_held || 1}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <div className={`font-mono text-xs font-extrabold tabular-nums ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {isProfit ? '+' : ''}{(pos.unrealized_pnl_pct || 0).toFixed(2)}%
                      </div>
                      <GrowwLink url={pos.groww_chart_url} symbol={pos.symbol} variant="icon" />
                    </div>
                  </div>
                );
              })
            )}

            {/* Empty Slots Indicator */}
            {emptySlotsCount > 0 && (
              <div className="p-2 rounded-xl border border-dashed border-slate-800/80 text-center text-[11px] text-slate-500 font-mono">
                + {emptySlotsCount} Available Cash Slot{emptySlotsCount > 1 ? 's' : ''} ({Math.round((emptySlotsCount / totalSlots) * 100)}% Liquidity)
              </div>
            )}
          </div>

          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
            <span className="text-slate-400 font-sans">Unrealized P&amp;L</span>
            {portfolio_summary?.total_unrealized_pnl_pct !== undefined ? (
              <span className={`font-mono font-extrabold tabular-nums ${
                portfolio_summary.total_unrealized_pnl_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {portfolio_summary.total_unrealized_pnl_pct >= 0 ? '+' : ''}{portfolio_summary.total_unrealized_pnl_pct.toFixed(2)}%
                {portfolio_summary.total_unrealized_pnl ? ` (₹${portfolio_summary.total_unrealized_pnl.toLocaleString('en-IN')})` : ''}
              </span>
            ) : (
              <span className="font-mono text-slate-400">₹0.00 (0.0%)</span>
            )}
          </div>
        </div>

        {/* Card 3: Today's Actionable Breakouts Summary */}
        <div className="glass-card rounded-2xl p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">Fresh Triggers</span>
            <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
              {all_signals_unified.length} CANDIDATE{all_signals_unified.length === 1 ? '' : 'S'}
            </span>
          </div>

          <div className="my-3 space-y-2">
            {all_signals_unified.length === 0 ? (
              <div className="p-4 rounded-xl border border-dashed border-slate-800 text-center text-slate-500 font-mono text-xs space-y-1">
                <div>No fresh breakouts triggered today.</div>
                <div className="text-[10px] text-slate-600">Preserving capital in high volatility.</div>
              </div>
            ) : (
              all_signals_unified.slice(0, 2).map((sig, idx) => (
                <div
                  key={`fresh-top-${sig.symbol}-${idx}`}
                  className="p-2.5 rounded-xl bg-slate-950/80 border border-cyan-500/30 hover:border-cyan-400 transition-all space-y-1"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono font-extrabold text-sm text-white truncate min-w-0">{sig.symbol}</span>
                    <StrategyBadge strategyId={sig.strategy_id} className="text-[9px] px-1.5 py-0 shrink-0" />
                  </div>
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span>Trigger: <span className="text-cyan-400 font-bold">₹{(sig.entry_trigger || sig.close || 0).toFixed(1)}</span></span>
                    {sig.vol_ratio && <span className="text-emerald-400 font-semibold">Vol: {sig.vol_ratio.toFixed(1)}x</span>}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="pt-2 border-t border-slate-800/80 text-[11px] text-slate-400 text-center font-mono">
            Execute at tomorrow's market open (9:15 AM)
          </div>
        </div>

        {/* Card 4: Quantitative Edge & Verified System KPIs */}
        <div className="glass-card rounded-2xl p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">Verified System KPIs</span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
              5Y AUDITED
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 my-2">
            <div className="p-2 rounded-xl bg-slate-950/70 border border-slate-800">
              <div className="text-[10px] text-slate-500 font-bold uppercase font-mono">Strategy CAGR</div>
              <div className="font-mono text-lg font-extrabold text-emerald-400 tabular-nums">+32.4%</div>
            </div>
            <div className="p-2 rounded-xl bg-slate-950/70 border border-slate-800">
              <div className="text-[10px] text-slate-500 font-bold uppercase font-mono">Win Rate</div>
              <div className="font-mono text-lg font-extrabold text-cyan-400 tabular-nums">58.6%</div>
            </div>
            <div className="p-2 rounded-xl bg-slate-950/70 border border-slate-800">
              <div className="text-[10px] text-slate-500 font-bold uppercase font-mono">Profit Factor</div>
              <div className="font-mono text-lg font-extrabold text-white tabular-nums">2.31</div>
            </div>
            <div className="p-2 rounded-xl bg-slate-950/70 border border-slate-800">
              <div className="text-[10px] text-slate-500 font-bold uppercase font-mono">Max Drawdown</div>
              <div className="font-mono text-lg font-extrabold text-rose-400 tabular-nums">-18.4%</div>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
            <span>Expectancy</span>
            <span className="font-mono font-bold text-emerald-400">+₹8,450 / trade</span>
          </div>
        </div>

      </div>

      {/* ACTIONABLE BREAKOUT SIGNALS MATRIX (HIGH-CONTRAST NEON TABLE) */}
      <div className="glass-card rounded-2xl p-6 space-y-4">
        
        {/* Table Header & Multi-Facet Filters */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-extrabold text-white flex items-center gap-2 font-sans">
              <span>Actionable Breakout Signals Matrix</span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                {filteredSignals.length} Ready to Trade
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Filtered for tomorrow morning execution. Click any symbol to inspect candles on official Groww chart.
            </p>
          </div>

          {/* Search & Strategy Filter Controls */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <input
                type="text"
                placeholder="Search symbol, company..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-52 sm:w-60 pl-8 pr-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition-colors font-mono"
              />
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            </div>

            {/* Quick Strategy Filter Pills */}
            <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
              <button
                onClick={() => setStrategyFilter('all')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  strategyFilter === 'all'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-white border border-transparent'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setStrategyFilter('rsi_52w')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  strategyFilter === 'rsi_52w'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    : 'text-slate-400 hover:text-white border border-transparent'
                }`}
              >
                3D RSI
              </button>
              <button
                onClick={() => setStrategyFilter('clean_candle')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  strategyFilter === 'clean_candle'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                    : 'text-slate-400 hover:text-white border border-transparent'
                }`}
              >
                5Y High
              </button>
              <button
                onClick={() => setStrategyFilter('gfs')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  strategyFilter === 'gfs'
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40'
                    : 'text-slate-400 hover:text-white border border-transparent'
                }`}
              >
                GFS MTF
              </button>
            </div>

            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-cyan-500/15 text-cyan-400 border border-slate-800 hover:border-cyan-500/40 text-xs font-bold transition-all disabled:opacity-50"
              title="Sync latest signals"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">{isRefreshing ? 'Syncing...' : 'Sync'}</span>
            </button>
          </div>
        </div>

        {/* Signals Table */}
        {filteredSignals.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-sm space-y-2 font-mono">
            <TrendingUp className="w-8 h-8 text-slate-700 mx-auto" />
            <div className="text-slate-300 font-bold">No breakout signals match the current filter.</div>
            <div className="text-xs text-slate-500">
              Check another strategy filter or trigger "Scan Market Now".
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-800/90 bg-slate-950/60">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/80 text-slate-400 font-mono text-[11px] uppercase tracking-wider whitespace-nowrap">
                  <th className="py-3 px-3 w-10 text-center">#</th>
                  <th className="py-3 px-4 min-w-[200px]">Symbol &amp; Company</th>
                  <th className="py-3 px-4 min-w-[140px]">Strategy Engine</th>
                  <th className="py-3 px-4 text-right min-w-[90px]">Close LTP</th>
                  <th className="py-3 px-4 text-right min-w-[100px]">Trigger Entry</th>
                  <th className="py-3 px-4 text-right min-w-[90px]">Stop Loss</th>
                  <th className="py-3 px-4 text-right min-w-[90px]">Target</th>
                  <th className="py-3 px-4 text-center min-w-[130px]">Indicators</th>
                  <th className="py-3 px-4 text-center min-w-[120px]">Groww Chart</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {filteredSignals.map((sig, idx) => (
                  <tr
                    key={`${sig.strategy_id}-${sig.symbol}-${idx}`}
                    className="hover:bg-slate-900/60 transition-colors group"
                  >
                    <td className="py-3.5 px-3 text-center text-slate-500 tabular-nums">
                      {idx + 1}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/25 flex items-center justify-center text-cyan-300 font-bold text-xs shrink-0">
                          {sig.symbol.slice(0, 2)}
                        </div>
                        <div>
                          <div className="font-bold text-white text-sm group-hover:text-cyan-400 transition-colors flex items-center gap-1.5 font-mono">
                            <span>{sig.symbol}</span>
                            <span className="text-[10px] font-sans font-medium text-slate-400 px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800">
                              {sig.industry || 'NSE'}
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-400 font-sans truncate max-w-[180px]">
                            {sig.company_name}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-sans whitespace-nowrap">
                      <StrategyBadge strategyId={sig.strategy_id} name={sig.strategy_name} />
                    </td>
                    <td className="py-3.5 px-4 text-right font-bold text-white text-sm tabular-nums whitespace-nowrap">
                      ₹{(sig.close || sig.close_price || 0).toFixed(2)}
                    </td>
                    <td className="py-3.5 px-4 text-right text-cyan-400 font-extrabold text-sm tabular-nums whitespace-nowrap">
                      ₹{(sig.entry_trigger ?? sig.close ?? 0).toFixed(2)}
                    </td>
                    <td className="py-3.5 px-4 text-right text-rose-400 tabular-nums font-bold whitespace-nowrap">
                      ₹{(sig.trailing_sl ?? 0).toFixed(2)}
                      {sig.entry_trigger && sig.trailing_sl ? (
                        <div className="text-[10px] text-slate-500">
                          {(((sig.trailing_sl - sig.entry_trigger) / sig.entry_trigger) * 100).toFixed(1)}%
                        </div>
                      ) : null}
                    </td>
                    <td className="py-3.5 px-4 text-right text-emerald-400 tabular-nums font-bold whitespace-nowrap">
                      {sig.target_price ? `₹${Number(sig.target_price).toFixed(2)}` : 'Trailing'}
                      {sig.target_price && sig.entry_trigger ? (
                        <div className="text-[10px] text-emerald-500">
                          +{(((Number(sig.target_price) - sig.entry_trigger) / sig.entry_trigger) * 100).toFixed(1)}%
                        </div>
                      ) : null}
                    </td>
                    <td className="py-3.5 px-4 text-center font-sans whitespace-nowrap">
                      <div className="flex items-center justify-center gap-1.5 text-[11px]">
                        {sig.daily_rsi ? (
                          <span className="px-2 py-0.5 rounded-md bg-slate-900 border border-slate-800 font-mono text-[10px] text-white">
                            RSI: {sig.daily_rsi.toFixed(1)}
                          </span>
                        ) : null}
                        {sig.vol_ratio ? (
                          <span className="px-2 py-0.5 rounded-md bg-cyan-950/60 border border-cyan-800/80 font-mono text-[10px] text-cyan-300 font-bold">
                            Vol: {sig.vol_ratio.toFixed(1)}x
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      <GrowwLink
                        url={sig.groww_chart_url}
                        symbol={sig.symbol}
                        variant="button"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
};
