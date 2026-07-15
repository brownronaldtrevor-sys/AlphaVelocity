@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run SETUP_WINDOWS.bat first.
  pause
  exit /b 1
)
echo Alpha Velocity SAFE TWS connection test
echo This command reads account state and submits NO strategy orders.
".venv\Scripts\python.exe" -m alpha_velocity.main --config config.yaml --connect
echo.
pause
