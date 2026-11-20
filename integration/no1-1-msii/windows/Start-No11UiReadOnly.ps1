param(
  [ValidateRange(1024,65535)][int]$Port = 8767,
  [ValidateRange(3,300)][int]$RefreshSeconds = 15,
  [ValidateRange(15,600)][int]$MaxModelAgeSeconds = 60,
  [string]$WorkbookPath = "C:\Ark\Ark_No11_RSS_DefaultHeaders_v2.xlsx",
  [string]$UiReadModelPath = (Join-Path $env:LOCALAPPDATA "ArkTerminal\No11\ui-read-model.json"),
  [string]$OwnershipBaselinePath = "",
  [switch]$NoAutoRefresh,
  [switch]$NoBrowser
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$server = Join-Path $root "ui\ark_ui2_readonly_server.py"
if (-not (Test-Path -LiteralPath $server -PathType Leaf)) { throw "NO11_UI_SERVER_MISSING" }
$python = (Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$nativeArgs = @($server,
  "--port",[string]$Port,
  "--refresh-seconds",[string]$RefreshSeconds,
  "--max-model-age-seconds",[string]$MaxModelAgeSeconds,
  "--workbook",([IO.Path]::GetFullPath($WorkbookPath)),
  "--model",([IO.Path]::GetFullPath($UiReadModelPath))
)
if (-not [string]::IsNullOrWhiteSpace($OwnershipBaselinePath)) {
  $nativeArgs += @("--ownership",(Resolve-Path -LiteralPath $OwnershipBaselinePath -ErrorAction Stop).Path)
}
if ($NoAutoRefresh) { $nativeArgs += "--no-refresh" }
if (-not $NoBrowser) { $nativeArgs += "--open-browser" }
Write-Host "NO11_UI2_LOOPBACK_READ_ONLY_STARTING"
Write-Host "URL         :" ("http://127.0.0.1:{0}/" -f $Port)
Write-Host "AutoRefresh :" (-not $NoAutoRefresh)
Write-Host "Transmit    : FALSE"
Write-Host "Mutations   : FALSE"
Write-Host "Stop        : Ctrl+C"
& $python @nativeArgs
if ($LASTEXITCODE -ne 0) { throw ("NO11_UI2_SERVER_FAILED:{0}" -f $LASTEXITCODE) }
