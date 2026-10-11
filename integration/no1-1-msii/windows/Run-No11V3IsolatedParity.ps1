# Executes frozen V2 and candidate V3 sequentially; account figures stay private on Windows.
# Comparison only, no Excel mutation, no orders, no Safety reset, no official snapshot overwrite.
param([string]$WorkbookPath=(Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ark_No11_MSII_RSS.xlsx'),
      [string]$V2File=(Join-Path $HOME 'Downloads\Ark-No11-CaptureReadOnly-v2.ps1'),
      [string]$V3File=(Join-Path $HOME 'Downloads\Ark-No11-CaptureReadOnly-v3-CANDIDATE.ps1'))
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$oldHash='0EAB3CA3081B2E0CB323D8438719F2B820B69FC02F373AD843B5907315838E2C'
$newHash='8B396BF22724ABBCA4BCEB7B93862AE46D40ACBDFE95B385F492E960E9F08DA3'
$private=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No11'
$parity=Join-Path $PSScriptRoot 'Test-No11V3LocalParity.ps1'
$mutex=[System.Threading.Mutex]::new($false,'Local\ArkTerminal_No11_RSS_ReadOnly')
$acquired=$false
try {
    if((Get-FileHash -LiteralPath $V2File -Algorithm SHA256).Hash -cne $oldHash) {
        throw 'V2_PINNED_HASH_MISMATCH'
    }
    if((Get-FileHash -LiteralPath $V3File -Algorithm SHA256).Hash -cne $newHash) {
        throw 'V3_PINNED_HASH_MISMATCH'
    }
    if(-not (Test-Path -LiteralPath $parity -PathType Leaf)) {
        throw 'V3_PARITY_READER_MISSING'
    }
    if(-not (Test-Path -LiteralPath $WorkbookPath -PathType Leaf)){
        throw 'EXPECTED_WORKBOOK_MISSING'
    }
    try{$acquired=$mutex.WaitOne(0)}catch [System.Threading.AbandonedMutexException]{
        $acquired=$true
        throw 'PREVIOUS_CAPTURE_ABANDONED_BLOCK'
    }
    if(-not $acquired){throw 'RSS_CAPTURE_ALREADY_RUNNING'}
    $runDir=Join-Path (Join-Path $private 'parity-v2') ([Guid]::NewGuid().ToString('N'))
    [void](New-Item -ItemType Directory -Path $runDir -Force -ErrorAction Stop)
    $snapshot=Join-Path $runDir 'snapshot.json'
    $health=Join-Path $runDir 'source-health.json'
    $ps=(Get-Command powershell.exe -CommandType Application -ErrorAction Stop).Source
    & $ps -NoProfile -ExecutionPolicy Bypass -File $V2File -WorkbookPath $WorkbookPath -SnapshotPath $snapshot -SourceHealthPath $health | Out-Null
    if($LASTEXITCODE -ne 0){throw 'V2_ISOLATED_CAPTURE_FAILED'}
    & $ps -NoProfile -ExecutionPolicy Bypass -File $V3File -WorkbookPath $WorkbookPath | Out-Null
    if($LASTEXITCODE -ne 0){throw 'V3_ISOLATED_CAPTURE_FAILED'}
    & $parity -PrivateRoot $private -V2SnapshotPath $snapshot -MaxComparisonGapSeconds 600
    if(-not $?){throw 'V3_COMPARISON_FAILED'}
} catch {
    $errorCode=[string]$_.Exception.Message
    if($errorCode -cnotmatch '^[A-Z][A-Z0-9_]*$'){$errorCode='BLOCKED_REDACTED_ERROR'}
    Write-Host "NO11_V3_ISOLATED_PARITY_ERROR=$errorCode"
    Write-Host 'NO11_V3_PARITY_RESULT=BLOCKED'
    Write-Host 'NO11_PRODUCTION_READY=False'
    Write-Host 'ORDER_TRANSMISSION=False'
} finally {
    if($acquired){[void]$mutex.ReleaseMutex()}
    $mutex.Dispose()
}
