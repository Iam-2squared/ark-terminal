# One-command No.1.1 chart50 read-only capture -> strict offline proxy Va join.
param(
 [switch]$OfflineSelfTest,
 [string]$RunDir,
 [string]$PinsFile,
 [ValidateRange(2,390)][int]$Samples=4,
 [ValidateRange(50,150)][int]$HistoryBars=120,
 [ValidateRange(5,60)][int]$WarmupSeconds=20
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=Split-Path -Parent $PSScriptRoot
$probe=Join-Path $PSScriptRoot 'Probe-No11Chart50ContinuousReadOnly.ps1'
$importer=Join-Path $root 'tools\no11_import_chart50_continuous_snapshot.mjs'
if($OfflineSelfTest){
 $o=@(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $probe -OfflineSelfTest -HistoryBars $HistoryBars)
 if($LASTEXITCODE -ne 0 -or -not ($o -contains 'NO11_C50_CONTINUOUS_OFFLINE_SELFTEST=PASS')){
  throw 'NO11_C50_E2E_OFFLINE_PROBE_FAILED'
 }
 Write-Host 'NO11_C50_E2E_OFFLINE_SELFTEST=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$arguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$probe,
 '-Samples',[string]$Samples,'-HistoryBars',[string]$HistoryBars,
 '-WarmupSeconds',[string]$WarmupSeconds)
if(-not [string]::IsNullOrWhiteSpace($RunDir)){
 $arguments+=@('-RunDir',$RunDir)
}
if(-not [string]::IsNullOrWhiteSpace($PinsFile)){
 $arguments+=@('-PinsFile',$PinsFile)
}
$out=@(& powershell.exe @arguments)
$ok=$LASTEXITCODE
$out | ForEach-Object {Write-Host $_}
if($ok -ne 0){throw 'NO11_C50_CAPTURE_FAILED_NO_IMPORT'}
$folderLine=@($out | Where-Object {$_ -like 'NO11_C50_PRIVATE_FOLDER=*'})
$planLine=@($out | Where-Object {$_ -like 'NO11_C50_PRIVATE_CHART_PLAN=*'})
if($folderLine.Count -ne 1 -or $planLine.Count -ne 1){
 throw 'NO11_C50_E2E_MISSING_PRIVATE_CAPTURE_PATH'
}
$folder=([string]$folderLine[0]).Substring('NO11_C50_PRIVATE_FOLDER='.Length)
$plan=([string]$planLine[0]).Substring('NO11_C50_PRIVATE_CHART_PLAN='.Length)
$files=@(Get-ChildItem -LiteralPath $folder -Filter 'snapshot-*.json' -File)
if($files.Count -lt 2 -or $files.Count -gt $Samples){
 throw 'NO11_C50_E2E_SNAPSHOT_COUNT_INVALID'
}
$latest=$null
foreach($file in $files){
 $stamp=Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
 if($stamp.schemaId -cne 'ARK_NO11_RSS_CHART50_1M_CAPTURE_V1' -or
  $stamp.orderTransmission -ne $false){
  throw 'NO11_C50_E2E_CAPTURE_HEADER_INVALID'
 }
 if($null -eq $latest -or $stamp.observedEndJst -gt $latest){
  $latest=[string]$stamp.observedEndJst
 }
}
if([string]::IsNullOrWhiteSpace($latest)){
 throw 'NO11_C50_E2E_LAST_RECEIVED_AT_MISSING'
}
$result=@(& node $importer --folder $folder --plan $plan --decision $latest)
$code=$LASTEXITCODE
$result | ForEach-Object {Write-Host $_}
if($code -ne 0){throw 'NO11_C50_E2E_PRIVATE_IMPORT_FAILED'}
Write-Host 'NO11_C50_E2E_READONLY=COMPLETE_NOT_SELECTOR_NOT_TRADING'
Write-Host 'NO11_PRODUCTION_READY=False'
Write-Host 'ORDER_TRANSMISSION=False'
