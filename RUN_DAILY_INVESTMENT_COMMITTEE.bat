@echo off
REM Run daily investment committee in dry-run mode (default, safe)

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo Alpha Velocity Daily Investment Committee Orchestrator
echo ======================================================
echo.
echo Running in DRY-RUN mode (default)
echo No paper submissions will be made unless explicitly approved
echo.

.\.venv\Scripts\python.exe -m alpha_velocity.committee.cli run --dry-run

if errorlevel 1 (
    echo.
    echo ERROR: Committee workflow failed
    exit /b 1
)

echo.
echo Committee session created successfully
echo.
echo Next steps:
echo   1. Review the morning report
echo   2. If approved, run: RUN_DAILY_INVESTMENT_COMMITTEE_SUBMIT.bat
echo.

pause
