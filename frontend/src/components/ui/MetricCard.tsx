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
  if (trend === 'bullish') valueColor = 'text-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.3)]';
  if (trend === 'bearish') valueColor = 'text-rose-400 drop-shadow-[0_0_8px_rgba(255,51,102,0.3)]';

  return (
    <div
      className={`glass-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between transition-all glass-card-hover ${
        highlight
          ? 'border-cyan-500/40 bg-cyan-950/20 shadow-[0_0_20px_rgba(0,229,255,0.15)]'
          : ''
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-mono">
          {label}
        </span>
        {icon && <span className="text-cyan-400">{icon}</span>}
      </div>

      <div className="flex flex-col">
        <span className={`font-mono text-xl sm:text-2xl font-extrabold tracking-tight tabular-nums ${valueColor}`}>
          {value}
        </span>
        {subtext && (
          <span className="text-xs font-semibold text-slate-400 mt-1 tabular-nums">
            {subtext}
          </span>
        )}
      </div>
    </div>
  );
};
