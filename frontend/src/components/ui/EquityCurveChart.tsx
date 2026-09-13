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

    const enriched = data.map((d) => {
      const val = d.portfolio_value;
      if (val > peak) peak = val;
      const dd = peak > 0 ? ((val - peak) / peak) * 100 : 0;
      if (dd < worstDD) worstDD = dd;
      return {
        ...d,
        drawdown: dd,
        peak
      };
    });

    const values = data.map((d) => d.portfolio_value);
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
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
        No equity curve data available. Run backtest refresh to generate historical data.
      </div>
    );
  }

  const width = 800; // SVG internal coordinate width
  const equityHeight = height * 0.65;
  const paddingX = 60;
  const paddingY = 20;

  // Coordinate scales
  const getX = (index: number) => {
    return paddingX + (index / (chartData.length - 1)) * (width - paddingX - 20);
  };

  const getEquityY = (val: number) => {
    const range = maxVal - minVal || 1;
    return paddingY + (1 - (val - minVal) / range) * (equityHeight - paddingY * 2);
  };

  const getDDY = (dd: number) => {
    const bottom = height - 20;
    const top = equityHeight + 30;
    const ddRange = Math.abs(maxDD) || 1;
    // dd is negative: 0 at top, maxDD at bottom
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
            <div className="text-xs font-medium text-slate-400">Selected Date</div>
            <div className="font-mono text-sm font-bold text-white tabular-nums">
              {hoveredPoint?.date || '--'}
            </div>
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Equity Value</div>
            <div className="font-mono text-sm font-bold text-trade-bullish tabular-nums">
              ₹{(hoveredPoint?.portfolio_value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Underwater DD</div>
            <div className={`font-mono text-sm font-bold tabular-nums ${hoveredPoint?.drawdown < -10 ? 'text-trade-bearish' : 'text-slate-300'}`}>
              {(hoveredPoint?.drawdown || 0).toFixed(2)}%
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5 text-slate-400">
            <span className="w-3 h-0.5 bg-trade-bullish rounded-full"></span>
            Strategy Equity
          </span>
          <span className="flex items-center gap-1.5 text-slate-400">
            <span className="w-3 h-0.5 bg-rose-500 rounded-full"></span>
            Drawdown %
          </span>
        </div>
      </div>

      {/* SVG Chart Pane */}
      <div className="w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto"
          onMouseLeave={() => setHoverIndex(null)}
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const mouseX = ((e.clientX - rect.left) / rect.width) * width;
            if (mouseX >= paddingX && mouseX <= width - 20) {
              const pct = (mouseX - paddingX) / (width - paddingX - 20);
              const idx = Math.round(pct * (chartData.length - 1));
              setHoverIndex(Math.max(0, Math.min(chartData.length - 1, idx)));
            }
          }}
        >
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22C55E" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#22C55E" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#EF4444" stopOpacity="0.0" />
              <stop offset="100%" stopColor="#EF4444" stopOpacity="0.3" />
            </linearGradient>
          </defs>

          {/* Grid Lines & Labels */}
          <g className="text-slate-600 font-mono text-[10px]">
            {/* Top / Mid / Bottom Equity Lines */}
            <line x1={paddingX} y1={paddingY} x2={width - 20} y2={paddingY} stroke="#1E293B" strokeDasharray="3,3" />
            <text x={paddingX - 8} y={paddingY + 3} textAnchor="end" fill="#64748B">
              ₹{(maxVal / 100000).toFixed(1)}L
            </text>

            <line x1={paddingX} y1={equityHeight / 2} x2={width - 20} y2={equityHeight / 2} stroke="#1E293B" strokeDasharray="3,3" />
            <text x={paddingX - 8} y={equityHeight / 2 + 3} textAnchor="end" fill="#64748B">
              ₹{(((maxVal + minVal) / 2) / 100000).toFixed(1)}L
            </text>

            <line x1={paddingX} y1={equityHeight} x2={width - 20} y2={equityHeight} stroke="#334155" />
            <text x={paddingX - 8} y={equityHeight + 3} textAnchor="end" fill="#64748B">
              ₹{(minVal / 100000).toFixed(1)}L
            </text>

            {/* Drawdown baseline & bottom */}
            <line x1={paddingX} y1={equityHeight + 30} x2={width - 20} y2={equityHeight + 30} stroke="#334155" />
            <text x={paddingX - 8} y={equityHeight + 33} textAnchor="end" fill="#64748B">0%</text>

            <line x1={paddingX} y1={height - 20} x2={width - 20} y2={height - 20} stroke="#1E293B" strokeDasharray="3,3" />
            <text x={paddingX - 8} y={height - 17} textAnchor="end" fill="#EF4444">
              {maxDD.toFixed(1)}%
            </text>
          </g>

          {/* Equity Shaded Area */}
          <path d={equityAreaPath} fill="url(#equityGradient)" />
          {/* Equity Line */}
          <path d={equityPath} fill="none" stroke="#22C55E" strokeWidth="2" strokeLinecap="round" />

          {/* Drawdown Shaded Area */}
          <path d={ddAreaPath} fill="url(#ddGradient)" />
          {/* Drawdown Line */}
          <path d={ddPath} fill="none" stroke="#EF4444" strokeWidth="1.5" strokeLinecap="round" />

          {/* Interactive Hover Crosshair */}
          {hoverIndex !== null && (
            <g>
              <line
                x1={getX(hoverIndex)}
                y1={paddingY}
                x2={getX(hoverIndex)}
                y2={height - 20}
                stroke="#38BDF8"
                strokeWidth="1"
                strokeDasharray="2,2"
              />
              <circle
                cx={getX(hoverIndex)}
                cy={getEquityY(hoveredPoint.portfolio_value)}
                r="4"
                fill="#22C55E"
                stroke="#020617"
                strokeWidth="2"
              />
              <circle
                cx={getX(hoverIndex)}
                cy={getDDY(hoveredPoint.drawdown)}
                r="3.5"
                fill="#EF4444"
                stroke="#020617"
                strokeWidth="2"
              />
            </g>
          )}
        </svg>
      </div>
    </div>
  );
};
