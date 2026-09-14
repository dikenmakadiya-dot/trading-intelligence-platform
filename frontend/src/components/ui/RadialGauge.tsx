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
  size = 230
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

  const glowColor = gateOpen ? 'rgba(0, 229, 255, 0.4)' : 'rgba(255, 51, 102, 0.4)';

  return (
    <div className="flex flex-col items-center justify-center p-2">
      <div className="relative" style={{ width: size, height: size * 0.62 }}>
        <svg
          width={size}
          height={size * 0.68}
          viewBox={`0 0 ${size} ${size * 0.68}`}
          className="overflow-visible"
        >
          <defs>
            <filter id="quantum-gauge-glow" x="-25%" y="-25%" width="150%" height="150%">
              <feDropShadow dx="0" dy="0" stdDeviation="5" floodColor={glowColor} />
            </filter>
            <linearGradient id="quantumGaugeGradOpen" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#00E5FF" />
              <stop offset="100%" stopColor="#10B981" />
            </linearGradient>
            <linearGradient id="quantumGaugeGradClosed" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#F59E0B" />
              <stop offset="100%" stopColor="#FF3366" />
            </linearGradient>
          </defs>

          {/* Background Track Arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke="#0F172E"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* 50% Threshold Tick Mark */}
          <line
            x1={cx}
            y1={cy - radius - strokeWidth / 2 - 4}
            x2={cx}
            y2={cy - radius + strokeWidth / 2 + 4}
            stroke="#38BDF8"
            strokeWidth="2.5"
            strokeDasharray="2,2"
            opacity="0.8"
          />

          {/* Active Progress Arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke={gateOpen ? 'url(#quantumGaugeGradOpen)' : 'url(#quantumGaugeGradClosed)'}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={arcLength}
            strokeDashoffset={progressOffset}
            filter="url(#quantum-gauge-glow)"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        {/* Center Tabular Metrics */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center text-center"
          style={{ top: '16%' }}
        >
          <span className="font-mono text-3xl sm:text-4xl font-extrabold text-white tabular-nums tracking-tight drop-shadow-[0_0_12px_rgba(255,255,255,0.2)]">
            {percentage.toFixed(1)}%
          </span>
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider font-mono mt-0.5">
            Nifty 500 &gt; EMA50
          </span>
        </div>
      </div>

      {/* Gate Regime Status */}
      <div className="mt-1 flex flex-col items-center text-center space-y-1">
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              gateOpen ? 'bg-emerald-400 beacon-pulse' : 'bg-rose-500 shadow-[0_0_10px_rgba(255,51,102,0.5)]'
            }`}
          />
          <span
            className={`text-xs sm:text-sm font-extrabold tracking-wide font-sans ${
              gateOpen ? 'text-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.3)]' : 'text-rose-400 drop-shadow-[0_0_8px_rgba(255,51,102,0.3)]'
            }`}
          >
            {statusLabel || (gateOpen ? 'GATE: OPEN (BULLISH ENTRY ALLOWED)' : 'DEFENSIVE: CASH PROTECTION ACTIVE')}
          </span>
        </div>
        <span className="font-mono text-[11px] text-slate-400 tabular-nums">
          <span className="text-white font-bold">{stocksAbove}</span> / {totalStocks} Stocks Trading Above 50 EMA
        </span>
      </div>
    </div>
  );
};
