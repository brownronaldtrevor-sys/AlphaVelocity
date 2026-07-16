@echo off
REM Reconcile end-of-day paper session

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo Alpha Velocity - End-of-Day Paper Session Reconciliation
echo ======================================================
echo.
echo This will:
echo   - Connect to IBKR paper account
echo   - Retrieve fill confirmations
echo   - Reconcile orders with broker
echo   - Record all fills, cancellations, and errors
echo   - Generate end-of-day report
echo.

if "%1"=="" (
    echo ERROR: Session ID required
    echo Usage: RECONCILE_PAPER_SESSION.bat COMM-20260115-143000-12345678
    exit /b 1
)

.\.venv\Scripts\python.exe -m alpha_velocity.committee.cli reconcile --session-id %1

if errorlevel 1 (
    echo.
    echo ERROR: Reconciliation failed
    exit /b 1
)

echo.
echo Reconciliation completed
echo.

pause
