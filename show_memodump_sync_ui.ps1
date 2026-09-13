param(
    [string]$TaskName = 'Memodump Discord to Drive'
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Get-DriveInboxFromTask {
    param([Microsoft.Management.Infrastructure.CimInstance]$Task)

    $arguments = [string]$Task.Actions[0].Arguments
    $match = [regex]::Match(
        $arguments,
        '(?i)(?:^|\s)-DriveInbox\s+(?:"(?<quoted>[^"]+)"|(?<plain>\S+))'
    )
    if (-not $match.Success) {
        return $null
    }
    if ($match.Groups['quoted'].Success) {
        return $match.Groups['quoted'].Value
    }
    return $match.Groups['plain'].Value
}

function Get-InboxJsonSnapshot {
    param([string]$InboxPath)

    if ([string]::IsNullOrWhiteSpace($InboxPath) -or
        -not (Test-Path -LiteralPath $InboxPath -PathType Container)) {
        return @{}
    }

    $snapshot = @{}
    Get-ChildItem -LiteralPath $InboxPath -Filter '*.json' -File | ForEach-Object {
        $snapshot[$_.FullName] = $_.LastWriteTimeUtc
    }
    return $snapshot
}

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Memodump 今すぐ同期'
$form.StartPosition = 'CenterScreen'
$form.Size = New-Object System.Drawing.Size(560, 300)
$form.MinimumSize = New-Object System.Drawing.Size(560, 300)
$form.Font = New-Object System.Drawing.Font('Yu Gothic UI', 10)

$description = New-Object System.Windows.Forms.Label
$description.Location = New-Object System.Drawing.Point(24, 20)
$description.Size = New-Object System.Drawing.Size(495, 44)
$description.Text = "Discordの新規投稿を取得し、Memo-RouterのinboxへJSONを送ります。`r`n新規投稿がない場合はJSONを作成しません。"
$form.Controls.Add($description)

$syncButton = New-Object System.Windows.Forms.Button
$syncButton.Location = New-Object System.Drawing.Point(24, 78)
$syncButton.Size = New-Object System.Drawing.Size(150, 52)
$syncButton.Text = '今すぐ同期'
$form.Controls.Add($syncButton)

$openButton = New-Object System.Windows.Forms.Button
$openButton.Location = New-Object System.Drawing.Point(185, 78)
$openButton.Size = New-Object System.Drawing.Size(165, 52)
$openButton.Text = 'Memo-Router inboxを開く'
$form.Controls.Add($openButton)

$setupButton = New-Object System.Windows.Forms.Button
$setupButton.Location = New-Object System.Drawing.Point(370, 78)
$setupButton.Size = New-Object System.Drawing.Size(149, 52)
$setupButton.Text = '初期設定'
$form.Controls.Add($setupButton)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Location = New-Object System.Drawing.Point(24, 150)
$statusLabel.Size = New-Object System.Drawing.Size(495, 72)
$statusLabel.BorderStyle = 'FixedSingle'
$statusLabel.Padding = New-Object System.Windows.Forms.Padding(10)
$statusLabel.Text = '状態を確認しています…'
$form.Controls.Add($statusLabel)

$detailLabel = New-Object System.Windows.Forms.Label
$detailLabel.Location = New-Object System.Drawing.Point(24, 228)
$detailLabel.Size = New-Object System.Drawing.Size(495, 24)
$detailLabel.ForeColor = [System.Drawing.Color]::DimGray
$form.Controls.Add($detailLabel)

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 1000
$task = $null
$driveInbox = $null
$beforeSnapshot = @{}
$startedAt = $null
$observedRunning = $false

function Set-Status {
    param(
        [string]$Message,
        [System.Drawing.Color]$Color = [System.Drawing.Color]::Black
    )
    $statusLabel.Text = $Message
    $statusLabel.ForeColor = $Color
}

function Refresh-TaskConfiguration {
    try {
        $script:task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        $script:driveInbox = Get-DriveInboxFromTask -Task $script:task
        if ([string]::IsNullOrWhiteSpace($script:driveInbox)) {
            throw "登録済みタスクからDriveInboxを読み取れません。"
        }
        if (-not (Test-Path -LiteralPath $script:driveInbox -PathType Container)) {
            throw "DriveInboxが見つかりません: $($script:driveInbox)"
        }
        $openButton.Enabled = $true
        $detailLabel.Text = "送信先: $($script:driveInbox)"
        return $true
    }
    catch {
        $script:task = $null
        $script:driveInbox = $null
        $syncButton.Enabled = $false
        $openButton.Enabled = $false
        Set-Status -Message "実行準備を確認できません。`r`n$($_.Exception.Message)" -Color ([System.Drawing.Color]::DarkRed)
        $detailLabel.Text = "タスク名: $TaskName"
        return $false
    }
}

$syncButton.Add_Click({
    if (-not (Refresh-TaskConfiguration)) {
        return
    }

    try {
        $script:beforeSnapshot = Get-InboxJsonSnapshot -InboxPath $script:driveInbox
        $script:startedAt = [datetime]::UtcNow
        $script:observedRunning = $false
        Start-ScheduledTask -TaskName $TaskName
        $syncButton.Enabled = $false
        Set-Status -Message '同期を開始しました。完了を待っています…' -Color ([System.Drawing.Color]::DarkBlue)
        $timer.Start()
    }
    catch {
        Set-Status -Message "同期を開始できませんでした。`r`n$($_.Exception.Message)" -Color ([System.Drawing.Color]::DarkRed)
        $syncButton.Enabled = $true
    }
})

$openButton.Add_Click({
    if ($script:driveInbox -and (Test-Path -LiteralPath $script:driveInbox -PathType Container)) {
        Start-Process -FilePath 'explorer.exe' -ArgumentList @($script:driveInbox)
    }
})

$setupButton.Add_Click({
    $envDialog = New-Object System.Windows.Forms.OpenFileDialog
    $envDialog.Title = 'Memodumpで使用する.envファイルを選択してください'
    $envDialog.Filter = '環境設定ファイル (.env)|*.env|すべてのファイル|*.*'
    $envDialog.CheckFileExists = $true
    if ($envDialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        return
    }

    $pythonDialog = New-Object System.Windows.Forms.OpenFileDialog
    $pythonDialog.Title = 'Python実行ファイルを選択してください'
    $pythonDialog.Filter = 'Python (python.exe)|python.exe|実行ファイル (*.exe)|*.exe'
    $bundledPython = 'C:\Users\Namba\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPython -PathType Leaf) {
        $pythonDialog.InitialDirectory = [System.IO.Path]::GetDirectoryName($bundledPython)
        $pythonDialog.FileName = 'python.exe'
    }
    if ($pythonDialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        return
    }

    $inboxDialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $inboxDialog.Description = 'Memo-Routerのinboxフォルダを選択してください'
    $knownInbox = 'D:\マネキネコンサル\AI_Workspace\Memo-Router\inbox'
    if (Test-Path -LiteralPath $knownInbox -PathType Container) {
        $inboxDialog.SelectedPath = $knownInbox
    }
    if ($inboxDialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        return
    }

    try {
        $registerScript = Join-Path $PSScriptRoot 'register_memodump_tasks.ps1'
        $registrationOutput = & powershell.exe `
            -NoProfile `
            -WindowStyle Hidden `
            -ExecutionPolicy Bypass `
            -File $registerScript `
            -EnvFile ([string]$envDialog.FileName) `
            -PythonExecutable ([string]$pythonDialog.FileName) `
            -DriveInbox ([string]$inboxDialog.SelectedPath) `
            -TaskName ([string]$TaskName) 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw (($registrationOutput | Out-String).Trim())
        }
        $ready = Refresh-TaskConfiguration
        if ($ready) {
            $syncButton.Enabled = $true
            Set-Status -Message '初期設定が完了しました。「今すぐ同期」を実行できます。' -Color ([System.Drawing.Color]::DarkGreen)
        }
    }
    catch {
        Set-Status -Message "初期設定に失敗しました。`r`n$($_.Exception.Message)" -Color ([System.Drawing.Color]::DarkRed)
    }
})

$timer.Add_Tick({
    try {
        $currentTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        if ($currentTask.State -eq 'Running') {
            $script:observedRunning = $true
            Set-Status -Message '同期中です…' -Color ([System.Drawing.Color]::DarkBlue)
            return
        }

        $elapsed = [datetime]::UtcNow - $script:startedAt
        if (-not $script:observedRunning -and $elapsed.TotalSeconds -lt 3) {
            return
        }
        if ($elapsed.TotalMinutes -ge 30) {
            throw '30分以内に完了を確認できませんでした。タスクスケジューラを確認してください。'
        }

        $timer.Stop()
        $info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
        $afterSnapshot = Get-InboxJsonSnapshot -InboxPath $script:driveInbox
        $newFiles = @(
            $afterSnapshot.Keys |
                Where-Object {
                    -not $script:beforeSnapshot.ContainsKey($_) -or
                    $afterSnapshot[$_] -gt $script:beforeSnapshot[$_]
                } |
                Sort-Object { $afterSnapshot[$_] } -Descending
        )

        if ($info.LastTaskResult -ne 0) {
            Set-Status -Message "同期処理がエラーで終了しました。`r`n結果コード: $($info.LastTaskResult)" -Color ([System.Drawing.Color]::DarkRed)
        }
        elseif ($newFiles.Count -gt 0) {
            $newestName = Split-Path -Leaf $newFiles[0]
            Set-Status -Message "同期が完了しました。`r`n作成JSON: $newestName" -Color ([System.Drawing.Color]::DarkGreen)
        }
        else {
            Set-Status -Message "同期が完了しました。`r`n新しいDiscord投稿はありませんでした。" -Color ([System.Drawing.Color]::DarkGreen)
        }
        $syncButton.Enabled = $true
    }
    catch {
        $timer.Stop()
        Set-Status -Message "完了状態を確認できませんでした。`r`n$($_.Exception.Message)" -Color ([System.Drawing.Color]::DarkRed)
        $syncButton.Enabled = $true
    }
})

$form.Add_Shown({
    $form.TopMost = $true
    $form.Activate()
    $form.BringToFront()
    $form.TopMost = $false
    $ready = Refresh-TaskConfiguration
    if ($ready) {
        Set-Status -Message '「今すぐ同期」を押すと、新規Discord投稿を確認します。'
    }
    else {
        $statusLabel.Text = "定期実行タスクが登録されていません。`r`n最初に「初期設定」を押してください。"
    }
})

$form.Add_FormClosed({ $timer.Stop() })
[void]$form.ShowDialog()
