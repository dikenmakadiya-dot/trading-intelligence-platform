@echo off
title QuantFlow - Unified Daily Pipeline & Intelligence Platform
color 0b
echo ======================================================================
echo           QUANTFLOW INSTITUTIONAL TRADING INTELLIGENCE
echo                Automated Daily Pipeline Runner
echo ======================================================================
echo.
cd /d "%~dp0"

echo [STAGE 1/3] Refreshing 5Y NIFTY 750 Base Technical Historical Data...
echo ----------------------------------------------------------------------
if exist "..\5Y Stock Historical Data\RUN_DAILY_PIPELINE.bat" (
    echo Calling 5Y Stock Historical Data update pipeline...
    call "..\5Y Stock Historical Data\RUN_DAILY_PIPELINE.bat"
) else (
    echo Executing python data pipeline updater...
    python src\data_pipeline\update_daily_nifty750.py
)
echo.
echo [STAGE 1 COMPLETE] Base historical data refreshed successfully.
echo.

echo [STAGE 2/3] Running Live Multi-Strategy Breakout Screeners...
echo ----------------------------------------------------------------------
python src\orchestrator.py --mode screener
echo.
echo [STAGE 2 COMPLETE] Fresh daily breakout triggers generated and consolidated.
echo.

echo [STAGE 3/3] Syncing Data and Starting QuantFlow Platform on Port 8000...
echo ----------------------------------------------------------------------
if not exist "frontend\dist\data" mkdir "frontend\dist\data"
if exist "output\consolidated_signals.json" copy /Y "output\consolidated_signals.json" "frontend\dist\data\consolidated_signals.json" >nul
if exist "data\verified_backtest_data.json" copy /Y "data\verified_backtest_data.json" "frontend\dist\data\verified_backtest_data.json" >nul

echo Starting browser on http://localhost:8000 ...
start http://localhost:8000
echo Running QuantFlow Server (Press Ctrl+C to stop)...
python -m src.api.server --port 8000

pause
