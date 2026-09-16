param([string]$OutputRoot = "", [string]$UsedFixtures = "")
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    Get-Command node -ErrorAction Stop | Out-Null
    Get-Command python -ErrorAction Stop | Out-Null
    if (!$OutputRoot) { $OutputRoot = Join-Path ([IO.Path]::GetTempPath()) 'ArkOfflineParity' }
    $runDir = Join-Path $OutputRoot ([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff') + '-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $runDir -ErrorAction Stop | Out-Null
    & python tools/phase57_offline_preflight.py --output (Join-Path $runDir 'preflight.json')
    if ($LASTEXITCODE -ne 0) { throw 'Preflight failed; no runtime was started' }
    & node --test scripts/tests/phase57-offline-parity.test.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Focused tests failed' }
    & node --test scripts/tests/phase57-offline-completion.test.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Restart or source diagnostic tests failed' }
    & node --test scripts/tests/phase57-offline-provenance.test.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Offline provenance checks failed' }
    $packet = Join-Path $runDir 'workbook-packet.json'
    & python tools/phase57_offline_excel_reader.py --output $packet
    if ($LASTEXITCODE -ne 0) { throw 'Offline workbook check failed' }
    & node scripts/phase57-offline-workbook-check.mjs $packet (Join-Path $runDir 'workbook-report')
    if ($LASTEXITCODE -ne 0) { throw 'Transport parity failed' }
    & node scripts/phase57-offline-local-gate.mjs (Join-Path $runDir 'local-gate')
    if ($LASTEXITCODE -ne 0) { throw 'Offline daily pipeline failed; evidence retained' }
    if ($UsedFixtures) {
        & node scripts/phase57-offline-historical-parity.mjs --used-fixtures $UsedFixtures --output (Join-Path $runDir 'historical-parity')
        if ($LASTEXITCODE -ne 0) { throw 'Historical parity failed; evidence retained' }
    }
    Write-Output "Offline parity complete: $runDir"
    Write-Output 'No Excel COM, MSII, RSS, account, or network connection was made.'
} finally { Pop-Location }
