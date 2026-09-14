param([switch]$Demo, [string]$Config = "$PSScriptRoot\local-config.json")
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
  $version = & node --version
  if ($LASTEXITCODE -ne 0 -or [int]($version.TrimStart('v').Split('.')[0]) -lt 22) { throw 'Node 22 or newer is required.' }
  if (-not $Demo -and -not (Test-Path -LiteralPath $Config)) { throw 'Create local-config.json from local-config.example.json or use -Demo.' }
  & npm.cmd ci --ignore-scripts --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
  & npm.cmd run build
  if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
  Write-Host 'Open http://127.0.0.1:8767 — READ ONLY. Ctrl+C stops the server.'
  if ($Demo) { & node server.mjs --demo } else { & node server.mjs --config $Config }
  if ($LASTEXITCODE -ne 0) { throw 'Server stopped with an error.' }
} finally { Pop-Location }
