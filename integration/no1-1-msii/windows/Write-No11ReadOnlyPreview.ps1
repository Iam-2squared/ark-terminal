param(
  [string]$WorkbookPath = "C:\Ark\Ark_MSII_LiveSource.xlsx",
  [string]$UiReadModelPath = (Join-Path $env:LOCALAPPDATA "ArkTerminal\No11\ui-read-model.json"),
  [string]$OwnershipBaselinePath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$snapshotScript = Join-Path $PSScriptRoot "Get-No11ReadOnlySnapshot.ps1"
$exporter = Join-Path $root "ui\phase57_ui_read_model_cli.mjs"
$local = Join-Path $env:LOCALAPPDATA "ArkTerminal\No11"
$snapshot = Join-Path $local "snapshot.json"
$health = Join-Path $local "source-health.json"
$safety = Join-Path $local "private-safety-ledger.json"
$model = [IO.Path]::GetFullPath($UiReadModelPath)
if (-not (Test-Path -LiteralPath $snapshotScript -PathType Leaf)) { throw "NO11_READ_ONLY_SNAPSHOT_SCRIPT_MISSING" }
if (-not (Test-Path -LiteralPath $exporter -PathType Leaf)) { throw "NO11_READ_ONLY_UI_EXPORTER_MISSING" }
$book = Split-Path -Leaf $WorkbookPath
# Workbook must already be open. The RSS XLL must be enabled through Excel.
$snapshotArgs = @{
    WorkbookName = $book
    WorkbookPath = $WorkbookPath
    SnapshotPath = $snapshot
    SourceHealthPath = $health
    DoNotAutoOpenWorkbook = $true
}
& $snapshotScript @snapshotArgs
if (-not (Test-Path -LiteralPath $snapshot -PathType Leaf) -or
    -not (Test-Path -LiteralPath $health -PathType Leaf)) { throw "NO11_SNAPSHOT_OR_HEALTH_MISSING" }

$node = (Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$targetDir = Split-Path -Parent $model
[void](New-Item -Path $targetDir -ItemType Directory -Force)
$tmp = Join-Path $targetDir ("ui-read-model-" + [guid]::NewGuid().ToString("N") + ".json")
try {
  $nativeArgs = @($exporter,"--snapshot",$snapshot,"--output",$tmp)
  if (-not [string]::IsNullOrWhiteSpace($OwnershipBaselinePath)) {
    $resolvedOwnership = (Resolve-Path -LiteralPath $OwnershipBaselinePath -ErrorAction Stop).Path
    $nativeArgs += @("--ownership",$resolvedOwnership)
  }
  # A persisted private Kill Switch is displayed if present.
  # Missing state remains UNKNOWN; NEVER fabricate a CLEAR state.
  if (Test-Path -LiteralPath $safety -PathType Leaf) {
    $nativeArgs += @("--runtime-safety",$safety)
  }
  & $node @nativeArgs
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $tmp -PathType Leaf)) { throw "NO11_UI_READ_MODEL_EXPORT_FAILED" }
  $read = [IO.File]::ReadAllText($tmp,[Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
  if ($read.schemaId -ne "ARK_TERMINAL_UI_READ_MODEL_V1" -or $read.readOnly -ne $true) { throw "NO11_UI_MODEL_INVALID" }
  foreach ($item in @("orderSubmit","orderCancel","killSwitchChange","strategyEdit","brokerWrite","excelOrderWrite","rssOrderFunction")) {
    if ($read.mutationCapabilities.$item -ne $false) { throw "NO11_UI_MUTATION_FLAG_INVALID:$item" }
  }
  if ([IO.File]::Exists($model)) { [IO.File]::Replace($tmp,$model,$null) }
  else { [IO.File]::Move($tmp,$model) }
  Write-Host "NO11_READ_ONLY_PREVIEW_UPDATED"
  Write-Host "SourceState :" $read.source.freshness.state
  Write-Host "Ownership   :" $read.system.ownership.state
  Write-Host "Runtime     :" $read.system.runtimeSafety.state
  Write-Host "Readiness   :" $read.system.tradeReadiness
  Write-Host "Mutations   : FALSE"
  Write-Host "OrderWrites : FALSE"
}
finally {
  if (Test-Path -LiteralPath $tmp -PathType Leaf) { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue }
}
