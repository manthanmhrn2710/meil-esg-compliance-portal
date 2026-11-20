@echo off
title BRSR-Report
cd /d "%~dp0backend"

echo ============================================================
echo   BRSR-Report
echo ============================================================
echo.

echo [1/2] Installing dependencies...
python -m pip install -q -r requirements.txt

echo [2/2] Starting server...
echo.
echo   Open browser: http://localhost:5000
echo   Login: director@meil.com / brsr@2026
echo.
echo   Press Ctrl+C to stop
echo.

python -m app.launcher
pause
