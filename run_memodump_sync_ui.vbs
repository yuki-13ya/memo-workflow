Option Explicit

Dim shell, fileSystem, baseDirectory, scriptPath, logPath, command
Set shell = CreateObject("WScript.Shell")
Set fileSystem = CreateObject("Scripting.FileSystemObject")

baseDirectory = fileSystem.GetParentFolderName(WScript.ScriptFullName)
scriptPath = fileSystem.BuildPath(baseDirectory, "show_memodump_sync_ui.ps1")
logPath = fileSystem.BuildPath(baseDirectory, "logs\memodump_sync_ui_launch.log")

command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -STA -Command " & Chr(34) & _
    "& { try { & '" & Replace(scriptPath, "'", "''") & "' } " & _
    "catch { Add-Content -LiteralPath '" & Replace(logPath, "'", "''") & _
    "' -Encoding UTF8 -Value ((Get-Date -Format o) + ' ' + ($_ | Out-String)); exit 1 } }" & Chr(34)

' Window style 0 keeps the PowerShell console hidden. Operational errors are
' shown by the UI; failures before the UI opens are appended to the launch log.
If WScript.Arguments.Named.Exists("validate") Then
    WScript.Echo command
Else
    shell.Run command, 0, False
End If
