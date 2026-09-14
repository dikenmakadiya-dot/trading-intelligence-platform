import React, { useState, useMemo } from 'react';
import { EquityCurvePoint } from '../../types';

interface EquityCurveChartProps {
  data: EquityCurvePoint[];
  height?: number;
}

export const EquityCurveChart: React.FC<EquityCurveChartProps> = ({ data, height = 340 }) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  // Compute metrics and underwater drawdown series
  const { chartData, minVal, maxVal, maxDD } = useMemo(() => {
    if (!data || data.length === 0) {
      return { chartData: [], minVal: 0, maxVal: 0, maxDD: 0 };
    }

    let peak = -Infinity;
    let worstDD = 0;

    const enriched = data.map((d: any) => {
      const val = Number(d.portfolio_value ?? d.portfolio_equity ?? 0);
      if (val > peak) peak = val;
      const dd = peak > 0 ? ((val - peak) / peak) * 100 : 0;
      if (dd < worstDD) worstDD = dd;
      return {
        ...d,
        portfolio_value: val,
        drawdown: dd,
        peak
      };
    });

    const values = enriched.map((d) => d.portfolio_value);
    const minV = Math.min(...values) * 0.95;
    const maxV = Math.max(...values) * 1.05;

    return {
      chartData: enriched,
      minVal: minV,
      maxVal: maxV,
      maxDD: worstDD
    };
  }, [data]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm font-mono">
        No equity curve data available. Trigger backtest refresh to generate historical data.
      </div>
    );
  }

  const width = 800; // SVG internal coordinate width
  const equityHeight = height * 0.65;
  const paddingX = 60;
  const paddingY = 20;

  // Coordinate scales
  const getX = (index: number) => {
    const denom = chartData.length > 1 ? chartData.length - 1 : 1;
    return paddingX + (index / denom) * (width - paddingX - 20);
  };

  const getEquityY = (val: number) => {
    const range = maxVal - minVal || 1;
    return paddingY + (1 - (val - minVal) / range) * (equityHeight - paddingY * 2);
  };

  const getDDY = (dd: number) => {
    const bottom = height - 20;
    const top = equityHeight + 30;
    const ddRange = Math.abs(maxDD) || 1;
    const norm = Math.abs(dd) / ddRange;
    return top + norm * (bottom - top);
  };

  // Build SVG paths
  const equityPath = chartData.reduce((path, d, i) => {
    const x = getX(i);
    const y = getEquityY(d.portfolio_value);
    return i === 0 ? `M ${x} ${y}` : `${path} L ${x} ${y}`;
  }, '');

  const equityAreaPath = `${equityPath} L ${getX(chartData.length - 1)} ${equityHeight} L ${getX(0)} ${equityHeight} Z`;

  const ddPath = chartData.reduce((path, d, i) => {
    const x = getX(i);
    const y = getDDY(d.drawdown);
    return i === 0 ? `M ${x} ${y}` : `${path} L ${x} ${y}`;
  }, '');

  const ddAreaPath = `${ddPath} L ${getX(chartData.length - 1)} ${equityHeight + 30} L ${getX(0)} ${equityHeight + 30} Z`;

  const hoveredPoint = hoverIndex !== null && chartData[hoverIndex] ? chartData[hoverIndex] : chartData[chartData.length - 1];

  return (
    <div className="w-full relative select-none">
      {/* Chart Header Stats */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-3 px-2">
        <div className="flex items-center gap-4">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono">Selected Date</div>
            <div className="font-mono text-sm font-bold text-white tabular-nums">
              {hoveredPoint?.date || '--'}
            </div>
          </div>
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono">Portfolio Equity</div>
            <div className="font-mono text-sm font-extrabold text-cyan-400 tabular-nums drop-shadow-[0_0_8px_rgba(0,229,255,0.3)]">
              ₹{(hoveredPoint?.portfolio_value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono">Underwater Drawdown</div>
            <div className={`font-mono text-sm font-bold tabular-nums ${hoveredPoint?.drawdown < -10 ? 'text-rose-400 font-extrabold' : 'text-slate-300'}`}>
              {(hoveredPoint?.drawdown || 0).toFixed(2)}%
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="flex items-center gap-1.5 text-cyan-400 font-bold">
            <span className="w-3 h-0.5 bg-cyan-400 rounded"></span> Strategy Curve
          </span>
          <span className="flex items-center gap-1.5 text-rose-400/80">
            <span className="w-3 h-0.5 bg-rose-500/80 rounded"></span> Drawdown
          </span>
        </div>
      </div>

      {/* Interactive SVG Chart */}
      <div className="w-full bg-slate-950/80 rounded-2xl border border-slate-800/90 p-2 relative overflow-hidden shadow-inner">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible cursor-crosshair"
          onMouseLeave={() => setHoverIndex(null)}
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const relX = ((e.clientX - rect.left) / rect.width) * width;
            const denom = width - paddingX - 20;
            const fraction = Math.max(0, Math.min(1, (relX - paddingX) / denom));
            const idx = Math.round(fraction * (chartData.length - 1));
            setHoverIndex(idx);
          }}
        >
          <defs>
            {/* Strategy Area Gradient */}
            <linearGradient id="quantumAreaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#00E5FF" stopOpacity="0.30" />
              <stop offset="60%" stopColor="#10B981" stopOpacity="0.08" />
              <stop offset="100%" stopColor="#030712" stopOpacity="0.0" />
            </linearGradient>

            {/* Drawdown Area Gradient */}
            <linearGradient id="quantumDDAreaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#FF3366" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#FF3366" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1={paddingX} y1={paddingY} x2={width - 20} y2={paddingY} stroke="#172445" strokeDasharray="3,3" opacity="0.6" />
          <line x1={paddingX} y1={equityHeight / 2} x2={width - 20} y2={equityHeight / 2} stroke="#172445" strokeDasharray="3,3" opacity="0.6" />
          <line x1={paddingX} y1={equityHeight} x2={width - 20} y2={equityHeight} stroke="#172445" opacity="0.8" />
          <line x1={paddingX} y1={equityHeight + 30} x2={width - 20} y2={equityHeight + 30} stroke="#172445" strokeDasharray="3,3" opacity="0.6" />
          <line x1={paddingX} y1={height - 20} x2={width - 20} y2={height - 20} stroke="#172445" opacity="0.8" />

          {/* Y-Axis Labels (Equity) */}
          <text x={paddingX - 8} y={paddingY + 4} fill="#64748B" fontSize="10" fontFamily="JetBrains Mono" textAnchor="end">
            ₹{(maxVal / 100000).toFixed(1)}L
          </text>
          <text x={paddingX - 8} y={equityHeight - 4} fill="#64748B" fontSize="10" fontFamily="JetBrains Mono" textAnchor="end">
            ₹{(minVal / 100000).toFixed(1)}L
          </text>

          {/* Y-Axis Labels (Drawdown) */}
          <text x={paddingX - 8} y={equityHeight + 34} fill="#64748B" fontSize="10" fontFamily="JetBrains Mono" textAnchor="end">
            0%
          </text>
          <text x={paddingX - 8} y={height - 22} fill="#FF3366" fontSize="10" fontFamily="JetBrains Mono" textAnchor="end">
            {maxDD.toFixed(0)}%
          </text>

          {/* Area Fills */}
          <path d={equityAreaPath} fill="url(#quantumAreaGradient)" />
          <path d={ddAreaPath} fill="url(#quantumDDAreaGradient)" />

          {/* Line Strokes */}
          <path d={equityPath} fill="none" stroke="#00E5FF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d={ddPath} fill="none" stroke="#FF3366" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />

          {/* Hover Crosshair Guide */}
          {hoverIndex !== null && chartData[hoverIndex] && (
            <g>
              <line
                x1={getX(hoverIndex)}
                y1={paddingY}
                x2={getX(hoverIndex)}
                y2={height - 20}
                stroke="#00E5FF"
                strokeWidth="1.5"
                strokeDasharray="2,2"
                opacity="0.8"
              />
              <circle
                cx={getX(hoverIndex)}
                cy={getEquityY(chartData[hoverIndex].portfolio_value)}
                r="5"
                fill="#00E5FF"
                stroke="#030712"
                strokeWidth="2.5"
              />
              <circle
                cx={getX(hoverIndex)}
                cy={getDDY(chartData[hoverIndex].drawdown)}
                r="4"
                fill="#FF3366"
                stroke="#030712"
                strokeWidth="2"
              />
            </g>
          )}
        </svg>
      </div>
    </div>
  );
};
