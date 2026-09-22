import React from 'react';
import { LayoutDashboard, TrendingUp, ShieldCheck } from 'lucide-react';

export type ActiveTab = 'live_tracker' | 'backtesting' | 'system_health';

interface MobileDockProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  triggerCount?: number;
}

export const MobileDock: React.FC<MobileDockProps> = ({
  activeTab,
  setActiveTab,
  triggerCount = 0
}) => {
  const items: Array<{ id: ActiveTab; label: string; icon: React.ReactNode; badge?: number }> = [
    {
      id: 'live_tracker',
      label: 'Live Tracker',
      icon: <LayoutDashboard className="w-5 h-5" />,
      badge: triggerCount > 0 ? triggerCount : undefined
    },
    {
      id: 'backtesting',
      label: 'Backtesting',
      icon: <TrendingUp className="w-5 h-5" />
    },
    {
      id: 'system_health',
      label: 'System & Cloud',
      icon: <ShieldCheck className="w-5 h-5" />
    }
  ];

  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-slate-950/95 backdrop-blur-xl border-t border-cyan-500/20 shadow-2xl safe-bottom">
      <div className="grid grid-cols-3 h-16 max-w-md mx-auto">
        {items.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex flex-col items-center justify-center min-h-[48px] relative transition-all active:scale-95 ${
                isActive ? 'text-cyan-400' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <div className="relative">
                <span className={isActive ? 'drop-shadow-[0_0_8px_rgba(0,229,255,0.5)]' : ''}>
                  {item.icon}
                </span>
                {item.badge !== undefined && (
                  <span className="absolute -top-1.5 -right-2.5 px-1.5 py-0.2 bg-gradient-to-r from-cyan-400 to-emerald-400 text-slate-950 text-[10px] font-black rounded-full font-mono shadow-sm">
                    {item.badge}
                  </span>
                )}
              </div>
              <span className={`text-[10px] font-bold mt-1 tracking-tight font-sans ${isActive ? 'text-cyan-300' : 'text-slate-500'}`}>
                {item.label}
              </span>
              {isActive && (
                <span className="absolute top-0 w-8 h-0.5 bg-gradient-to-r from-cyan-400 to-emerald-400 rounded-full shadow-[0_0_10px_rgba(0,229,255,0.8)]"></span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
