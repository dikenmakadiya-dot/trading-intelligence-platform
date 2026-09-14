import React from 'react';

interface StrategyBadgeProps {
  strategyId: string;
  name?: string;
  className?: string;
}

export const StrategyBadge: React.FC<StrategyBadgeProps> = ({ strategyId, name, className = '' }) => {
  let label = name || strategyId;
  let colorClass = 'bg-slate-800/80 text-slate-300 border-slate-700';
  let dotColor = 'bg-slate-400';

  if (strategyId.includes('rsi_52w') || strategyId.includes('rsi') || strategyId === 'strategy_1') {
    label = name || '3-Day RSI UP';
    colorClass = 'bg-amber-500/15 text-amber-300 border-amber-500/30 shadow-sm';
    dotColor = 'bg-amber-400';
  } else if (strategyId.includes('clean_candle') || strategyId.includes('5y') || strategyId === 'strategy_2') {
    label = name || '5Y Clean Candle';
    colorClass = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30 shadow-sm';
    dotColor = 'bg-emerald-400';
  } else if (strategyId.includes('gfs') || strategyId.includes('mtf') || strategyId === 'strategy_3') {
    label = name || 'GFS Multi-TF';
    colorClass = 'bg-purple-500/15 text-purple-300 border-purple-500/30 shadow-sm';
    dotColor = 'bg-purple-400';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg text-xs font-bold font-sans border ${colorClass} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`}></span>
      <span>{label}</span>
    </span>
  );
};

interface RegimeGateBadgeProps {
  gateOpen: boolean;
  statusLabel?: string;
  className?: string;
}

export const RegimeGateBadge: React.FC<RegimeGateBadgeProps> = ({
  gateOpen,
  statusLabel,
  className = ''
}) => {
  if (gateOpen) {
    return (
      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold font-sans bg-emerald-500/15 text-emerald-300 border border-emerald-500/35 shadow-[0_0_15px_rgba(0,255,157,0.2)] ${className}`}>
        <span className="beacon-pulse w-2 h-2 rounded-full bg-emerald-400"></span>
        <span>{statusLabel || 'GATE: OPEN (BULLISH)'}</span>
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold font-sans bg-rose-500/15 text-rose-300 border border-rose-500/35 shadow-[0_0_15px_rgba(255,51,102,0.2)] ${className}`}>
      <span className="w-2 h-2 rounded-full bg-rose-400"></span>
      <span>{statusLabel || 'DEFENSIVE CASH (GATE CLOSED)'}</span>
    </span>
  );
};
