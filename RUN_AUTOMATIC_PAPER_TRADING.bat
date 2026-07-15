@echo off
cd /d "%~dp0"
echo ===================================================
echo  ALPHA VELOCITY - AUTOMATIC IBKR PAPER TRADING
echo ===================================================
echo.
echo HARD LIMITS:
echo - IBKR DU paper account only
echo - Maximum 3 selected stocks
echo - Maximum 10 percent per position
echo - Maximum 30 percent gross exposure
echo - Long stocks only
echo - Bracket orders required
echo.
choice /M "Transmit the generated orders to your IBKR PAPER account"
if errorlevel 2 exit /b 0
".venv\Scripts\python.exe" -m alpha_velocity.paper_trade_main --config config.paper.yaml --research-folder research_reports
echo.
pause
