' Launches the dashboard (via watchdog, auto-restarts on crash) with no visible
' console window, for use with a scheduled task.
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "C:\temp\py_project"
shell.Run "cmd /c dashboard_watchdog.bat", 0, False
