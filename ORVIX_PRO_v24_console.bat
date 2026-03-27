@echo off
title Orvix Lite — console (debug)
cd /d "%~dp0"
echo Starting Orvix... This window stays open until the app exits.
echo.

where py >nul 2>&1
if %errorlevel% equ 0 (
  py -3 "%~dp0ORVIX_PRO_v24.py"
  echo.
  echo Exit code: %errorlevel%
  pause
  exit /b %errorlevel%
)

where python >nul 2>&1
if %errorlevel% equ 0 (
  python "%~dp0ORVIX_PRO_v24.py"
  echo.
  echo Exit code: %errorlevel%
  pause
  exit /b %errorlevel%
)

echo [ERROR] Neither py nor python found in PATH.
pause
exit /b 1
