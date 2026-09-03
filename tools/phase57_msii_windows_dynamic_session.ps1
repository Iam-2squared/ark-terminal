param(
  [Parameter(Mandatory=$true)][string]$Workbook,
  [Parameter(Mandatory=$true)][ValidateSet('SHARES')][string]$MarketSizeUnit,
  [Parameter(Mandatory=$true)][ValidateSet('SHARES')][string]$TickSizeUnit,
  [string]$SessionDate = (Get-Date -Format 'yyyy-MM-dd'),
  [string]$Python = "py",
  [string]$Node = "node",
  [int]$Slots = 80,
  [int]$TickRows = 100,
  [double]$CaptureIntervalSeconds = 1.0,
  [double]$SyncPollSeconds = 2.0,
  [double]$WatchlistPollSeconds = 0.5,
  [int]$CaptureSamples = 30000,
  [int]$StartupTimeoutSeconds = 20,
  [int]$RetentionPoints = 3,
  [string]$DataRoot = "data/phase57-msii-dynamic-live",
  [string]$DurableRef = "origin/automation/phase57-realtime-live-data",
  [string]$StopAtJst = "16:10"
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Safety = [ordered]@{
  mode = 'LANE_M_WINDOWS_DYNAMIC_MARKET_DATA_QUERY_ONLY'
  executionAllowed = $false
  brokerWriteAllowed = $false
  excelOrderWriteAllowed = $false
  excelMarketDataQueryWriteAllowed = $true
  rssOrderFunctionAllowed = $false
  liveTradingAllowed = $false
  paperTradingAllowed = $false
  automaticPromotionAllowed = $false
  productionUpdateAllowed = $false
  transmitted = $false
}
foreach ($key in @('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed')) {
  if ($Safety[$key] -ne $false) { throw "Unsafe dynamic Lane M flag: $key" }
}
if ($Safety.excelMarketDataQueryWriteAllowed -ne $true) { throw 'Dynamic market-data query writes must be explicitly scoped.' }
if ($MarketSizeUnit -ne 'SHARES' -or $TickSizeUnit -ne 'SHARES') { throw 'MarketSpeed quantity units must be explicitly attested as SHARES.' }
if ($Slots -lt 50) { throw 'Slots must be >= 50.' }
if ($TickRows -lt 20) { throw 'TickRows must be >= 20.' }
if ($CaptureIntervalSeconds -lt 0.2) { throw 'CaptureIntervalSeconds must be >= 0.2.' }
if ($SyncPollSeconds -lt 1.0) { throw 'SyncPollSeconds must be >= 1.0.' }
if ($WatchlistPollSeconds -lt 0.2) { throw 'WatchlistPollSeconds must be >= 0.2.' }
if ($RetentionPoints -lt 0) { throw 'RetentionPoints must be >= 0.' }
if (-not (Test-Path '.git')) { throw 'Run from the ark-terminal repository root.' }
foreach ($requiredFile in @(
  'tools/phase58_excel_dynamic_slot_capture.py',
  'tools/phase58_dynamic_slot_compat_projector.py',
  'tools/phase57_msii_dynamic_watchlist_watch.mjs',
  'tools/phase57_msii_full_session_runner.mjs',
  'tools/phase57_msii_dashboard_watch.mjs'
)) { if (-not (Test-Path $requiredFile -PathType Leaf)) { throw "Missing runtime file: $requiredFile" } }

function Abs([string]$Value) { return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Value)) }
function StopIso([string]$Date,[string]$Hm) {
  if ($Date -notmatch '^\d{4}-\d{2}-\d{2}$') { throw 'SessionDate must be YYYY-MM-DD.' }
  if ($Hm -notmatch '^([01]\d|2[0-3]):[0-5]\d$') { throw 'StopAtJst must be HH:mm.' }
  return "${Date}T${Hm}:00+09:00"
}
function QuoteArg([string]$Value) {
  if ($Value -notmatch '[\s"]') { return $Value }
  return '"' + ($Value -replace '(\\*)"','$1$1\"' -replace '(\\+)$','$1$1') + '"'
}
function StartLoggedProcess([string]$FilePath,[string[]]$Args,[string]$Stdout,[string]$Stderr) {
  $line = (($Args | ForEach-Object { QuoteArg ([string]$_) }) -join ' ')
  return Start-Process -FilePath $FilePath -ArgumentList $line -PassThru -NoNewWindow -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr
}

$root = Abs $DataRoot
$sessionRoot = Join-Path $root $SessionDate
$rawDir = Join-Path $sessionRoot 'lane-y-raw'
$envelopeDir = Join-Path $sessionRoot 'msii-envelopes'
$outputDir = Join-Path $sessionRoot 'lane-m-output'
$logDir = Join-Path $sessionRoot 'logs'
$watchlist = Join-Path $sessionRoot 'dynamic-watchlist-latest.json'
$watchlistState = Join-Path $sessionRoot 'dynamic-watchlist-state.json'
$dynamicRaw = Join-Path $sessionRoot 'msii-dynamic-p32.jsonl'
$compatRaw = Join-Path $sessionRoot 'msii-runtime-p31.jsonl'
$projectorState = Join-Path $sessionRoot 'projector-state.json'
$lockFile = Join-Path $sessionRoot 'lane-m-dynamic-session.lock'
New-Item -ItemType Directory -Force -Path $sessionRoot,$rawDir,$envelopeDir,$outputDir,$logDir | Out-Null

$lockHandle = $null
try {
  $lockHandle = [System.IO.File]::Open($lockFile,[System.IO.FileMode]::OpenOrCreate,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None)
  $lockHandle.SetLength(0)
  $bytes = [System.Text.Encoding]::UTF8.GetBytes("pid=$PID started=$(Get-Date -Format o)`n")
  $lockHandle.Write($bytes,0,$bytes.Length); $lockHandle.Flush()
} catch { throw "Another dynamic Lane M launcher appears to own $lockFile" }

$stopAt = StopIso $SessionDate $StopAtJst
$repoRoot = (Get-Location).Path
$syncScript = Join-Path $sessionRoot 'sync-durable.generated.ps1'
$syncLog = Join-Path $logDir 'durable-sync.log'
$syncBody = @'
param($RepoRoot,$DurableRef,$SessionDate,$RawDir,$EnvelopeDir,$PollSeconds,$StopAtIso,$LogFile)
$ErrorActionPreference='Stop'
Set-Location $RepoRoot
$stop=[DateTimeOffset]::Parse($StopAtIso)
$prefix="data/phase57-realtime-live/$SessionDate"
while([DateTimeOffset]::Now -lt $stop){
  try {
    git fetch --quiet origin 'refs/heads/automation/phase57-realtime-live-data:refs/remotes/origin/automation/phase57-realtime-live-data'
    if($LASTEXITCODE -ne 0){ throw 'git fetch durable branch failed' }
    foreach($kind in @('raw','msii-envelopes')){
      $remotePrefix="$prefix/$kind"
      $destRoot=if($kind -eq 'raw'){$RawDir}else{$EnvelopeDir}
      $paths=@(git ls-tree -r --name-only $DurableRef -- $remotePrefix 2>$null)
      foreach($remotePath in $paths){
        if(-not $remotePath.EndsWith('.json')){ continue }
        $name=[System.IO.Path]::GetFileName($remotePath)
        $destination=Join-Path $destRoot $name
        if(Test-Path $destination){ continue }
        $temp="$destination.tmp-$PID"
        $payload=git show "${DurableRef}:$remotePath" 2>$null
        if($LASTEXITCODE -ne 0 -or -not $payload){ throw "git show failed: $remotePath" }
        [System.IO.File]::WriteAllText($temp,($payload -join "`n")+"`n",[System.Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temp -Destination $destination
        Add-Content -Path $LogFile -Value "$(Get-Date -Format o) SYNCED $kind/$name"
      }
    }
  } catch { Add-Content -Path $LogFile -Value "$(Get-Date -Format o) SYNC_WAIT $($_.Exception.Message)" }
  Start-Sleep -Milliseconds ([int]($PollSeconds*1000))
}
'@
[System.IO.File]::WriteAllText($syncScript,$syncBody,[System.Text.UTF8Encoding]::new($false))

$syncJob=$null; $capture=$null; $projector=$null; $watcher=$null; $dashboard=$null
try {
  Write-Host (([ordered]@{status='PHASE57_MSII_WINDOWS_DYNAMIC_SESSION_START';sessionDate=$SessionDate;workbook=$Workbook;slots=$Slots;tickRows=$TickRows;marketSizeUnit=$MarketSizeUnit;tickSizeUnit=$TickSizeUnit;sizeUnitAttestation=@{explicit=$true;inferred=$false;operatorProvided=$true};stopAt=$stopAt;safety=$Safety} | ConvertTo-Json -Depth 5 -Compress))

  $syncJob = Start-Job -FilePath $syncScript -ArgumentList $repoRoot,$DurableRef,$SessionDate,$rawDir,$envelopeDir,$SyncPollSeconds,$stopAt,$syncLog

  # Capture starts before the first 09:05 selection and emits a heartbeat. Only ArkControl symbol cells
  # may be changed later; no formula/order/account cells are writable at runtime.
  $captureArgs=@('-u','tools/phase58_excel_dynamic_slot_capture.py','--workbook',$Workbook,'--watchlist',$watchlist,'--output',$dynamicRaw,'--market-size-unit',$MarketSizeUnit,'--tick-size-unit',$TickSizeUnit,'--slots',[string]$Slots,'--tick-rows',[string]$TickRows,'--interval-seconds',[string]$CaptureIntervalSeconds,'--samples',[string]$CaptureSamples)
  $capture=StartLoggedProcess $Python $captureArgs (Join-Path $logDir 'capture.stdout.log') (Join-Path $logDir 'capture.stderr.log')
  $deadline=(Get-Date).AddSeconds($StartupTimeoutSeconds)
  while((Get-Date)-lt $deadline){
    $capture.Refresh(); if($capture.HasExited){throw 'Dynamic MarketSpeed capture exited during startup.'}
    if((Test-Path $dynamicRaw -PathType Leaf)-and (Get-Item $dynamicRaw).Length -gt 0){break}
    Start-Sleep -Milliseconds 250
  }
  if(-not (Test-Path $dynamicRaw -PathType Leaf)){throw 'Dynamic MarketSpeed capture produced no startup heartbeat.'}

  $projectorArgs=@('-u','tools/phase58_dynamic_slot_compat_projector.py','--source',$dynamicRaw,'--output',$compatRaw,'--state',$projectorState,'--poll-seconds','0.5','--iterations',[string]$CaptureSamples)
  $projector=StartLoggedProcess $Python $projectorArgs (Join-Path $logDir 'projector.stdout.log') (Join-Path $logDir 'projector.stderr.log')

  $watchlistArgs=@('tools/phase57_msii_dynamic_watchlist_watch.mjs','--raw-dir',$rawDir,'--output',$watchlist,'--state',$watchlistState,'--session-date',$SessionDate,'--slot-count',[string]$Slots,'--retention-points',[string]$RetentionPoints,'--poll-ms',[string][int]($WatchlistPollSeconds*1000),'--lane-m-state',(Join-Path $outputDir 'full-session-state.json'),'--stop-at',$stopAt)
  $watcher=StartLoggedProcess $Node $watchlistArgs (Join-Path $logDir 'watchlist.stdout.log') (Join-Path $logDir 'watchlist.stderr.log')

  $dashboardArgs=@('tools/phase57_msii_dashboard_watch.mjs','--output-dir',$outputDir,'--poll-ms','1000','--stop-at',$stopAt)
  $dashboard=StartLoggedProcess $Node $dashboardArgs (Join-Path $logDir 'dashboard.stdout.log') (Join-Path $logDir 'dashboard.stderr.log')

  $fullArgs=@('tools/phase57_msii_full_session_runner.mjs','--envelope-dir',$envelopeDir,'--captures',$compatRaw,'--output-dir',$outputDir,'--session-date',$SessionDate,'--poll-ms','1000','--reference-max-age-ms','5000','--ttl-ms','5000','--decision-latency-ms','100','--settle-grace-ms','1000','--stop-at',$stopAt)
  & $Node @fullArgs
  if($LASTEXITCODE -ne 0){throw "Lane M full-session watcher exited $LASTEXITCODE"}

  foreach($process in @($capture,$projector,$watcher,$dashboard)){
    if($process -and -not $process.HasExited){$process.WaitForExit(3000)|Out-Null}
  }
  $finalFile=Join-Path $outputDir 'full-session-final.json'
  if(-not (Test-Path $finalFile -PathType Leaf)){throw 'Lane M final session artifact was not produced.'}
  $final=Get-Content $finalFile -Raw | ConvertFrom-Json
  Write-Host (([ordered]@{status='PHASE57_MSII_WINDOWS_DYNAMIC_SESSION_COMPLETE';sessionDate=$SessionDate;committedPointCount=$final.committedPointCount;blockedPointCount=$final.blockedPointCount;missingCaptureCount=$final.missingCaptureCount;coverage=$final.coverageSummary;marketSizeUnit=$MarketSizeUnit;tickSizeUnit=$TickSizeUnit;safety=$Safety} | ConvertTo-Json -Depth 8 -Compress))
}
finally {
  if($syncJob){Stop-Job $syncJob -ErrorAction SilentlyContinue;Remove-Job $syncJob -Force -ErrorAction SilentlyContinue}
  foreach($process in @($capture,$projector,$watcher,$dashboard)){if($process -and -not $process.HasExited){Stop-Process -Id $process.Id -ErrorAction SilentlyContinue}}
  Remove-Item -LiteralPath $syncScript -Force -ErrorAction SilentlyContinue
  if($lockHandle){$lockHandle.Dispose()}
  Remove-Item -LiteralPath $lockFile -Force -ErrorAction SilentlyContinue
}
