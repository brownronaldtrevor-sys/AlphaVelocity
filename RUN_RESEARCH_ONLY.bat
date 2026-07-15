@echo off
cd /d "%~dp0"
echo Alpha Velocity RESEARCH-ONLY run
echo Downloads market data, ranks the configured watchlist, and submits NO orders.
echo.
".venv\Scripts\python.exe" -m alpha_velocity.research_main --config config.yaml
echo.
pause
