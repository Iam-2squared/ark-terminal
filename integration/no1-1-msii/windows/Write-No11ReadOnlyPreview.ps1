param(
  [string]$WorkbookPath = "C:\Ark\Ark_No11_RSS_ReadOnly.xlsx",
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
$faultCli = Join-Path $root "tools\no11_fault_cli.mjs"
$node = (Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
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
# Bounded COM retry applies only to RPC_E_CALL_REJECTED. Exhaustion latches
# a private Kill Switch. Unrelated failures never receive blind retries.
$captured=$false
for ($attempt=1; $attempt -le 3; $attempt++) {
  try {
    & $snapshotScript @snapshotArgs
    $captured=$true
    break
  }
  catch {
    $msg=[string]$_.Exception.Message
    $busy=$msg -match 'RPC_E_CALL_REJECTED|0x80010001'
    if ($busy -and $attempt -lt 3) {
      Start-Sleep -Milliseconds 250
      continue
    }
    $fault = if ($busy) { 'EXCEL_COM_RETRY_EXHAUSTED' }
      elseif ($msg -match 'RSS_ADDIN|#NAME') { 'RSS_ADDIN_NOT_LOADED' }
      else { 'READ_ONLY_CAPTURE_FAILED' }
    & $node $faultCli latch --ledger $safety --reason $fault | Out-Null
    throw ("NO11_CAPTURE_FAIL_CLOSED:{0}" -f $fault)
  }
}
if (-not $captured) { throw "NO11_CAPTURE_RETRY_EXHAUSTED" }
if (-not (Test-Path -LiteralPath $snapshot -PathType Leaf) -or
    -not (Test-Path -LiteralPath $health -PathType Leaf)) { throw "NO11_SNAPSHOT_OR_HEALTH_MISSING" }

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
  # Validate the persisted ledger checksum before exposing it to UI. Missing
  # ledger starts latched; corrupted ledgers never project a fabricated CLEAR.
  & $node $faultCli status --ledger $safety | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "NO11_PRIVATE_SAFETY_LEDGER_INVALID" }
  $nativeArgs += @("--runtime-safety",$safety)
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
