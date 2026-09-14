param(
    [string]$Workbook = 'C:\Ark\Source.xlsx',
    [string[]]$Symbols = @('7203.T'),
    [ValidateRange(1,3000)][int]$Rows = 120,
    [ValidateRange(1,28800)][int]$Seconds = 60,
    [switch]$FixtureTest
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    Get-Command python -ErrorAction Stop | Out-Null
    Get-Command node -ErrorAction Stop | Out-Null
    if ($FixtureTest) {
        & python tools/test_phase57_rss_raw.py
        if ($LASTEXITCODE -ne 0) { throw 'Raw workbook fixture gate failed' }
        Write-Output 'RSS_SETUP_FIXTURE_PASS; ACTUAL_EXCEL_UNVERIFIED'
        return
    }
    & python -c 'import sys; assert sys.version_info >= (3,10)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required; workbook unchanged.' }
    & python -c 'import importlib.util, sys; sys.exit(0 if importlib.util.find_spec("win32com") else 1)'
    if ($LASTEXITCODE -ne 0) {
        & python -m pip install pywin32
        if ($LASTEXITCODE -ne 0) { throw 'pywin32 installation failed; workbook unchanged.' }
    }
    & python -c 'import win32com.client'
    if ($LASTEXITCODE -ne 0) {
        throw 'Python 3.10+ with pywin32 is required. No workbook has been changed.'
    }
    & python tools/phase57_setup_rss_source.py --workbook $Workbook --rows $Rows --symbols $Symbols
    if ($LASTEXITCODE -ne 0) { throw 'RSS setup failed. Preserve output and backup; no strategy was started.' }
    $config = Join-Path (Split-Path -Parent $Workbook) 'local-source.json'
    & ./tools/Start-ArkParity.ps1 -Mode SOURCE_SEMANTICS_ONLY -Config $config -Seconds $Seconds
    if ($LASTEXITCODE -ne 0) { throw 'Source diagnostic failed; raw evidence retained.' }
} finally { Pop-Location }
