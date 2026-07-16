@echo off
REM Build Alpha Lab sample data in warehouse
REM Generates 5 equities and 4 futures for testing strategies

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo Alpha Lab - Build Sample Data
echo ============================================================
echo.

REM Run the build-sample-data command
.\.venv\Scripts\python.exe -m alpha_velocity.alpha_lab_main build-sample-data --warehouse-path "./warehouse.db"

if errorlevel 1 (
    echo.
    echo Error: Failed to build sample data
    echo.
    exit /b 1
)

echo.
echo ============================================================
echo Sample data built successfully
echo ============================================================
echo.

exit /b 0
