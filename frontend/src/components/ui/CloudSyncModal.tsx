import React, { useState } from 'react';
import {
  Cloud,
  CheckCircle2,
  RefreshCw,
  ExternalLink,
  Calendar,
  Clock,
  Key,
  ShieldCheck,
  Zap,
  Play,
  X,
  Database
} from 'lucide-react';

interface CloudSyncModalProps {
  isOpen: boolean;
  onClose: () => void;
  mode: 'screener' | 'backtest';
  lastSyncTime?: string;
  onRefreshData: () => Promise<void>;
}

export const CloudSyncModal: React.FC<CloudSyncModalProps> = ({
  isOpen,
  onClose,
  mode,
  lastSyncTime,
  onRefreshData
}) => {
  const [activeTab, setActiveTab] = useState<'screener' | 'backtest'>(mode);
  const [isPullingData, setIsPullingData] = useState(false);
  const [pullStatus, setPullStatus] = useState<string | null>(null);
  
  // GitHub PAT for optional direct dispatch
  const [githubToken, setGithubToken] = useState<string>(() => {
    return localStorage.getItem('gh_actions_pat') || '';
  });
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchResult, setDispatchResult] = useState<{ success: boolean; message: string } | null>(null);

  if (!isOpen) return null;

  const REPO_OWNER = 'dikenmakadiya-dot';
  const REPO_NAME = 'trading-intelligence-platform';

  const handlePullData = async () => {
    setIsPullingData(true);
    setPullStatus(null);
    try {
      await onRefreshData();
      setPullStatus('Latest cloud dataset successfully synchronized!');
      setTimeout(() => setPullStatus(null), 4000);
    } catch (err: any) {
      setPullStatus(`Sync error: ${err.message || 'Failed to fetch cloud data'}`);
    } finally {
      setIsPullingData(false);
    }
  };

  const handleSaveToken = (val: string) => {
    setGithubToken(val);
    if (val) {
      localStorage.setItem('gh_actions_pat', val.trim());
    } else {
      localStorage.removeItem('gh_actions_pat');
    }
  };

  const handleDirectDispatch = async (workflowName: 'daily_screener_cron.yml' | 'manual_backtest.yml') => {
    if (!githubToken.trim()) {
      setShowTokenInput(true);
      return;
    }

    setIsDispatching(true);
    setDispatchResult(null);

    try {
      const res = await fetch(
        `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows/${workflowName}/dispatches`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${githubToken.trim()}`,
            Accept: 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            ref: 'main'
          })
        }
      );

      if (res.status === 204) {
        setDispatchResult({
          success: true,
          message: `Cloud pipeline successfully triggered! GitHub Actions is now executing ${
            workflowName === 'daily_screener_cron.yml' ? 'the Daily Screener' : 'the Backtest Simulation'
          }. It will automatically update and publish to this dashboard in ~2-3 minutes.`
        });
      } else {
        const errorData = await res.json().catch(() => ({}));
        setDispatchResult({
          success: false,
          message: errorData.message || `GitHub returned status ${res.status}. Check your token permissions (Actions: write required).`
        });
      }
    } catch (err: any) {
      setDispatchResult({
        success: false,
        message: err.message || 'Network error triggering cloud workflow.'
      });
    } finally {
      setIsDispatching(false);
    }
  };

  const githubActionsUrl = activeTab === 'screener'
    ? `https://github.com/${REPO_OWNER}/${REPO_NAME}/actions/workflows/daily_screener_cron.yml`
    : `https://github.com/${REPO_OWNER}/${REPO_NAME}/actions/workflows/manual_backtest.yml`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-slate-950 border border-slate-800 rounded-3xl shadow-2xl shadow-cyan-950/50 overflow-hidden font-sans">
        
        {/* Glow accent */}
        <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-cyan-500 via-emerald-500 to-cyan-500"></div>

        {/* Modal Header */}
        <div className="p-6 pb-4 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Cloud className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-wide">
                Cloud Pipeline & Sync Hub
              </h3>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                GitHub Actions Automated Execution & Data Synchronization
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-900 border border-transparent hover:border-slate-800 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs: Daily Screener vs Backtest */}
        <div className="px-6 pt-4 flex gap-2 border-b border-slate-900">
          <button
            onClick={() => setActiveTab('screener')}
            className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 flex items-center gap-2 ${
              activeTab === 'screener'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Daily Live Screener</span>
          </button>
          <button
            onClick={() => setActiveTab('backtest')}
            className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 flex items-center gap-2 ${
              activeTab === 'backtest'
                ? 'border-emerald-400 text-emerald-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Manual Backtest Simulation</span>
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-5 max-h-[70vh] overflow-y-auto">
          
          {/* Status Banner */}
          <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold">
              <span className="text-slate-400 flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>Last Published Cloud Data:</span>
              </span>
              <span className="font-mono text-cyan-300 bg-cyan-950/60 px-2.5 py-1 rounded-lg border border-cyan-800/50">
                {lastSyncTime || 'Active (Continuous Sync)'}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs font-semibold pt-2 border-t border-slate-800/80">
              <span className="text-slate-400 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-emerald-400" />
                <span>Automated Cron Schedule:</span>
              </span>
              <span className="font-mono text-emerald-300">
                {activeTab === 'screener' ? 'Mon-Fri at 4:15 PM IST (Market Close)' : 'Manual / On-Demand Only'}
              </span>
            </div>
          </div>

          {/* Workflow Explanation */}
          <div className="p-4 rounded-2xl bg-cyan-950/20 border border-cyan-500/20 text-xs text-slate-300 space-y-2">
            <div className="font-bold text-cyan-300 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              <span>How Cloud Execution Operates:</span>
            </div>
            {activeTab === 'screener' ? (
              <p className="leading-relaxed text-slate-300">
                The daily screener runs on GitHub's cloud servers. It first updates the <strong>5Y Historical Technical Data</strong> for 750 NSE stocks, then runs the <strong>3-Day RSI</strong> and <strong>5Y Breakout</strong> screeners, and automatically publishes the updated dashboard to GitHub Pages.
              </p>
            ) : (
              <p className="leading-relaxed text-slate-300">
                Backtesting simulates 5 years of historical executions across 750 stocks. To protect daily resources, it runs <strong>on-demand only</strong> via GitHub Actions and publishes audited KPIs directly to this dashboard.
              </p>
            )}
          </div>

          {/* Action Row 1: Instant Cache-Busted Pull */}
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <div className="text-xs font-bold text-white">
                Pull Latest Cloud Dataset
              </div>
              <div className="text-[11px] text-slate-400">
                Force-fetch newest published signals and bypass browser cache
              </div>
            </div>
            <button
              onClick={handlePullData}
              disabled={isPullingData}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 hover:text-white border border-cyan-500/40 active:scale-95 transition-all shrink-0 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isPullingData ? 'animate-spin' : ''}`} />
              <span>{isPullingData ? 'Syncing...' : 'Sync Cloud Data Now'}</span>
            </button>
          </div>

          {/* Pull Status feedback */}
          {pullStatus && (
            <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{pullStatus}</span>
            </div>
          )}

          {/* Action Row 2: Trigger Cloud Execution in GitHub Actions */}
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <div className="text-xs font-bold text-white">
                  Trigger Cloud Run on GitHub Actions
                </div>
                <div className="text-[11px] text-slate-400">
                  Execute the Python pipeline on GitHub's cloud infrastructure immediately
                </div>
              </div>

              {/* 1-Click Link to GitHub Actions */}
              <a
                href={githubActionsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 text-emerald-300 hover:text-white border border-emerald-500/40 hover:border-emerald-400 shadow-md shadow-emerald-950/40 active:scale-95 transition-all shrink-0"
              >
                <span>Open in GitHub Actions</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>

            {/* Direct Dispatch with Token */}
            <div className="pt-3 border-t border-slate-800/60">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setShowTokenInput(!showTokenInput)}
                  className="text-[11px] font-mono text-cyan-400 hover:underline flex items-center gap-1.5"
                >
                  <Key className="w-3.5 h-3.5" />
                  <span>{showTokenInput ? 'Hide GitHub Token' : 'Trigger directly from this page (Optional Token)'}</span>
                </button>

                {githubToken && (
                  <button
                    onClick={() => handleDirectDispatch(
                      activeTab === 'screener' ? 'daily_screener_cron.yml' : 'manual_backtest.yml'
                    )}
                    disabled={isDispatching}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-cyan-500 text-slate-950 hover:bg-cyan-400 active:scale-95 transition-all disabled:opacity-50"
                  >
                    <Play className={`w-3 h-3 ${isDispatching ? 'animate-spin' : ''}`} />
                    <span>{isDispatching ? 'Triggering...' : '1-Tap Run on Cloud'}</span>
                  </button>
                )}
              </div>

              {showTokenInput && (
                <div className="mt-3 p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                  <div className="text-[11px] text-slate-400">
                    Paste a GitHub Personal Access Token (with <code className="text-cyan-300 font-mono">repo</code> or <code className="text-cyan-300 font-mono">workflow</code> scope). It is stored solely in your browser's localStorage.
                  </div>
                  <input
                    type="password"
                    value={githubToken}
                    onChange={(e) => handleSaveToken(e.target.value)}
                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-400"
                  />
                  {githubToken && (
                    <div className="flex justify-end pt-1">
                      <button
                        onClick={() => handleDirectDispatch(
                          activeTab === 'screener' ? 'daily_screener_cron.yml' : 'manual_backtest.yml'
                        )}
                        disabled={isDispatching}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-500 to-emerald-500 text-slate-950 hover:brightness-110 active:scale-95 transition-all disabled:opacity-50"
                      >
                        <Play className="w-3.5 h-3.5" />
                        <span>Dispatch Workflow via GitHub API</span>
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Dispatch feedback */}
              {dispatchResult && (
                <div className={`mt-3 p-3 rounded-xl text-xs font-semibold flex items-start gap-2 ${
                  dispatchResult.success
                    ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-500/15 border border-rose-500/30 text-rose-300'
                }`}>
                  {dispatchResult.success ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <X className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  )}
                  <div className="leading-relaxed">{dispatchResult.message}</div>
                </div>
              )}
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-900/60 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="font-mono text-[11px]">Cloud Engine Ready</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-all"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
};
