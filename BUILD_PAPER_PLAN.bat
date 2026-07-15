@echo off
cd /d "%~dp0"
echo Building a PAPER-ONLY stock-selection and order plan.
echo This command does not submit orders.
echo.
".venv\Scripts\python.exe" -m alpha_velocity.paper_plan_main --research-folder research_reports --equity 100000
echo.
pause
