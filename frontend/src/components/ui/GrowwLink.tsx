import React from 'react';
import { ArrowUpRight } from 'lucide-react';

interface GrowwLinkProps {
  url: string;
  symbol?: string;
  className?: string;
  variant?: 'button' | 'icon' | 'compact';
}

export const GrowwLink: React.FC<GrowwLinkProps> = ({
  url,
  symbol,
  className = '',
  variant = 'button'
}) => {
  const effectiveUrl =
    url ||
    (symbol
      ? `https://groww.in/charts/stocks/${symbol.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-ltd?exchange=NSE`
      : '');

  if (!effectiveUrl) return null;

  if (variant === 'icon') {
    return (
      <a
        href={effectiveUrl}
        target="_blank"
        rel="noopener noreferrer"
        title={`Open ${symbol || 'stock'} interactive chart on Groww`}
        className={`inline-flex items-center justify-center w-8 h-8 rounded-xl bg-slate-900/90 hover:bg-emerald-500/20 text-slate-300 hover:text-emerald-300 border border-slate-700/80 hover:border-emerald-500/40 shadow-sm transition-all active:scale-95 ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        <ArrowUpRight className="w-4 h-4 text-emerald-400" />
      </a>
    );
  }

  if (variant === 'compact') {
    return (
      <a
        href={effectiveUrl}
        target="_blank"
        rel="noopener noreferrer"
        title={`Open ${symbol || 'stock'} on Groww Chart`}
        className={`inline-flex items-center gap-1 text-xs font-semibold text-emerald-400 hover:text-emerald-300 hover:underline transition-colors ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        <span>Groww</span>
        <ArrowUpRight className="w-3.5 h-3.5" />
      </a>
    );
  }

  return (
    <a
      href={effectiveUrl}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold font-sans bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 hover:text-white border border-emerald-500/30 hover:border-emerald-400 shadow-sm hover:shadow-[0_0_15px_rgba(0,255,157,0.2)] transition-all active:scale-95 ${className}`}
      onClick={(e) => e.stopPropagation()}
    >
      <span>Groww Chart</span>
      <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400" />
    </a>
  );
};
