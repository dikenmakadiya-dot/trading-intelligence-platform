import React, { useState, useMemo } from 'react';
import { ConsolidatedSignalsPayload, PositionItem } from '../types';
import { RadialGauge } from '../components/ui/RadialGauge';
import { GrowwLink } from '../components/ui/GrowwLink';
import { StrategyBadge } from '../components/ui/Badge';
import { Search, Briefcase, Sparkles, TrendingUp, AlertTriangle, CheckCircle2, ArrowUpRight, ArrowDownRight, RefreshCw } from 'lucide-react';

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
        sig.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        sig.industry.toLowerCase().includes(searchQuery.toLowerCase());

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
      {/* Top Banner & Regime Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Market Breadth & Gate Card */}
        <div className="glass-card rounded-2xl p-5 flex flex-col justify-between relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Market Regime &amp; Gate Filter
            </span>
            <span className="font-mono text-xs text-slate-500 tabular-nums">
              As of: {as_of_date || 'Today'}
            </span>
          </div>

          <RadialGauge
            percentage={market_regime?.breadth_pct || 0}
            gateOpen={market_regime?.gate_open || false}
            stocksAbove={market_regime?.stocks_above_ema50 || 0}
            totalStocks={market_regime?.total_stocks_evaluated || 500}
            statusLabel={market_regime?.status_label}
            size={230}
          />

          <div className="mt-3 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 text-center">
            {market_regime?.gate_open ? (
              <span className="text-emerald-400 flex items-center justify-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Breadth &ge; 50.0% — Fresh breakout entry orders permitted.
              </span>
            ) : (
              <span className="text-rose-400 flex items-center justify-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" />
                Defensive Cash Protection Active. New purchases throttled.
              </span>
            )}
          </div>
        </div>

        {/* Active Trade Slots Deck (5 Capacity) */}
        <div className="lg:col-span-2 glass-card rounded-2xl p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-trade-accent" />
              <span className="text-sm font-bold text-white">Active Portfolio Slots Deck</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-full bg-slate-800 text-sky-400 border border-slate-700 tabular-nums">
                {positions.length} / {totalSlots} Filled
              </span>
              {portfolio_summary?.total_unrealized_pnl_pct !== undefined && (
                <span className={`font-mono text-xs font-bold px-2 py-0.5 rounded-full tabular-nums ${
                  portfolio_summary.total_unrealized_pnl_pct >= 0
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                }`}>
                  Unrealized: {portfolio_summary.total_unrealized_pnl_pct >= 0 ? '+' : ''}{portfolio_summary.total_unrealized_pnl_pct.toFixed(2)}%
                </span>
              )}
            </div>
          </div>

          {/* Slots Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {positions.map((pos) => {
              const isProfit = (pos.unrealized_pnl_pct || 0) >= 0;
              return (
                <div
                  key={pos.id || `${pos.symbol}-${pos.entry_date}`}
                  className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono font-bold text-sm text-white">
                        {pos.symbol}
                      </span>
                      <StrategyBadge strategyId={pos.strategy_id} className="text-[10px] px-1.5 py-0" />
                    </div>
                    <GrowwLink url={pos.groww_chart_url} symbol={pos.symbol} variant="icon" />
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <div className="text-[10px] text-slate-400">Entry / LTP</div>
                      <div className="font-mono text-slate-200 tabular-nums">
                        ₹{(pos.entry_price || 0).toFixed(1)} &rarr; ₹{(pos.current_price || 0).toFixed(1)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] text-slate-400">Unrealized P&amp;L</div>
                      <div className={`font-mono font-bold tabular-nums flex items-center justify-end gap-0.5 ${
                        isProfit ? 'text-trade-bullish' : 'text-trade-bearish'
                      }`}>
                        {isProfit ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                        {isProfit ? '+' : ''}{(pos.unrealized_pnl_pct || 0).toFixed(2)}%
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span>Held: {pos.days_held || 0}d</span>
                    <span>SL: ₹{(pos.trailing_sl || 0).toFixed(1)}</span>
                  </div>
                </div>
              );
            })}

            {/* Empty capacity slots */}
            {Array.from({ length: emptySlotsCount }).map((_, idx) => (
              <div
                key={`empty-slot-${idx}`}
                className="p-4 rounded-xl border border-dashed border-slate-800 flex flex-col items-center justify-center text-center text-slate-600 space-y-1 min-h-[110px]"
              >
                <div className="w-6 h-6 rounded-full border border-dashed border-slate-700 flex items-center justify-center text-xs font-mono">
                  {positions.length + idx + 1}
                </div>
                <span className="text-xs font-medium text-slate-400">Available Cash Slot</span>
                <span className="text-[10px] text-slate-400">Ready for Day T+1 Trigger</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Actionable Fresh Breakout Signals Section */}
      <div className="glass-card rounded-2xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-trade-accent" />
            <div>
              <h2 className="text-base font-bold text-white leading-tight">
                Consolidated Fresh Breakout Signals
              </h2>
              <p className="text-xs text-slate-400">
                Actionable candidate stocks triggering technical breakout rules for Day T+1
              </p>
            </div>
          </div>

          {/* Search & Filter Controls */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search symbol, company..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-48 sm:w-56 pl-9 pr-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-400 transition-colors"
              />
            </div>

            <select
              value={strategyFilter}
              onChange={(e) => setStrategyFilter(e.target.value)}
              className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-300 focus:outline-none focus:border-sky-400 transition-colors"
            >
              <option value="all">All Strategies</option>
              <option value="rsi_52w">3-Day RSI + 52W</option>
              <option value="clean_candle">5Y Clean Breakout</option>
              <option value="gfs">GFS MTF RSI</option>
            </select>

            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-sky-500/20 text-sky-400 border border-slate-700 hover:border-sky-500/40 text-xs font-semibold transition-all disabled:opacity-50"
              title="Sync latest signals"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">{isRefreshing ? 'Syncing...' : 'Sync'}</span>
            </button>
          </div>
        </div>

        {/* Signals Table / Cards */}
        {filteredSignals.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-sm space-y-2">
            <TrendingUp className="w-8 h-8 text-slate-600 mx-auto" />
            <div>No breakout triggers found matching the current criteria.</div>
            <div className="text-xs text-slate-400">
              Use "Refresh Signals" above to check the latest cloud run.
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                  <th className="py-3 px-3">#</th>
                  <th className="py-3 px-3">Symbol &amp; Company</th>
                  <th className="py-3 px-3">Strategy</th>
                  <th className="py-3 px-3 text-right">Close Price</th>
                  <th className="py-3 px-3 text-right">Entry Trigger</th>
                  <th className="py-3 px-3 text-right">Initial SL</th>
                  <th className="py-3 px-3 text-right">Target</th>
                  <th className="py-3 px-3 text-center">Indicators</th>
                  <th className="py-3 px-3 text-center">Groww Chart</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {filteredSignals.map((sig, idx) => (
                  <tr
                    key={`${sig.strategy_id}-${sig.symbol}-${idx}`}
                    className="hover:bg-slate-900/50 transition-colors"
                  >
                    <td className="py-3 px-3 text-slate-400 tabular-nums">
                      {idx + 1}
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-sans font-bold text-sm text-white">
                        {sig.symbol}
                      </div>
                      <div className="font-sans text-[11px] text-slate-400 truncate max-w-[180px]">
                        {sig.company_name}
                      </div>
                    </td>
                    <td className="py-3 px-3 font-sans">
                      <StrategyBadge strategyId={sig.strategy_id} name={sig.strategy_name} />
                    </td>
                    <td className="py-3 px-3 text-right font-bold text-slate-200 tabular-nums">
                      ₹{(sig.close || sig.close_price || 0).toFixed(2)}
                    </td>
                    <td className="py-3 px-3 text-right text-sky-400 font-bold tabular-nums">
                      ₹{(sig.entry_trigger ?? 0).toFixed(2)}
                    </td>
                    <td className="py-3 px-3 text-right text-rose-400 tabular-nums">
                      ₹{(sig.trailing_sl ?? 0).toFixed(2)}
                    </td>
                    <td className="py-3 px-3 text-right text-emerald-400 tabular-nums">
                      {sig.target_price ? `₹${Number(sig.target_price).toFixed(2)}` : 'Trailing'}
                    </td>
                    <td className="py-3 px-3 text-center font-sans">
                      <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-400">
                        {sig.daily_rsi ? (
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-[10px]">
                            RSI: {sig.daily_rsi.toFixed(1)}
                          </span>
                        ) : null}
                        {sig.vol_ratio ? (
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-[10px] text-sky-400">
                            Vol: {sig.vol_ratio.toFixed(1)}x
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-center">
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
