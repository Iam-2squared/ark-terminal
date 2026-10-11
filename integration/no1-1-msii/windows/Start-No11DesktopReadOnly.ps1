# Desktop RSS reader only. Windows PowerShell 5.1. No Excel/order writes.
param(
    [string]$WorkbookPath = (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ark_No11_MSII_RSS.xlsx'),
    [string]$FrozenRepo = 'C:\ArkTerminal\repo',
    [string]$CaptureDownload = (Join-Path $env:USERPROFILE 'Downloads\Ark-No11-CaptureReadOnly-v3-CANDIDATE.ps1'),
    [ValidateRange(15,3600)][int]$RefreshSeconds = 30,
    [switch]$Watch
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$freeze = '10c94c92c4bd2a59a22744667fd0210252602df4'
$expectedCaptureHash = '8B396BF22724ABBCA4BCEB7B93862AE46D40ACBDFE95B385F492E960E9F08DA3'
$root = Split-Path -Parent $PSScriptRoot
$gate = Join-Path $root 'tools\no11_v3_desktop_publish.mjs'
$faultCli = Join-Path $root 'tools\no11_fault_cli.mjs'
$local = Join-Path $env:LOCALAPPDATA 'ArkTerminal\No11'
$target = Join-Path $local 'private-capture-v3.ps1'
$candidateRoot = Join-Path $local 'capture-v3-candidate'
$snapshot = Join-Path $local 'snapshot.json'
$health = Join-Path $local 'source-health.json'
$ownership = Join-Path $local 'ownership-baseline.json'
$report = Join-Path $local 'desktop-capital-readonly.json'
$ledger = Join-Path $local 'private-safety-ledger.json'
if (-not (Test-Path -LiteralPath $gate -PathType Leaf)) { throw 'DESKTOP_GATE_CODE_MISSING' }
if (-not (Test-Path -LiteralPath $faultCli -PathType Leaf)) { throw 'DESKTOP_FAULT_REPORTER_MISSING' }
if (-not (Test-Path -LiteralPath $WorkbookPath -PathType Leaf)) { throw 'DESKTOP_WORKBOOK_MISSING' }
if (-not (Test-Path -LiteralPath (Join-Path $FrozenRepo '.git'))) { throw 'FROZEN_REPO_MISSING' }
$head = ((& git -C $FrozenRepo rev-parse HEAD) | Select-Object -First 1)
if ($LASTEXITCODE -ne 0 -or [string]$head -cne $freeze) { throw 'NO11_FROZEN_HEAD_MISMATCH' }
$dirty = @(& git -C $FrozenRepo status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0) { throw 'NO11_FROZEN_TRACKED_FILES_CHANGED' }
$node = (Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$ps = (Get-Command powershell.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
[void](New-Item -ItemType Directory -Force -Path $local)
if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
    if (-not (Test-Path -LiteralPath $CaptureDownload -PathType Leaf)) {
        throw 'PHYSICALLY_VERIFIED_CAPTURE_V2_MISSING'
    }
    $downloadHash = (Get-FileHash -LiteralPath $CaptureDownload -Algorithm SHA256).Hash
    if ($downloadHash -cne $expectedCaptureHash) { throw 'CAPTURE_V2_SHA256_MISMATCH' }
    Copy-Item -LiteralPath $CaptureDownload -Destination $target -ErrorAction Stop
}
if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -cne $expectedCaptureHash) {
    throw 'PINNED_CAPTURE_SCRIPT_CHANGED'
}
if (-not (Test-Path -LiteralPath $ownership -PathType Leaf)) {
    throw 'EXPLICIT_PRIVATE_OWNERSHIP_MISSING'
}
function Run-Once {
    # Never poll the same Excel workbook concurrently from UI and watcher.
    $mutex = [System.Threading.Mutex]::new($false, 'Local\ArkTerminal_No11_RSS_ReadOnly')
    $lockTaken = $false
    $faultReason = 'READ_ONLY_CAPTURE_FAILED'
    try {
        try {
            $lockTaken = $mutex.WaitOne(0)
        } catch [System.Threading.AbandonedMutexException] {
            $lockTaken = $true
            throw 'NO11_RSS_CAPTURE_PREVIOUS_RUN_ABANDONED'
        }
        if (-not $lockTaken) { throw 'NO11_RSS_CAPTURE_ALREADY_RUNNING' }
        Write-Host 'NO11_DESKTOP_READ_ONLY_POLL_START'
        # Only a newly generated V3 run may be published; never recycle an older capture.
        $existing = @{}
        if (Test-Path -LiteralPath $candidateRoot -PathType Container) {
            foreach ($folder in @(Get-ChildItem -LiteralPath $candidateRoot -Directory)) {
                $existing[$folder.Name] = $true
            }
        }
        $nativeArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$target,
            '-WorkbookPath',$WorkbookPath)
        & $ps @nativeArgs | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'PRIVATE_V3_RSS_CAPTURE_FAILED' }
        if (-not (Test-Path -LiteralPath $candidateRoot -PathType Container)) {
            throw 'PRIVATE_V3_CAPTURE_ROOT_MISSING'
        }
        $newFolders = @(Get-ChildItem -LiteralPath $candidateRoot -Directory |
            Where-Object { -not $existing.ContainsKey($_.Name) })
        if ($newFolders.Count -ne 1 -or $newFolders[0].Name -cnotmatch '^[a-f0-9]{32}$') {
            throw 'PRIVATE_V3_CAPTURE_IDENTITY_UNVERIFIED'
        }
        $faultReason = 'CAPITAL_OR_OWNERSHIP_GATE_BLOCKED'
        & $node $gate $newFolders[0].Name | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'CASH_OR_OWNERSHIP_GATE_BLOCKED' }
        Write-Host 'NO11_DESKTOP_READ_ONLY_POLL_PASS=True'
        Write-Host 'EXCEL_MODIFIED=False'
        Write-Host 'ORDER_TRANSMISSION=False'
    } catch {
        $originalError = $_
        if ($lockTaken) {
            # Never reset safety or mask the original failure. Private ledger only.
            try {
                & $node $faultCli 'latch' '--ledger' $ledger '--reason' $faultReason | Out-Null
                if ($LASTEXITCODE -ne 0) { Write-Warning 'NO11_SAFETY_LEDGER_LATCH_FAILED' }
            } catch {
                Write-Warning 'NO11_SAFETY_LEDGER_LATCH_FAILED'
            }
        }
        throw $originalError
    } finally {
        if ($lockTaken) { [void]$mutex.ReleaseMutex() }
        $mutex.Dispose()
    }
}
if ($Watch) {
    Write-Host 'NO11_DESKTOP_READ_ONLY_WATCH=ON; STOP=CTRL+C'
    while ($true) {
        Run-Once
        Start-Sleep -Seconds $RefreshSeconds
    }
} else {
    Run-Once
}
