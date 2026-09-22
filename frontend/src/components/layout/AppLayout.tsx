import React from 'react';
import { Navbar } from './Navbar';
import { MobileDock, ActiveTab } from './MobileDock';
import { LayoutDashboard, TrendingUp, ShieldCheck, Radio } from 'lucide-react';

interface AppLayoutProps {
  children: React.ReactNode;
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  lastSyncTime?: string;
  triggerCount?: number;
  gateOpen?: boolean;
  onOpenCloudModal?: () => void;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  activeTab,
  setActiveTab,
  onRefresh,
  isRefreshing,
  lastSyncTime,
  triggerCount = 0,
  gateOpen = true,
  onOpenCloudModal
}) => {
  const navLinks: Array<{ id: ActiveTab; label: string; sub: string; badgeText?: string; icon: React.ReactNode; badge?: number }> = [
    {
      id: 'live_tracker',
      label: 'Live Tracker',
      sub: 'Signals, Slots & Drift Monitor',
      badgeText: 'LIVE',
      icon: <LayoutDashboard className="w-5 h-5" />,
      badge: triggerCount > 0 ? triggerCount : undefined
    },
    {
      id: 'backtesting',
      label: 'Backtesting Hub',
      sub: '3 Audited Strategies (5Y Sim)',
      badgeText: '3 AUDITED',
      icon: <TrendingUp className="w-5 h-5" />
    },
    {
      id: 'system_health',
      label: 'System & Cloud',
      sub: 'Integrity, Engine & Backups',
      badgeText: 'WAL OK',
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
        onOpenCloudModal={onOpenCloudModal}
      />

      {/* Main Body - Edge to edge widescreen layout */}
      <div className="flex-1 flex w-full px-2 sm:px-4 lg:px-6 pb-24 md:pb-8 relative z-10 gap-3">
        {/* Desktop Left Sidebar (3 Master Tabs) */}
        <aside className="hidden md:flex flex-col w-64 p-3 border-r border-slate-800/80 shrink-0 gap-4">
          <div className="space-y-2">
            <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500 px-3 mb-2 flex items-center justify-between">
              <span>Navigation Control</span>
              <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">3 HUBS</span>
            </div>

            {navLinks.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-3 rounded-2xl text-left transition-all duration-200 group relative ${
                    isActive
                      ? 'bg-gradient-to-r from-cyan-500/15 via-cyan-500/10 to-transparent text-cyan-300 border border-cyan-500/40 shadow-lg shadow-cyan-950/50'
                      : 'text-slate-400 hover:text-white hover:bg-slate-900/60 border border-slate-800/40 hover:border-slate-700/60'
                  }`}
                >
                  {isActive && (
                    <span className="absolute left-0 top-2 bottom-2 w-1 bg-gradient-to-b from-cyan-400 to-emerald-400 rounded-r-full shadow-[0_0_12px_rgba(0,229,255,0.8)]"></span>
                  )}
                  <div className="flex items-center gap-3">
                    <span className={`p-2 rounded-xl transition-transform group-hover:scale-105 ${
                      isActive 
                        ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 drop-shadow-[0_0_8px_rgba(0,229,255,0.4)]' 
                        : 'bg-slate-900/80 text-slate-400 border border-slate-800'
                    }`}>
                      {item.icon}
                    </span>
                    <div>
                      <div className="text-xs font-bold leading-tight font-sans tracking-tight">
                        {item.label}
                      </div>
                      <div className="text-[10px] text-slate-500 leading-tight font-mono mt-0.5">
                        {item.sub}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {item.badge !== undefined ? (
                      <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm animate-pulse">
                        {item.badge}
                      </span>
                    ) : item.badgeText ? (
                      <span className={`font-mono text-[9px] font-bold px-1.5 py-0.5 rounded border ${
                        isActive
                          ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                          : 'bg-slate-900 text-slate-500 border-slate-800'
                      }`}>
                        {item.badgeText}
                      </span>
                    ) : null}
                  </div>
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
