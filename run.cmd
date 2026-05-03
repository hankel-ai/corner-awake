@echo off
:: ============================================================
::  Corner Awake - launcher (no install)
::  Use install_and_run.bat for first-time setup.
:: ============================================================

where pythonw >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pythonw not found on PATH.
    echo         Run install_and_run.bat first, or install Python 3.9+ with "Add to PATH".
    pause
    exit /b 1
)

start "" pythonw "%~dp0corner_awake.pyw"
