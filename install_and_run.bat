@echo off
:: ============================================================
::  Corner Awake – installer + launcher
::  Run this once.  After that you can launch corner_awake.pyw
::  directly (or add it to your Startup folder).
:: ============================================================

title Corner Awake – Setup

echo.
echo  ================================================
echo   Corner Awake – Installing dependencies...
echo  ================================================
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.  Install Python 3.9+ from https://python.org
    echo          Make sure "Add Python to PATH" is checked during install.
    pause
    exit /b 1
)

:: Install required packages quietly
echo  Installing pystray and Pillow ...
python -m pip install --upgrade pystray Pillow --quiet

if errorlevel 1 (
    echo.
    echo  [ERROR] pip install failed.  Try running this script as Administrator,
    echo          or run:  pip install pystray Pillow
    pause
    exit /b 1
)

echo.
echo  Dependencies installed successfully.
echo.
echo  ================================================
echo   Launching Corner Awake in the system tray...
echo  ================================================
echo.

:: Launch without a console window (pythonw)
start "" pythonw "%~dp0corner_awake.pyw"

echo  Done!  Look for the grey circle in your system tray.
echo.
echo  Usage:
echo    - Drag mouse to LOWER-RIGHT corner  ^→  sleep blocked  (rising beep + green icon)
echo    - Move mouse away                   ^→  sleep allowed  (falling beep + grey icon)
echo    - Right-click tray icon ^→ Quit
echo.
echo  To run on Windows startup, place a shortcut to corner_awake.pyw in:
echo    %%APPDATA%%\Microsoft\Windows\Start Menu\Programs\Startup
echo.
timeout /t 5 >nul
