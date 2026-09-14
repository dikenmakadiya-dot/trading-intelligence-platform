# Cloud-Native Multi-Strategy Trading Intelligence Platform

Institutional-grade, cloud-autonomous quantitative trading intelligence platform and signals nexus for the **NIFTY 750** universe (NIFTY 500 + NIFTY Microcap 250).

---

## 🌟 Overview
This platform automates data ingestion, 23 technical indicator computations, macro market regime gating, and breakout signal generation across multiple quantitative strategies:
- **Strategy 1**: Champion 3-Day RSI UP + Volume Surge + 52W High Breakout (with Macro Breadth Gate)
- **Strategy 2**: 5-Year High Breakout Momentum (Clean Candle Quality Filter)
- **Strategy 3**: GFS Multi-Timeframe RSI Swing Engine (Daily / Weekly / Monthly)

Technical charting is integrated directly with broker portals (**Groww**) via 1-tap direct hyperlinks (`https://groww.in/charts/stocks/<slug>?exchange=NSE`).

---

## 🎨 Quantum Obsidian UI/UX Design System
The frontend is built with **React 18 + Vite + TypeScript + Tailwind CSS** as an institutional Progressive Web App (PWA):
- **Aesthetic**: Quantum Obsidian Dark OLED theme (`#030712`) with ambient radial mesh glow.
- **Glassmorphic Depth**: Smoked `.glass-card` surfaces with dual-layer specular highlight borders (`rgba(0,229,255,0.14)` and `inset 0 1px 0 rgba(255,255,255,0.08)`).
- **Typography**: `Plus Jakarta Sans` for clean titles + `JetBrains Mono` with `tabular-nums` alignment for zero-jitter figures.
- **Bento Grid Layout**: Macro Breadth Gate radial gauge, Active 5-Slot Portfolio Capacity Deck, Fresh Breakout Signals Matrix, and Verified 5Y Quantitative KPIs.
- **Large Dataset Virtualization**: Smooth 60 FPS scrolling across 750 stocks and 480+ historical trade executions powered by `@tanstack/react-virtual`.

---

## 📁 Repository Structure
```text
├── .github/
│   └── workflows/              # Headless cloud automation (Daily 4:15 PM IST Cron & GitHub Pages)
├── config/                     # Universal configuration & Groww slug mappers
├── frontend/                   # Quantum Obsidian React 18 + TypeScript PWA
│   ├── src/                    # Components, views (MasterStage, StrategyDashboard, SystemHealth)
│   ├── dist/                   # Production distribution bundle (pre-compiled PWA)
│   └── build_pwa.ps1           # High-performance local PWA compiler
├── src/
│   ├── api/                    # Lightweight standard library ThreadingHTTPServer (Port 8000)
│   ├── core/                   # BaseStrategy abstract interface & data loaders
│   ├── data_pipeline/          # Nifty 750 Bhavcopy ingestion & 23 indicators
│   ├── db/                     # Relational SQLite database with WAL & ACID transactions
│   │   ├── schema.sql          # Relational DDL tables and indexes
│   │   ├── database.py         # DatabaseManager with PRAGMA integrity verification
│   │   ├── portfolio_manager.py# Active positions & mark-to-market tracker
│   │   ├── backup_manager.py   # Versioned compressed Parquet/JSON snapshots
│   │   └── restore_backup.py   # CLI disaster recovery & export utility
│   ├── strategies/             # Modularized strategy rule engines
│   └── orchestrator.py         # Headless CLI sequencer with DB persistence
├── tests/                      # Automated unit and integration test suite (23 passing tests)
├── output/                     # Consolidated payloads and disaster recovery backups
├── start_dashboard.bat         # 1-Click Windows launcher (Starts server & opens browser)
└── .gitignore                  # Protection against committing large datasets & DBs
```

---

## 🚀 Running Locally

### 1-Click Launcher (Windows):
Double-click `start_dashboard.bat` or run:
```bash
start_dashboard.bat
```
This automatically serves the API and Quantum Obsidian PWA on `http://localhost:8000`.

### Manual CLI Start:
```bash
python -m src.api.server --port 8000
```

---

## 💾 Database & Disaster Recovery
The platform features an ACID-compliant relational SQLite database with automatic WAL concurrency mode and automated Parquet/JSON.GZ disaster recovery snapshots:
1. **Market Regime History**: Date, Breadth %, Gate Open/Closed status.
2. **Consolidated Daily Signals**: Multi-strategy triggers, ranks, SLs, Groww URLs.
3. **Active Portfolio Positions**: Entry price, current price, trailing SL, P&L %, days held.
4. **Strategy KPIs & Trade Logs**: Sharpe, Sortino, Calmar, MDD, CAGR, expectancy.

### Disaster Recovery CLI (`src/db/restore_backup.py`):
```bash
# List available backup snapshots
python src/db/restore_backup.py --list

# Run database integrity check
python src/db/restore_backup.py --verify

# Trigger an immediate manual backup snapshot
python src/db/restore_backup.py --backup --tag manual_run

# Export all tables to Parquet, JSON, or CSV
python src/db/restore_backup.py --export-all output/exports --format parquet

# Restore database from snapshot
python src/db/restore_backup.py --restore snapshot_2026-09-13_111328_daily_screener
```

---

## 🧪 Testing & Verification
Execute the automated test suite:
```bash
python -m unittest discover -s tests -p "test_*.py"
```
*(All 23 tests pass covering database integrity, backup snapshot creation & restore, API endpoints, and orchestrator integration).*

---

## 🌐 Cloud CI/CD & GitHub Pages Deployment
- **Daily Screener Cron** (`.github/workflows/daily_screener_cron.yml`): Runs automatically Monday through Friday at 4:15 PM IST (10:45 UTC), executing the multi-strategy screener, saving signals, and caching database backups.
- **GitHub Pages PWA Deploy** (`.github/workflows/deploy_pwa.yml`): Automatically builds and deploys the latest Quantum Obsidian PWA bundle to GitHub Pages whenever changes are pushed to `main`.
