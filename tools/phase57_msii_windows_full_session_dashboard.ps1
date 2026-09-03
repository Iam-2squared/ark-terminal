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
  [string]$StopAtJst = "16:10",
  [int]$DashboardPollMs = 1000
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Safety = [ordered]@{
  mode = 'LANE_M_WINDOWS_DASHBOARD_SESSION_READ_ONLY'
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

function Quote-ProcessArgument([string]$Value) {
  if ($Value -notmatch '[\s"]') { return $Value }
  return '"' + ($Value -replace '(\\*)"','$1$1\"' -replace '(\\+)$','$1$1') + '"'
}

foreach ($key in @('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed')) {
  if ($Safety[$key] -ne $false) { throw "Unsafe Lane M dashboard wrapper flag: $key" }
}
if ($DashboardPollMs -lt 200) { throw 'DashboardPollMs must be >= 200' }
if ($SessionDate -notmatch '^\d{4}-\d{2}-\d{2}$') { throw 'SessionDate must be YYYY-MM-DD' }
if ($StopAtJst -notmatch '^([01]\d|2[0-3]):[0-5]\d$') { throw 'StopAtJst must be HH:mm' }
if (-not (Test-Path 'tools/phase57_msii_windows_full_session.ps1' -PathType Leaf)) { throw 'Core Lane M Windows launcher not found.' }
if (-not (Test-Path 'tools/phase57_msii_dashboard_watch.mjs' -PathType Leaf)) { throw 'Lane M dashboard watcher not found.' }

$sessionRoot = Join-Path ([System.IO.Path]::GetFullPath((Join-Path (Get-Location) $DataRoot))) $SessionDate
$outputDir = Join-Path $sessionRoot 'lane-m-output'
$logDir = Join-Path $sessionRoot 'logs'
New-Item -ItemType Directory -Force -Path $outputDir,$logDir | Out-Null
$stopAtIso = "${SessionDate}T${StopAtJst}:00+09:00"

$dashboardStdout = Join-Path $logDir 'dashboard.stdout.log'
$dashboardStderr = Join-Path $logDir 'dashboard.stderr.log'
$dashboardArgs = @(
  'tools/phase57_msii_dashboard_watch.mjs',
  '--output-dir', $outputDir,
  '--poll-ms', [string]$DashboardPollMs,
  '--stop-at', $stopAtIso
)
$dashboardArgumentLine = (($dashboardArgs | ForEach-Object { Quote-ProcessArgument ([string]$_) }) -join ' ')
$dashboardProcess = $null

try {
  Write-Host (([ordered]@{status='PHASE57_MSII_WINDOWS_DASHBOARD_SESSION_START';sessionDate=$SessionDate;outputDir=$outputDir;stopAt=$stopAtIso;safety=$Safety} | ConvertTo-Json -Depth 5 -Compress))
  $dashboardProcess = Start-Process -FilePath $Node -ArgumentList $dashboardArgumentLine -PassThru -NoNewWindow -RedirectStandardOutput $dashboardStdout -RedirectStandardError $dashboardStderr

  $coreArgs = @(
    '-ExecutionPolicy','Bypass',
    '-File','tools\phase57_msii_windows_full_session.ps1',
    '-Registry',$Registry,
    '-SessionDate',$SessionDate,
    '-Python',$Python,
    '-Node',$Node,
    '-CaptureIntervalSeconds',[string]$CaptureIntervalSeconds,
    '-EnvelopePollSeconds',[string]$EnvelopePollSeconds,
    '-CaptureSamples',[string]$CaptureSamples,
    '-CaptureStartupTimeoutSeconds',[string]$CaptureStartupTimeoutSeconds,
    '-DataRoot',$DataRoot,
    '-DurableRef',$DurableRef,
    '-StopAtJst',$StopAtJst
  )
  if ($Workbook) { $coreArgs += @('-Workbook',$Workbook) }
  & powershell @coreArgs
  if ($LASTEXITCODE -ne 0) { throw "Core Lane M full-session launcher exited $LASTEXITCODE" }

  if ($dashboardProcess -and -not $dashboardProcess.HasExited) {
    $dashboardProcess.WaitForExit(5000) | Out-Null
  }
  $dashboardLatest = Join-Path $outputDir 'dashboard-latest.json'
  $dashboardHistory = Join-Path $outputDir 'dashboard-history.json'
  if (-not (Test-Path $dashboardLatest -PathType Leaf)) { throw 'Lane M dashboard-latest.json was not produced.' }
  if (-not (Test-Path $dashboardHistory -PathType Leaf)) { throw 'Lane M dashboard-history.json was not produced.' }
  $latest = Get-Content $dashboardLatest -Raw | ConvertFrom-Json
  Write-Host (([ordered]@{status='PHASE57_MSII_WINDOWS_DASHBOARD_SESSION_COMPLETE';sessionDate=$SessionDate;dashboardAt=$latest.at;strategyCount=$latest.aggregate.strategyCount;fillRatePercent=$latest.aggregate.fillRatePercent;netPnlJpy=$latest.aggregate.netPnlJpy;pairCount=$latest.aggregate.pairCount;coveragePercent=$latest.aggregate.coveragePercent;safety=$Safety} | ConvertTo-Json -Depth 5 -Compress))
}
finally {
  if ($dashboardProcess -and -not $dashboardProcess.HasExited) { Stop-Process -Id $dashboardProcess.Id -ErrorAction SilentlyContinue }
}
