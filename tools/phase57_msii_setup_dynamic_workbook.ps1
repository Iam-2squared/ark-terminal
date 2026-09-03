param(
  [Parameter(Mandatory=$true)][string]$WorkbookPath,
  [int]$Slots = 80,
  [int]$TickRows = 100,
  [string]$Python = "py",
  [switch]$Overwrite
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Safety = [ordered]@{
  mode = 'LANE_M_DYNAMIC_WORKBOOK_SETUP_MARKET_DATA_QUERY_ONLY'
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
  if ($Safety[$key] -ne $false) { throw "Unsafe workbook setup flag: $key" }
}
if ($Safety.excelMarketDataQueryWriteAllowed -ne $true) { throw 'Market-data query cell writes must be explicitly scoped.' }
if ($Slots -lt 50) { throw 'Slots must be >= 50.' }
if ($TickRows -lt 20) { throw 'TickRows must be >= 20.' }
if (-not (Test-Path 'tools/phase58_excel_dynamic_slot_setup.py' -PathType Leaf)) { throw 'Run from the ark-terminal repository root.' }

$manifest = [System.IO.Path]::ChangeExtension([System.IO.Path]::GetFullPath($WorkbookPath), '.manifest.json')
$args = @(
  'tools/phase58_excel_dynamic_slot_setup.py',
  '--workbook', $WorkbookPath,
  '--slots', [string]$Slots,
  '--tick-rows', [string]$TickRows,
  '--manifest', $manifest
)
if ($Overwrite) { $args += '--overwrite' }

Write-Host (([ordered]@{status='PHASE57_MSII_DYNAMIC_WORKBOOK_SETUP_START';workbook=$WorkbookPath;slots=$Slots;tickRows=$TickRows;safety=$Safety} | ConvertTo-Json -Depth 5 -Compress))
& $Python @args
if ($LASTEXITCODE -ne 0) { throw "Dynamic workbook setup exited $LASTEXITCODE" }
if (-not (Test-Path $WorkbookPath -PathType Leaf)) { throw 'Dynamic workbook was not created.' }
if (-not (Test-Path $manifest -PathType Leaf)) { throw 'Dynamic workbook manifest was not created.' }
Write-Host (([ordered]@{status='PHASE57_MSII_DYNAMIC_WORKBOOK_SETUP_COMPLETE';workbook=[System.IO.Path]::GetFullPath($WorkbookPath);manifest=$manifest;slots=$Slots;tickRows=$TickRows;safety=$Safety} | ConvertTo-Json -Depth 5 -Compress))
