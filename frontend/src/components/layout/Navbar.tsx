import React from 'react';
import { RefreshCw, Activity } from 'lucide-react';

interface NavbarProps {
  onRefresh: () => void;
  isRefreshing: boolean;
  lastSyncTime?: string;
  gateOpen?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  onRefresh,
  isRefreshing,
  lastSyncTime,
  gateOpen = true
}) => {
  return (
    <header className="sticky top-0 z-40 w-full bg-slate-950/85 backdrop-blur-xl border-b border-cyan-500/15 px-4 py-3 sm:px-8 shadow-2xl">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        
        {/* Brand & Market Status */}
        <div className="flex items-center gap-3.5">
          <div className="relative group">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-cyan-600 via-emerald-500 to-teal-400 p-[1px] shadow-lg shadow-cyan-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[15px] flex items-center justify-center">
                <Activity className="w-5 h-5 text-cyan-400 group-hover:scale-110 transition-transform" />
              </div>
            </div>
            <span className="beacon-pulse absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-emerald-400 border-2 border-slate-950"></span>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight text-white font-sans">
                QUANT<span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400">FLOW</span>
              </span>
              <span className="text-[10px] font-mono font-bold tracking-widest px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm">
                INSTITUTIONAL
              </span>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-slate-400 font-medium">
              <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span>CLOUD SYNC</span>
              </span>
              <span className="text-slate-600">•</span>
              <span className={`font-semibold ${gateOpen ? 'text-emerald-400' : 'text-rose-400'}`}>
                {gateOpen ? 'GATE: OPEN' : 'DEFENSIVE: CASH'}
              </span>
              <span className="text-slate-600">•</span>
              <span className="font-mono text-slate-400">NIFTY 750</span>
            </div>
          </div>
        </div>

        {/* System Intelligence Pulse Bar (Desktop) */}
        <div className="hidden lg:flex items-center gap-3 bg-slate-900/80 px-4 py-2 rounded-2xl border border-slate-800/90 shadow-inner">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="beacon-pulse absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-bold text-slate-200">ORCHESTRATOR ACTIVE</span>
          </div>
          <span className="text-slate-700">|</span>
          <div className="text-xs text-slate-400 font-mono">
            SYNC: <span className="text-slate-200 font-semibold">{lastSyncTime || '11-Sep-2026 16:15 IST'}</span>
          </div>
          <span className="text-slate-700">|</span>
          <div className={`text-xs font-bold flex items-center gap-1 ${gateOpen ? 'text-emerald-400' : 'text-rose-400'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${gateOpen ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
            <span>{gateOpen ? 'BULLISH GATE' : 'CAPITAL PRESERVATION'}</span>
          </div>
        </div>

        {/* Right side controls */}
        <div className="flex items-center gap-3">
          {lastSyncTime && (
            <div className="hidden sm:flex lg:hidden flex-col text-right text-xs">
              <span className="text-slate-500 text-[10px] uppercase font-bold">Last Synced</span>
              <span className="font-mono text-slate-300 tabular-nums text-[11px]">
                {lastSyncTime}
              </span>
            </div>
          )}

          {/* 1-Tap Refresh / Scan Action Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="relative group flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs bg-gradient-to-r from-cyan-500/20 to-emerald-500/20 text-cyan-300 hover:text-white border border-cyan-500/40 hover:border-cyan-400 shadow-lg shadow-cyan-950/50 hover:shadow-cyan-500/20 active:scale-95 transition-all disabled:opacity-50"
            title="Trigger on-demand cloud screener scan"
          >
            <RefreshCw className={`w-4 h-4 text-cyan-400 group-hover:rotate-180 transition-transform duration-500 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">
              {isRefreshing ? 'Scanning Market...' : 'Scan Market Now'}
            </span>
          </button>
        </div>

      </div>
    </header>
  );
};
