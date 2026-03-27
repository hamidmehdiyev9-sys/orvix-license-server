@echo off
title Orvix Lite
cd /d "%~dp0"
if exist "C:\Python312\python.exe" (
  "C:\Python312\python.exe" "%~dp0ORVIX_PRO_v24.py"
) else (
  py -3 "%~dp0ORVIX_PRO_v24.py"
)
if errorlevel 1 pause
