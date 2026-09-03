param(
  [Parameter(Mandatory=$true)][string]$Registry,
  [string]$Workbook = "",
  [string]$SessionDate = (Get-Date -Format 'yyyy-MM-dd'),
  [string]$Python = "py",
  [string]$Node = "node",
  [double]$CaptureIntervalSeconds = 1.0,
  [double]$EnvelopePollSeconds = 10.0,
  [int]$CaptureSamples = 30000,
  [int]$CaptureStartupTimeoutSeconds = 20,
  [string]$DataRoot = "data/phase57-msii-live",
  [string]$DurableRef = "origin/automation/phase57-realtime-live-data",
  [string]$StopAtJst = "16:10"
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Safety = [ordered]@{
  mode = 'LANE_M_WINDOWS_FULL_SESSION_READ_ONLY'
  executionAllowed = $false
  brokerWriteAllowed = $false
  excelOrderWriteAllowed = $false
  rssOrderFunctionAllowed = $false
  liveTradingAllowed = $false
  paperTradingAllowed = $false
  automaticPromotionAllowed = $false
  productionUpdateAllowed = $false
  transmitted = $false
}

function Assert-ReadOnlySafety {
  foreach ($key in @('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed')) {
    if ($Safety[$key] -ne $false) { throw "Unsafe Lane M launcher flag: $key" }
  }
}
function Resolve-AbsolutePath([string]$PathValue) { return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $PathValue)) }
function Get-StopAtIso([string]$Date,[string]$Hm) {
  if ($Date -notmatch '^\d{4}-\d{2}-\d{2}$') { throw 'SessionDate must be YYYY-MM-DD' }
  if ($Hm -notmatch '^([01]\d|2[0-3]):[0-5]\d$') { throw 'StopAtJst must be HH:mm' }
  return "${Date}T${Hm}:00+09:00"
}
function Quote-ProcessArgument([string]$Value) {
  if ($Value -notmatch '[\s"]') { return $Value }
  return '"' + ($Value -replace '(\\*)"','$1$1\"' -replace '(\\+)$','$1$1') + '"'
}

Assert-ReadOnlySafety
if ($CaptureIntervalSeconds -lt 0.2) { throw 'CaptureIntervalSeconds must be >= 0.2' }
if ($EnvelopePollSeconds -lt 1.0) { throw 'EnvelopePollSeconds must be >= 1.0' }
if ($CaptureSamples -lt 1) { throw 'CaptureSamples must be >= 1' }
if ($CaptureStartupTimeoutSeconds -lt 5) { throw 'CaptureStartupTimeoutSeconds must be >= 5' }
if (-not (Test-Path $Registry -PathType Leaf)) { throw "Registry not found: $Registry" }
if (-not (Test-Path '.git')) { throw 'Run this launcher from the ark-terminal repository root.' }

$root = Resolve-AbsolutePath $DataRoot
$sessionRoot = Join-Path $root $SessionDate
$captureFile = Join-Path $sessionRoot 'msii-multisymbol-live.jsonl'
$envelopeDir = Join-Path $sessionRoot 'msii-envelopes'
$outputDir = Join-Path $sessionRoot 'lane-m-output'
$logDir = Join-Path $sessionRoot 'logs'
$lockFile = Join-Path $sessionRoot 'lane-m-session.lock'
New-Item -ItemType Directory -Force -Path $sessionRoot,$envelopeDir,$outputDir,$logDir | Out-Null

$lockHandle = $null
try {
  $lockHandle = [System.IO.File]::Open($lockFile,[System.IO.FileMode]::OpenOrCreate,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None)
  $lockHandle.SetLength(0)
  $lockBytes = [System.Text.Encoding]::UTF8.GetBytes("pid=$PID started=$(Get-Date -Format o)`n")
  $lockHandle.Write($lockBytes,0,$lockBytes.Length)
  $lockHandle.Flush()
} catch {
  throw "Another Lane M full-session launcher appears to own $lockFile"
}

$stopAtIso = Get-StopAtIso $SessionDate $StopAtJst
$remoteEnvelopePrefix = "data/phase57-realtime-live/$SessionDate/msii-envelopes"
$syncScript = Join-Path $sessionRoot 'sync-envelopes.generated.ps1'
$syncLog = Join-Path $logDir 'envelope-sync.log'

# Generated worker reads the durable research branch only. Explicit source:destination
# refspec refreshes the remote-tracking ref used by ls-tree/show; main is never checked out.
$syncBody = @'
param($RepoRoot,$DurableRef,$RemotePrefix,$EnvelopeDir,$PollSeconds,$StopAtIso,$LogFile)
$ErrorActionPreference='Stop'
Set-Location $RepoRoot
$stop=[DateTimeOffset]::Parse($StopAtIso)
while([DateTimeOffset]::Now -lt $stop){
  try {
    git fetch --quiet origin 'refs/heads/automation/phase57-realtime-live-data:refs/remotes/origin/automation/phase57-realtime-live-data'
    if($LASTEXITCODE -ne 0){ throw 'git fetch durable branch failed' }
    $paths = @(git ls-tree -r --name-only $DurableRef -- $RemotePrefix 2>$null)
    foreach($remotePath in $paths){
      if(-not $remotePath.EndsWith('.json')){ continue }
      $name=[System.IO.Path]::GetFileName($remotePath)
      $destination=Join-Path $EnvelopeDir $name
      if(Test-Path $destination){ continue }
      $temp="$destination.tmp-$PID"
      $payload = git show "${DurableRef}:$remotePath" 2>$null
      if($LASTEXITCODE -ne 0 -or -not $payload){ throw "git show failed: $remotePath" }
      [System.IO.File]::WriteAllText($temp,($payload -join "`n")+"`n",[System.Text.UTF8Encoding]::new($false))
      Move-Item -LiteralPath $temp -Destination $destination
      Add-Content -Path $LogFile -Value "$(Get-Date -Format o) SYNCED $name"
    }
  } catch {
    Add-Content -Path $LogFile -Value "$(Get-Date -Format o) SYNC_WAIT $($_.Exception.Message)"
  }
  Start-Sleep -Milliseconds ([int]($PollSeconds*1000))
}
'@
[System.IO.File]::WriteAllText($syncScript,$syncBody,[System.Text.UTF8Encoding]::new($false))

$captureArgs = @('-u','tools/phase58_excel_multisymbol_microstructure_capture.py','--registry',(Resolve-AbsolutePath $Registry),'--output',$captureFile,'--interval-seconds',[string]$CaptureIntervalSeconds,'--samples',[string]$CaptureSamples)
if ($Workbook) { $captureArgs += @('--workbook',$Workbook) }
$captureArgumentLine = (($captureArgs | ForEach-Object { Quote-ProcessArgument ([string]$_) }) -join ' ')
$captureStdout = Join-Path $logDir 'capture.stdout.log'
$captureStderr = Join-Path $logDir 'capture.stderr.log'

$syncJob = $null
$captureProcess = $null
try {
  Write-Host (([ordered]@{status='PHASE57_MSII_WINDOWS_FULL_SESSION_START';sessionDate=$SessionDate;captureFile=$captureFile;envelopeDir=$envelopeDir;outputDir=$outputDir;stopAt=$stopAtIso;safety=$Safety} | ConvertTo-Json -Depth 5 -Compress))

  # Start prospective MarketSpeed capture first, then require fresh bytes from this launch.
  # Existing JSONL is allowed for crash recovery, but the file length must increase while
  # this new capture process is alive before the watcher is started.
  $priorCaptureLength = if (Test-Path $captureFile -PathType Leaf) { (Get-Item $captureFile).Length } else { 0L }
  $captureProcess = Start-Process -FilePath $Python -ArgumentList $captureArgumentLine -PassThru -NoNewWindow -RedirectStandardOutput $captureStdout -RedirectStandardError $captureStderr
  $startupDeadline = (Get-Date).AddSeconds($CaptureStartupTimeoutSeconds)
  $captureReady = $false
  while ((Get-Date) -lt $startupDeadline) {
    $captureProcess.Refresh()
    if ($captureProcess.HasExited) {
      $detail = if (Test-Path $captureStderr) { (Get-Content $captureStderr -Raw -ErrorAction SilentlyContinue) } else { '' }
      throw "MarketSpeed capture exited before producing fresh evidence. $detail"
    }
    if ((Test-Path $captureFile -PathType Leaf) -and (Get-Item $captureFile).Length -gt $priorCaptureLength) { $captureReady = $true; break }
    Start-Sleep -Milliseconds 250
  }
  if (-not $captureReady) { throw "MarketSpeed capture produced no fresh evidence within $CaptureStartupTimeoutSeconds seconds." }

  # Sync only immutable Lane Y -> M capsules from the durable branch. The job never writes GitHub.
  $repoRoot = (Get-Location).Path
  $syncJob = Start-Job -FilePath $syncScript -ArgumentList $repoRoot,$DurableRef,$remoteEnvelopePrefix,$envelopeDir,$EnvelopePollSeconds,$stopAtIso,$syncLog

  # Lane Y ingests Yahoo's finalized bar with an approximately 960-second source delay.
  # Keep this watcher alive after JPX close so the final 15:30 causal capsule can arrive;
  # MarketSpeed evidence was already captured prospectively near the original timestamp.
  $watcherArgs = @(
    'tools/phase57_msii_full_session_runner.mjs',
    '--envelope-dir',$envelopeDir,
    '--captures',$captureFile,
    '--output-dir',$outputDir,
    '--session-date',$SessionDate,
    '--poll-ms','1000',
    '--reference-max-age-ms','5000',
    '--ttl-ms','5000',
    '--decision-latency-ms','100',
    '--settle-grace-ms','1000',
    '--stop-at',$stopAtIso
  )
  & $Node @watcherArgs
  if ($LASTEXITCODE -ne 0) { throw "Lane M full-session watcher exited $LASTEXITCODE" }
}
finally {
  if ($syncJob) {
    Stop-Job $syncJob -ErrorAction SilentlyContinue
    Remove-Job $syncJob -Force -ErrorAction SilentlyContinue
  }
  if ($captureProcess -and -not $captureProcess.HasExited) { Stop-Process -Id $captureProcess.Id -ErrorAction SilentlyContinue }
  Remove-Item -LiteralPath $syncScript -Force -ErrorAction SilentlyContinue
  if ($lockHandle) { $lockHandle.Dispose() }
  Remove-Item -LiteralPath $lockFile -Force -ErrorAction SilentlyContinue
}

$finalFile = Join-Path $outputDir 'full-session-final.json'
if (-not (Test-Path $finalFile -PathType Leaf)) { throw 'Lane M final session artifact was not produced.' }
$final = Get-Content $finalFile -Raw | ConvertFrom-Json
Write-Host (([ordered]@{status='PHASE57_MSII_WINDOWS_FULL_SESSION_COMPLETE';sessionDate=$SessionDate;committedPointCount=$final.committedPointCount;blockedPointCount=$final.blockedPointCount;missingCaptureCount=$final.missingCaptureCount;finalArtifact=$finalFile;safety=$Safety} | ConvertTo-Json -Depth 5 -Compress))
