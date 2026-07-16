@echo off
REM Run Alpha Lab with sample data
REM Runs Swing Repricing and Turtle Trend strategies
REM Sample mode: dry_run=true, transmit=false, execution_authorized=false

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo Alpha Lab - Run with Sample Data
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

REM Run both strategies
.\.venv\Scripts\python.exe -m alpha_velocity.alpha_lab_main run ^
    --strategy all ^
    --warehouse-path "./warehouse.db" ^
    --output "./alpha_lab_results.json"

if errorlevel 1 (
    echo.
    echo Error: Failed to run Alpha Lab
    echo.
    exit /b 1
)

echo.
echo ============================================================
echo Alpha Lab run completed
echo ============================================================
echo.

if exist "alpha_lab_results.json" (
    set "full_path=%cd%\alpha_lab_results.json"
    echo Results saved to: !full_path!
    echo.
    echo Opening results in default application...
    start "" "!full_path!"
)

exit /b 0
