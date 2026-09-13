@echo off
title QuantFlow Trading Intelligence Platform
echo ======================================================================
echo  Starting QuantFlow Trading Intelligence Platform
echo  Serving API and Progressive Web App (PWA) on http://localhost:8000
echo ======================================================================
echo.

cd /d "%~dp0"
start http://localhost:8000
python -m src.api.server --port 8000

pause
