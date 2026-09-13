import React from 'react';
import { Navbar } from './Navbar';
import { MobileDock, ActiveTab } from './MobileDock';
import { LayoutDashboard, TrendingUp, Zap, Clock, ShieldCheck } from 'lucide-react';

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
    <div className="min-h-screen bg-oled-canvas text-oled-text flex flex-col">
      {/* Top Navbar */}
      <Navbar
        onRefresh={onRefresh}
        isRefreshing={isRefreshing}
        lastSyncTime={lastSyncTime}
        gateOpen={gateOpen}
      />

      {/* Main Body */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto pb-20 md:pb-8">
        {/* Desktop Left Sidebar (hidden on mobile) */}
        <aside className="hidden md:flex flex-col w-64 p-4 border-r border-oled-border shrink-0 gap-6">
          {/* Navigation Section */}
          <div className="space-y-1">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 px-3 mb-2">
              Navigation
            </div>
            {navLinks.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-left transition-all ${
                    isActive
                      ? 'bg-sky-500/10 text-trade-accent border border-sky-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={isActive ? 'text-trade-accent' : 'text-slate-400'}>
                      {item.icon}
                    </span>
                    <div>
                      <div className="text-sm font-semibold leading-tight">
                        {item.label}
                      </div>
                      <div className="text-[11px] text-slate-400 leading-tight">
                        {item.sub}
                      </div>
                    </div>
                  </div>
                  {item.badge !== undefined && (
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-full bg-trade-accent/20 text-trade-accent">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Institutional Status Deck */}
          <div className="mt-auto p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
            <div className="text-xs font-bold text-slate-300 flex items-center justify-between">
              <span>System Status</span>
              <span className="flex items-center gap-1 text-[10px] text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                ACTIVE
              </span>
            </div>
            <div className="text-[11px] text-slate-400 font-mono">
              <div>Constituents: 750 (500+250)</div>
              <div>Database: SQLite WAL</div>
              <div>Alerts: WhatsApp Cloud</div>
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
