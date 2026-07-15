@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m alpha_velocity.grade_outcomes_main
echo.
".venv\Scripts\python.exe" -m alpha_velocity.learning_main
echo.
pause
