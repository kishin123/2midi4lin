@echo off
chcp 65001 >nul
title 2midi4lin Dev Mode
cd /d "%~dp0"
echo ============================================
echo   2midi4lin Dev Mode - hot reload + GUI
echo   edit frontend, save, window auto refresh
echo   close GUI window to exit
echo ============================================
echo.

python -m src.cli dev

echo.
echo GUI exited.
pause
