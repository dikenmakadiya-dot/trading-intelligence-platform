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
│   ├── strategies/             # Modularized strategy rule engines
│   └── orchestrator.py         # Headless CLI sequencer
├── frontend/                   # Universal PWA web application
└── .gitignore                  # Protection against committing large datasets
```

---

## 🚀 Workflow
- **Development**: Local development, AI-assisted coding, and math verification using **Antigravity IDE**.
- **Version Control & Backup**: **GitHub** acts as the central logic vault and automated CI/CD runner.
- **Access**: Universal mobile/browser PWA for instant signal tracking from anywhere.
