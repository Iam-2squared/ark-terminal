# READ ONLY: Windows V3 capture + Capital/Ownership proof on isolated candidate files.
# Does not overwrite official Snapshot/Health/Capital or reset a Safety latch.
param(
    [string]$WorkbookPath=(Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ark_No11_MSII_RSS.xlsx'),
    [string]$V3File=(Join-Path $HOME 'Downloads\Ark-No11-CaptureReadOnly-v3-CANDIDATE.ps1')
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=Split-Path -Parent $PSScriptRoot
# Use the byte-pinned, already PC-tested Downloads copy. The Git worktree copy may
# have CRLF checkout smudging on an individual Windows installation despite attributes.
# Strict SHA256 attestation remains mandatory; do not rewrite or normalize the source.
$v3=$V3File
$gate=Join-Path $root 'tools\no11_v3_capital_probe.mjs'
$local=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No11'
$runs=Join-Path $local 'capture-v3-candidate'
$owner=Join-Path $local 'ownership-baseline.json'
$frozenRepo='C:\ArkTerminal\repo'
$expectedV3Hash='8B396BF22724ABBCA4BCEB7B93862AE46D40ACBDFE95B385F492E960E9F08DA3'
$freeze='10c94c92c4bd2a59a22744667fd0210252602df4'
$mutex=[System.Threading.Mutex]::new($false,'Local\ArkTerminal_No11_RSS_ReadOnly')
$lockTaken=$false
try {
    if(-not (Test-Path -LiteralPath $v3 -PathType Leaf)){throw 'V3_CANDIDATE_CODE_MISSING'}
    if((Get-FileHash -LiteralPath $v3 -Algorithm SHA256).Hash -cne $expectedV3Hash){throw 'V3_CANDIDATE_HASH_MISMATCH'}
    Write-Host 'NO11_V3_PINNED_DOWNLOAD_SOURCE_VERIFIED=True'
    if(-not (Test-Path -LiteralPath $gate -PathType Leaf)){throw 'V3_CAPITAL_PROBE_CODE_MISSING'}
    if(-not (Test-Path -LiteralPath $owner -PathType Leaf)){throw 'PRIVATE_OWNERSHIP_BASELINE_MISSING'}
    if(-not (Test-Path -LiteralPath $WorkbookPath -PathType Leaf)){throw 'DESKTOP_WORKBOOK_MISSING'}
    $frozenHead=((& git -C $frozenRepo rev-parse HEAD) | Select-Object -First 1)
    if($LASTEXITCODE -ne 0 -or [string]$frozenHead -cne $freeze){throw 'NO11_FROZEN_HEAD_MISMATCH'}
    $dirty=@(& git -C $frozenRepo status --porcelain --untracked-files=no)
    if($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0){throw 'NO11_FROZEN_TRACKED_FILES_CHANGED'}
    $ps=(Get-Command powershell.exe -CommandType Application -ErrorAction Stop).Source
    $node=(Get-Command node -CommandType Application -ErrorAction Stop).Source
    try{$lockTaken=$mutex.WaitOne(0)}
    catch [System.Threading.AbandonedMutexException] {
        $lockTaken=$true
        throw 'PREVIOUS_READ_ONLY_CAPTURE_ABANDONED'
    }
    if(-not $lockTaken){throw 'READ_ONLY_CAPTURE_ALREADY_RUNNING'}
    $existing=@{}
    if(Test-Path -LiteralPath $runs -PathType Container){
        foreach($dir in @(Get-ChildItem -LiteralPath $runs -Directory)){
            $existing[$dir.Name]=$true
        }
    }
    & $ps -NoProfile -ExecutionPolicy Bypass -File $v3 -WorkbookPath $WorkbookPath | Out-Null
    if($LASTEXITCODE -ne 0){throw 'V3_CANDIDATE_CAPTURE_FAILED'}
    $newDirs=@(Get-ChildItem -LiteralPath $runs -Directory | Where-Object {
        -not $existing.ContainsKey($_.Name)
    })
    if($newDirs.Count -ne 1 -or $newDirs[0].Name -cnotmatch '^[a-f0-9]{32}$'){
        throw 'V3_RUN_IDENTITY_UNVERIFIED'
    }
    & $node $gate $newDirs[0].Name
    if($LASTEXITCODE -ne 0) {
        Write-Host 'NO11_V3_CAPITAL_DIAGNOSTIC_PASS=False'
    } else {
        Write-Host 'NO11_V3_CAPITAL_DIAGNOSTIC_PASS=True'
    }
} catch {
    $reason=[string]$_.Exception.Message
    if($reason -cnotmatch '^[A-Z][A-Z0-9_]*$'){$reason='REDACTED_DIAGNOSTIC_ERROR'}
    Write-Host "NO11_V3_CAPITAL_PRECHECK_ERROR=$reason"
    Write-Host 'NO11_V3_CAPITAL_DIAGNOSTIC_PASS=False'
    Write-Host 'NO11_PRODUCTION_READY=False'
    Write-Host 'ORDER_TRANSMISSION=False'
} finally {
    if($lockTaken){[void]$mutex.ReleaseMutex()}
    $mutex.Dispose()
}
