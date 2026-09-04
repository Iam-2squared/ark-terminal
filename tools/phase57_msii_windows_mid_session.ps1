param(
  [Parameter(Mandatory=$true)][string]$Workbook,
  [Parameter(Mandatory=$true)][ValidateSet('SHARES')][string]$MarketSizeUnit,
  [Parameter(Mandatory=$true)][ValidateSet('SHARES')][string]$TickSizeUnit,
  [string]$SessionDate = (Get-Date -Format 'yyyy-MM-dd'),
  [string]$Python = 'py',
  [string]$DataRoot = 'data/phase57-msii-dynamic-live'
)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if(-not (Test-Path '.git')){throw 'Run from the ark-terminal repository root.'}
if($MarketSizeUnit -ne 'SHARES' -or $TickSizeUnit -ne 'SHARES'){throw 'MarketSpeed quantity units must be explicitly attested as SHARES.'}

$sessionRoot=Join-Path $DataRoot $SessionDate
$rawDir=Join-Path $sessionRoot 'lane-y-raw'
$stateFile=Join-Path $sessionRoot 'dynamic-watchlist-state.json'
$outputDir=Join-Path $sessionRoot 'lane-m-output'
$laneMState=Join-Path $outputDir 'full-session-state.json'
New-Item -ItemType Directory -Force -Path $sessionRoot,$rawDir,$outputDir | Out-Null

# Start from the next JPX 5-minute decision bucket after this launcher is invoked.
$startAt=[DateTimeOffset]::Now.ToString('o')
& $Python 'tools/phase57_msii_prepare_mid_session.py' `
  '--raw-dir' $rawDir `
  '--state' $stateFile `
  '--lane-m-state' $laneMState `
  '--session-date' $SessionDate `
  '--start-at' $startAt
if($LASTEXITCODE -ne 0){throw "Mid-session bootstrap failed with exit code $LASTEXITCODE"}

Write-Host '{"status":"PHASE57_MSII_MID_SESSION_LAUNCH","collectionMode":"MID_SESSION_CAUSAL","notEligibleForFullFreshScore":true,"eligibleForMidSessionScore":true,"stateInitialization":"COLD_START","executionAllowed":false,"brokerWriteAllowed":false,"excelOrderWriteAllowed":false,"rssOrderFunctionAllowed":false,"liveTradingAllowed":false,"paperTradingAllowed":false,"automaticPromotionAllowed":false,"productionUpdateAllowed":false,"transmitted":false}'

& powershell -ExecutionPolicy Bypass -File 'tools/phase57_msii_windows_dynamic_session.ps1' `
  -Workbook $Workbook `
  -MarketSizeUnit $MarketSizeUnit `
  -TickSizeUnit $TickSizeUnit `
  -SessionDate $SessionDate `
  -Python $Python `
  -DataRoot $DataRoot
exit $LASTEXITCODE
