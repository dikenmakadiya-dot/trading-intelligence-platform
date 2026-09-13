import React from 'react';
import { ExternalLink } from 'lucide-react';

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
  if (!url) return null;

  if (variant === 'icon') {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        title={`Open ${symbol || 'stock'} on Groww Chart (NSE)`}
        className={`inline-flex items-center justify-center w-8 h-8 rounded-lg bg-slate-800/80 hover:bg-sky-500/20 text-slate-300 hover:text-sky-400 border border-slate-700 hover:border-sky-500/40 transition-all ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        <ExternalLink className="w-4 h-4" />
      </a>
    );
  }

  if (variant === 'compact') {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        title={`Open ${symbol || 'stock'} on Groww Chart`}
        className={`inline-flex items-center gap-1 text-xs font-medium text-sky-400 hover:text-sky-300 hover:underline transition-colors ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        <span>Groww</span>
        <ExternalLink className="w-3 h-3" />
      </a>
    );
  }

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 hover:text-sky-300 border border-sky-500/30 hover:border-sky-400 transition-all shadow-sm active:scale-95 ${className}`}
      onClick={(e) => e.stopPropagation()}
    >
      <span>Groww Chart</span>
      <ExternalLink className="w-3.5 h-3.5" />
    </a>
  );
};
