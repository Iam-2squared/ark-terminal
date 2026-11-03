# Ark No11 after-close -> next-session handoff, installed as the existing Weekly button's child.
# No trading process, broker order, background approval, synthetic pricing or portfolio reset.
param(
 [string]$FullSymbolsFile='',
 [switch]$WeekendFriday,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why) {
 if(-not $ok){throw ('NO11_NIGHTLY_CYCLE_'+$why)}
}
$original=Join-Path $PSScriptRoot 'Prepare-No11WeeklyAfterCloseReadOnly.ps1'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$bindingFile=Join-Path $store 'automatic-inputs.json'

if($OfflineSelfTest){
 Need (Test-Path -LiteralPath $original -PathType Leaf) 'ORIGINAL_AFTERCLOSE_SOURCE_MISSING'
 Need (-not $WeekendFriday) 'OFFLINE_WEEKEND_NOT_ALLOWED'
 Write-Host 'NO11_NIGHTLY_CYCLE_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}

try {
 Need (Test-Path -LiteralPath $original -PathType Leaf) 'ORIGINAL_AFTERCLOSE_SOURCE_MISSING'
 Need (Test-Path -LiteralPath $bindingFile -PathType Leaf) 'DAILY_CYCLE_NOT_INSTALLED'
 $binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
       $binding.orderTransmission -eq $false -and
       $binding.manualPriceInputRequired -eq $false -and
       $binding.manualEvidenceRequired -eq $false) 'BINDING_MODE'
 $python=[string]$binding.python
 $cycle=[string]$binding.dailyCycleTool
 $root=[string]$binding.dailyCycleRoot
 Need ([IO.Path]::IsPathRooted($python) -and
       (Test-Path -LiteralPath $python -PathType Leaf) -and
       [IO.Path]::IsPathRooted($cycle) -and
       (Test-Path -LiteralPath $cycle -PathType Leaf) -and
       [IO.Path]::IsPathRooted($root) -and
       (Test-Path -LiteralPath $root -PathType Container)) 'BOUND_DAILY_RUNTIME_MISSING'
 $digest=(Get-FileHash -LiteralPath $cycle -Algorithm SHA256).Hash.ToLowerInvariant()
 Need ($digest -ceq [string]$binding.dailyCycleToolSha256) 'DAILY_TOOL_SOURCE_HASH'
 Need (-not [string]::IsNullOrWhiteSpace($FullSymbolsFile) -and
       [IO.Path]::IsPathRooted($FullSymbolsFile) -and
       (Test-Path -LiteralPath $FullSymbolsFile -PathType Leaf)) 'FULL_SYMBOLS_FILE'
 $logs=Join-Path $root 'logs'
 [void][IO.Directory]::CreateDirectory($logs)
 $day=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-dd')
 $log=Join-Path $logs ('original-nightly-'+$day+'-'+[guid]::NewGuid().ToString('N')+'.log')
 $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
          '-File',$original,'-FullSymbolsFile',$FullSymbolsFile,
          '-PythonExecutable',$python)
 if($WeekendFriday){$args+=@('-WeekendFriday')}
 Write-Host 'NO11_NIGHTLY_CYCLE_STAGE=ORIGINAL_WEEKLY_OR_DAILY_RSS'
 $lines=@(& powershell.exe @args)
 $code=$LASTEXITCODE
 foreach($line in $lines){Write-Host ([string]$line)}
 [IO.File]::WriteAllLines($log,[string[]]$lines,[Text.UTF8Encoding]::new($false))
 Need ($code -eq 0) 'ORIGINAL_RSS_NIGHTLY_INCOMPLETE'
 Write-Host 'NO11_NIGHTLY_CYCLE_STAGE=PREPARE_NEXT_DAY_HANDOFF'
 & $python -B -X utf8 $cycle stage --binding $bindingFile --nightly-log $log
 Need ($LASTEXITCODE -eq 0) 'NEXT_SESSION_HANDOFF_INCOMPLETE'
 Write-Host 'NO11_NIGHTLY_CYCLE=NEXT_SESSION_READY_FOR_TRADE_BUTTON'
 Write-Host 'MANUAL_EVIDENCE_REQUIRED=False'
 Write-Host 'MANUAL_PRICE_INPUT_REQUIRED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch {
 $message=[string]$_.Exception.Message
 if($message -cnotmatch '^NO11_NIGHTLY_CYCLE_[A-Z0-9_]+$'){
  $message='NO11_NIGHTLY_CYCLE_SOURCE_OR_RUNTIME_FAILURE'
 }
 Write-Host ('NO11_NIGHTLY_CYCLE=BLOCKED|'+$message)
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
