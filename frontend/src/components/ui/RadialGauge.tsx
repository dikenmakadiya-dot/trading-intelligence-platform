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
  const strokeWidth = 12;
  const radius = (size - strokeWidth * 2 - 20) / 2;
  const cx = size / 2;
  const cy = radius + strokeWidth + 16;
  const svgHeight = cy + strokeWidth / 2 + 6;

  // Semicircle arc length = PI * radius
  const arcLength = Math.PI * radius;
  // Clamp pct between 0 and 100
  const clampedPct = Math.max(0, Math.min(100, percentage));
  const progressOffset = arcLength - (clampedPct / 100) * arcLength;

  const glowColor = gateOpen ? 'rgba(0, 229, 255, 0.4)' : 'rgba(255, 51, 102, 0.4)';

  return (
    <div className="flex flex-col items-center justify-center p-1 w-full">
      <div className="relative flex items-center justify-center" style={{ width: size, height: svgHeight }}>
        <svg
          width={size}
          height={svgHeight}
          viewBox={`0 0 ${size} ${svgHeight}`}
          className="overflow-visible"
        >
          <defs>
            <filter id="quantum-gauge-glow" x="-25%" y="-25%" width="150%" height="150%">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor={glowColor} />
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
            opacity="0.85"
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

        {/* Center Tabular Metrics (Positioned below the top tick mark) */}
        <div
          className="absolute inset-x-0 flex flex-col items-center justify-center text-center pointer-events-none"
          style={{ bottom: strokeWidth + 6 }}
        >
          <span className="font-mono text-2xl sm:text-3xl font-extrabold text-white tabular-nums tracking-tight drop-shadow-[0_0_12px_rgba(255,255,255,0.25)]">
            {percentage.toFixed(1)}%
          </span>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono mt-0.5">
            Nifty 500 &gt; EMA50
          </span>
        </div>
      </div>

      {/* Gate Regime Status */}
      <div className="mt-2 flex flex-col items-center text-center space-y-1">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/80 border border-slate-800">
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              gateOpen ? 'bg-emerald-400 beacon-pulse' : 'bg-rose-500 shadow-[0_0_8px_rgba(255,51,102,0.6)]'
            }`}
          />
          <span
            className={`text-xs font-bold tracking-wide font-sans ${
              gateOpen ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {statusLabel || (gateOpen ? 'GATE: OPEN (BULLISH)' : 'DEFENSIVE: CASH MODE')}
          </span>
        </div>
        <span className="font-mono text-[11px] text-slate-400 tabular-nums">
          <span className="text-white font-bold">{stocksAbove}</span> / {totalStocks} Above 50 EMA
        </span>
      </div>
    </div>
  );
};
