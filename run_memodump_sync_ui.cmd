@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0show_memodump_sync_ui.ps1"
if errorlevel 1 pause
