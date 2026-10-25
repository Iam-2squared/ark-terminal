param(
 [string]$RequestPath='',
 [string]$ExpectedRequestSha256='',
 [string]$NodeExecutable='',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$OutputEncoding=[Console]::OutputEncoding

# This file is not called by the read-only launcher. The default invocation
# does not attach to Excel. A LIVE packet, committed one-shot ledger permit,
# operator configuration and an already-open, pinned workbook are mandatory.
# No workbook is opened/saved, no RSS permission or safety switch is changed.

function Need-No11Transport([bool]$Condition,[string]$Code){
 if(-not $Condition){throw ('NO11_TRANSPORT_'+$Code)}
}
function Get-No11Result($Command,[string]$Status,[string]$Reason,[bool]$Attempted){
 $id=$null;$sha=$null;$rss=$null
 if($null -ne $Command){$id=$Command.commandId;$sha=$Command.commandSha256;$rss=$Command.rssOrderId}
 return [ordered]@{schemaId='ARK_NO11_MSII_TRANSPORT_RESULT_V1';commandId=$id;commandSha256=$sha;rssOrderId=$rss;
  status=$Status;reason=$Reason;dispatchAttempted=$Attempted;brokerAcknowledged=$false;executionConfirmed=$false;
  cancellationAcknowledged=$false;cashReserveReleased=$false;orderCanBeResent=$false;productionReady=$false}
}
function Assert-No11Readback($Command,$Readback){
 Need-No11Transport ($null -ne $Readback -and $Readback.functionName -ceq $Command.functionName) 'READBACK_FUNCTION'
 $actual=@($Readback.arguments);$expected=@($Command.arguments)
 Need-No11Transport ($actual.Count -eq $expected.Count -and ($actual.Count -eq 20 -or $actual.Count -eq 3)) 'READBACK_COUNT'
 for($i=0;$i -lt $expected.Count;$i++){
  Need-No11Transport ([string]$actual[$i] -ceq [string]$expected[$i]) ('READBACK_ARGUMENT_'+$i)
 }
 Need-No11Transport ($actual[1] -ceq '0') 'TRIGGER_NOT_ZERO'
}

# The complete staged algorithm is tested with injected scriptblock sinks.
# A production sink contains the only trigger write; no retry is possible.
function Invoke-No11TransportCore($Packet,$Sink){
 $command=$Packet.command;$attempted=$false;$locked=$false;$response=$null;$statusText='';$restored=$false
 try{
  & $Sink.AssertSession $Packet $Sink.State
  & $Sink.Acquire $Packet $Sink.State
  $locked=$true
  & $Sink.AssertUnused $Packet $Sink.State
  & $Sink.AssertIdle $Packet $Sink.State
  & $Sink.Prepare $Packet $Sink.State
  Assert-No11Readback $command (& $Sink.Readback $Packet $Sink.State)
  Need-No11Transport ((& $Sink.PreparedStatus $Packet $Sink.State) -ceq '待機中') 'VENDOR_NOT_WAITING_AT_ZERO'
  & $Sink.AssertSession $Packet $Sink.State
  Assert-No11Readback $command (& $Sink.Readback $Packet $Sink.State)
  # The durable file is created before the trigger, in addition to the
  # parent's already-committed IN_FLIGHT record. Crashes never enable retry.
  & $Sink.Consume $Packet $Sink.State
  & $Sink.AssertSession $Packet $Sink.State
  Assert-No11Readback $command (& $Sink.Readback $Packet $Sink.State)
  $attempted=$true
  & $Sink.CommitOnce $Packet $Sink.State
  $statusText=[string](& $Sink.Response $Packet $Sink.State)
  $id=[string]$command.rssOrderId
  if($statusText -match ('^発注済み[（(]発注ID='+[regex]::Escape($id)+'[）)]$')){
   $response=Get-No11Result $command 'SENT_AWAITING_RECONCILIATION' 'VENDOR_RETURN_IS_NOT_ACK_OR_FILL' $true
  }else{
   $response=Get-No11Result $command 'UNKNOWN' 'BROKER_RECONCILIATION_REQUIRED' $true
  }
 }catch{
  $reason=[string]$_.Exception.Message
  if($reason -notmatch '^NO11_TRANSPORT_[A-Z0-9_]+$'){$reason='NO11_TRANSPORT_SINK_ERROR'}
  if($attempted){$response=Get-No11Result $command 'UNKNOWN' $reason $true}
  else{$response=Get-No11Result $command 'NOT_SENT' $reason $false}
 }finally{
  if($attempted){
   try{& $Sink.RestoreZero $Packet $Sink.State;$restored=$true}
   catch{$response=Get-No11Result $command 'UNKNOWN' 'NO11_TRANSPORT_TRIGGER_RESET_UNCERTAIN' $true}
  }
  if($locked){try{& $Sink.Release $Packet $Sink.State}catch{$response=Get-No11Result $command 'UNKNOWN' 'NO11_TRANSPORT_SLOT_RELEASE_UNCERTAIN' $attempted}}
 }
 $response.statusText=$statusText
 $response.triggerRestoredToZero=$restored
 return $response
}

function Test-No11TransportOffline {
 $count=0
 function New-Mock([string]$Failure=''){
  $state=@{calls=[Collections.Generic.List[string]]::new();commits=0;sessionChecks=0;failure=$Failure;consumed=$false}
  $sink=@{}
  $sink.AssertSession={param($p,$state) $state.calls.Add('session');$state.sessionChecks++
   if($state.failure -eq 'session' -and $state.sessionChecks -gt 1){throw 'NO11_TRANSPORT_EXCEL_SESSION_CHANGED'}
   if($state.failure -eq 'guard' -and $state.sessionChecks -gt 1){throw 'NO11_TRANSPORT_OPERATOR_GUARD_BLOCKED'}
   if($state.failure -eq 'expired' -and $state.sessionChecks -gt 1){throw 'NO11_TRANSPORT_PERMIT_STALE'}
  }
  $sink.Acquire={param($p,$state)$state.calls.Add('lock')}
  $sink.AssertUnused={param($p,$state)$state.calls.Add('unused');if($state.consumed){throw 'NO11_TRANSPORT_PERMIT_ALREADY_CONSUMED'}}
  $sink.AssertIdle={param($p,$state)$state.calls.Add('idle');if($state.failure -eq 'trigger'){throw 'NO11_TRANSPORT_TRIGGER_NOT_ZERO'}}
  $sink.Prepare={param($p,$state)$state.calls.Add('prepare')}
  $sink.Readback={param($p,$state)$state.calls.Add('readback');$a=@($p.command.arguments)
   if($state.failure -eq 'changed'){$a[0]='987'}
   return @{functionName=$p.command.functionName;arguments=$a}
  }
  $sink.PreparedStatus={param($p,$state)$state.calls.Add('waiting');if($state.failure -eq 'input'){'入力エラー'}else{'待機中'}}
  $sink.Consume={param($p,$state)$state.calls.Add('consume');if($state.failure -eq 'duplicate' -or $state.consumed){throw 'NO11_TRANSPORT_PERMIT_ALREADY_CONSUMED'};$state.consumed=$true}
  $sink.CommitOnce={param($p,$state)$state.calls.Add('commit');$state.commits++;if($state.failure -eq 'write'){throw 'NO11_TRANSPORT_WRITE_REPLY_LOST'}}
  $sink.Response={param($p,$state)$state.calls.Add('response')
   if($state.failure -eq 'timeout'){'応答待ち'}elseif($state.failure -eq 'cancelled'){'キャンセル'}else{'発注済み(発注ID='+$p.command.rssOrderId+')'}
  }
  $sink.RestoreZero={param($p,$state)$state.calls.Add('zero');if($state.failure -eq 'reset'){throw 'NO11_TRANSPORT_ZERO_FAILED'}}
  $sink.Release={param($p,$state)$state.calls.Add('release')}
  $sink.State=$state
  return @{sink=$sink;state=$state}
 }
 $order=@{command=@{commandId=('a'*64);commandSha256=('b'*64);rssOrderId=81;functionName='RssStockOrder';
  arguments=@('81','0','7203.T','3','0','0','100','0','','1','','0','','','','','0','','','')}}
 $cancel=@{command=@{commandId=('c'*64);commandSha256=('d'*64);rssOrderId=82;functionName='RssCancelOrder';arguments=@('82','0','12345')}}
 foreach($p in @($order,$cancel)){
  $f=New-Mock;$r=Invoke-No11TransportCore $p $f.sink
  Need-No11Transport ($r.status -eq 'SENT_AWAITING_RECONCILIATION' -and $f.state.commits -eq 1 -and -not $r.brokerAcknowledged -and -not $r.executionConfirmed -and -not $r.cashReserveReleased) 'SELFTEST_SUCCESS'
  Need-No11Transport ($f.state.calls.IndexOf('prepare') -lt $f.state.calls.IndexOf('consume') -and $f.state.calls.IndexOf('consume') -lt $f.state.calls.IndexOf('commit')) 'SELFTEST_EVENT_ORDER'
  $count++
 }
 foreach($failure in @('changed','trigger','input','duplicate','session','guard','expired')){
  $f=New-Mock $failure;$r=Invoke-No11TransportCore $order $f.sink
  Need-No11Transport ($r.status -eq 'NOT_SENT' -and $f.state.commits -eq 0 -and -not $r.dispatchAttempted) ('SELFTEST_BEFORE_'+$failure.ToUpperInvariant())
  $count++
 }
 foreach($failure in @('write','timeout','cancelled','reset')){
  $f=New-Mock $failure;$r=Invoke-No11TransportCore $order $f.sink
  Need-No11Transport ($r.status -eq 'UNKNOWN' -and $f.state.commits -eq 1 -and -not $r.orderCanBeResent -and -not $r.brokerAcknowledged) ('SELFTEST_AFTER_'+$failure.ToUpperInvariant())
  $count++
 }
 $f=New-Mock;$first=Invoke-No11TransportCore $order $f.sink;$second=Invoke-No11TransportCore $order $f.sink
 Need-No11Transport ($first.status -eq 'SENT_AWAITING_RECONCILIATION' -and $second.status -eq 'NOT_SENT' -and $f.state.commits -eq 1) 'SELFTEST_REPLAY'
 $count++
 foreach($command in @($order.command,$cancel.command)){
  $p=@{command=$command;config=@{triggerCell='B1'}}
  $formula=Get-No11BoundFormula $p
  Need-No11Transport ($formula.Contains(',$B$1,')) 'SELFTEST_TRIGGER_REFERENCE'
  $fakeState=@{formula=@{Formula=$formula};trigger=@{Value2=[double]0}}
  Assert-No11Readback $command (Read-No11BoundArguments $p $fakeState)
  $count++
 }
 $p=@{command=$order.command;config=@{triggerCell='B1'}}
 foreach($failure in @('formula','trigger')){
  $fakeState=@{formula=@{Formula=(Get-No11BoundFormula $p)};trigger=@{Value2=[double]0}}
  if($failure -eq 'formula'){$fakeState.formula.Formula=$fakeState.formula.Formula.Replace('7203.T','6501.T')}
  else{$fakeState.trigger.Value2=[double]1}
  $blocked=$false;try{Read-No11BoundArguments $p $fakeState|Out-Null}catch{$blocked=$true}
  Need-No11Transport $blocked 'SELFTEST_READBACK_CHANGED'
  $count++
 }
 function TemporaryFixture {
  $cell=[pscustomobject]@{HasFormula=$false;Value2=('ARK_NO11_C50_TEMP_'+('a'*32))}
  $sheet=[pscustomobject]@{Name='ARK_NO11_CUMULATIVE';Identity=$cell}
  $sheet|Add-Member ScriptMethod Range {param($address) return $this.Identity}
  $temporary=[pscustomobject]@{Name='Book1';Path='';FullName='Book1';Worksheets=@($sheet,[pscustomobject]@{Name='Q01'})}
  $saved=[pscustomobject]@{Name='Transport.xlsx';Path='C:\ArkPrivate';FullName='C:\ArkPrivate\Transport.xlsx'}
  $descriptor=@{name='Book1';worksheetNames=@('ARK_NO11_CUMULATIVE','Q01');identitySheet='ARK_NO11_CUMULATIVE';identityCell='G1';identityValue=$cell.Value2}
  return @{excel=[pscustomobject]@{Workbooks=@($saved,$temporary)};temporary=$temporary;cell=$cell;
   config=@{expectedOpenWorkbooks=@('C:\ArkPrivate\Transport.xlsx');expectedTemporaryWorkbooks=@($descriptor)}}
 }
 $f=TemporaryFixture;Assert-No11OpenWorkbooks $f.excel $f.config;$count++
 $f=TemporaryFixture;$f.excel.Workbooks=@($f.excel.Workbooks[0]);$f.config.expectedTemporaryWorkbooks=@()
 Assert-No11OpenWorkbooks $f.excel $f.config;$count++
 foreach($failure in @('saved','name','worksheets','token','formula','missing','extra','unexpectedSaved')){
  $f=TemporaryFixture
  switch($failure){
   'saved' {$f.temporary.Path='C:\ArkPrivate'}
   'name' {$f.temporary.Name='Book2'}
   'worksheets' {$f.temporary.Worksheets+=,[pscustomobject]@{Name='Unexpected'}}
   'token' {$f.cell.Value2='ARK_NO11_C50_TEMP_'+('b'*32)}
   'formula' {$f.cell.HasFormula=$true}
   'missing' {$f.config.expectedTemporaryWorkbooks=@()}
   'extra' {$f.excel.Workbooks+=,[pscustomobject]@{Name='Other';Path='';FullName='Other'}}
   'unexpectedSaved' {$f.excel.Workbooks+=,[pscustomobject]@{Name='Other.xlsx';Path='C:\ArkPrivate';FullName='C:\ArkPrivate\Other.xlsx'}}
  }
  $blocked=$false;try{Assert-No11OpenWorkbooks $f.excel $f.config}catch{$blocked=$true}
  Need-No11Transport $blocked ('SELFTEST_TEMPORARY_'+$failure.ToUpperInvariant());$count++
 }
 return @{status='PASS_OFFLINE_MOCK_ONLY';tests=$count;excelAttached=$false;brokerTransmissions=0;orderTransmission=$false;productionReady=$false}
}

function Read-No11ValidatedPacket {
 Need-No11Transport ($RequestPath -ne '' -and $ExpectedRequestSha256 -match '^[a-f0-9]{64}$') 'REQUEST_PIN_REQUIRED'
 Need-No11Transport ([IO.Path]::IsPathRooted($NodeExecutable) -and [IO.Path]::GetFileName($NodeExecutable) -ieq 'node.exe' -and (Test-Path -LiteralPath $NodeExecutable -PathType Leaf)) 'NODE_EXECUTABLE'
 Need-No11Transport ((Get-FileHash -LiteralPath $RequestPath -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $ExpectedRequestSha256) 'REQUEST_BYTES_CHANGED'
 $validator=Join-Path $PSScriptRoot '../tools/no11_msii_transport.mjs'
 $output=@(& $NodeExecutable $validator '--validate-packet' $RequestPath)
 Need-No11Transport ($LASTEXITCODE -eq 0 -and $output.Count -eq 1) 'PACKET_VALIDATION'
 $p=([string]$output[0])|ConvertFrom-Json
 Need-No11Transport ($p.config.mode -ceq 'LIVE' -and $p.config.orderTransmission -eq $true -and $p.config.operatorEnabled -eq $true) 'LIVE_NOT_EXPLICIT'
 return $p
}
function Assert-No11PrivateDirectory([string]$Directory){
 Need-No11Transport ([IO.Path]::IsPathRooted($Directory) -and (Test-Path -LiteralPath $Directory -PathType Container)) 'PRIVATE_DIRECTORY'
 for($item=Get-Item -LiteralPath $Directory;$null -ne $item;$item=$item.Parent){
  Need-No11Transport (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'PRIVATE_REPARSE_POINT'
 }
}
function Get-No11MarkerName($Packet){
 $sha=[Security.Cryptography.SHA256]::Create()
 try{$bytes=$sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Packet.command.rssSessionKey+'|'+[string]$Packet.command.rssOrderId));return ([BitConverter]::ToString($bytes).Replace('-','').ToLowerInvariant()+'.consumed')}
 finally{$sha.Dispose()}
}
function Get-No11BoundFormula($Packet){
 $values=[Collections.Generic.List[string]]::new()
 for($i=0;$i -lt $Packet.command.arguments.Count;$i++){
  $x=[string]$Packet.command.arguments[$i]
  if($i -eq 1){$values.Add(($Packet.config.triggerCell.Replace('$','') -replace '^([A-Z]+)([0-9]+)$','$$$1$$$2'))}
  elseif($x -ne '' -and $x -match '^-?\d+(?:\.\d+)?$'){$values.Add($x)}
  else{$values.Add('"'+$x.Replace('"','""')+'"')}
 }
 return '='+$Packet.command.functionName+'('+[string]::Join(',',$values)+')'
}
function Read-No11BoundArguments($Packet,$State){
 $formula=[string]$State.formula.Formula
 $expected=Get-No11BoundFormula $Packet
 Need-No11Transport ($formula -ceq $expected) 'FORMULA_CHANGED'
 $match=[regex]::Match($formula,'^=(RssStockOrder|RssCancelOrder)\((.*)\)$')
 Need-No11Transport $match.Success 'FORMULA_FUNCTION'
 $tokens=$match.Groups[2].Value.Split(',');$parsedArgs=[Collections.Generic.List[string]]::new()
 for($i=0;$i -lt $tokens.Count;$i++){
  if($i -eq 1){
   $value=$State.trigger.Value2
   Need-No11Transport (($value -is [double] -or $value -is [int]) -and $value -eq 0) 'TRIGGER_NOT_ZERO'
   $parsedArgs.Add('0')
  }else{
   $s=[string]$tokens[$i]
   if($s.StartsWith('"') -and $s.EndsWith('"')){$s=$s.Substring(1,$s.Length-2)}
   $parsedArgs.Add($s)
  }
 }
 return @{functionName=$match.Groups[1].Value;arguments=$parsedArgs.ToArray()}
}

function Assert-No11OpenWorkbooks($Excel,$Config){
 $saved=@($Excel.Workbooks|Where-Object{[string]$_.Path -cne ''})
 $temporary=@($Excel.Workbooks|Where-Object{[string]$_.Path -ceq ''})
 $actual=@($saved|ForEach-Object{[IO.Path]::GetFullPath([string]$_.FullName).ToLowerInvariant()}|Sort-Object)
 $expected=@($Config.expectedOpenWorkbooks|ForEach-Object{[IO.Path]::GetFullPath([string]$_).ToLowerInvariant()}|Sort-Object)
 Need-No11Transport (($actual -join '|') -ceq ($expected -join '|')) 'OPEN_WORKBOOKS_CHANGED'
 $descriptors=@($Config.expectedTemporaryWorkbooks)
 Need-No11Transport ($temporary.Count -eq $descriptors.Count) 'TEMPORARY_WORKBOOKS_CHANGED'
 foreach($descriptor in $descriptors){
  $matches=@($temporary|Where-Object{[string]$_.Name -ceq [string]$descriptor.name})
  Need-No11Transport ($matches.Count -eq 1 -and [string]$matches[0].Path -ceq '') 'TEMPORARY_WORKBOOK_CHANGED'
  $sheets=@($matches[0].Worksheets)
  $names=@($sheets|ForEach-Object{[string]$_.Name}|Sort-Object)
  $pinned=@($descriptor.worksheetNames|Sort-Object)
  Need-No11Transport (($names -join '|') -ceq ($pinned -join '|')) 'TEMPORARY_WORKSHEETS_CHANGED'
  $identity=@($sheets|Where-Object{[string]$_.Name -ceq [string]$descriptor.identitySheet})
  Need-No11Transport ($identity.Count -eq 1) 'TEMPORARY_IDENTITY_SHEET_CHANGED'
  $cell=$identity[0].Range([string]$descriptor.identityCell)
  Need-No11Transport ($cell.HasFormula -eq $false -and $cell.Value2 -is [string] -and
   [string]$cell.Value2 -ceq [string]$descriptor.identityValue) 'TEMPORARY_IDENTITY_CHANGED'
 }
}

function New-No11ExcelSink($Packet){
 # Definition only during offline tests; neither Add-Type nor COM is reached.
 if(-not ('ArkNo11TransportNative' -as [type])){
  Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ArkNo11TransportNative {
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
}
'@ | Out-Null
 }
 $state=@{excel=$null;book=$null;sheet=$null;formula=$null;trigger=$null;lock=$null}
 $sink=@{}
 $sink.AssertSession={param($p,$state)
  $again=Read-No11ValidatedPacket
  Need-No11Transport ($again.command.commandSha256 -ceq $p.command.commandSha256 -and $again.permit.permitSha256 -ceq $p.permit.permitSha256) 'PIN_CHANGED'
  $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
  Need-No11Transport ([long]$excel.Hwnd -eq [long]$p.config.expectedExcelHwnd) 'EXCEL_WINDOW_CHANGED'
  [uint32]$processIdValue=0
  [void][ArkNo11TransportNative]::GetWindowThreadProcessId([IntPtr][long]$excel.Hwnd,[ref]$processIdValue)
  Need-No11Transport ($processIdValue -eq $p.config.expectedExcelPid) 'EXCEL_PROCESS_CHANGED'
  $process=Get-Process -Id $processIdValue
  $expectedStart=[DateTimeOffset]::Parse($p.config.expectedExcelStartedAt,[Globalization.CultureInfo]::InvariantCulture)
  Need-No11Transport ($process.StartTime.ToUniversalTime().Ticks -eq $expectedStart.UtcDateTime.Ticks) 'EXCEL_START_CHANGED'
  Need-No11Transport ($excel.Ready -eq $true -and [int]$excel.CalculationState -eq 0 -and [int]$excel.Calculation -eq -4105) 'EXCEL_BUSY_OR_NOT_AUTOMATIC'
  Assert-No11OpenWorkbooks $excel $p.config
  $matches=@($excel.Workbooks|Where-Object{[IO.Path]::GetFullPath([string]$_.FullName) -ieq [IO.Path]::GetFullPath($p.config.workbookPath)})
  Need-No11Transport ($matches.Count -eq 1 -and -not $matches[0].ReadOnly) 'WORKBOOK_NOT_WRITABLE_OR_AMBIGUOUS'
  foreach($addonPath in $p.config.expectedAddInPaths){
   $addin=@($excel.AddIns|Where-Object{[IO.Path]::GetFullPath([string]$_.FullName) -ieq [IO.Path]::GetFullPath([string]$addonPath)})
   Need-No11Transport ($addin.Count -eq 1 -and $addin[0].Installed -eq $true) 'ADDIN_NOT_PINNED_OR_CONNECTED'
  }
  $sheet=$matches[0].Worksheets.Item([string]$p.config.worksheetName)
  Need-No11Transport (-not $sheet.ProtectContents) 'SHEET_PROTECTED'
  Need-No11Transport (-not $sheet.Range($p.config.guardCell).HasFormula -and [string]$sheet.Range($p.config.guardCell).Value2 -ceq $p.config.guardValue) 'OPERATOR_GUARD_BLOCKED'
  Need-No11Transport (-not $sheet.Range($p.config.sessionCell).HasFormula -and [string]$sheet.Range($p.config.sessionCell).Value2 -ceq $p.command.rssSessionKey) 'WORKBOOK_SESSION_CHANGED'
  $formula=$sheet.Range($p.config.formulaCell);$trigger=$sheet.Range($p.config.triggerCell)
  Need-No11Transport (-not $formula.MergeCells -and -not $formula.HasArray -and -not $trigger.MergeCells -and -not $trigger.HasFormula -and [string]$formula.NumberFormat -ceq 'General') 'CELL_NOT_DEDICATED'
  $state.excel=$excel;$state.book=$matches[0];$state.sheet=$sheet;$state.formula=$formula;$state.trigger=$trigger
 }
 $sink.Acquire={param($p,$state)
  Assert-No11PrivateDirectory $p.config.dispatchDirectory
  $state.lock=[IO.File]::Open((Join-Path $p.config.dispatchDirectory 'no11-transport.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 }
 $sink.AssertUnused={param($p,$state)
  Need-No11Transport (-not (Test-Path -LiteralPath (Join-Path $p.config.dispatchDirectory (Get-No11MarkerName $p)))) 'PERMIT_ALREADY_CONSUMED'
 }
 $sink.AssertIdle={param($p,$state)
  $value=$state.trigger.Value2
  Need-No11Transport (($value -is [double] -or $value -is [int]) -and $value -eq 0) 'TRIGGER_NOT_ZERO'
  if(-not $state.formula.HasFormula){Need-No11Transport ([string]$state.formula.Value2 -ceq '') 'FORMULA_CELL_NOT_EMPTY'}
  else{Need-No11Transport ([string]$state.formula.Formula -match '^=Rss(?:StockOrder|CancelOrder)\(') 'FORMULA_CELL_NOT_OWNED'}
 }
 $sink.Prepare={param($p,$state)
  $state.formula.Formula=Get-No11BoundFormula $p
  # Only this prepared, trigger-zero cell is calculated. No global calculation.
  [void]$state.formula.Calculate()
 }
 $sink.Readback={param($p,$state)return (Read-No11BoundArguments $p $state)}
 $sink.PreparedStatus={param($p,$state)
  $timer=[Diagnostics.Stopwatch]::StartNew()
  do{$value=[string]$state.formula.Value2;if($value -ceq '待機中'){return $value};Start-Sleep -Milliseconds 25}
  while($timer.ElapsedMilliseconds -lt [Math]::Min(2000,[int]$p.config.responseTimeoutMs))
  return $value
 }
 $sink.Consume={param($p,$state)
  $marker=Join-Path $p.config.dispatchDirectory (Get-No11MarkerName $p)
  $bytes=[Text.Encoding]::UTF8.GetBytes(($p.permit|ConvertTo-Json -Depth 10 -Compress))
  $stream=[IO.File]::Open($marker,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 }
 $sink.CommitOnce={param($p,$state)
  # THE ONLY SENDING WRITE. This is never executed by OfflineSelfTest.
  $state.trigger.Value2=1
 }
 $sink.Response={param($p,$state)
  $timer=[Diagnostics.Stopwatch]::StartNew();$value=''
  do{
   $value=[string]$state.formula.Value2
   if($value -match '^発注済み[（(]発注ID=\d+[）)]$'){return $value}
   if($value -ne '待機中' -and $value -ne '応答待ち' -and $value -ne ''){return $value}
   Start-Sleep -Milliseconds 25
  }while($timer.ElapsedMilliseconds -lt $p.config.responseTimeoutMs)
  return $value
 }
 $sink.RestoreZero={param($p,$state)
  $state.trigger.Value2=0
  Need-No11Transport ($state.trigger.Value2 -eq 0) 'TRIGGER_RESET_UNCERTAIN'
 }
 $sink.Release={param($p,$state)if($null -ne $state.lock){$state.lock.Dispose();$state.lock=$null}}
 $sink.State=$state
 return $sink
}

if($OfflineSelfTest){
 try{(Test-No11TransportOffline)|ConvertTo-Json -Depth 5 -Compress;exit 0}
 catch{[ordered]@{status='FAIL_OFFLINE_MOCK_ONLY';reason=[string]$_.Exception.Message;orderTransmission=$false}|ConvertTo-Json -Compress;exit 2}
}
$packet=$null;$boundaryEntered=$false
try{
 if($RequestPath -eq ''){throw 'NO11_TRANSPORT_DISABLED'}
 $packet=Read-No11ValidatedPacket
 $sink=New-No11ExcelSink $packet
 $boundaryEntered=$true
 $result=Invoke-No11TransportCore $packet $sink
 $result|ConvertTo-Json -Depth 6 -Compress
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -notmatch '^NO11_TRANSPORT_[A-Z0-9_]+$'){$reason='NO11_TRANSPORT_PREPARATION_FAILED'}
 $knownCommand=$null;if($null -ne $packet){$knownCommand=$packet.command}
 $status=if($boundaryEntered){'UNKNOWN'}else{'NOT_SENT'}
 (Get-No11Result $knownCommand $status $reason $boundaryEntered)|ConvertTo-Json -Depth 6 -Compress
}
