# Ark No.1.1 PRIVATE V2/V3 parity inspection; no original file changes or raw values printed.
param([string]$PrivateRoot=(Join-Path $env:LOCALAPPDATA 'ArkTerminal\No11'),
      [int]$MaxComparisonGapSeconds=600,
      [string]$V2SnapshotPath='')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function PrivateJson([string]$File) {
    if(-not (Test-Path -LiteralPath $File -PathType Leaf)){throw 'PRIVATE_PARITY_FILE_MISSING'}
    if((Get-Item -LiteralPath $File).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'PRIVATE_PARITY_REPARSE_BLOCKED'}
    return Get-Content -LiteralPath $File -Raw -Encoding UTF8 | ConvertFrom-Json
}
function EqualRows($One,$Two,[string[]]$Fields) {
    $a=@($One);$b=@($Two)
    if($a.Count -ne $b.Count){return $false}
    for($i=0;$i -lt $a.Count;$i++){
        foreach($f in $Fields){
            $p=$a[$i].PSObject.Properties[$f]
            $q=$b[$i].PSObject.Properties[$f]
            if($null -eq $p -or $null -eq $q){return $false}
            if((ConvertTo-Json -InputObject $p.Value -Compress -Depth 4) -cne
               (ConvertTo-Json -InputObject $q.Value -Compress -Depth 4)){return $false}
        }
    }
    return $true
}
try {
    $baseFull=[IO.Path]::GetFullPath($PrivateRoot).TrimEnd('\')+'\'
    if([string]::IsNullOrWhiteSpace($V2SnapshotPath)){$V2SnapshotPath=Join-Path $PrivateRoot 'snapshot.json'}
    $v2Full=[IO.Path]::GetFullPath($V2SnapshotPath)
    if(-not $v2Full.StartsWith($baseFull,[StringComparison]::OrdinalIgnoreCase)){throw 'PARITY_V2_OUTSIDE_PRIVATE_DIRECTORY'}
    $old=PrivateJson $v2Full
    $runs=Join-Path $PrivateRoot 'capture-v3-candidate'
    if(-not (Test-Path -LiteralPath $runs -PathType Container)){throw 'PRIVATE_V3_DIR_MISSING'}
    $dirs=@(Get-ChildItem -LiteralPath $runs -Directory | Sort-Object LastWriteTimeUtc -Descending)
    if($dirs.Count -eq 0){throw 'PRIVATE_V3_CANDIDATE_MISSING'}
    if($dirs[0].Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'PRIVATE_V3_REPARSE_BLOCKED'}
    $new=PrivateJson (Join-Path $dirs[0].FullName 'snapshot.json')
    $health=PrivateJson (Join-Path $dirs[0].FullName 'source-health.json')
    if($old.schemaId -cne 'ARK_ACCOUNT_READONLY_SNAPSHOT_V2' -or
       $new.schemaId -cne 'ARK_ACCOUNT_READONLY_SNAPSHOT_V2' -or
       $new.captureMethod -cne 'ISOLATED_BULK_CANDIDATE_NOT_PRODUCTION' -or
       $old.source -cne 'MARKETSPEED_II_RSS' -or $new.source -cne 'MARKETSPEED_II_RSS' -or
       $old.mode -cne 'READ_ONLY' -or $new.mode -cne 'READ_ONLY'){
        throw 'PRIVATE_PARITY_SOURCE_IDENTITY_INVALID'
    }
    $before=[DateTimeOffset]::Parse([string]$old.captureCompletedAt)
    $after=[DateTimeOffset]::Parse([string]$new.captureCompletedAt)
    $within=[math]::Abs(($after-$before).TotalSeconds) -le $MaxComparisonGapSeconds
    $positions=EqualRows $old.positions $new.positions @('symbol','name','account','quantity','orderQuantity','averagePrice','marketPrice','marketValue','unrealizedPnl','unrealizedPnlPercent')
    $orders=EqualRows $old.orders $new.orders @('orderNumber','status','symbol','quantity','filledQty')
    $fills=EqualRows $old.executions $new.executions @('executionDate','symbol','account','side','quantity','price')
    $cash=(ConvertTo-Json -InputObject $old.buyingPower -Compress) -ceq (ConvertTo-Json -InputObject $new.buyingPower -Compress)
    $feed=($old.rssStatus.capacity -ceq $new.rssStatus.capacity -and $old.rssStatus.orders -ceq $new.rssStatus.orders -and
           $old.rssStatus.executions -ceq $new.rssStatus.executions -and $old.rssStatus.positions -ceq $new.rssStatus.positions)
    $flags=@('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed',
             'paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','productionReady')
    $safe=$true
    foreach($key in $flags){if($old.safety.$key -ne $false -or $new.safety.$key -ne $false){$safe=$false}}
    $observedValid=($health.actualFeedTimestampCertified -eq $false)
    foreach($name in @('capacity','orders','executions','positions')){
        $item=$health.feeds.$name
        $when=[DateTimeOffset]::Parse([string]$item.observedAt)
        if($when -gt $after.AddSeconds(1) -or ($after-$when).TotalSeconds -gt 30){$observedValid=$false}
    }
    Write-Host "NO11_V3_PARITY_SAME_TIME_WINDOW=$within"
    Write-Host "NO11_V3_PARITY_POSITIONS_EQUAL=$positions"
    Write-Host "NO11_V3_PARITY_ORDERS_EQUAL=$orders"
    Write-Host "NO11_V3_PARITY_EXECUTIONS_EQUAL=$fills"
    Write-Host "NO11_V3_PARITY_CASH_EQUAL=$cash"
    Write-Host "NO11_V3_PARITY_RSS_STATUS_EQUAL=$feed"
    Write-Host "NO11_V3_PARITY_SAFETY_FALSE=$safe"
    Write-Host "NO11_V3_PARITY_OBSERVATION_TIME_VALID=$observedValid"
    $valid=($within -and $positions -and $orders -and $fills -and $cash -and $feed -and $safe -and $observedValid)
    $verdict=if($valid){'OBSERVED_CANDIDATE_PARITY_ONLY'}else{'NOT_PROVEN'}
    Write-Host "NO11_V3_PARITY_RESULT=$verdict"
} catch {
    Write-Host 'NO11_V3_PARITY_RESULT=BLOCKED_DIAGNOSTIC_ERROR'
}
Write-Host 'ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False'
Write-Host 'NO11_PRODUCTION_READY=False'
Write-Host 'ORDER_TRANSMISSION=False'
