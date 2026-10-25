# ==============================================================================
# Autonomous Tech Fresher Job Pipeline - Windows Task Scheduler & Startup Setup
# Configures:
#   1. Daily 9:00 PM scheduled task via Windows Task Scheduler
#   2. Windows Startup auto-run (silent background execution)
# ==============================================================================

param (
    [string]$Action = "all" # all, create, enable-startup, disable-startup, shortcut, run, status, remove
)

$TaskName = "TechJobAgent_Mumbai_9PM"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$AgentScript = Join-Path $ScriptDir "agent.py"
$RunDailyBat = Join-Path $ScriptDir "run_daily.bat"
$SilentVbs = Join-Path $ScriptDir "run_on_startup_silent.vbs"
$StartupDir = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup)
$StartupShortcut = Join-Path $StartupDir "TechJobAgent_Startup.lnk"
$DesktopDir = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$DesktopShortcut = Join-Path $DesktopDir "Run Tech Job Agent.lnk"
$DesktopSilentShortcut = Join-Path $DesktopDir "Run Tech Job Agent (Silent).lnk"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   TECH JOB AGENT - WINDOWS SCHEDULER & SHORTCUT SETUP" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Task Name:        $TaskName"
Write-Host "Schedule:         Daily at 21:00 (9:00 PM)"
Write-Host "Startup Auto-Run: $StartupShortcut"
Write-Host "Desktop Shortcut: $DesktopShortcut"
Write-Host "Python Exec:      $PythonExe"
Write-Host "Agent Script:     $AgentScript"
Write-Host "======================================================================" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    Write-Error "Virtual environment Python executable not found at: $PythonExe"
    exit 1
}

function Register-DailyTask {
    Write-Host "`n[1/3] Registering 9:00 PM Daily Scheduled Task..." -ForegroundColor Yellow
    try {
        $taskAction = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$AgentScript`"" -WorkingDirectory $ScriptDir
        $taskTrigger = New-ScheduledTaskTrigger -Daily -At "21:00"
        $taskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        $taskPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
        Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -Principal $taskPrincipal -Force | Out-Null
        Write-Host "[SUCCESS] Daily task '$TaskName' registered for 9:00 PM with Working Directory, Battery, and Missed-Run Catchup support." -ForegroundColor Green
    } catch {
        Write-Warning "PowerShell ScheduledTask command failed ($_); falling back to schtasks..."
        & schtasks /Create /SC DAILY /TN $TaskName /TR "`"$PythonExe`" `"$AgentScript`"" /ST 21:00 /F
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[SUCCESS] Daily task '$TaskName' registered for 9:00 PM via schtasks." -ForegroundColor Green
        }
    }
}

function Enable-StartupRun {
    Write-Host "`n[2/3] Configuring Auto-Run on Windows Startup..." -ForegroundColor Yellow
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

function Create-DesktopShortcuts {
    Write-Host "`n[3/3] Creating Desktop Shortcuts (for manual run when laptop was off)..." -ForegroundColor Yellow
    try {
        $wsh = New-Object -ComObject WScript.Shell
        
        # 1. Interactive Desktop Shortcut (opens console, shows progress, pauses when done)
        $shortcut = $wsh.CreateShortcut($DesktopShortcut)
        $shortcut.TargetPath = $RunDailyBat
        $shortcut.WorkingDirectory = $ScriptDir
        $shortcut.Description = "Run Tech Job Agent (Manual / Catch-up Run with Live Output)"
        $shortcut.IconLocation = "$PythonExe,0"
        $shortcut.Save()
        Write-Host "[SUCCESS] Interactive Desktop shortcut created: $DesktopShortcut" -ForegroundColor Green

        # 2. Silent Desktop Shortcut (background execution without console window)
        $silentShortcut = $wsh.CreateShortcut($DesktopSilentShortcut)
        $silentShortcut.TargetPath = "wscript.exe"
        $silentShortcut.Arguments = "`"$SilentVbs`""
        $silentShortcut.WorkingDirectory = $ScriptDir
        $silentShortcut.Description = "Run Tech Job Agent Silently (Logs to agent_execution.log)"
        $silentShortcut.IconLocation = "$PythonExe,0"
        $silentShortcut.Save()
        Write-Host "[SUCCESS] Silent Desktop shortcut created: $DesktopSilentShortcut" -ForegroundColor Green
    } catch {
        Write-Error "Failed to create desktop shortcuts: $_"
    }
}

switch ($Action.ToLower()) {
    "all" {
        Register-DailyTask
        Enable-StartupRun
        Create-DesktopShortcuts
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
    "shortcut" {
        Create-DesktopShortcuts
    }
    "desktop" {
        Create-DesktopShortcuts
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
        Write-Host "`n--- Desktop Shortcuts Status ---" -ForegroundColor Yellow
        if (Test-Path $DesktopShortcut) {
            Write-Host "[ENABLED] Interactive Desktop shortcut: $DesktopShortcut" -ForegroundColor Green
        } else {
            Write-Host "[NOT FOUND] Interactive Desktop shortcut not found." -ForegroundColor Yellow
        }
        if (Test-Path $DesktopSilentShortcut) {
            Write-Host "[ENABLED] Silent Desktop shortcut:      $DesktopSilentShortcut" -ForegroundColor Green
        } else {
            Write-Host "[NOT FOUND] Silent Desktop shortcut not found." -ForegroundColor Yellow
        }
    }
    "remove" {
        Write-Host "`nRemoving scheduled task '$TaskName'..." -ForegroundColor Yellow
        & schtasks /Delete /TN $TaskName /F
        Disable-StartupRun
        if (Test-Path $DesktopShortcut) { Remove-Item $DesktopShortcut -Force }
        if (Test-Path $DesktopSilentShortcut) { Remove-Item $DesktopSilentShortcut -Force }
        Write-Host "[REMOVED] Scheduled task, startup shortcut, and desktop shortcuts removed." -ForegroundColor Green
    }
    default {
        Write-Host "Usage: .\setup_windows_scheduler.ps1 -Action [all|create|enable-startup|disable-startup|shortcut|run|status|remove]"
    }
}
