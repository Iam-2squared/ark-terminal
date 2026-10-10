# Desktop workbook -> UI2 read-only model. Never creates Excel or issues orders.
param(
 [string]$WorkbookPath=(Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ark_No11_MSII_RSS.xlsx'),
 [string]$UiReadModelPath=(Join-Path $env:LOCALAPPDATA 'ArkTerminal\No11\ui-read-model.json'),
 [string]$OwnershipBaselinePath=(Join-Path $env:LOCALAPPDATA 'ArkTerminal\No11\ownership-baseline.json')
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=Split-Path -Parent $PSScriptRoot
$local=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No11'
$snapshot=Join-Path $local 'snapshot.json'
$ledger=Join-Path $local 'private-safety-ledger.json'
$report=Join-Path $local 'desktop-capital-readonly.json'
$collector=Join-Path $PSScriptRoot 'Start-No11DesktopReadOnly.ps1'
$uiCli=Join-Path $root 'ui\phase57_ui_read_model_cli.mjs'
$faultCli=Join-Path $root 'tools\no11_fault_cli.mjs'
$node=(Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
if(-not (Test-Path -LiteralPath $OwnershipBaselinePath -PathType Leaf)) { throw 'PRIVATE_OWNER_CONFIRMATION_MISSING' }
if(-not (Test-Path -LiteralPath $collector -PathType Leaf)) { throw 'DESKTOP_CAPTURE_ENTRYPOINT_MISSING' }
& $collector -WorkbookPath $WorkbookPath | Out-Null
if(-not $?) { throw 'DESKTOP_CAPTURE_BLOCKED' }
if($LASTEXITCODE -ne 0) { throw 'DESKTOP_CAPTURE_EXIT_NONZERO' }
$funding=Get-Content -LiteralPath $report -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
if($funding.status -cne 'READ_ONLY_CAPITAL_PREVIEW' -or $funding.productionReady -ne $false) {
 throw 'CAPITAL_AND_OWNER_NOT_VERIFIED'
}
# Runtime safety defaults to latched; never supply an approval/reset.
& $node $faultCli 'status' '--ledger' $ledger | Out-Null
if($LASTEXITCODE -ne 0) { throw 'PRIVATE_LEDGER_INVALID' }
$target=[IO.Path]::GetFullPath($UiReadModelPath)
$base=[IO.Path]::GetFullPath($local).TrimEnd('\')+'\'
if(-not $target.StartsWith($base,[StringComparison]::OrdinalIgnoreCase)) {
 throw 'UI_MODEL_OUTSIDE_PRIVATE_DIRECTORY'
}
$tmp=Join-Path $local ('ui-model-'+[Guid]::NewGuid().ToString('N')+'.json')
try {
 $nodeArgs=@($uiCli,'--snapshot',$snapshot,'--ownership',$OwnershipBaselinePath,
  '--runtime-safety',$ledger,'--output',$tmp)
 & $node @nodeArgs | Out-Null
 if($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $tmp)) {
  throw 'UI2_READ_MODEL_CREATION_FAILED'
 }
 $model=Get-Content -LiteralPath $tmp -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
 if($model.schemaId -cne 'ARK_TERMINAL_UI_READ_MODEL_V1' -or $model.readOnly -ne $true) {
  throw 'UI2_READ_MODEL_CONTRACT_INVALID'
 }
 foreach($key in @('orderSubmit','orderCancel','killSwitchChange','strategyEdit',
  'brokerWrite','excelOrderWrite','rssOrderFunction')) {
  if($model.mutationCapabilities.$key -ne $false) { throw "UI2_MUTATION_CAPABILITY_INVALID:$key" }
 }
 if(Test-Path -LiteralPath $target -PathType Leaf) {
  [IO.File]::Replace($tmp,$target,$null)
 } else {
  [IO.File]::Move($tmp,$target)
 }
 Write-Host 'NO11_DESKTOP_UI_READ_ONLY_READY=True'
 Write-Host 'ORDER_TRANSMISSION=False'
} finally {
 if(Test-Path -LiteralPath $tmp -PathType Leaf) {
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
 }
}
