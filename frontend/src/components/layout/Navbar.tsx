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
    <header className="sticky top-0 z-40 w-full bg-oled-canvas/90 backdrop-blur-md border-b border-oled-border px-4 py-3 sm:px-6">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Brand & Market Status */}
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-slate-900 border border-slate-700 shadow-sm">
            <Activity className="w-5 h-5 text-trade-accent" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-base tracking-tight text-white">
                Quant<span className="text-trade-accent">Flow</span>
              </span>
              <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/30">
                PRO
              </span>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-slate-400">
              <span className="flex items-center gap-1 text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>CLOUD SYNC</span>
              </span>
              <span>•</span>
              <span className={`font-semibold ${gateOpen ? 'text-emerald-400' : 'text-rose-400'}`}>
                {gateOpen ? 'GATE OPEN' : 'DEFENSIVE'}
              </span>
              <span>•</span>
              <span>NIFTY 750</span>
            </div>
          </div>
        </div>

        {/* Right side controls */}
        <div className="flex items-center gap-3">
          {lastSyncTime && (
            <div className="hidden md:flex flex-col text-right text-xs">
              <span className="text-slate-500">Last Synced</span>
              <span className="font-mono text-slate-300 tabular-nums text-[11px]">
                {lastSyncTime}
              </span>
            </div>
          )}

          {/* 1-Tap Refresh Action Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 hover:text-sky-300 border border-sky-500/30 hover:border-sky-400 active:scale-95 transition-all shadow-sm disabled:opacity-50"
            title="Trigger on-demand cloud screener sync"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-sky-400' : ''}`} />
            <span className="hidden sm:inline">
              {isRefreshing ? 'Syncing...' : 'Refresh Signals'}
            </span>
          </button>
        </div>
      </div>
    </header>
  );
};
