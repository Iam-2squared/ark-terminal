param([Parameter(Mandatory=$true)][string]$Engine)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$windows=Join-Path $Engine 'windows'
$checks=0
function Check([bool]$Ok,[string]$Name){if(-not $Ok){throw ('TEST_FAILED_'+$Name)};$script:checks++}
$files=@('No11RssFundingContract.ps1','Run-No11ReceivedSessionOperatorLive.ps1','Start-No11UnifiedLauncher.ps1')
foreach($file in $files){
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile((Join-Path $windows $file),[ref]$tokens,[ref]$errors)
 Check ($errors.Count -eq 0) ('PARSE_'+$file)
}
$tokens=$null;$errors=$null
[void][Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Install-No11RssFunding.ps1'),[ref]$tokens,[ref]$errors)
Check ($errors.Count -eq 0) 'INSTALLER_PARSE'
. (Join-Path $windows 'No11RssFundingContract.ps1')
$general=-join [char[]]@(0x4e00,0x822c)
$json=@'
{"schemaId":"ARK_NO11_BROKER_EXECUTION_CONFIG_V1","sessionDate":"2026-11-09","fundingPolicy":"RSS_BUYING_POWER","evidenceMode":"BROKER_OBSERVATION","feeCourse":"ZERO","productionReady":false,"orderTransmission":true,"ledger":{"sessionDate":"2026-11-09","account":"GENERAL","allocatedCashJpy":"AUTO_RSS_BUYING_POWER","maxSymbols":3,"lotSize":100},"transport":{"mode":"LIVE","sessionDate":"2026-11-09","orderTransmission":true,"operatorEnabled":true,"approvedForSession":true},"orderTerms":{"sor":true,"accountType":1,"accountTypeVerified":true,"orderType":"MARKET","timeInForce":"DAY"}}
'@
$c=$json.Replace('GENERAL',$general)|ConvertFrom-Json
Assert-No11RssFundingContract $c '2026-11-09';Check $true 'RSS_NO_BANK_FILES'
Check (-not (Test-No11RssFundingPolicy ([pscustomobject]@{}))) 'LEGACY_ABSENT_POLICY'
foreach($failure in @('DAY','APPROVAL','MAX3','SOR')){
 $c=$json.Replace('GENERAL',$general)|ConvertFrom-Json
 switch($failure){
  DAY {$c.transport.sessionDate='2026-11-06'}
  APPROVAL {$c.transport.approvedForSession=$false}
  MAX3 {$c.ledger.maxSymbols=1}
  SOR {$c.orderTerms.sor=$false}
 }
 $bad=$false;try{Assert-No11RssFundingContract $c '2026-11-09'}catch{$bad=$true}
 Check $bad ('REJECT_'+$failure)
}
foreach($name in @('Read-No11BrokerSnapshot.ps1','Capture-No11SessionReferenceReadOnly.ps1','Observe-No11AccountReadOnly.ps1','Invoke-No11MsiiOrder.ps1','Run-No11ReceivedSessionOperatorLive.ps1','Start-No11UnifiedLauncher.ps1')){
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $windows $name) -OfflineSelfTest
 Check ($LASTEXITCODE -eq 0) ('OFFLINE_'+$name)
}
Write-Host ('RSS_FUNDING_PS_CHECKS='+$checks)
Write-Host 'RSS_FUNDING_PS=PASS_OFFLINE_ONLY'
Write-Host 'ORDER_TRANSMISSION=False'
