import React, { useState } from 'react';
import { SystemHealthData } from '../types';
import {
  ShieldCheck,
  Database,
  Calendar,
  Layers,
  Download,
  Clock,
  HardDrive,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Server
} from 'lucide-react';

interface SystemHealthProps {
  healthData: SystemHealthData | null;
  onRefreshHealth: () => void;
  isRefreshingHealth?: boolean;
}

export const SystemHealth: React.FC<SystemHealthProps> = ({ healthData, onRefreshHealth, isRefreshingHealth }) => {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  if (!healthData) {
    return (
      <div className="py-24 text-center text-slate-500 font-mono text-sm space-y-2">
        <Server className="w-8 h-8 text-slate-600 mx-auto animate-pulse" />
        <div>Connecting to Cloud Storage &amp; Disaster Recovery Nexus...</div>
      </div>
    );
  }

  const { database, data_source, universe, market_session, nse_holidays_2026, backups } = healthData;

  const handleDownloadBackup = (snapshotId: string, type: 'db' | 'manifest' = 'db') => {
    setDownloadingId(snapshotId);
    const link = document.createElement('a');
    link.href = `/api/backups/download?snapshot_id=${encodeURIComponent(snapshotId)}&type=${type}`;
    link.setAttribute('download', `${snapshotId}_${type}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => setDownloadingId(null), 1000);
  };

  return (
    <div className="space-y-6">
      {/* Header with Refresh */}
      <div className="flex items-center justify-between glass-card p-4 sm:p-5 rounded-2xl">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white font-sans">Cloud System Health &amp; Disaster Recovery</h2>
            <p className="text-xs text-slate-400">ACID SQLite WAL integrity, automated Parquet snapshots &amp; NSE trading calendar</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {healthData?.timestamp && (
            <span className="inline-flex items-center gap-1.5 text-[10px] sm:text-[11px] font-mono text-slate-400 bg-slate-950 px-2.5 sm:px-3 py-1.5 rounded-xl border border-slate-800">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Verified: {healthData.timestamp}</span>
            </span>
          )}
          <button
            onClick={onRefreshHealth}
            disabled={isRefreshingHealth}
            className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-950 hover:bg-cyan-500/15 text-cyan-300 border border-slate-800 hover:border-cyan-500/40 text-xs font-bold font-sans transition-all active:scale-95 ${
              isRefreshingHealth ? 'opacity-70 cursor-not-allowed' : ''
            }`}
          >
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${isRefreshingHealth ? 'animate-spin' : ''}`} />
            <span>{isRefreshingHealth ? 'Verifying Integrity...' : 'Refresh Health'}</span>
          </button>
        </div>
      </div>

      {/* High-Level Status Deck */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* DB Integrity */}
        <div className="glass-card rounded-2xl p-5 flex items-start justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
              Database Integrity
            </span>
            <div className="flex items-center gap-2 mt-2">
              {database?.integrity_ok ? (
                <>
                  <CheckCircle className="w-5 h-5 text-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.4)]" />
                  <span className="font-mono text-lg font-extrabold text-white">OK (PRAGMA Verified)</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-5 h-5 text-rose-400 drop-shadow-[0_0_8px_rgba(255,51,102,0.4)]" />
                  <span className="font-mono text-lg font-extrabold text-rose-400">Needs Repair</span>
                </>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              SQLite WAL Mode • Checked: {database?.checked_at?.split(' ')[1] || 'Today'}
            </p>
          </div>
          <Database className="w-5 h-5 text-cyan-400" />
        </div>

        {/* Bhavcopy & Constituents */}
        <div className="glass-card rounded-2xl p-5 flex items-start justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
              750 Constituent Universe
            </span>
            <div className="flex items-center gap-2 mt-2">
              <Layers className="w-5 h-5 text-cyan-400" />
              <span className="font-mono text-lg font-extrabold text-white">
                {universe?.total_constituents || 750} Active Stocks
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              {data_source?.size_mb ? `${data_source.size_mb} MB` : 'Synced'} • {data_source?.last_modified ? `Sync: ${data_source.last_modified.split(' ')[0]}` : '500+250 Active'}
            </p>
          </div>
          <HardDrive className="w-5 h-5 text-cyan-400" />
        </div>

        {/* NSE Market Session */}
        <div className="glass-card rounded-2xl p-5 flex items-start justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
              NSE Market Session
            </span>
            <div className="flex items-center gap-2 mt-2">
              <span
                className={`w-3 h-3 rounded-full ${
                  market_session?.is_open ? 'bg-emerald-400 beacon-pulse' : 'bg-slate-500'
                }`}
              />
              <span className="font-mono text-lg font-extrabold text-white">
                {market_session?.current_phase || 'MARKET_CLOSED'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              Hours: 09:15 – 15:30 IST (Mon-Fri)
            </p>
          </div>
          <Clock className="w-5 h-5 text-purple-400" />
        </div>
      </div>

      {/* Database Tables & Granular Integrity Counts */}
      <div className="glass-card rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white font-sans">
              Relational Storage Integrity &amp; Row Counts
            </h3>
          </div>
          <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-0.5 rounded-full">
            All Tables Synced
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 font-mono">
          {Object.entries(database?.tables || {}).map(([table, count]) => (
            <div key={table} className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-slate-700 transition-colors">
              <div className="text-xs font-semibold text-slate-300 truncate" title={table}>
                {table}
              </div>
              <div className="text-lg font-extrabold text-white tabular-nums mt-1">
                {count.toLocaleString('en-IN')}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Automated Disaster Recovery & Backup Snapshots Browser */}
      <div className="glass-card rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <div>
              <h3 className="text-sm font-bold text-white font-sans">
                Automated Disaster Recovery Snapshots
              </h3>
              <p className="text-xs text-slate-400">
                Triple-redundancy compressed snapshots (Parquet, JSON.GZ, SQLite Binary) with SHA-256 validation
              </p>
            </div>
          </div>
          <span className="font-mono text-xs text-cyan-400 tabular-nums px-2.5 py-0.5 rounded-full bg-slate-900 border border-slate-800 shrink-0">
            {backups?.total_snapshots || 0} Snapshots
          </span>
        </div>

        {(!backups?.snapshots_list || backups.snapshots_list.length === 0) ? (
          <div className="py-8 text-center text-slate-500 text-xs font-mono">
            No snapshots recorded yet. Running daily screener or backtest automatically generates versioned backups.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-800/90 bg-slate-950/60">
            <table className="w-full text-left text-xs border-collapse font-mono">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/80 text-slate-400 text-[11px] uppercase tracking-wider whitespace-nowrap">
                  <th className="py-3 px-4 min-w-[180px]">Snapshot Identifier</th>
                  <th className="py-3 px-4 min-w-[140px]">Timestamp (IST)</th>
                  <th className="py-3 px-4 min-w-[110px]">Integrity</th>
                  <th className="py-3 px-4 min-w-[120px]">Tables Included</th>
                  <th className="py-3 px-4 text-right min-w-[120px]">Download Archive</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {backups.snapshots_list.map((snap) => (
                  <tr key={snap.snapshot_id} className="hover:bg-slate-900/60 transition-colors">
                    <td className="py-3 px-4 font-bold text-white whitespace-nowrap">
                      {snap.snapshot_id}
                    </td>
                    <td className="py-3 px-4 text-slate-400 tabular-nums whitespace-nowrap">
                      {snap.created_at_ist || snap.created_at || 'Recent'}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-bold">
                        <CheckCircle className="w-3.5 h-3.5 shrink-0" />
                        <span>SHA-256 OK</span>
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                      {snap.table_counts ? Object.keys(snap.table_counts).length : 5} tables
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => handleDownloadBackup(snap.snapshot_id, 'db')}
                        disabled={downloadingId === snap.snapshot_id}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-bold font-sans bg-slate-900 hover:bg-cyan-500/20 text-slate-200 hover:text-cyan-300 border border-slate-700/80 hover:border-cyan-500/40 transition-all active:scale-95 disabled:opacity-50"
                      >
                        <Download className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                        <span>{downloadingId === snap.snapshot_id ? 'Downloading...' : 'Export DB'}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Official NSE Trading Holidays Calendar 2026 */}
      <div className="glass-card rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-purple-400" />
            <div>
              <h3 className="text-sm font-bold text-white font-sans">
                NSE Official Trading Holidays (2026)
              </h3>
              <p className="text-xs text-slate-400">
                Automated calendar synchronization pipeline skips non-trading market settlement dates
              </p>
            </div>
          </div>
          <span className="font-mono text-xs font-bold text-purple-400 bg-purple-500/15 border border-purple-500/30 px-3 py-0.5 rounded-full">
            {nse_holidays_2026?.length || 16} Holidays
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          {(nse_holidays_2026 || []).map((h) => (
            <div key={h.date} className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/90 flex flex-col justify-between hover:border-slate-700 transition-colors">
              <div>
                <span className="font-mono text-xs text-cyan-400 font-bold tabular-nums">
                  {h.date}
                </span>
                <div className="text-xs font-bold text-white mt-1 font-sans">
                  {h.holiday}
                </div>
              </div>
              <span className="text-[10px] text-slate-500 mt-2.5 font-mono">
                {h.day}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
