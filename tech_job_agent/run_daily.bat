@echo off
title Tech Job Agent - Mumbai MMR Pipeline Runner
color 0A
setlocal enabledelayedexpansion

REM ==============================================================================
REM Autonomous Tech Fresher Job Pipeline - Manual / Catch-up Runner
REM Useful when laptop was off during the 9:00 PM scheduled run.
REM ==============================================================================

cd /d "%~dp0"

echo ======================================================================
echo    TECH JOB AGENT - MUMBAI MMR PIPELINE RUNNER
echo ======================================================================
echo  Triggered at:  %DATE% %TIME%
echo  Target Scope:  Mumbai, Navi Mumbai, Thane (0-1 Yrs Tech Freshers)
echo  Sync Target:   Local SQLite + Notion Database
echo  Log File:      %~dp0agent_execution.log
echo ======================================================================
echo.

if exist "..\.venv\Scripts\python.exe" (
    set "PYTHON_EXEC=..\.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXEC=python"
)

echo [RUNNING] Executing autonomous pipeline via %PYTHON_EXEC%...
echo.

"%PYTHON_EXEC%" "agent.py"
set EXIT_CODE=%ERRORLEVEL%

echo.
echo ======================================================================
if %EXIT_CODE% EQU 0 (
    echo [SUCCESS] Pipeline execution finished successfully at %DATE% %TIME%!
    echo Check your Notion database and 'agent_execution.log' for details.
) else (
    echo [WARNING] Pipeline exited with status code %EXIT_CODE%.
    echo Please inspect 'agent_execution.log' for details.
)
echo ======================================================================
echo.
echo Press any key to close this window...
pause >nul
