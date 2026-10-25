# Dot-source library for existing read-only books. No COM attachment, workbook
# mutation, formula evaluation request, order function, or permission changes.
param([Alias('OfflineSelfTest')][switch]$BrokerOfflineSelfTest)

function Assert-No11Broker([bool]$Ok,[string]$Code) {
 if(-not $Ok){throw ('NO11_BROKER_'+$Code)}
}
function Get-No11BrokerHash([string]$Value) {
 $hash=[Security.Cryptography.SHA256]::Create()
 try{return ([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($Value)))).Replace('-','').ToLowerInvariant()}
 finally{$hash.Dispose()}
}
function Get-No11BrokerText($Value) {return ([string]$Value).Trim()}
function Test-No11BrokerEmpty($Value) {
 $s=Get-No11BrokerText $Value
 return ($s.Length -eq 0 -or $s -match '^[\-－—–―‐‑‒−ー]+$')
}
function Get-No11BrokerNumber($Value,[bool]$Integer=$false) {
 Assert-No11Broker ($Value -is [ValueType] -and $Value -isnot [bool] -and $Value -isnot [datetime]) 'NUMBER_TYPE'
 $n=[double]$Value
 Assert-No11Broker (-not [double]::IsNaN($n) -and -not [double]::IsInfinity($n)) 'NUMBER_FINITE'
 if($Integer){Assert-No11Broker ($n -ge 0 -and $n -le 1000000000 -and $n -eq [math]::Floor($n)) 'QUANTITY'}
 return $n
}
function Get-No11BrokerOrderNumber($Value,[bool]$Optional=$false) {
 if($Optional -and (Test-No11BrokerEmpty $Value)){return $null}
 if($Value -is [ValueType]){
  $n=Get-No11BrokerNumber $Value
  Assert-No11Broker ($n -ge 1 -and $n -le 9007199254740991 -and $n -eq [math]::Floor($n)) 'ORDER_NUMBER_PRECISION'
  return $n.ToString('0',[Globalization.CultureInfo]::InvariantCulture)
 }
 $s=Get-No11BrokerText $Value
 Assert-No11Broker ($s -cmatch '^[1-9][0-9]{0,31}$') 'ORDER_NUMBER'
 return $s
}
function Convert-No11RssDateValue($Value,[ValidateSet('DATE','TIME','DATETIME')][string]$Part) {
 $culture=[Globalization.CultureInfo]::InvariantCulture
 $d=[datetime]::MinValue
 if($Value -is [ValueType] -and $Value -isnot [bool] -and $Value -isnot [datetime]){
  $n=Get-No11BrokerNumber $Value
  if($Part -eq 'TIME'){Assert-No11Broker ($n -ge 0 -and $n -lt 1) 'TIME_SERIAL'}
  try{$d=[datetime]::FromOADate($n)}catch{throw 'NO11_BROKER_DATE_SERIAL'}
  # Excel doubles can be a fraction of a millisecond from the vendor's second.
  # Only remove representation noise; never round meaningful subsecond input.
  $rem=$d.Ticks % [timespan]::TicksPerSecond
  if($rem -le 20000){$d=$d.AddTicks(-$rem)}
  elseif(([timespan]::TicksPerSecond-$rem) -le 20000){$d=$d.AddTicks([timespan]::TicksPerSecond-$rem)}
  else{throw 'NO11_BROKER_DATE_SUBSECOND'}
 }else{
  Assert-No11Broker ($Value -is [string]) 'DATE_TYPE'
  $s=Get-No11BrokerText $Value
  $formats=switch($Part){
   DATE {@('yyyy/MM/dd','yyyy/M/d','yyyy-MM-dd','yyyy-M-d','yyyyMMdd')}
   TIME {@('HH:mm:ss')}
   DATETIME {@('yyyy/MM/dd HH:mm:ss','yyyy/M/d HH:mm:ss','yyyy-MM-dd HH:mm:ss',"yyyy-MM-dd'T'HH:mm:ss", "yyyy-MM-dd'T'HH:mm:ss'+09:00'")}
  }
  Assert-No11Broker ([datetime]::TryParseExact($s,[string[]]$formats,$culture,[Globalization.DateTimeStyles]::None,[ref]$d)) 'DATE_FORMAT'
 }
 if($Part -eq 'TIME'){return $d.ToString('HH:mm:ss',$culture)}
 Assert-No11Broker ($d.Year -ge 2000 -and $d.Year -le 2099) 'DATE_RANGE'
 if($Part -eq 'DATE'){
  Assert-No11Broker ($d.TimeOfDay.Ticks -eq 0) 'DATE_HAS_TIME'
  return $d.ToString('yyyy-MM-dd',$culture)
 }
 return $d.ToString('yyyy/MM/dd HH:mm:ss',$culture)
}
function Convert-No11ExecutionDate($Value) {return Convert-No11RssDateValue $Value 'DATETIME'}
function New-No11ExcelSession([int]$ProcessId,[string]$StartedAtUtc,[string]$AccountWorkbookPath,[string]$OrderIdWorkbookPath) {
 Assert-No11Broker ($ProcessId -gt 0 -and $StartedAtUtc.EndsWith('Z')) 'EXCEL_SESSION'
 $account=Get-No11BrokerHash ([IO.Path]::GetFullPath($AccountWorkbookPath).ToLowerInvariant())
 $ids=Get-No11BrokerHash ([IO.Path]::GetFullPath($OrderIdWorkbookPath).ToLowerInvariant())
 $key=Get-No11BrokerHash ((@([string]$ProcessId,$StartedAtUtc,$account,$ids)) -join "`n")
 return [ordered]@{processId=$ProcessId;startedAtUtc=$StartedAtUtc;accountWorkbookIdentity=$account;orderIdWorkbookIdentity=$ids;sessionKey=$key}
}
function Get-No11BrokerHeaders([ValidateSet('IDS','ORDERS','EXECUTIONS')][string]$Kind) {
 switch($Kind){
  IDS {return ,@('発注ID','関数名','発注日','発注時刻','注文番号','発注結果')}
  ORDERS {return ,@('注文番号','受付No','通常注文状況','逆指値注文状況','アルゴ注文状況','銘柄コード','銘柄名称','口座区分','市場名称','信用区分','弁済期限','発注/受注日時','売買','取引','執行条件','注文期限','注文数量','約定数量','注文単価','注文区分','逆指値条件','セット注文','セット注文条件','税区分','注文失効日時','注文失効理由','入力経路','アルゴ注文条件','SOR判定時刻','SOR判定時主市場情報/対象外理由')}
  EXECUTIONS {return ,@('約定日','受渡日','銘柄コード','銘柄名称','口座区分','市場名称','信用区分','弁済期限','取引','売買','約定数量','約定単価','約定代金','税区分','特別空売り料(円)')}
 }
}
function Get-No11BrokerCell([array]$Data,[int]$Row,[int]$Column) {
 Assert-No11Broker ($Data.Rank -eq 2 -and $Row -ge 0 -and $Row -lt $Data.GetLength(0) -and $Column -ge 0 -and $Column -lt $Data.GetLength(1)) 'BULK_INDEX'
 return $Data.GetValue($Data.GetLowerBound(0)+$Row,$Data.GetLowerBound(1)+$Column)
}
function Get-No11BrokerFormula([string]$Formula) {return (($Formula.Trim() -replace '^=@','=') -replace '\$','')}
function Assert-No11BrokerStatus($Cell,[string]$Formula) {
 Assert-No11Broker ([bool]$Cell.HasFormula -and (Get-No11BrokerFormula ([string]$Cell.Formula)) -ceq $Formula) 'FORMULA'
 $v=Get-No11BrokerText $Cell.Value2
 $ok=$v -ceq '配信中'
 if($v -match '^(.*) => (.*)$'){$ok=((Get-No11BrokerFormula $Matches[1]) -ceq $Formula -and $Matches[2] -ceq '配信中')}
 Assert-No11Broker $ok 'RSS_STATUS'
}
function Assert-No11BrokerHeaders([array]$Data,[string]$Kind) {
 $headers=Get-No11BrokerHeaders $Kind
 Assert-No11Broker ($Data.Rank -eq 2 -and $Data.GetLength(0) -ge 1 -and $Data.GetLength(1) -eq $headers.Count) 'HEADER_SHAPE'
 for($c=0;$c -lt $headers.Count;$c++){
  $actual=Get-No11BrokerText (Get-No11BrokerCell $Data 0 $c)
  $accepted=$actual -ceq $headers[$c]
  # Both names occur in Rakuten's current official PDF/online item lists.
  if($Kind -eq 'EXECUTIONS' -and $c -eq 14 -and $actual -ceq '特別空売り料'){$accepted=$true}
  Assert-No11Broker $accepted 'HEADER'
 }
}
function Get-No11BrokerTableDefinitions {
 return ,@(
  @{kind='IDS';cell='A1';first='A';last='F';formula='=RssOrderIDList(A2:F2)'},
  @{kind='ORDERS';cell='H1';first='H';last='AK';formula='=RssOrderList(H2:AK2,0,1)'},
  @{kind='EXECUTIONS';cell='AM1';first='AM';last='BA';formula='=RssExecutionList(AM2:BA2,1)'}
 )
}
function Assert-No11BrokerLayout($Sheet) {
 Assert-No11Broker ([string]$Sheet.Name -ceq 'ARK_ORDER_IDS_READONLY') 'SHEET_IDENTITY'
 foreach($d in (Get-No11BrokerTableDefinitions)){
  Assert-No11BrokerStatus ($Sheet.Range($d.cell)) $d.formula
  $data=$Sheet.Range($d.first+'2:'+$d.last+'2').Value2
  Assert-No11Broker ($data -is [array]) 'BULK_ARRAY'
  Assert-No11BrokerHeaders $data $d.kind
 }
}
function Convert-No11BrokerRows([array]$Data,[string]$Kind,[int]$MaximumRows=5000) {
 $headers=Get-No11BrokerHeaders $Kind
 Assert-No11Broker ($MaximumRows -ge 1 -and $MaximumRows -le 5000 -and $Data.Rank -eq 2 -and $Data.GetLength(0) -eq ($MaximumRows+2) -and $Data.GetLength(1) -eq $headers.Count) 'BULK_SHAPE'
 Assert-No11BrokerHeaders $Data $Kind
 $rows=@();$padding=$false;$seen=@{}
 for($r=1;$r -le ($MaximumRows+1);$r++){
  $empty=$true
  for($c=0;$c -lt $headers.Count;$c++){if(-not (Test-No11BrokerEmpty (Get-No11BrokerCell $Data $r $c))){$empty=$false;break}}
  if($empty){$padding=$true;continue}
  Assert-No11Broker ($r -le $MaximumRows) 'ROW_LIMIT'
  Assert-No11Broker (-not $padding) 'ROW_GAP'
  switch($Kind){
   IDS {
    $id=Get-No11BrokerNumber (Get-No11BrokerCell $Data $r 0)
    Assert-No11Broker ($id -ge 1 -and $id -le 2147483647 -and $id -eq [math]::Floor($id) -and -not $seen.ContainsKey([string]$id)) 'RSS_ID'
    $seen[[string]$id]=$true
    $fn=Get-No11BrokerText (Get-No11BrokerCell $Data $r 1)
    $result=Get-No11BrokerText (Get-No11BrokerCell $Data $r 5)
    Assert-No11Broker ($fn -cmatch '^Rss[A-Za-z0-9_]+$' -and -not (Test-No11BrokerEmpty $result)) 'ID_FIELDS'
    $rows += [pscustomobject][ordered]@{rssOrderId=[int]$id;functionName=$fn;
      orderDate=(Convert-No11RssDateValue (Get-No11BrokerCell $Data $r 2) 'DATE');
      orderTime=(Convert-No11RssDateValue (Get-No11BrokerCell $Data $r 3) 'TIME');
      orderNumber=(Get-No11BrokerOrderNumber (Get-No11BrokerCell $Data $r 4) $true);result=$result}
   }
   ORDERS {
    $id=Get-No11BrokerOrderNumber (Get-No11BrokerCell $Data $r 0)
    Assert-No11Broker (-not $seen.ContainsKey($id)) 'DUPLICATE_ORDER';$seen[$id]=$true
    $q=Get-No11BrokerNumber (Get-No11BrokerCell $Data $r 16) $true
    $f=Get-No11BrokerNumber (Get-No11BrokerCell $Data $r 17) $true
    $trade=Get-No11BrokerText (Get-No11BrokerCell $Data $r 13)
    Assert-No11Broker ($q -gt 0 -and $f -le $q -and $trade -ceq '現物') 'ORDER_CASH_FIELDS'
    $rows += [pscustomobject][ordered]@{orderNumber=$id;status=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 2));
      symbol=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 5));account=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 7));
      market=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 8));orderReceivedAt=(Convert-No11ExecutionDate (Get-No11BrokerCell $Data $r 11));
      side=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 12));trade=$trade;executionCondition=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 14));
      quantity=$q;filledQty=$f;orderPrice=(Get-No11BrokerCell $Data $r 18);orderType=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 19));
      setOrder=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 21));inputRoute=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 26))}
   }
   EXECUTIONS {
    $q=Get-No11BrokerNumber (Get-No11BrokerCell $Data $r 10) $true
    $p=Get-No11BrokerNumber (Get-No11BrokerCell $Data $r 11)
    $trade=Get-No11BrokerText (Get-No11BrokerCell $Data $r 8)
    Assert-No11Broker ($q -gt 0 -and $p -gt 0 -and $trade -ceq '現物') 'EXECUTION_CASH_FIELDS'
    # The date, price and quantity all come from this SAME bulk Value2 array.
    $rows += [pscustomobject][ordered]@{executionDate=(Convert-No11ExecutionDate (Get-No11BrokerCell $Data $r 0));
      settlementDate=(Convert-No11RssDateValue (Get-No11BrokerCell $Data $r 1) 'DATE');
      symbol=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 2));account=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 4));
      market=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 5));trade=$trade;side=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 9));
      quantity=$q;price=$p;grossConsideration=(Get-No11BrokerCell $Data $r 12);taxClass=(Get-No11BrokerText (Get-No11BrokerCell $Data $r 13))}
   }
  }
 }
 return ,$rows
}
function Read-No11BrokerTables($Sheet,[int]$MaximumRows=5000) {
 Assert-No11Broker ([string]$Sheet.Name -ceq 'ARK_ORDER_IDS_READONLY') 'SHEET_IDENTITY'
 $definitions=Get-No11BrokerTableDefinitions
 $result=[ordered]@{}
 foreach($d in $definitions){
  Assert-No11BrokerStatus ($Sheet.Range($d.cell)) $d.formula
  $address=$d.first+'2:'+$d.last+($MaximumRows+3)
  $data=$Sheet.Range($address).Value2
  Assert-No11Broker ($data -is [array]) 'BULK_ARRAY'
  $result[$d.kind]=Convert-No11BrokerRows $data $d.kind $MaximumRows
  Assert-No11BrokerStatus ($Sheet.Range($d.cell)) $d.formula
 }
 return $result
}
function Get-No11BrokerComparable($Snapshot) {
 $orders=@($Snapshot.orders | ForEach-Object {
  [ordered]@{orderNumber=$_.orderNumber;status=$_.status;symbol=$_.symbol;account=$_.account;side=$_.side;trade=$_.trade;executionCondition=$_.executionCondition;quantity=$_.quantity;filledQty=$_.filledQty}
 } | ForEach-Object {ConvertTo-Json -InputObject $_ -Compress -Depth 8} | Sort-Object)
 $executions=@($Snapshot.executions | ForEach-Object {
  [ordered]@{executionDate=(Convert-No11ExecutionDate $_.executionDate);symbol=$_.symbol;account=$_.account;side=$_.side;trade=$_.trade;market=$_.market;quantity=$_.quantity;price=$_.price}
 } | ForEach-Object {ConvertTo-Json -InputObject $_ -Compress -Depth 8} | Sort-Object)
 $positions=@($Snapshot.positions | ForEach-Object {
  [ordered]@{symbol=$_.symbol;account=$_.account;quantity=$_.quantity}
 } | ForEach-Object {ConvertTo-Json -InputObject $_ -Compress -Depth 8} | Sort-Object)
 return ConvertTo-Json -InputObject ([ordered]@{orders=$orders;executions=$executions;positions=$positions;buyingPower=$Snapshot.buyingPower}) -Compress -Depth 10
}
function New-No11UnavailableBrokerObservation([string]$Reason) {
 return [ordered]@{schemaId='ARK_NO11_BROKER_OBSERVATION_V1';status='UNAVAILABLE';reason=$Reason;readOnly=$true;
  actualFeedTimestampCertified=$false;buyingPowerFreshnessCertified=$false;productionReady=$false;orderTransmission=$false}
}
function Read-No11BrokerSnapshot($AccountSheet,$OrderIdSheet,[scriptblock]$CaptureAccount,$ExcelSession,[scriptblock]$VerifySession,[int]$MaximumRows=5000) {
 $first=$null;$started=Get-Date
 try{
  $tablesA=Read-No11BrokerTables $OrderIdSheet $MaximumRows
  $first=& $CaptureAccount $AccountSheet
  $second=& $CaptureAccount $AccountSheet
  $tablesB=Read-No11BrokerTables $OrderIdSheet $MaximumRows
  $finalSession=& $VerifySession
  Assert-No11Broker ($finalSession.sessionKey -ceq $ExcelSession.sessionKey) 'EXCEL_SESSION_CHANGED_DURING_CAPTURE'
  Assert-No11Broker ((ConvertTo-Json -InputObject $tablesA -Depth 20 -Compress) -ceq (ConvertTo-Json -InputObject $tablesB -Depth 20 -Compress)) 'BROKER_TABLE_CHANGED_DURING_CAPTURE'
  Assert-No11Broker ((Get-No11BrokerComparable $first.snapshot) -ceq (Get-No11BrokerComparable $second.snapshot)) 'ACCOUNT_CHANGED_DURING_CAPTURE'
  $cross=[ordered]@{orders=$tablesA.ORDERS;executions=$tablesA.EXECUTIONS;positions=$first.snapshot.positions;buyingPower=$first.snapshot.buyingPower}
  Assert-No11Broker ((Get-No11BrokerComparable $first.snapshot) -ceq (Get-No11BrokerComparable $cross)) 'ACCOUNT_BROKER_TABLE_MISMATCH'
  $end=Get-Date;$duration=($end-$started).TotalSeconds
  Assert-No11Broker ($duration -ge 0 -and $duration -lt 25) 'CAPTURE_DURATION'
  $observation=[ordered]@{schemaId='ARK_NO11_BROKER_OBSERVATION_V1';status='OBSERVED';capturedAt=$started.ToString('o');captureCompletedAt=$end.ToString('o');
   readOnly=$true;excelSession=$ExcelSession;idRows=@($tablesA.IDS);orders=@($tablesA.ORDERS);executions=@($tablesA.EXECUTIONS);positions=@($first.snapshot.positions);buyingPower=$first.snapshot.buyingPower;
   cashScope='ALL_CHANNELS_ALL_STATUSES_CASH_ONLY';completeTables=$true;rowsTruncated=$false;
   sameSnapshotVerified=$true;verificationBasis='DOUBLE_READ_EQUAL_NOT_ATOMIC_FEED';actualFeedTimestampCertified=$false;buyingPowerFreshnessCertified=$false;
   accountComparisonBasis='CASH_ORDERS_EXECUTIONS_POSITION_QUANTITY_AND_BUYING_POWER';
   productionReady=$false;orderTransmission=$false}
 }catch{
  $reason='BROKER_SOURCE_UNAVAILABLE'
  if($_.Exception.Message -cmatch '^NO11_BROKER_[A-Z0-9_]+$'){$reason=$_.Exception.Message}
  $observation=New-No11UnavailableBrokerObservation $reason
 }
 if($null -eq $first){$first=& $CaptureAccount $AccountSheet}
 return @{snapshot=$first.snapshot;health=$first.health;brokerObservation=$observation}
}
function Test-No11BrokerSnapshotOffline {
 function Check([bool]$Ok,[string]$Name){Assert-No11Broker $Ok ('SELFTEST_'+$Name)}
 function Fails([scriptblock]$Body,[string]$Code){$failed=$false;try{& $Body | Out-Null}catch{if($_.Exception.Message -eq ('NO11_BROKER_'+$Code)){$failed=$true}else{throw}};Check $failed $Code}
 function Matrix([string]$Kind,[int]$Limit=2){
  $h=Get-No11BrokerHeaders $Kind;$a=[array]::CreateInstance([object],[int[]]@(($Limit+2),$h.Count),[int[]]@(1,1))
  for($i=0;$i -lt $h.Count;$i++){$a.SetValue($h[$i],1,$i+1)};return ,$a
 }
 $id=Matrix 'IDS';$id[2,1]=77;$id[2,2]='RssStockOrder';$id[2,3]='2026/10/26';$id[2,4]='09:30:00';$id[2,5]='123';$id[2,6]='発注済み(発注ID=77)'
 $rows=Convert-No11BrokerRows $id 'IDS' 2
 Check ($rows.Count -eq 1 -and $rows[0].rssOrderId -eq 77 -and $rows[0].orderDate -ceq '2026-10-26') 'ID_ROW'
 $id[3,1]=77;$id[3,2]='RssStockOrder';$id[3,3]='2026/10/26';$id[3,4]='09:30:00';$id[3,5]='123';$id[3,6]='発注済み'
 Fails {Convert-No11BrokerRows $id 'IDS' 2} 'RSS_ID'
 $gap=Matrix 'IDS';for($c=1;$c -le 6;$c++){$gap[3,$c]=$id[2,$c]};Fails {Convert-No11BrokerRows $gap 'IDS' 2} 'ROW_GAP'
 $over=Matrix 'IDS';for($r=2;$r -le 4;$r++){for($c=1;$c -le 6;$c++){$over[$r,$c]=$id[2,$c]};$over[$r,1]=$r};Fails {Convert-No11BrokerRows $over 'IDS' 2} 'ROW_LIMIT'
 $bad=Matrix 'IDS';$bad[1,1]='注文番号';Fails {Convert-No11BrokerRows $bad 'IDS' 2} 'HEADER'
 Check ((Convert-No11ExecutionDate ([datetime]'2026-10-26T09:30:04').ToOADate()) -ceq '2026/10/26 09:30:04') 'BULK_DATE_SERIAL'
 Check ((Convert-No11RssDateValue (9.5/24) 'TIME') -ceq '09:30:00') 'TIME_SERIAL'
 Fails {Convert-No11ExecutionDate '2026/02/30 09:30:00'} 'DATE_FORMAT'
 Fails {Convert-No11ExecutionDate $true} 'DATE_TYPE'
 Fails {Convert-No11ExecutionDate ([datetime]'2026-10-26T09:30:04.125').ToOADate()} 'DATE_SUBSECOND'
 $ex=Matrix 'EXECUTIONS';$vals=@('2026/10/26 09:30:04','20261028','7203','SYNTHETIC','特定','東証','-','-','現物','買付',100,1000.1,100010,'源泉あり','-')
 for($c=1;$c -le 15;$c++){$ex[2,$c]=$vals[$c-1]}
 $e=Convert-No11BrokerRows $ex 'EXECUTIONS' 2
 Check ($e[0].market -ceq '東証' -and $e[0].trade -ceq '現物' -and $e[0].price -eq 1000.1 -and $e[0].executionDate -ceq '2026/10/26 09:30:04') 'EXECUTION_ROW'
 $ex[2,9]='信用新規';Fails {Convert-No11BrokerRows $ex 'EXECUTIONS' 2} 'EXECUTION_CASH_FIELDS'
 $s1=New-No11ExcelSession 123 '2026-10-25T23:00:00.0000000Z' ([IO.Path]::GetFullPath('account.xlsx')) ([IO.Path]::GetFullPath('ids.xlsx'))
 $s2=New-No11ExcelSession 123 '2026-10-25T23:01:00.0000000Z' ([IO.Path]::GetFullPath('account.xlsx')) ([IO.Path]::GetFullPath('ids.xlsx'))
 Check ($s1.sessionKey -cne $s2.sessionKey) 'SESSION_RESET_KEY'
 $cell=[pscustomobject]@{HasFormula=$true;Formula='=@RssOrderIDList($A$2:$F$2)';Value2='配信中'}
 Assert-No11BrokerStatus $cell '=RssOrderIDList(A2:F2)'
 $cell.Formula='=RssOrderList(A2:F2)';Fails {Assert-No11BrokerStatus $cell '=RssOrderIDList(A2:F2)'} 'FORMULA'
 # Exercise the complete read boundary using mock Range objects. No Excel,
 # workbook, network or actual account is involved, including on Windows CI.
 $mi=Matrix 'IDS';for($c=1;$c -le 6;$c++){$mi[2,$c]=$id[2,$c]}
 $mo=Matrix 'ORDERS'
 $orderValues=@('123','1','約定','-','-','7203','SYNTHETIC','特定','東証','-','-','2026/10/26 09:30:00','買付','現物','本日中','-',100,100,'成行','通常注文','-','-','-','源泉あり','-','-','MARKET SPEED','-','-','-')
 for($c=1;$c -le 30;$c++){$mo[2,$c]=$orderValues[$c-1]}
 $me=Matrix 'EXECUTIONS';for($c=1;$c -le 15;$c++){$me[2,$c]=$vals[$c-1]}
 $mock=[pscustomobject]@{Name='ARK_ORDER_IDS_READONLY';Ranges=@{
  A1=[pscustomobject]@{HasFormula=$true;Formula='=RssOrderIDList(A2:F2)';Value2='配信中'};
  H1=[pscustomobject]@{HasFormula=$true;Formula='=RssOrderList(H2:AK2,0,1)';Value2='配信中'};
  AM1=[pscustomobject]@{HasFormula=$true;Formula='=RssExecutionList(AM2:BA2,1)';Value2='配信中'};
  'A2:F5'=[pscustomobject]@{Value2=$mi};'H2:AK5'=[pscustomobject]@{Value2=$mo};'AM2:BA5'=[pscustomobject]@{Value2=$me}
 };IdReads=0;ChangeAfterFirst=$false}
 $mock | Add-Member -MemberType ScriptMethod -Name Range -Value {
  param([string]$Address)
  if($Address -eq 'A2:F5'){$this.IdReads++;if($this.ChangeAfterFirst -and $this.IdReads -gt 1){$this.Ranges[$Address].Value2[2,1]=78}}
  if(-not $this.Ranges.ContainsKey($Address)){throw 'NO11_BROKER_SELFTEST_UNEXPECTED_RANGE'}
  return $this.Ranges[$Address]
 }
 $account=[pscustomobject]@{orders=@([pscustomobject]@{orderNumber='123';status='約定';symbol='7203';account='特定';side='買付';trade='現物';executionCondition='本日中';quantity=100.0;filledQty=100.0});
  executions=@([pscustomobject]@{executionDate='2026/10/26 09:30:04';symbol='7203';account='特定';side='買付';trade='現物';market='東証';quantity=100.0;price=1000.1});
  positions=@([pscustomobject]@{symbol='7203';account='特定';quantity=100.0});buyingPower=100000.0}
 $capture={param($unused) return @{snapshot=$account;health=@{}}}
 $verify={return $s1}
 $observed=Read-No11BrokerSnapshot $null $mock $capture $s1 $verify 2
 Check ($observed.brokerObservation.status -ceq 'OBSERVED' -and $observed.brokerObservation.idRows.Count -eq 1) 'COMPLETE_MOCK_CAPTURE'
 Check ($observed.brokerObservation.orders[0].orderReceivedAt -ceq '2026/10/26 09:30:00' -and $observed.brokerObservation.orders[0].inputRoute -ceq 'MARKET SPEED') 'ORDER_PROVENANCE'
 $mock.IdReads=0;$mock.ChangeAfterFirst=$true
 $shift=Read-No11BrokerSnapshot $null $mock $capture $s1 $verify 2
 Check ($shift.brokerObservation.status -ceq 'UNAVAILABLE' -and $shift.brokerObservation.reason -ceq 'NO11_BROKER_BROKER_TABLE_CHANGED_DURING_CAPTURE') 'CHANGING_TABLE_REJECTED'
 $mock.ChangeAfterFirst=$false;$mock.Ranges['A2:F5'].Value2[2,1]=77
 $reset=Read-No11BrokerSnapshot $null $mock $capture $s1 {return $s2} 2
 Check ($reset.brokerObservation.reason -ceq 'NO11_BROKER_EXCEL_SESSION_CHANGED_DURING_CAPTURE') 'MID_CAPTURE_RESTART'
 $account.orders[0].filledQty=99
 $mismatch=Read-No11BrokerSnapshot $null $mock $capture $s1 $verify 2
 Check ($mismatch.brokerObservation.reason -ceq 'NO11_BROKER_ACCOUNT_BROKER_TABLE_MISMATCH') 'CROSS_BOOK_MISMATCH'
 Write-Host 'NO11_BROKER_SNAPSHOT_OFFLINE_SELFTEST=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
}
if($BrokerOfflineSelfTest){Test-No11BrokerSnapshotOffline}
