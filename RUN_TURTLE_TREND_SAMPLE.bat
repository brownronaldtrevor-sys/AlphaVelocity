@echo off
REM Run Turtle Trend strategy with sample data
REM Focus: Futures with trend-following channel breakouts and volatility sizing
REM Sample mode: dry_run=true, transmit=false, execution_authorized=false

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo Turtle Trend Strategy - Sample Run
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

REM Run Turtle Trend strategy only
.\.venv\Scripts\python.exe -m alpha_velocity.alpha_lab_main run ^
    --strategy turtle-trend ^
    --warehouse-path "./warehouse.db" ^
    --output "./turtle_trend_results.json"

if errorlevel 1 (
    echo.
    echo Error: Failed to run Turtle Trend strategy
    echo.
    exit /b 1
)

echo.
echo ============================================================
echo Turtle Trend strategy completed
echo ============================================================
echo.

if exist "turtle_trend_results.json" (
    echo Results saved to: turtle_trend_results.json
    echo.
)

exit /b 0
