param(
    [string]$EnvFile = $env:MEMO_WORKFLOW_ENV_FILE,
    [string]$PythonExecutable = $env:MEMO_WORKFLOW_PYTHON,
    [string]$DriveInbox = $env:MEMODUMP_DRIVE_INBOX
)

$ErrorActionPreference = 'Stop'
$ProjectDir = $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($EnvFile)) {
    throw 'EnvFile is required. Pass -EnvFile or set MEMO_WORKFLOW_ENV_FILE.'
}
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "EnvFile was not found: $EnvFile"
}
if ([string]::IsNullOrWhiteSpace($DriveInbox)) {
    throw 'DriveInbox is required. Pass -DriveInbox or set MEMODUMP_DRIVE_INBOX.'
}
if (-not (Test-Path -LiteralPath $DriveInbox -PathType Container)) {
    throw "DriveInbox was not found: $DriveInbox"
}
if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    $PythonExecutable = 'python'
}

Push-Location $ProjectDir
try {
    $IngestResultText = (& $PythonExecutable 'discord-ingest\catch_up_discord.py' `
        --env-file $EnvFile `
        --queue-path 'state\discord_message_queue.json' | Out-String)
    if ($LASTEXITCODE -ne 0) {
        throw "Discord ingest failed with exit code $LASTEXITCODE"
    }
    Write-Output $IngestResultText.Trim()

    $IngestResult = $IngestResultText | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace($IngestResult.batch_path)) {
        Write-Output 'drive_handoff=skipped reason=no_new_messages'
        return
    }
    $SourceJson = Join-Path $ProjectDir $IngestResult.batch_path

    & $PythonExecutable 'discord-ingest\publish_drive_handoff.py' `
        --source $SourceJson `
        --inbox $DriveInbox `
        --state-file 'state\drive_handoff_state.json'
    if ($LASTEXITCODE -ne 0) {
        throw "Drive handoff failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
