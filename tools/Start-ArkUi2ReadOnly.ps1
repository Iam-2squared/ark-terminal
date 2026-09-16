param(
    [ValidateRange(1024,65535)][int]$Port = 8767,
    [ValidateRange(1,300)][int]$RefreshSeconds = 5,
    [ValidateRange(2,600)][int]$MaxModelAgeSeconds = 15,
    [string]$WorkbookPath = "C:\Ark\Ark_MSII_LiveSource.xlsx",
    [string]$UiReadModelPath = "C:\Ark\ui-readonly\ark-terminal-ui-read-model.json",
    [string]$OwnershipBaselinePath = "",
    [switch]$NoAutoRefresh,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$server = Join-Path $PSScriptRoot "ark_ui2_readonly_server.py"
if (-not (Test-Path -LiteralPath $server -PathType Leaf)) { throw "ARK_UI2_READ_ONLY_SERVER_MISSING" }

$python = Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1
$arguments = @(
    $server,
    "--port", [string]$Port,
    "--refresh-seconds", [string]$RefreshSeconds,
    "--max-model-age-seconds", [string]$MaxModelAgeSeconds,
    "--workbook", ([IO.Path]::GetFullPath($WorkbookPath)),
    "--model", ([IO.Path]::GetFullPath($UiReadModelPath))
)
if (-not [string]::IsNullOrWhiteSpace($OwnershipBaselinePath)) {
    $ownership = (Resolve-Path -LiteralPath $OwnershipBaselinePath -ErrorAction Stop).Path
    $arguments += @("--ownership", $ownership)
}
if ($NoAutoRefresh) { $arguments += "--no-refresh" }
if (-not $NoBrowser) { $arguments += "--open-browser" }

Write-Host "ARK_UI2_READ_ONLY_STARTING"
Write-Host "URL           :" ("http://127.0.0.1:{0}/" -f $Port)
Write-Host "Workbook      :" ([IO.Path]::GetFullPath($WorkbookPath))
Write-Host "ReadModel     :" ([IO.Path]::GetFullPath($UiReadModelPath))
Write-Host "AutoRefresh   :" (-not $NoAutoRefresh)
Write-Host "Mutations     : FALSE"
Write-Host "Stop          : Ctrl+C"

Push-Location $repo
try {
    & $python.Source @arguments
    if ($LASTEXITCODE -ne 0) { throw "ARK_UI2_READ_ONLY_SERVER_FAILED:$LASTEXITCODE" }
}
finally {
    Pop-Location
}
