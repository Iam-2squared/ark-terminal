param([Parameter(Mandatory=$true)][string]$EngineRoot,
      [Parameter(Mandatory=$true)][string]$PackageRoot,
      [Parameter(Mandatory=$true)][string]$BaselineRoot)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$script:checks=0
function Check([bool]$Ok,[string]$Name){if(-not $Ok){throw ('TEST_FAILED_'+$Name)};$script:checks++}
function Reject([scriptblock]$Operation,[string]$Name){
 $rejected=$false;try{& $Operation | Out-Null}catch{$rejected=$true}
 Check $rejected $Name
}
$windows=Join-Path $EngineRoot 'windows'
$helper=Join-Path $windows 'No11CleanCompatibility.ps1'
. $helper
$m=Get-Content -LiteralPath (Join-Path $PackageRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($entry in $m.files){
 if($entry.path.EndsWith('.ps1')){
  $file=Join-Path (Join-Path $PackageRoot 'payload') $entry.path
  $tokens=$null;$errors=$null
  [void][Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$errors)
  Check ($errors.Count -eq 0) ('PARSE_'+[IO.Path]::GetFileName($file))
 }
}
Check ((Convert-No11CleanFunctionName '国内株式 現物注文') -ceq 'RssStockOrder') 'JAPANESE_CASH'
Check ((Convert-No11CleanFunctionName '国内株式　取消注文') -ceq 'RssCancelOrder') 'JAPANESE_CANCEL'
Check ((Convert-No11CleanFunctionName 'RssStockOrder') -ceq 'RssStockOrder') 'ENGLISH_RETAINED'
Reject {Convert-No11CleanFunctionName '知らない注文'} 'UNKNOWN_NAME'
Check ((Convert-No11CleanFormula '=@RssStockOrder(1,0)') -ceq '=RssStockOrder(1,0)') 'LEADING_AT'
Check ((Convert-No11CleanFormula '=RssStockOrder(@A1,0)') -ceq '=RssStockOrder(@A1,0)') 'INTERNAL_AT_RETAINED'

$value=[ordered]@{text="日本語`n`"quoted`"\";empty=@();one=@(7);null=$null;truth=$true;falsehood=$false;
 nested=[pscustomobject]@{quantity=100;price=[decimal]12.34};precise=[long]9007199254740991}
$json=ConvertTo-No11CleanJson $value
$decoded=$json | ConvertFrom-Json
Check ($decoded.text -ceq $value.text) 'JSON_TEXT'
Check (@($decoded.empty).Count -eq 0 -and @($decoded.one).Count -eq 1) 'JSON_ARRAYS'
Check ($null -eq $decoded.null -and $decoded.truth -eq $true -and $decoded.falsehood -eq $false) 'JSON_TYPES'
Check ($decoded.nested.quantity -eq 100 -and $decoded.nested.price -eq 12.34) 'JSON_NUMBERS'
Check ($json.Contains('9007199254740991')) 'JSON_LONG_PRECISION'
$culture=[Threading.Thread]::CurrentThread.CurrentCulture
try{
 [Threading.Thread]::CurrentThread.CurrentCulture=[Globalization.CultureInfo]::GetCultureInfo('fr-FR')
 Check ((ConvertTo-No11CleanJson ([double]1.5)) -ceq '1.5') 'JSON_INVARIANT'
}finally{[Threading.Thread]::CurrentThread.CurrentCulture=$culture}
Reject {ConvertTo-No11CleanJson ([double]::NaN)} 'JSON_NAN'
Reject {ConvertTo-No11CleanJson ([double]::PositiveInfinity)} 'JSON_INFINITY'
Reject {ConvertTo-No11CleanJson ([datetime]::Now)} 'JSON_DATE_UNSUPPORTED'
Reject {ConvertTo-No11CleanJson ([array]::CreateInstance([object],2,2))} 'JSON_MATRIX_UNSUPPORTED'
$cycle=@{};$cycle['self']=$cycle
Reject {ConvertTo-No11CleanJson $cycle} 'JSON_CYCLE_BOUNDED'

# Load function definitions only. Top-level LIVE/Excel code is never evaluated.
$orderFile=Join-Path $windows 'Invoke-No11MsiiOrder.ps1'
$tokens=$null;$errors=$null
$tree=[Management.Automation.Language.Parser]::ParseFile($orderFile,[ref]$tokens,[ref]$errors)
$functions=@($tree.EndBlock.Statements | Where-Object {$_ -is [Management.Automation.Language.FunctionDefinitionAst]})
. ([scriptblock]::Create((($functions | ForEach-Object {$_.Extent.Text}) -join "`n")))
$result=Test-No11TransportOffline
Check ($result.status -ceq 'PASS_OFFLINE_MOCK_ONLY' -and $result.brokerTransmissions -eq 0) 'ORIGINAL_TRANSPORT_SUITE'
$packet=@{command=@{commandId=('a'*64);commandSha256=('b'*64);rssOrderId=81;functionName='RssStockOrder';
 arguments=@('81','0','7203.T','3','0','1','100','0','','1','','1','','','','','0','','','')};config=@{triggerCell='B1'}}
$formula=Get-No11BoundFormula $packet
Check ((Get-No11CleanVendorStatus ($formula+' => 待機中') $packet) -ceq '待機中') 'WAITING_ECHO'
Check ((Get-No11CleanVendorStatus ($formula.Replace('=Rss','=@Rss')+' => 発注済み(注文ID=81)') $packet) -ceq '発注済み(注文ID=81)') 'SENT_ECHO'
Reject {Get-No11CleanVendorStatus ($formula.Replace('7203.T','6501.T')+' => 待機中') $packet} 'WRONG_ECHO'
$fake=@{formula=@{Formula=$formula.Replace('=Rss','=@Rss')};trigger=@{Value2=[double]0}}
Assert-No11Readback $packet.command (Read-No11BoundArguments $packet $fake)
Check $true 'AT_READBACK'
$fake.formula.Formula=$fake.formula.Formula.Replace('7203.T','6501.T')
Reject {Read-No11BoundArguments $packet $fake} 'CHANGED_READBACK'
function MakeSink([string]$Reply,[string]$Waiting){
 $state=@{commits=0;reply=$Reply;waiting=$Waiting}
 return @{State=$state;AssertSession={param($p,$s)};Acquire={param($p,$s)};AssertUnused={param($p,$s)};
 AssertIdle={param($p,$s)};Prepare={param($p,$s)};Consume={param($p,$s)};
 Readback={param($p,$s)return @{functionName=$p.command.functionName;arguments=$p.command.arguments}};
 PreparedStatus={param($p,$s)return $s.waiting};CommitOnce={param($p,$s)$s.commits++};
 Response={param($p,$s)return $s.reply};RestoreZero={param($p,$s)};Release={param($p,$s)}}
}
foreach($label in @('注文ID','発注ID')){
 $sink=MakeSink ($formula+' => 発注済み('+$label+'=81)') ($formula+' => 待機中')
 $r=Invoke-No11TransportCore $packet $sink
 Check ($r.status -ceq 'SENT_AWAITING_RECONCILIATION' -and $sink.State.commits -eq 1 -and -not $r.executionConfirmed) ('ECHO_CORE_'+$label)
}
$sink=MakeSink '発注済み(注文ID=82)' '待機中'
$r=Invoke-No11TransportCore $packet $sink
Check ($r.status -ceq 'UNKNOWN' -and -not $r.orderCanBeResent) 'WRONG_ID_UNKNOWN'
$sink=MakeSink '発注済み(注文ID=81)' ($formula.Replace('7203.T','6501.T')+' => 待機中')
$r=Invoke-No11TransportCore $packet $sink
Check ($r.status -ceq 'NOT_SENT' -and $sink.State.commits -eq 0) 'BAD_WAIT_ECHO_NO_SEND'

$sheet=[pscustomobject]@{calls=0}
$sheet | Add-Member ScriptMethod Range {
 param($address)
 $this.calls++
 $row=[array]::CreateInstance([object],1,12)
 for($i=0;$i -lt 12;$i++){$row.SetValue($address,0,$i)}
 return [pscustomobject]@{Value2=$row}
}
$matrix=Read-No11CleanReferenceRows $sheet 2
Check ($matrix.Rank -eq 2 -and $matrix.GetLength(0) -eq 2 -and $sheet.calls -eq 2) 'ROWWISE_SHAPE'
Check ($matrix.GetValue(0,0) -ceq 'A1:L1' -and $matrix.GetValue(1,0) -ceq 'A2:L2') 'ROWWISE_ORDER'

# Exercise actual rebuilt broker parser with the observed display label.
$brokerFile=Join-Path $windows 'Read-No11BrokerSnapshot.ps1'
$tree=[Management.Automation.Language.Parser]::ParseFile($brokerFile,[ref]$tokens,[ref]$errors)
$functions=@($tree.EndBlock.Statements | Where-Object {$_ -is [Management.Automation.Language.FunctionDefinitionAst]})
. ([scriptblock]::Create((($functions | ForEach-Object {$_.Extent.Text}) -join "`n")))
$table=[array]::CreateInstance([object],4,6)
$headers=Get-No11BrokerHeaders 'IDS'
for($c=0;$c -lt 6;$c++){$table.SetValue($headers[$c],0,$c)}
$data=@(81,'国内株式 現物注文','2026/11/09','09:00:00','1001','発注済み')
for($c=0;$c -lt 6;$c++){$table.SetValue($data[$c],1,$c)}
$parsed=Convert-No11BrokerRows $table 'IDS' 2
Check ($parsed.Count -eq 1 -and $parsed[0].functionName -ceq 'RssStockOrder') 'ACTUAL_BROKER_JAPANESE_ROW'
$table.SetValue('不明注文',1,1)
Reject {Convert-No11BrokerRows $table 'IDS' 2} 'ACTUAL_BROKER_UNKNOWN_ROW'

$stageTool=Join-Path $PackageRoot 'Stage-No11CleanRebuild.ps1'
$destination=Join-Path ([IO.Path]::GetTempPath()) ('no11-clean-test-stage-'+[guid]::NewGuid().ToString('N'))
try{
 & $stageTool -SourceRoot $BaselineRoot -Stage -Destination $destination
 Check (Test-Path -LiteralPath (Join-Path $destination 'manifest.json')) 'STAGE_PAYLOAD_CREATED'
 Reject {& $stageTool -SourceRoot $BaselineRoot -Stage -Destination $destination} 'STAGE_NO_OVERWRITE'
}finally{if(Test-Path -LiteralPath $destination){Remove-Item -LiteralPath $destination -Recurse -Force}}
Write-Host ('NO11_CLEAN_POWERSHELL_CHECKS='+$script:checks)
Write-Host ('NO11_CLEAN_POWERSHELL_VERSION='+$PSVersionTable.PSVersion.ToString())
Write-Host 'NO11_CLEAN_POWERSHELL=PASS_OFFLINE_ONLY'
Write-Host 'ORDER_TRANSMISSION=False'
