# Installed only over the exact known legacy Run-No11NightlyCycle.ps1.
# Existing WHITE UI calls the same path. No Trade or automatic approval.
param([string]$FullSymbolsFile='', [switch]$WeekendFriday, [switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if($OfflineSelfTest){
 if($WeekendFriday){throw 'SELFTEST_FLAGS'}
 Write-Host 'NO11_NIGHTLY_CYCLE_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $binding=Join-Path $store 'automatic-inputs.json'
 $b=Get-Content -LiteralPath $binding -Raw -Encoding UTF8|ConvertFrom-Json
 if($b.schemaId -cne 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -or $b.orderTransmission -ne $false){throw 'BINDING_CONTRACT'}
 $tool=[string]$b.nightlyResumeTool
 $python=[string]$b.python
 foreach($p in @($tool,$python,$FullSymbolsFile)){
  if(-not [IO.Path]::IsPathRooted($p) -or -not (Test-Path -LiteralPath $p -PathType Leaf)){throw 'MISSING_RUNTIME_OR_SYMBOLS'}
 }
 $actual=(Get-FileHash -LiteralPath $tool -Algorithm SHA256).Hash.ToLowerInvariant()
 if($actual -cne [string]$b.nightlyResumeToolSha256){throw 'NIGHTLY_RESUME_SOURCE_CHANGED'}
 $args=@('-B','-X','utf8',$tool,'--binding',$binding,'--symbols',$FullSymbolsFile)
 if($WeekendFriday){$args+=@('--weekend-friday')}
 & $python @args
 if($LASTEXITCODE -ne 0){throw 'NIGHTLY_RESUME_BLOCKED'}
 exit 0
}catch{
 Write-Host 'NO11_NIGHTLY_CYCLE=BLOCKED|NO11_NIGHTLY_RESUME_ENTRYPOINT_FAILED'
 Write-Host 'SAVED_RECEIPTS_PRESERVED=True'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
