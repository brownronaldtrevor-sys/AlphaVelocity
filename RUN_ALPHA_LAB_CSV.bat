@echo off
REM Generate sample CSV data for Alpha Lab
REM Creates sample OHLCV data files for testing

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo Alpha Lab - Generate Sample CSV Data
echo ============================================================
echo.

REM Generate CSV data
.\.venv\Scripts\python.exe -m alpha_velocity.alpha_lab_main generate-csv --output-dir "./sample_data"

if errorlevel 1 (
    echo.
    echo Error: Failed to generate CSV data
    echo.
    exit /b 1
)

echo.
echo ============================================================
echo CSV data generated successfully
echo ============================================================
echo.

exit /b 0
