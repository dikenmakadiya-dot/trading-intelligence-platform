import React from 'react';

interface RadialGaugeProps {
  percentage: number;
  gateOpen: boolean;
  stocksAbove?: number;
  totalStocks?: number;
  statusLabel?: string;
  size?: number;
}

export const RadialGauge: React.FC<RadialGaugeProps> = ({
  percentage,
  gateOpen,
  stocksAbove = 0,
  totalStocks = 500,
  statusLabel,
  size = 220
}) => {
  const strokeWidth = 14;
  const radius = (size - strokeWidth * 2) / 2;
  const cx = size / 2;
  const cy = size / 2 + 10;

  // Semicircle arc length = PI * radius
  const arcLength = Math.PI * radius;
  // Clamp pct between 0 and 100
  const clampedPct = Math.max(0, Math.min(100, percentage));
  const progressOffset = arcLength - (clampedPct / 100) * arcLength;

  const strokeColor = gateOpen ? '#22C55E' : '#EF4444';
  const glowColor = gateOpen ? 'rgba(34, 197, 94, 0.25)' : 'rgba(239, 68, 68, 0.25)';

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <div className="relative" style={{ width: size, height: size * 0.65 }}>
        <svg
          width={size}
          height={size * 0.7}
          viewBox={`0 0 ${size} ${size * 0.7}`}
          className="overflow-visible"
        >
          <defs>
            <filter id="gauge-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor={glowColor} />
            </filter>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#EF4444" />
              <stop offset="50%" stopColor="#F59E0B" />
              <stop offset="100%" stopColor="#22C55E" />
            </linearGradient>
          </defs>

          {/* Background Track Arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke="#1E293B"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* 50% Threshold Mark */}
          <line
            x1={cx}
            y1={cy - radius - strokeWidth / 2 - 2}
            x2={cx}
            y2={cy - radius + strokeWidth / 2 + 2}
            stroke="#94A3B8"
            strokeWidth="2"
            strokeDasharray="2,2"
          />

          {/* Active Progress Arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={arcLength}
            strokeDashoffset={progressOffset}
            filter="url(#gauge-glow)"
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* Center Numbers */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center text-center"
          style={{ top: '15%' }}
        >
          <span className="font-mono text-3xl sm:text-4xl font-black text-white tabular-nums tracking-tight">
            {percentage.toFixed(1)}%
          </span>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-0.5">
            Nifty 500 &gt; EMA50
          </span>
        </div>
      </div>

      {/* Gate Regime Status */}
      <div className="mt-1 flex flex-col items-center text-center">
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              gateOpen ? 'bg-emerald-400 animate-pulse shadow-bull-glow' : 'bg-rose-500 shadow-bear-glow'
            }`}
          />
          <span
            className={`text-sm font-bold tracking-wide ${
              gateOpen ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {statusLabel || (gateOpen ? 'GATE: OPEN (AGGRESSIVE BUY)' : 'GATE: CLOSED (DEFENSIVE CASH)')}
          </span>
        </div>
        <span className="font-mono text-xs text-slate-400 mt-1 tabular-nums">
          {stocksAbove} / {totalStocks} Stocks Trading Above 50-day EMA
        </span>
      </div>
    </div>
  );
};
