param(
    [ValidateSet('OFFLINE_FIXTURE','SOURCE_SEMANTICS_ONLY','REALTIME_SHADOW','POST_CLOSE_PARITY')]
    [string]$Mode = 'OFFLINE_FIXTURE',
    [string]$Config = '', [string]$InputPacket = '', [string]$OutputRoot = '', [int]$Seconds = 60
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    Get-Command node -ErrorAction Stop | Out-Null
    Get-Command python -ErrorAction Stop | Out-Null
    if (!$OutputRoot) { $OutputRoot = Join-Path ([IO.Path]::GetTempPath()) 'ArkParity' }
    if ($Mode -eq 'REALTIME_SHADOW') { throw 'REALTIME_SHADOW_LOCKED: source semantics, PIT universe and session admission required' }
    if ($Mode -eq 'OFFLINE_FIXTURE' -and !$InputPacket) {
        & ./tools/Start-ArkOfflineParity.ps1 -OutputRoot $OutputRoot
        if ($LASTEXITCODE -ne 0) { throw 'Offline gate failed' }
        return
    }
    $runDir = Join-Path $OutputRoot ([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff') + '-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $runDir | Out-Null
    if ($Mode -eq 'POST_CLOSE_PARITY') {
        if (!$InputPacket) { throw 'POST_CLOSE_PARITY requires an authorized paired-stage packet' }
        & node scripts/phase57-post-close-parity.mjs $InputPacket (Join-Path $runDir 'parity.json')
        if ($LASTEXITCODE -ne 0) { throw 'Parity comparison failed; evidence retained' }
    } elseif ($Mode -eq 'OFFLINE_FIXTURE') {
        & node scripts/phase57-frozen-main-runner.mjs --input $InputPacket --journal-dir (Join-Path $runDir 'journal') --export-dir (Join-Path $runDir 'export')
        if ($LASTEXITCODE -ne 0) { throw 'Frozen runtime failed; evidence retained' }
    } else {
        if (!$Config) { throw 'SOURCE_SEMANTICS_ONLY requires a reviewed local field-map config' }
        & python tools/phase57_source_capture.py --config $Config --output (Join-Path $runDir 'capture') --seconds $Seconds
        if ($LASTEXITCODE -ne 0) { throw 'Read-only capture failed; no strategy was started' }
        & node scripts/phase57-source-diagnostic.mjs (Join-Path $runDir 'capture/capture.jsonl') (Join-Path $runDir 'diagnostic')
        if ($LASTEXITCODE -ne 0) { throw 'Source diagnostic failed; original capture retained' }
    }
    Write-Output "Evidence: $runDir"
    Write-Output 'ORDER_TRANSMISSION_DISABLED; source observations do not unlock strategy execution'
} finally { Pop-Location }
