import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  trend?: 'bullish' | 'bearish' | 'neutral';
  icon?: React.ReactNode;
  highlight?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtext,
  trend = 'neutral',
  icon,
  highlight = false
}) => {
  let valueColor = 'text-white';
  if (trend === 'bullish') valueColor = 'text-trade-bullish';
  if (trend === 'bearish') valueColor = 'text-trade-bearish';

  return (
    <div
      className={`glass-card rounded-xl p-3.5 sm:p-4 flex flex-col justify-between transition-all ${
        highlight ? 'border-sky-500/40 bg-sky-950/20 shadow-accent-glow' : 'hover:border-slate-700'
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {label}
        </span>
        {icon && <span className="text-slate-400">{icon}</span>}
      </div>

      <div className="flex flex-col">
        <span className={`font-mono text-xl sm:text-2xl font-bold tracking-tight tabular-nums ${valueColor}`}>
          {value}
        </span>
        {subtext && (
          <span className="text-xs font-medium text-slate-400 mt-0.5 tabular-nums">
            {subtext}
          </span>
        )}
      </div>
    </div>
  );
};
