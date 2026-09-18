import React, { useState, useEffect } from 'react';
import { Cloud, Key, CheckCircle, AlertCircle, ExternalLink, X, Shield, RefreshCw } from 'lucide-react';
import { getStoredGitHubToken, setStoredGitHubToken, clearStoredGitHubToken } from '../services/api';

interface CloudConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnected?: () => void;
}

export const CloudConnectModal: React.FC<CloudConnectModalProps> = ({ isOpen, onClose, onConnected }) => {
  const [token, setToken] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      const stored = getStoredGitHubToken();
      if (stored) {
        setToken(stored);
        setIsConnected(true);
      } else {
        setIsConnected(false);
      }
      setStatusMessage(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = async () => {
    if (!token.trim()) {
      setStatusMessage('Please enter a valid GitHub token.');
      return;
    }

    setIsTesting(true);
    setStatusMessage('Verifying GitHub Actions permissions...');

    try {
      // Test the token against GitHub API
      const res = await fetch('https://api.github.com/repos/dikenmakadiya-dot/trading-intelligence-platform/actions/workflows', {
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'Authorization': `Bearer ${token.trim()}`
        }
      });

      if (res.ok) {
        setStoredGitHubToken(token.trim());
        setIsConnected(true);
        setStatusMessage('Connected successfully! You can now run cloud scans anytime, anywhere.');
        setTimeout(() => {
          if (onConnected) onConnected();
          onClose();
        }, 1500);
      } else {
        const data = await res.json();
        setStatusMessage(`GitHub API returned ${res.status}: ${data.message || 'Invalid permissions. Ensure token has repo or workflow scope.'}`);
      }
    } catch (err: any) {
      setStatusMessage(`Connection failed: ${err.message}`);
    } finally {
      setIsTesting(false);
    }
  };

  const handleDisconnect = () => {
    clearStoredGitHubToken();
    setToken('');
    setIsConnected(false);
    setStatusMessage('Cloud connection removed.');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-lg glass-card rounded-2xl border border-cyan-500/30 p-6 shadow-2xl bg-slate-950/95 space-y-5">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Cloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white font-sans">100% Cloud Automation</h2>
              <p className="text-xs text-slate-400">Run Market Scans &amp; Backtests Anywhere, Anytime</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status Indicator */}
        <div className={`p-3.5 rounded-xl border flex items-center justify-between text-xs font-mono ${
          isConnected ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300' : 'bg-slate-900 border-slate-800 text-slate-400'
        }`}>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            )}
            <span>{isConnected ? 'GitHub Actions Cloud Runner: CONNECTED' : 'Status: LOCAL / DISCONNECTED'}</span>
          </div>
          {isConnected && (
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">ACTIVE</span>
          )}
        </div>

        {/* Explanation */}
        <div className="space-y-2 text-xs text-slate-300">
          <p>
            Connect your personal GitHub Token once to trigger automated cloud virtual machines directly from your phone, laptop, or tablet.
          </p>
          <div className="flex items-center gap-2 text-slate-400 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
            <Shield className="w-4 h-4 text-cyan-400 shrink-0" />
            <span className="text-[11px]">Your token is stored safely only in your device's browser (localStorage) and never sent to third-party servers.</span>
          </div>
        </div>

        {/* Token Input */}
        <div className="space-y-2">
          <label className="block text-xs font-bold font-mono uppercase tracking-wider text-slate-300">
            GitHub Personal Access Token (PAT)
          </label>
          <div className="relative">
            <Key className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx or github_pat_..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 text-xs font-mono text-white placeholder:text-slate-600 outline-none transition-colors"
            />
          </div>
          <div className="flex items-center justify-between text-[11px] pt-1">
            <a
              href="https://github.com/settings/tokens/new?scopes=repo,workflow&description=QuantFlow+Cloud+Dispatcher"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              <span>Generate GitHub Token in 10s (repo + workflow scope)</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>

        {/* Status Message */}
        {statusMessage && (
          <div className="text-xs font-mono text-cyan-300 bg-cyan-950/40 border border-cyan-500/20 p-2.5 rounded-lg">
            {statusMessage}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-800">
          {isConnected ? (
            <button
              onClick={handleDisconnect}
              className="px-3.5 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-xs font-bold font-sans transition-all"
            >
              Disconnect
            </button>
          ) : (
            <div></div>
          )}
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-bold font-sans transition-all"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isTesting}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 hover:from-cyan-400 hover:to-emerald-400 text-black font-extrabold text-xs font-sans shadow-lg shadow-cyan-500/25 transition-all active:scale-95 disabled:opacity-50"
            >
              {isTesting ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Connecting...</span>
                </>
              ) : (
                <span>Save &amp; Connect Cloud</span>
              )}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
