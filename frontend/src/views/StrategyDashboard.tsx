import React, { useState, useMemo } from 'react';
import { BacktestDataPayload, StrategyKPI, BacktestTrade } from '../types';
import { MetricCard } from '../components/ui/MetricCard';
import { EquityCurveChart } from '../components/ui/EquityCurveChart';
import { GrowwLink } from '../components/ui/GrowwLink';
import {
  TrendingUp,
  RotateCcw,
  Search,
  ArrowUpDown,
  DollarSign,
  Percent,
  Activity,
  Award,
  ShieldAlert,
  Compass,
  CheckCircle2,
  XCircle
} from 'lucide-react';

interface StrategyDashboardProps {
  initialStrategyId: string;
  backtestData: BacktestDataPayload | null;
  onRefreshBacktest: (strategyId: string) => void;
  isRefreshingBacktest: boolean;
}

export const StrategyDashboard: React.FC<StrategyDashboardProps> = ({
  initialStrategyId,
  backtestData,
  onRefreshBacktest,
  isRefreshingBacktest
}) => {
  const [activeStrategy, setActiveStrategy] = useState<string>(initialStrategyId);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<keyof BacktestTrade>('exit_date');
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  // Sync state if initial prop changes
  React.useEffect(() => {
    setActiveStrategy(initialStrategyId);
  }, [initialStrategyId]);

  const strategies = [
    { id: 'rsi_52w_breakout', name: '3-Day RSI UP + 52W High', short: '3D-RSI' },
    { id: 'clean_candle_5y', name: '5Y High Clean Breakout', short: '5Y Clean' },
    { id: 'gfs_mtf_rsi', name: 'GFS Multi-Timeframe RSI', short: 'GFS MTF' }
  ];

  const currentKpiData = backtestData?.kpis?.[activeStrategy];
  const kpis: StrategyKPI = currentKpiData?.kpis || {
    initial_capital: 1000000,
    final_equity: 1000000,
    total_pnl: 0,
    cagr_pct: 0,
    max_drawdown_pct: 0,
    win_rate_pct: 0,
    profit_factor: 0,
    total_trades: 0
  };

  // Filter and sort trades
  const trades: BacktestTrade[] = useMemo(() => {
    const raw = (backtestData?.trades || []).filter(
      (t) => !t.strategy_id || t.strategy_id === activeStrategy
    );

    const filtered = raw.filter((t) => {
      return (
        t.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (t.exit_reason && t.exit_reason.toLowerCase().includes(searchQuery.toLowerCase()))
      );
    });

    return filtered.sort((a, b) => {
      const valA = a[sortField];
      const valB = b[sortField];
      if (valA === undefined || valB === undefined) return 0;
      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [backtestData?.trades, activeStrategy, searchQuery, sortField, sortAsc]);

  const toggleSort = (field: keyof BacktestTrade) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Strategy Switcher Tabs & Backtest Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-card p-4 rounded-2xl">
        {/* Strategy Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-900/80 rounded-xl border border-slate-800">
          {strategies.map((strat) => {
            const isActive = activeStrategy === strat.id;
            return (
              <button
                key={strat.id}
                onClick={() => setActiveStrategy(strat.id)}
                className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all ${
                  isActive
                    ? 'bg-sky-500/20 text-trade-accent border border-sky-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <span>{strat.name}</span>
              </button>
            );
          })}
        </div>

        {/* 1-Tap Refresh Backtest Button */}
        <button
          onClick={() => onRefreshBacktest(activeStrategy)}
          disabled={isRefreshingBacktest}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 hover:text-sky-300 border border-sky-500/30 hover:border-sky-400 active:scale-95 transition-all shadow-sm disabled:opacity-50"
        >
          <RotateCcw className={`w-3.5 h-3.5 ${isRefreshingBacktest ? 'animate-spin' : ''}`} />
          <span>{isRefreshingBacktest ? 'Simulating Trades...' : 'Refresh Backtest'}</span>
        </button>
      </div>

      {/* 8-Metric Institutional KPI Scorecard */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <MetricCard
          label="Initial Capital"
          value={`₹${(kpis.initial_capital / 100000).toFixed(2)}L`}
          subtext="Base Allocation"
          icon={<DollarSign className="w-4 h-4" />}
        />
        <MetricCard
          label="Final Equity"
          value={`₹${(kpis.final_equity / 100000).toFixed(2)}L`}
          subtext={`Net P&L: ₹${((kpis.total_pnl || 0) / 100000).toFixed(2)}L`}
          trend={kpis.total_pnl >= 0 ? 'bullish' : 'bearish'}
          icon={<TrendingUp className="w-4 h-4" />}
          highlight
        />
        <MetricCard
          label="Net CAGR"
          value={`${(kpis.cagr_pct || 0).toFixed(1)}%`}
          subtext="Compounded Annual Growth"
          trend="bullish"
          icon={<Percent className="w-4 h-4" />}
        />
        <MetricCard
          label="Max Drawdown"
          value={`-${Math.abs(kpis.max_drawdown_pct || 0).toFixed(1)}%`}
          subtext="Peak-to-Trough Risk"
          trend="bearish"
          icon={<ShieldAlert className="w-4 h-4" />}
        />
        <MetricCard
          label="Win Rate"
          value={`${(kpis.win_rate_pct || 0).toFixed(1)}%`}
          subtext={`${kpis.win_trades || 0} Wins / ${kpis.loss_trades || 0} Losses`}
          icon={<Award className="w-4 h-4" />}
        />
        <MetricCard
          label="Profit Factor"
          value={(kpis.profit_factor || 0).toFixed(2)}
          subtext="Gross Win / Gross Loss"
          trend={(kpis.profit_factor || 0) >= 1.5 ? 'bullish' : 'neutral'}
          icon={<Activity className="w-4 h-4" />}
        />
        <MetricCard
          label="Realized R:R"
          value={`${(kpis.realized_rr || 0).toFixed(2)} : 1`}
          subtext="Risk-to-Reward Ratio"
          icon={<Compass className="w-4 h-4" />}
        />
        <MetricCard
          label="Expectancy"
          value={`₹${(kpis.expectancy_amt || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          subtext={`Avg +${(kpis.expectancy_pct || 0).toFixed(2)}% / Trade`}
          trend={(kpis.expectancy_amt || 0) >= 0 ? 'bullish' : 'bearish'}
          icon={<DollarSign className="w-4 h-4" />}
        />
      </div>

      {/* Equity Curve & Underwater Drawdown Chart */}
      <div className="glass-card rounded-2xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-trade-accent" />
            <h3 className="text-sm font-bold text-white">
              Historical Equity Growth &amp; Underwater Drawdown
            </h3>
          </div>
          <span className="font-mono text-xs text-slate-400 tabular-nums">
            {backtestData?.equity_curve?.length || 0} Daily Points
          </span>
        </div>

        <EquityCurveChart data={backtestData?.equity_curve || []} height={320} />
      </div>

      {/* Audited Historical Trade Log */}
      <div className="glass-card rounded-2xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-white">
              Audited Historical Trade Log
            </h3>
            <p className="text-xs text-slate-400">
              Complete trade executions with holding days, exit reason, and 1-tap Groww chart links
            </p>
          </div>

          {/* Search bar */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search symbol, exit reason..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-56 pl-9 pr-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-400 transition-colors"
            />
          </div>
        </div>

        {/* Trade Log Table */}
        {trades.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-sm">
            No historical trades match your search.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                  <th className="py-2.5 px-3">Symbol</th>
                  <th
                    className="py-2.5 px-3 cursor-pointer hover:text-white"
                    onClick={() => toggleSort('entry_date')}
                  >
                    <div className="flex items-center gap-1">
                      <span>Entry Date</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="py-2.5 px-3 text-right">Entry Price</th>
                  <th
                    className="py-2.5 px-3 cursor-pointer hover:text-white"
                    onClick={() => toggleSort('exit_date')}
                  >
                    <div className="flex items-center gap-1">
                      <span>Exit Date</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="py-2.5 px-3 text-right">Exit Price</th>
                  <th
                    className="py-2.5 px-3 text-right cursor-pointer hover:text-white"
                    onClick={() => toggleSort('net_return_pct')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      <span>Return %</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="py-2.5 px-3 text-right">P&amp;L (₹)</th>
                  <th
                    className="py-2.5 px-3 text-center cursor-pointer hover:text-white"
                    onClick={() => toggleSort('holding_days')}
                  >
                    <div className="flex items-center justify-center gap-1">
                      <span>Hold (d)</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="py-2.5 px-3">Exit Reason</th>
                  <th className="py-2.5 px-3 text-center">Groww Chart</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {trades.slice(0, 150).map((t, idx) => {
                  const isWin = (t.net_return_pct || 0) >= 0;
                  return (
                    <tr key={`${t.symbol}-${t.entry_date}-${idx}`} className="hover:bg-slate-900/50 transition-colors">
                      <td className="py-2.5 px-3 font-sans font-bold text-white">
                        {t.symbol}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400 tabular-nums">
                        {t.entry_date}
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-200 tabular-nums">
                        ₹{t.entry_price.toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400 tabular-nums">
                        {t.exit_date}
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-200 tabular-nums">
                        ₹{t.exit_price.toFixed(2)}
                      </td>
                      <td className={`py-2.5 px-3 text-right font-bold tabular-nums ${
                        isWin ? 'text-trade-bullish' : 'text-trade-bearish'
                      }`}>
                        {isWin ? '+' : ''}{t.net_return_pct.toFixed(2)}%
                      </td>
                      <td className={`py-2.5 px-3 text-right font-bold tabular-nums ${
                        (t.pnl_amount || 0) >= 0 ? 'text-trade-bullish' : 'text-trade-bearish'
                      }`}>
                        {(t.pnl_amount || 0) >= 0 ? '+' : ''}₹{Math.round(t.pnl_amount || 0).toLocaleString('en-IN')}
                      </td>
                      <td className="py-2.5 px-3 text-center text-slate-400 tabular-nums">
                        {t.holding_days}
                      </td>
                      <td className="py-2.5 px-3 font-sans text-xs">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] ${
                          isWin ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                        }`}>
                          {isWin ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                          {t.exit_reason || (isWin ? 'Target Hit' : 'Stop Loss')}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <GrowwLink url={t.groww_chart_url} symbol={t.symbol} variant="icon" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {trades.length > 150 && (
              <div className="py-3 text-center text-xs text-slate-500">
                Showing top 150 of {trades.length} audited trades.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
