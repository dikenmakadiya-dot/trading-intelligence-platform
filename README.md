# Cloud-Native Multi-Strategy Trading Intelligence Platform

Institutional-grade, cloud-autonomous quantitative trading intelligence platform and signals nexus for the **NIFTY 750** universe (NIFTY 500 + NIFTY Microcap 250).

---

## 🌟 Overview
This platform automates data ingestion, 23 technical indicator computations, macro market regime gating, and breakout signal generation across multiple quantitative strategies:
- **Strategy 1**: Champion 3-Day RSI UP + Volume Surge + 52W High Breakout (with Macro Breadth Gate)
- **Strategy 2**: 5-Year High Breakout Momentum (Clean Candle Quality Filter)
- **Strategy 3**: GFS Multi-Timeframe RSI Swing Engine (Daily / Weekly / Monthly)

Technical charting is integrated directly with broker portals (**Groww**) via 1-tap direct hyperlinks.

---

## 📁 Repository Structure
```text
├── .github/
│   └── workflows/              # Headless cloud automation (Daily 4:15 PM IST Cron)
├── config/                     # Universal configuration & Groww slug mappers
├── src/
│   ├── core/                   # BaseStrategy abstract interface & loaders
│   ├── data_pipeline/          # Nifty 750 Bhavcopy ingestion & 23 indicators
│   ├── db/                     # Relational persistence & disaster recovery
│   │   ├── schema.sql          # Relational DDL tables and indexes
│   │   ├── database.py         # DatabaseManager with WAL & ACID transactions
│   │   ├── portfolio_manager.py# Active positions & mark-to-market tracker
│   │   ├── backup_manager.py   # Versioned compressed Parquet/JSON snapshots
│   │   └── restore_backup.py   # CLI disaster recovery & export utility
│   ├── strategies/             # Modularized strategy rule engines
│   └── orchestrator.py         # Headless CLI sequencer with DB persistence
├── tests/                      # Automated unit and integration test suite
├── output/                     # Consolidated payloads and disaster recovery backups
└── .gitignore                  # Protection against committing large datasets & DBs
```

---

## 💾 Database & Disaster Recovery (Phase 2)
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

---

## 🚀 Workflow
- **Development**: Local development, AI-assisted coding, and math verification using **Antigravity IDE**.
- **Version Control & Backup**: **GitHub** acts as the central logic vault and automated CI/CD runner.
- **Access**: Universal mobile/browser PWA for instant signal tracking from anywhere.

