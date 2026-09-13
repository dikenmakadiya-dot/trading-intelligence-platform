import React from 'react';
import { LayoutDashboard, TrendingUp, Zap, Clock, ShieldCheck } from 'lucide-react';

export type ActiveTab = 'nexus' | 'strategy_1' | 'strategy_2' | 'strategy_3' | 'health';

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
      id: 'nexus',
      label: 'Nexus',
      icon: <LayoutDashboard className="w-5 h-5" />,
      badge: triggerCount > 0 ? triggerCount : undefined
    },
    {
      id: 'strategy_1',
      label: '3D-RSI',
      icon: <TrendingUp className="w-5 h-5" />
    },
    {
      id: 'strategy_2',
      label: '5Y-High',
      icon: <Zap className="w-5 h-5" />
    },
    {
      id: 'strategy_3',
      label: 'GFS MTF',
      icon: <Clock className="w-5 h-5" />
    },
    {
      id: 'health',
      label: 'Health',
      icon: <ShieldCheck className="w-5 h-5" />
    }
  ];

  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-slate-950/95 backdrop-blur-lg border-t border-slate-800 safe-bottom">
      <div className="grid grid-cols-5 h-16 max-w-lg mx-auto">
        {items.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex flex-col items-center justify-center min-h-[48px] relative transition-colors ${
                isActive ? 'text-trade-accent' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <div className="relative">
                {item.icon}
                {item.badge !== undefined && (
                  <span className="absolute -top-1.5 -right-2 px-1.5 py-0.2 bg-trade-accent text-slate-950 text-[10px] font-black rounded-full font-mono">
                    {item.badge}
                  </span>
                )}
              </div>
              <span className={`text-[10px] font-semibold mt-1 tracking-tight ${isActive ? 'text-trade-accent' : 'text-slate-400'}`}>
                {item.label}
              </span>
              {isActive && (
                <span className="absolute top-0 w-8 h-0.5 bg-trade-accent rounded-full"></span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
