@echo off
REM ==============================================================================
REM Autonomous Tech Fresher Job Pipeline - Windows Startup Runner
REM Automatically runs when Windows starts up.
REM Waits for network initialization, then executes the pipeline and logs results.
REM ==============================================================================

cd /d "%~dp0"

echo ====================================================================== >> "%~dp0agent_execution.log"
echo [STARTUP RUN] Windows Startup run triggered at %DATE% %TIME% >> "%~dp0agent_execution.log"
echo Waiting 30 seconds for network and Wi-Fi initialization... >> "%~dp0agent_execution.log"

REM Wait 30 seconds for Wi-Fi / Ethernet to connect after boot
timeout /t 30 /nobreak >nul

if exist "..\.venv\Scripts\python.exe" (
    echo Executing: "..\.venv\Scripts\python.exe" agent.py >> "%~dp0agent_execution.log"
    "..\.venv\Scripts\python.exe" "agent.py"
) else (
    echo Executing: python agent.py >> "%~dp0agent_execution.log"
    python "agent.py"
)

echo [STARTUP RUN COMPLETED] Finished at %DATE% %TIME% >> "%~dp0agent_execution.log"
echo ====================================================================== >> "%~dp0agent_execution.log"
