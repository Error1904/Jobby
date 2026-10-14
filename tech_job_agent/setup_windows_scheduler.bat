@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM Autonomous Tech Fresher Job Pipeline - Windows Task & Startup Manager
REM Configures:
REM   1. Daily 9:00 PM run via Windows Task Scheduler
REM   2. Auto-run on Windows boot/startup (silent background execution)
REM ==============================================================================

set TASK_NAME=TechJobAgent_Mumbai_9PM
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe
set AGENT_SCRIPT=%SCRIPT_DIR%agent.py
set SILENT_VBS=%SCRIPT_DIR%run_on_startup_silent.vbs

echo ======================================================================
echo    TECH JOB AGENT - WINDOWS SCHEDULER ^& STARTUP SETUP
echo ======================================================================
echo Task Name:      %TASK_NAME%
echo Schedule:       Daily at 21:00 (9:00 PM) + Auto-run on Startup
echo Python Exec:    %PYTHON_EXE%
echo Agent Script:   %AGENT_SCRIPT%
echo ======================================================================

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment Python not found at %PYTHON_EXE%!
    echo Please make sure the .venv environment is created in the project root.
    pause
    exit /b 1
)

if "%1"=="remove" goto REMOVE_TASK
if "%1"=="status" goto CHECK_STATUS
if "%1"=="run" goto RUN_NOW
if "%1"=="enable-startup" goto ENABLE_STARTUP
if "%1"=="disable-startup" goto DISABLE_STARTUP
if "%1"=="startup-only" goto ENABLE_STARTUP

:CREATE_TASK
echo.
echo [1/2] Creating/Updating 9:00 PM Daily Scheduled Task...
schtasks /Create /SC DAILY /TN "%TASK_NAME%" /TR "\"%PYTHON_EXE%\" \"%AGENT_SCRIPT%\"" /ST 21:00 /F
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Daily task "%TASK_NAME%" registered for 9:00 PM.
) else (
    echo [WARNING] schtasks returned code %ERRORLEVEL%.
)

:ENABLE_STARTUP
echo.
echo [2/2] Configuring Auto-Run on Windows Startup...
powershell -NoProfile -Command "$wsh = New-Object -ComObject WScript.Shell; $startupDir = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup); $shortcut = $wsh.CreateShortcut((Join-Path $startupDir 'TechJobAgent_Startup.lnk')); $shortcut.TargetPath = 'wscript.exe'; $shortcut.Arguments = '\"%SILENT_VBS%\"'; $shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $shortcut.Description = 'Tech Job Agent Startup Runner'; $shortcut.Save(); Write-Host '[SUCCESS] Startup shortcut created at: ' $shortcut.FullName"
if "%1"=="enable-startup" goto END
if "%1"=="startup-only" goto END
goto END

:CHECK_STATUS
echo.
echo --- Scheduled Task (9:00 PM) ---
schtasks /Query /TN "%TASK_NAME%" /FO LIST /V
echo.
echo --- Startup Auto-Run Status ---
powershell -NoProfile -Command "$startupDir = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup); $shortcut = Join-Path $startupDir 'TechJobAgent_Startup.lnk'; if (Test-Path $shortcut) { Write-Host '[ENABLED] Startup shortcut exists:' $shortcut -ForegroundColor Green } else { Write-Host '[DISABLED] No startup shortcut found.' -ForegroundColor Yellow }"
goto END

:RUN_NOW
echo.
echo Manually triggering scheduled task "%TASK_NAME%" now...
schtasks /Run /TN "%TASK_NAME%"
goto END

:REMOVE_TASK
echo.
echo Removing scheduled task "%TASK_NAME%"...
schtasks /Delete /TN "%TASK_NAME%" /F
echo Task removed.
goto END

:DISABLE_STARTUP
echo.
echo Removing Windows Startup auto-run shortcut...
powershell -NoProfile -Command "$startupDir = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup); $shortcut = Join-Path $startupDir 'TechJobAgent_Startup.lnk'; if (Test-Path $shortcut) { Remove-Item $shortcut -Force; Write-Host '[REMOVED] Startup shortcut removed successfully.' -ForegroundColor Green } else { Write-Host 'Startup shortcut was not installed.' }"
goto END

:END
echo.
echo ======================================================================
echo Available management commands:
echo   setup_windows_scheduler.bat                 - Setup both 9:00 PM daily + Startup
echo   setup_windows_scheduler.bat run             - Trigger task immediately
echo   setup_windows_scheduler.bat status          - View scheduler and startup status
echo   setup_windows_scheduler.bat enable-startup  - Enable startup run only
echo   setup_windows_scheduler.bat disable-startup - Disable startup run only
echo   setup_windows_scheduler.bat remove          - Delete 9:00 PM scheduled task
echo ======================================================================
