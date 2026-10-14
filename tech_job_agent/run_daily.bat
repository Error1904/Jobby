@echo off
REM Launcher script for Tech Job Agent Daily Run
cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" "agent.py"
) else (
    python "agent.py"
)
