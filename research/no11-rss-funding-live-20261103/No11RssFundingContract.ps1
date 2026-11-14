# Pure policy checks plus bounded observer-file wait. No Excel or order writes.
function Test-No11RssFundingPolicy($Broker) {
 $property=$Broker.PSObject.Properties['fundingPolicy']
 return ($null -ne $property -and $property.Value -ceq 'RSS_BUYING_POWER')
}
function Assert-No11RssFundingContract($Broker,[string]$SessionDate) {
 function RequireRss([bool]$Ok,[string]$Reason) {if(-not $Ok){throw ('NO11_OPERATOR_LIVE_RSS_'+$Reason)}}
 RequireRss (Test-No11RssFundingPolicy $Broker) 'POLICY_REQUIRED'
 RequireRss ($Broker.schemaId -ceq 'ARK_NO11_BROKER_EXECUTION_CONFIG_V1' -and
  $Broker.sessionDate -ceq $SessionDate -and $Broker.evidenceMode -ceq 'BROKER_OBSERVATION' -and
  $Broker.productionReady -ceq $false -and $Broker.orderTransmission -ceq $true) 'CONFIG'
 RequireRss ($Broker.transport.mode -ceq 'LIVE' -and
  $Broker.transport.orderTransmission -ceq $true -and
  $Broker.transport.operatorEnabled -ceq $true -and
  $Broker.transport.approvedForSession -ceq $true -and
  $Broker.transport.sessionDate -ceq $SessionDate) 'SESSION_APPROVAL'
 RequireRss ($Broker.ledger.allocatedCashJpy -ceq 'AUTO_RSS_BUYING_POWER' -and
  $Broker.ledger.account -ceq (-join [char[]]@(0x4e00,0x822c)) -and
  $Broker.ledger.sessionDate -ceq $SessionDate -and
  $Broker.ledger.maxSymbols -eq 3 -and $Broker.ledger.lotSize -eq 100) 'MAX3_GENERAL_100'
 RequireRss ($Broker.feeCourse -ceq 'ZERO' -and $Broker.orderTerms.sor -ceq $true -and
  $Broker.orderTerms.accountType -eq 1 -and $Broker.orderTerms.accountTypeVerified -ceq $true -and
  $Broker.orderTerms.orderType -ceq 'MARKET' -and $Broker.orderTerms.timeInForce -ceq 'DAY') 'SOR_TERMS'
 foreach($name in @('securitiesCashEvidenceFile','buyingPowerEvidenceFile')) {
  $p=$Broker.PSObject.Properties[$name]
  RequireRss ($null -eq $p -or [string]::IsNullOrWhiteSpace([string]$p.Value)) 'MIXED_POLICY'
 }
}
function Wait-No11RssFundingObservation([string]$Path,[string]$Day,$Observer,[int]$TimeoutSeconds=60) {
 $watch=[Diagnostics.Stopwatch]::StartNew()
 try {
  while($watch.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
   if($Observer.HasExited){throw 'NO11_OPERATOR_LIVE_RSS_OBSERVER_EXITED'}
   if(Test-Path -LiteralPath $Path -PathType Leaf) {
    try {
     $r=Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
     $b=$r.brokerObservation
     $stamp=[datetimeoffset]::Parse([string]$b.captureCompletedAt,[Globalization.CultureInfo]::InvariantCulture)
     $age=([datetimeoffset]::UtcNow-$stamp).TotalSeconds
     if($r.status -ceq 'OBSERVED' -and $r.readOnly -ceq $true -and $r.orderTransmission -ceq $false -and
        $b.status -ceq 'OBSERVED' -and $b.completeTables -ceq $true -and
        $b.sameSnapshotVerified -ceq $true -and $b.rowsTruncated -ceq $false -and
        $stamp.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-dd') -ceq $Day -and
        $age -ge 0 -and $age -le 30) {return}
    } catch {
     # Incomplete writes or unavailable rows do not authorize the controller.
    }
   }
   Start-Sleep -Milliseconds 250
  }
  throw 'NO11_OPERATOR_LIVE_RSS_FIRST_OBSERVATION_TIMEOUT'
 } finally {$watch.Stop()}
}
