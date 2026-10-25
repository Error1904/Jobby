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
if "%1"=="shortcut" goto CREATE_SHORTCUT
if "%1"=="desktop" goto CREATE_SHORTCUT

:CREATE_TASK
echo.
echo [1/3] Creating/Updating 9:00 PM Daily Scheduled Task...
schtasks /Create /SC DAILY /TN "%TASK_NAME%" /TR "\"%PYTHON_EXE%\" \"%AGENT_SCRIPT%\"" /ST 21:00 /F
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Daily task "%TASK_NAME%" registered for 9:00 PM.
) else (
    echo [WARNING] schtasks returned code %ERRORLEVEL%.
)

:ENABLE_STARTUP
echo.
echo [2/3] Configuring Auto-Run on Windows Startup...
powershell -NoProfile -Command "$wsh = New-Object -ComObject WScript.Shell; $startupDir = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup); $shortcut = $wsh.CreateShortcut((Join-Path $startupDir 'TechJobAgent_Startup.lnk')); $shortcut.TargetPath = 'wscript.exe'; $shortcut.Arguments = '\"%SILENT_VBS%\"'; $shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $shortcut.Description = 'Tech Job Agent Startup Runner'; $shortcut.Save(); Write-Host '[SUCCESS] Startup shortcut created at: ' $shortcut.FullName"
if "%1"=="enable-startup" goto END
if "%1"=="startup-only" goto END

:CREATE_SHORTCUT
echo.
echo [3/3] Creating Desktop Shortcuts (Interactive and Silent)...
powershell -NoProfile -Command "$wsh = New-Object -ComObject WScript.Shell; $desktop = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop); $s1 = $wsh.CreateShortcut((Join-Path $desktop 'Run Tech Job Agent.lnk')); $s1.TargetPath = (Join-Path '%SCRIPT_DIR%' 'run_daily.bat'); $s1.WorkingDirectory = '%SCRIPT_DIR%'; $s1.Description = 'Run Tech Job Agent (Mumbai MMR tech fresher jobs & Notion sync)'; $s1.IconLocation = '%PYTHON_EXE%,0'; $s1.Save(); Write-Host '[SUCCESS] Interactive Desktop shortcut created:' $s1.FullName; $s2 = $wsh.CreateShortcut((Join-Path $desktop 'Run Tech Job Agent (Silent).lnk')); $s2.TargetPath = 'wscript.exe'; $s2.Arguments = '\"%SILENT_VBS%\"'; $s2.WorkingDirectory = '%SCRIPT_DIR%'; $s2.Description = 'Run Tech Job Agent Silently in Background'; $s2.IconLocation = '%PYTHON_EXE%,0'; $s2.Save(); Write-Host '[SUCCESS] Silent Desktop shortcut created:     ' $s2.FullName"
if "%1"=="shortcut" goto END
if "%1"=="desktop" goto END
goto END

:CHECK_STATUS
echo.
echo --- Scheduled Task (9:00 PM) ---
schtasks /Query /TN "%TASK_NAME%" /FO LIST /V
echo.
echo --- Windows Startup Auto-Run Status ---
powershell -NoProfile -Command "$startupDir = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup); $shortcut = Join-Path $startupDir 'TechJobAgent_Startup.lnk'; if (Test-Path $shortcut) { Write-Host '[ENABLED] Startup shortcut exists:' $shortcut -ForegroundColor Green } else { Write-Host '[DISABLED] No startup shortcut found.' -ForegroundColor Yellow }"
echo.
echo --- Desktop Shortcuts Status ---
powershell -NoProfile -Command "$desktop = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop); $s1 = Join-Path $desktop 'Run Tech Job Agent.lnk'; $s2 = Join-Path $desktop 'Run Tech Job Agent (Silent).lnk'; if (Test-Path $s1) { Write-Host '[ENABLED] Interactive Desktop shortcut:' $s1 -ForegroundColor Green } else { Write-Host '[NOT FOUND] Interactive Desktop shortcut missing.' -ForegroundColor Yellow }; if (Test-Path $s2) { Write-Host '[ENABLED] Silent Desktop shortcut:     ' $s2 -ForegroundColor Green } else { Write-Host '[NOT FOUND] Silent Desktop shortcut missing.' -ForegroundColor Yellow }"
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
echo   setup_windows_scheduler.bat                 - Setup 9:00 PM task + Startup + Desktop Shortcuts
echo   setup_windows_scheduler.bat shortcut        - Create Desktop shortcuts only
echo   setup_windows_scheduler.bat run             - Trigger task immediately
echo   setup_windows_scheduler.bat status          - View scheduler, startup, and desktop status
echo   setup_windows_scheduler.bat enable-startup  - Enable startup run only
echo   setup_windows_scheduler.bat disable-startup - Disable startup run only
echo   setup_windows_scheduler.bat remove          - Delete 9:00 PM scheduled task
echo ======================================================================
