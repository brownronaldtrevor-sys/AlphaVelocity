@echo off
REM Run Swing Repricing strategy with sample data
REM Focus: Equities with weekly structure, daily breakout, and catalysts
REM Sample mode: dry_run=true, transmit=false, execution_authorized=false

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo Swing Repricing Strategy - Sample Run
echo ============================================================
echo.

REM Check if warehouse exists
if not exist "warehouse.db" (
    echo Error: warehouse.db not found
    echo.
    echo Please run BUILD_ALPHA_LAB_SAMPLE_DATA.bat first:
    echo   .\BUILD_ALPHA_LAB_SAMPLE_DATA.bat
    echo.
    exit /b 1
)

REM Run Swing Repricing strategy only
.\.venv\Scripts\python.exe -m alpha_velocity.alpha_lab_main run ^
    --strategy swing-repricing ^
    --warehouse-path "./warehouse.db" ^
    --output "./swing_repricing_results.json"

if errorlevel 1 (
    echo.
    echo Error: Failed to run Swing Repricing strategy
    echo.
    exit /b 1
)

echo.
echo ============================================================
echo Swing Repricing strategy completed
echo ============================================================
echo.

if exist "swing_repricing_results.json" (
    echo Results saved to: swing_repricing_results.json
    echo.
)

exit /b 0
