import React from 'react';

interface StrategyBadgeProps {
  strategyId: string;
  name?: string;
  className?: string;
}

export const StrategyBadge: React.FC<StrategyBadgeProps> = ({ strategyId, name, className = '' }) => {
  let label = name || strategyId;
  let colorClass = 'bg-slate-800 text-slate-300 border-slate-700';

  if (strategyId.includes('rsi_52w') || strategyId.includes('rsi') || strategyId === 'strategy_1') {
    label = name || '3-Day RSI';
    colorClass = 'bg-sky-500/10 text-sky-400 border-sky-500/30';
  } else if (strategyId.includes('clean_candle') || strategyId.includes('5y') || strategyId === 'strategy_2') {
    label = name || '5Y Breakout';
    colorClass = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
  } else if (strategyId.includes('gfs') || strategyId.includes('mtf') || strategyId === 'strategy_3') {
    label = name || 'GFS MTF';
    colorClass = 'bg-purple-500/10 text-purple-400 border-purple-500/30';
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${colorClass} ${className}`}>
      {label}
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
      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-bull-glow ${className}`}>
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span>{statusLabel || 'GATE: OPEN'}</span>
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30 shadow-bear-glow ${className}`}>
      <span className="w-2 h-2 rounded-full bg-rose-400"></span>
      <span>{statusLabel || 'GATE: CLOSED (DEFENSIVE CASH PROTECTION)'}</span>
    </span>
  );
};
