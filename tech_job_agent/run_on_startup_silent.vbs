' ==============================================================================
' Autonomous Tech Fresher Job Pipeline - Silent Startup Launcher
' Launches run_on_startup.bat completely hidden in background (no CMD pop-up)
' ==============================================================================
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = strDir & "\run_on_startup.bat"

' Window Style 0 = Hidden
WshShell.Run """" & batPath & """", 0, False
