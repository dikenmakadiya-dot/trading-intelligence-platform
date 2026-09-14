import React from 'react';
import { Navbar } from './Navbar';
import { MobileDock, ActiveTab } from './MobileDock';
import { LayoutDashboard, TrendingUp, Zap, Clock, ShieldCheck, Radio } from 'lucide-react';

interface AppLayoutProps {
  children: React.ReactNode;
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  lastSyncTime?: string;
  triggerCount?: number;
  gateOpen?: boolean;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  activeTab,
  setActiveTab,
  onRefresh,
  isRefreshing,
  lastSyncTime,
  triggerCount = 0,
  gateOpen = true
}) => {
  const navLinks: Array<{ id: ActiveTab; label: string; sub: string; icon: React.ReactNode; badge?: number }> = [
    {
      id: 'nexus',
      label: 'Signal Nexus',
      sub: 'Master Stage & Active Slots',
      icon: <LayoutDashboard className="w-5 h-5" />,
      badge: triggerCount > 0 ? triggerCount : undefined
    },
    {
      id: 'strategy_1',
      label: '3-Day RSI Breakout',
      sub: 'Swing RSI + 52W High',
      icon: <TrendingUp className="w-5 h-5" />
    },
    {
      id: 'strategy_2',
      label: '5Y Clean Candle',
      sub: 'Clean Momentum Breakout',
      icon: <Zap className="w-5 h-5" />
    },
    {
      id: 'strategy_3',
      label: 'GFS Multi-Timeframe',
      sub: 'Daily / Weekly / Monthly RSI',
      icon: <Clock className="w-5 h-5" />
    },
    {
      id: 'health',
      label: 'Cloud Health & Backups',
      sub: 'Integrity, Snapshots & Data',
      icon: <ShieldCheck className="w-5 h-5" />
    }
  ];

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 flex flex-col relative selection:bg-cyan-500 selection:text-black">
      {/* Ambient Top Mesh Glow */}
      <div className="ambient-glow"></div>

      {/* Top Navbar */}
      <Navbar
        onRefresh={onRefresh}
        isRefreshing={isRefreshing}
        lastSyncTime={lastSyncTime}
        gateOpen={gateOpen}
      />

      {/* Main Body */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto pb-24 md:pb-8 relative z-10">
        {/* Desktop Left Sidebar (hidden on mobile) */}
        <aside className="hidden md:flex flex-col w-64 p-4 border-r border-slate-800/80 shrink-0 gap-6">
          {/* Navigation Section */}
          <div className="space-y-1.5">
            <div className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-500 px-3 mb-2 flex items-center justify-between">
              <span>Navigation</span>
              <span className="text-[10px] text-cyan-400">PWA</span>
            </div>

            {navLinks.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-3 rounded-2xl text-left transition-all group ${
                    isActive
                      ? 'bg-gradient-to-r from-cyan-500/15 via-cyan-500/10 to-transparent text-cyan-300 border border-cyan-500/30 shadow-lg shadow-cyan-950/40'
                      : 'text-slate-400 hover:text-white hover:bg-slate-900/60 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`transition-transform group-hover:scale-110 ${isActive ? 'text-cyan-400 drop-shadow-[0_0_8px_rgba(0,229,255,0.4)]' : 'text-slate-400'}`}>
                      {item.icon}
                    </span>
                    <div>
                      <div className="text-xs font-bold leading-tight font-sans">
                        {item.label}
                      </div>
                      <div className="text-[10px] text-slate-500 leading-tight font-mono mt-0.5">
                        {item.sub}
                      </div>
                    </div>
                  </div>
                  {item.badge !== undefined && (
                    <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Institutional Status Deck */}
          <div className="mt-auto p-4 rounded-2xl bg-slate-950/70 border border-slate-800/80 space-y-2.5 shadow-inner">
            <div className="text-xs font-bold text-slate-200 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
                <span>Quant Engine</span>
              </span>
              <span className="font-mono text-[10px] font-bold text-emerald-400 px-1.5 py-0.2 rounded bg-emerald-500/15 border border-emerald-500/30">
                ACTIVE
              </span>
            </div>
            <div className="text-[11px] text-slate-400 font-mono space-y-1 pt-1 border-t border-slate-900">
              <div className="flex justify-between">
                <span>Universe:</span>
                <span className="text-slate-300 font-semibold">750 Stocks</span>
              </div>
              <div className="flex justify-between">
                <span>Database:</span>
                <span className="text-slate-300 font-semibold">SQLite WAL</span>
              </div>
              <div className="flex justify-between">
                <span>Disaster BKP:</span>
                <span className="text-cyan-400 font-semibold">Parquet Snap</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Content Pane */}
        <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>

      {/* Mobile Sticky Bottom Dock */}
      <MobileDock
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        triggerCount={triggerCount}
      />
    </div>
  );
};
