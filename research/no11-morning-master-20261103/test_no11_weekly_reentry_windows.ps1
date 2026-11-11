# Test only the original native StartChild function, never Excel/RSS/order.
param([Parameter(Mandatory=$true)][string]$Candidate)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Check([bool]$ok,[string]$why){if(-not $ok){throw ('WEEKLY_REENTRY_TEST_'+$why)}}
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Candidate,[ref]$tokens,[ref]$errors)
Check ($errors.Count -eq 0) 'NATIVE_PARSE'
$names=@('StartChild','Need','SafeArg','Clock')
$functions=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in $names},$true))
Check ($functions.Count -eq $names.Count) 'FUNCTIONS_MISSING'
foreach($fn in $functions){Invoke-Expression $fn.Extent.Text}
$store=Join-Path $env:TEMP ('ARK-No11-Weekly-Mock-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($store)
$script:Launches=0
$script:MockBusy=$false
function Start-Process {
 param([string]$FilePath,[string]$ArgumentList,[string]$WorkingDirectory,
       [string]$RedirectStandardOutput,[string]$RedirectStandardError,[switch]$PassThru)
 $script:Launches++
 return [pscustomobject]@{Id=8080}
}
function Get-CimInstance {
 param([string]$ClassName,$ErrorAction)
 if($script:MockBusy){
  return [pscustomobject]@{Name='powershell.exe';ProcessId=123456;CommandLine='powershell.exe -File Run-No11NightlyCycle.ps1'}
 }
 return @()
}
try{
 $day='2026-11-06'
 $source='a'*64
 $fake=Join-Path $store 'weekly-fixture.ps1'
 [IO.File]::WriteAllText($fake,'# no broker code')
 StartChild 'WEEKLY' $fake @('-FullSymbolsFile','X:\symbols.txt') $source $day
 Check ($script:Launches -eq 1) 'FIRST_LAUNCH'
 $marker=Join-Path $store ('WEEKLY-'+$day+'.launch.json')
 Check (Test-Path -LiteralPath $marker -PathType Leaf) 'MARKER_MISSING'
 $before=[IO.File]::ReadAllBytes($marker)
 StartChild 'WEEKLY' $fake @('-FullSymbolsFile','X:\symbols.txt') $source $day
 Check ($script:Launches -eq 2) 'SECOND_DATA_ONLY_REQUEST'
 Check (([IO.File]::ReadAllBytes($marker) -join ',') -ceq ($before -join ',')) 'MARKER_OVERWRITTEN'
 $script:MockBusy=$true
 $blocked=$false
 try{StartChild 'WEEKLY' $fake @() $source $day}catch{$blocked=($_.Exception.Message -match 'WEEKLY_PREVIOUS_WORKER_STILL_RUNNING')}
 Check ($blocked -and $script:Launches -eq 2) 'ACTIVE_WORKER_DUPLICATED'
 $script:MockBusy=$false
 $blocked=$false
 try{StartChild 'WEEKLY' $fake @() ('b'*64) $day}catch{$blocked=($_.Exception.Message -match 'WEEKLY_OLD_REQUEST_DIFFERENT')}
 Check ($blocked -and $script:Launches -eq 2) 'DIFFERENT_SOURCE_ADMITTED'
 $trade=Join-Path $store ('TRADE-'+$day+'.launch.json')
 [IO.File]::WriteAllText($trade,'{"kind":"TRADE"}')
 $blocked=$false
 try{StartChild 'TRADE' $fake @() $source $day}catch{$blocked=($_.Exception.Message -match 'TRADE_ALREADY_STARTED_NO_DUPLICATE')}
 Check ($blocked -and $script:Launches -eq 2) 'TRADE_MARKER_REUSED'
 Write-Host 'NO11_WEEKLY_REENTRY_WINDOWS_TESTS=PASS'
 Write-Host 'BROKER_FUNCTION_CALLED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}finally{
 if(Test-Path -LiteralPath $store -PathType Container){Remove-Item -LiteralPath $store -Recurse -Force}
}
