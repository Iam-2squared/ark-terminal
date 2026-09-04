param(
  [Parameter(Mandatory=$true)][string]$Workbook,
  [Parameter(Mandatory=$true)][ValidateSet('SHARES')][string]$MarketSizeUnit,
  [Parameter(Mandatory=$true)][ValidateSet('SHARES')][string]$TickSizeUnit,
  [string]$SessionDate = (Get-Date -Format 'yyyy-MM-dd'),
  [string]$Python = 'py',
  [string]$DataRoot = 'data/phase57-msii-dynamic-live'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not (Test-Path '.git')) { throw 'Run from the ark-terminal repository root.' }
if ($MarketSizeUnit -ne 'SHARES' -or $TickSizeUnit -ne 'SHARES') { throw 'MarketSpeed quantity units must be explicitly attested as SHARES.' }
Write-Warning 'PARTIAL_SMOKE is smoke-only. Normal late starts use tools\phase57_msii_windows_mid_session.ps1.'

$sessionRoot = Join-Path $DataRoot $SessionDate
$rawDir = Join-Path $sessionRoot 'lane-y-raw'
$stateFile = Join-Path $sessionRoot 'dynamic-watchlist-state.json'
& $Python 'tools/phase57_msii_prepare_partial_smoke.py' '--raw-dir' $rawDir '--state' $stateFile '--session-date' $SessionDate
if ($LASTEXITCODE -ne 0) { throw "Partial-smoke bootstrap failed with exit code $LASTEXITCODE" }
Write-Host '{"status":"PHASE57_MSII_PARTIAL_SMOKE_LAUNCH","sessionEligibility":"PARTIAL_SMOKE","notEligibleForProspectiveScore":true,"executionAllowed":false,"brokerWriteAllowed":false,"excelOrderWriteAllowed":false,"rssOrderFunctionAllowed":false,"liveTradingAllowed":false,"paperTradingAllowed":false,"automaticPromotionAllowed":false,"productionUpdateAllowed":false,"transmitted":false}'
& powershell -ExecutionPolicy Bypass -File 'tools/phase57_msii_windows_dynamic_session.ps1' -Workbook $Workbook -MarketSizeUnit $MarketSizeUnit -TickSizeUnit $TickSizeUnit -SessionDate $SessionDate -Python $Python -DataRoot $DataRoot
exit $LASTEXITCODE
