@echo off
REM Run daily investment committee in explicit dry-run mode with detailed output

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo Alpha Velocity Daily Investment Committee - DRY RUN MODE
echo =======================================================
echo.
echo This run will:
echo   - Scan the investable universe
echo   - Rank all opportunities
echo   - Create a capital allocation proposal
echo   - Submit to risk and governance review
echo   - NOT submit any orders to the paper broker
echo.

.\.venv\Scripts\python.exe -m alpha_velocity.committee.cli run --dry-run --config config.committee.yaml

if errorlevel 1 (
    echo.
    echo ERROR: Committee workflow failed
    exit /b 1
)

echo.
echo Dry-run completed successfully
echo Next: Review the morning report before submission
echo.

pause
