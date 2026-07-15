@echo off
cd /d "%~dp0"
echo Alpha Velocity SAFE TWS connection test
echo This reads account state and submits NO strategy orders.
echo.
".venv\Scripts\python.exe" -m alpha_velocity.main --config config.yaml --connect
echo.
pause
