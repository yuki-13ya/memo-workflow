param(
    [string]$DailyAt = '20:00',
    [Parameter(Mandatory = $true)][string]$EnvFile,
    [Parameter(Mandatory = $true)][string]$PythonExecutable,
    [Parameter(Mandatory = $true)][string]$DriveInbox,
    [string]$TaskName = 'Memodump Discord to Drive',
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "EnvFile was not found: $EnvFile"
}
if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    throw "Python executable was not found: $PythonExecutable"
}
if (-not (Test-Path -LiteralPath $DriveInbox -PathType Container)) {
    throw "Drive inbox was not found: $DriveInbox"
}

$Runner = Join-Path $PSScriptRoot 'run_memodump_sync.ps1'
$PowerShell = (Get-Command powershell.exe).Source
$ActionArguments = @(
    '-NoProfile'
    '-NonInteractive'
    '-ExecutionPolicy Bypass'
    "-File `"$Runner`""
    "-EnvFile `"$EnvFile`""
    "-PythonExecutable `"$PythonExecutable`""
    "-DriveInbox `"$DriveInbox`""
) -join ' '

$Action = New-ScheduledTaskAction -Execute $PowerShell -Argument $ActionArguments -WorkingDirectory $PSScriptRoot
$Triggers = @(
    New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    New-ScheduledTaskTrigger -Daily -At $DailyAt
)
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$Principal = New-ScheduledTaskPrincipal `
    -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited

if ($ValidateOnly) {
    [pscustomobject]@{
        TaskName = $TaskName
        EnvFile = $EnvFile
        PythonExecutable = $PythonExecutable
        DriveInbox = $DriveInbox
        ActionExecutable = $Action.Execute
        TriggerCount = $Triggers.Count
    }
    return
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Description 'Fetch Discord memos and copy changed JSON to the Google Drive synced inbox.' `
    -Action $Action `
    -Trigger $Triggers `
    -Settings $Settings `
    -Principal $Principal `
    -Force | Out-Null

Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo
