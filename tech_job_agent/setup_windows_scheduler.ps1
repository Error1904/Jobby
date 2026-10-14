# ==============================================================================
# Autonomous Tech Fresher Job Pipeline - Windows Task Scheduler & Startup Setup
# Configures:
#   1. Daily 9:00 PM scheduled task via Windows Task Scheduler
#   2. Windows Startup auto-run (silent background execution)
# ==============================================================================

param (
    [string]$Action = "all" # all, create, enable-startup, disable-startup, run, status, remove
)

$TaskName = "TechJobAgent_Mumbai_9PM"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$AgentScript = Join-Path $ScriptDir "agent.py"
$SilentVbs = Join-Path $ScriptDir "run_on_startup_silent.vbs"
$StartupDir = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup)
$StartupShortcut = Join-Path $StartupDir "TechJobAgent_Startup.lnk"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   TECH JOB AGENT - WINDOWS SCHEDULER & STARTUP SETUP" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Task Name:        $TaskName"
Write-Host "Schedule:         Daily at 21:00 (9:00 PM)"
Write-Host "Startup Auto-Run: $StartupShortcut"
Write-Host "Python Exec:      $PythonExe"
Write-Host "Agent Script:     $AgentScript"
Write-Host "======================================================================" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    Write-Error "Virtual environment Python executable not found at: $PythonExe"
    exit 1
}

function Register-DailyTask {
    Write-Host "`n[1/2] Registering 9:00 PM Daily Scheduled Task..." -ForegroundColor Yellow
    & schtasks /Create /SC DAILY /TN $TaskName /TR "`"$PythonExe`" `"$AgentScript`"" /ST 21:00 /F
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Daily task '$TaskName' registered for 9:00 PM." -ForegroundColor Green
    } else {
        Write-Warning "schtasks returned exit code $LASTEXITCODE."
    }
}

function Enable-StartupRun {
    Write-Host "`n[2/2] Configuring Auto-Run on Windows Startup..." -ForegroundColor Yellow
    try {
        $wsh = New-Object -ComObject WScript.Shell
        $shortcut = $wsh.CreateShortcut($StartupShortcut)
        $shortcut.TargetPath = "wscript.exe"
        $shortcut.Arguments = "`"$SilentVbs`""
        $shortcut.WorkingDirectory = $ScriptDir
        $shortcut.Description = "Tech Job Agent Startup Runner"
        $shortcut.Save()
        Write-Host "[SUCCESS] Windows Startup auto-run enabled: $StartupShortcut" -ForegroundColor Green
        Write-Host "The agent will automatically run silently in the background when your computer starts." -ForegroundColor Green
    } catch {
        Write-Error "Failed to create startup shortcut: $_"
    }
}

function Disable-StartupRun {
    Write-Host "`nDisabling Windows Startup auto-run..." -ForegroundColor Yellow
    if (Test-Path $StartupShortcut) {
        Remove-Item $StartupShortcut -Force
        Write-Host "[SUCCESS] Windows Startup auto-run disabled." -ForegroundColor Green
    } else {
        Write-Host "No startup shortcut was found at: $StartupShortcut" -ForegroundColor Yellow
    }
}

switch ($Action.ToLower()) {
    "all" {
        Register-DailyTask
        Enable-StartupRun
    }
    "create" {
        Register-DailyTask
    }
    "enable-startup" {
        Enable-StartupRun
    }
    "disable-startup" {
        Disable-StartupRun
    }
    "run" {
        Write-Host "`nManually triggering task '$TaskName' now..." -ForegroundColor Yellow
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "[TRIGGERED] Task is now running." -ForegroundColor Green
    }
    "status" {
        Write-Host "`n--- Scheduled Task Status (9:00 PM) ---" -ForegroundColor Yellow
        & schtasks /Query /TN $TaskName /FO LIST /V
        Write-Host "`n--- Windows Startup Auto-Run Status ---" -ForegroundColor Yellow
        if (Test-Path $StartupShortcut) {
            Write-Host "[ENABLED] Startup shortcut found: $StartupShortcut" -ForegroundColor Green
        } else {
            Write-Host "[DISABLED] Startup shortcut not found." -ForegroundColor Yellow
        }
    }
    "remove" {
        Write-Host "`nRemoving scheduled task '$TaskName'..." -ForegroundColor Yellow
        & schtasks /Delete /TN $TaskName /F
        Disable-StartupRun
        Write-Host "[REMOVED] Scheduled task and startup shortcut removed." -ForegroundColor Green
    }
    default {
        Write-Host "Usage: .\setup_windows_scheduler.ps1 -Action [all|create|enable-startup|disable-startup|run|status|remove]"
    }
}
