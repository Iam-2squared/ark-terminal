# Observe the existing account book alongside the market/temporary books.
# Uses byte-pinned original parsing. Never creates/changes/saves an Excel book.
param(
 [string]$WorkbookPath,[string]$OutputFile,[string]$StopFile,
 [string]$OrderIdWorkbookPath,
 [ValidateRange(1,10000)][int]$Samples=5000,
 [ValidateRange(2,30)][int]$PollSeconds=5,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'Read-No11BrokerSnapshot.ps1')
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$original=Join-Path $repo 'integration\no1-1-msii\windows\Ark-No11-CaptureReadOnly-v3-CANDIDATE.ps1'
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_ACCOUNT_CAPTURE_'+$code)}}
# Only original parser error CODES are exposed, never exception prose,
# workbook paths, symbols, account amounts or order numbers.
function Sanitized-No11AccountReason($failure){
 $message=[string]$failure.Exception.Message
 if($message.Length -le 96 -and
    $message -cmatch '^(?:NO11_[A-Z0-9_]+|(?:RSS|POSITION|ORDER|EXECUTION|BUYING_POWER|INVALID_POSITIVE_QUANTITY|CAPTURE|NO_VERIFIED|EXCEL|ACCOUNT)_[A-Z0-9_]+)(?::[A-Z0-9_]+)?$'){
  return ('NO11_ACCOUNT_CAPTURE_'+$message.Replace(':','_'))
 }
 $category=[string]$failure.Exception.GetType().Name
 if($category -notmatch '^[A-Za-z0-9_]{1,48}$'){$category='UNCLASSIFIED'}
 return ('NO11_ACCOUNT_CAPTURE_UNEXPECTED_'+$category.ToUpperInvariant())
}

function PatchOnce([string]$body,[string]$old,[string]$new){
 Need (([regex]::Matches($body,[regex]::Escape($old))).Count -eq 1) 'PINNED_CONTEXT_CHANGED'
 return $body.Replace($old,$new)
}
function LoadPinnedCapture {
 $bytes=[IO.File]::ReadAllBytes($original)
 $text=[Text.Encoding]::UTF8.GetString($bytes).Replace("`r`n","`n")
 $canonical=[Text.Encoding]::UTF8.GetBytes($text)
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$canonical.Length)+[char]0)
 $hash=[Security.Cryptography.SHA1]::Create()
 try{
  $all=New-Object byte[] ($header.Length+$canonical.Length)
  [array]::Copy($header,0,$all,0,$header.Length)
  [array]::Copy($canonical,0,$all,$header.Length,$canonical.Length)
  $sha=([BitConverter]::ToString($hash.ComputeHash($all))).Replace('-','').ToLowerInvariant()
 }finally{$hash.Dispose()}
 Need ($sha -ceq 'f8be4d704ebad539762471ba62476c32b02a65b1') 'ORIGINAL_SOURCE_CHANGED'
 $tokens=$null;$errors=$null
 $ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors)
 Need ($errors.Count -eq 0) 'ORIGINAL_PARSE_FAILED'
 $helpers=$ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)
 $definitions=($helpers | ForEach-Object {$_.Extent.Text}) -join "`n"
 $begin=$text.IndexOf("    `$Stage = 'VERIFY_LAYOUT'")
 $finish=$text.IndexOf("    `$base=Join-Path `$env:LOCALAPPDATA")
 Need ($begin -gt 0 -and $finish -gt $begin) 'ORIGINAL_CAPTURE_BOUNDARY_CHANGED'
 $body=$text.Substring($begin,$finish-$begin)
 # A fully verified all-padding account table is a genuine empty account.
 # Do not require a personal position merely to run the read-only observer.
 $body=PatchOnce $body "    if (`$positions.Count -lt 1) { throw 'NO_VERIFIED_BROKER_POSITIONS' }" ''
 $old='            symbol=(Trim-Value (Bulk-Value $ordersBlock $idx 2))'
 $extra=@'
            symbol=(Trim-Value (Bulk-Value $ordersBlock $idx 2))
            account=(Trim-Value (Bulk-Value $ordersBlock $idx 4))
            side=(Trim-Value (Bulk-Value $ordersBlock $idx 5))
            trade=(Trim-Value (Bulk-Value $ordersBlock $idx 6))
            executionCondition=(Trim-Value (Bulk-Value $ordersBlock $idx 7))
'@
 $body=PatchOnce $body $old $extra
 # Read the vendor datetime from the SAME bulk row as price and quantity.
 # A later per-cell .Text read could refer to a shifted/new execution row.
 $body=PatchOnce $body '$date=Trim-Value ($sheet.Cells.Item($row,27).Text)' '$date=Convert-No11ExecutionDate (Bulk-Value $executionsBlock $idx 0)'
 $executionAccount='            account=(Trim-Value (Bulk-Value $executionsBlock $idx 3))'
 $executionFields=@'
            account=(Trim-Value (Bulk-Value $executionsBlock $idx 3))
            market=(Trim-Value (Bulk-Value $executionsBlock $idx 4))
            trade=(Trim-Value (Bulk-Value $executionsBlock $idx 5))
'@
 $body=PatchOnce $body $executionAccount $executionFields
 $program='param($sheet)' + "`n" + $definitions + "`n" + '$maxCaptureSeconds=25' + "`n" + $body + "`n" + 'return @{snapshot=$snapshot;health=$health}'
 return [scriptblock]::Create($program)
}
function PrivatePath([string]$value,[bool]$newFile=$false){
 Need (-not [string]::IsNullOrWhiteSpace($value) -and [IO.Path]::IsPathRooted($value)) 'ABSOLUTE_PATH_REQUIRED'
 $full=[IO.Path]::GetFullPath($value)
 Need (-not ($full.Equals($repo,[StringComparison]::OrdinalIgnoreCase) -or $full.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase))) 'PRIVATE_PATH_IN_REPO'
 $parent=Split-Path -Parent $full
 Need (Test-Path -LiteralPath $parent -PathType Container) 'PRIVATE_PARENT_MISSING'
 $cursor=$full
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  if(Test-Path -LiteralPath $cursor){
   $item=Get-Item -LiteralPath $cursor -Force
   Need (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_POINT'
  }
  $next=Split-Path -Parent $cursor;if($next -ceq $cursor){break};$cursor=$next
 }
 if($newFile){Need (-not (Test-Path -LiteralPath $full)) 'CONTROL_ALREADY_EXISTS'}
 return $full
}
function Publish([string]$file,$value){
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $value -Depth 20 -Compress)+[char]10)
 $tmp=$file+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
 try{
  $f=[IO.File]::Open($tmp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
  # Windows PowerShell binds ordinary $null to an empty string parameter.
  # File.Replace needs a real null backup path; keep atomic replacement.
  if([IO.File]::Exists($file)){[IO.File]::Replace($tmp,$file,[System.Management.Automation.Language.NullString]::Value)}else{[IO.File]::Move($tmp,$file)}
 }finally{if([IO.File]::Exists($tmp)){[IO.File]::Delete($tmp)}}
}
function CaptureAccount([string]$target,[scriptblock]$capture){
 $excelProcesses=@(Get-Process EXCEL -ErrorAction SilentlyContinue)
 Need ($excelProcesses.Count -eq 1) 'EXCEL_PROCESS_NOT_UNIQUE'
 $excel=$null;$book=$null;$sheet=$null;$idBook=$null;$idSheet=$null
 try{
  $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
  Need ($excel.Workbooks.Count -ge 1 -and $excel.Workbooks.Count -le 8) 'BOOK_COUNT_INVALID'
  $hits=0
  foreach($candidate in $excel.Workbooks){
   if([string]::Equals([IO.Path]::GetFullPath([string]$candidate.FullName),$target,[StringComparison]::OrdinalIgnoreCase)){
    $hits++;$book=$candidate
   }
  }
  Need ($hits -eq 1) 'ACCOUNT_BOOK_NOT_UNIQUE'
  Need ($book.Worksheets.Count -eq 1) 'ACCOUNT_SHEET_COUNT'
  Need (-not [bool]$book.Date1904) 'UNSUPPORTED_EXCEL_DATE_EPOCH'
  $sheet=$book.Worksheets.Item(1)
  Need ([string]$sheet.Name -ceq 'ARK_ACCOUNT_READONLY') 'ACCOUNT_SHEET_IDENTITY'
  if([string]::IsNullOrWhiteSpace($OrderIdWorkbookPath)){
   $observed=& $capture $sheet
   return @{snapshot=$observed.snapshot;health=$observed.health;
     brokerObservation=(New-No11UnavailableBrokerObservation 'ORDER_ID_WORKBOOK_NOT_CONFIGURED')}
  }
  try{
   Need ([IO.Path]::IsPathRooted($OrderIdWorkbookPath) -and (Test-Path -LiteralPath $OrderIdWorkbookPath -PathType Leaf)) 'ORDER_ID_FILE_REQUIRED'
   $idTarget=[IO.Path]::GetFullPath($OrderIdWorkbookPath)
   Need (-not $idTarget.Equals($target,[StringComparison]::OrdinalIgnoreCase)) 'ORDER_ID_BOOK_MUST_BE_SEPARATE'
   $idHits=0
   foreach($candidate in $excel.Workbooks){
    if([string]::Equals([IO.Path]::GetFullPath([string]$candidate.FullName),$idTarget,[StringComparison]::OrdinalIgnoreCase)){$idHits++;$idBook=$candidate}
   }
   Need ($idHits -eq 1 -and $idBook.Worksheets.Count -eq 1) 'ORDER_ID_BOOK_NOT_UNIQUE'
   Need (-not [bool]$idBook.Date1904) 'UNSUPPORTED_EXCEL_DATE_EPOCH'
   $idSheet=$idBook.Worksheets.Item(1)
   Need ([string]$idSheet.Name -ceq 'ARK_ORDER_IDS_READONLY') 'ORDER_ID_SHEET_IDENTITY'
   $session=New-No11ExcelSession $excelProcesses[0].Id $excelProcesses[0].StartTime.ToUniversalTime().ToString('o') $target $idTarget
   $verify={
    $p=@(Get-Process EXCEL -ErrorAction SilentlyContinue)
    Assert-No11Broker ($p.Count -eq 1) 'EXCEL_PROCESS_CHANGED'
    Assert-No11Broker (([IO.Path]::GetFullPath([string]$book.FullName)).Equals($target,[StringComparison]::OrdinalIgnoreCase) -and
      ([IO.Path]::GetFullPath([string]$idBook.FullName)).Equals($idTarget,[StringComparison]::OrdinalIgnoreCase)) 'WORKBOOK_CHANGED'
    Assert-No11Broker (-not [bool]$book.Date1904 -and -not [bool]$idBook.Date1904 -and
      [string]$sheet.Name -ceq 'ARK_ACCOUNT_READONLY' -and [string]$idSheet.Name -ceq 'ARK_ORDER_IDS_READONLY') 'WORKBOOK_CHANGED'
    return New-No11ExcelSession $p[0].Id $p[0].StartTime.ToUniversalTime().ToString('o') $target $idTarget
   }
   return Read-No11BrokerSnapshot $sheet $idSheet $capture $session $verify
  }catch{
   $observed=& $capture $sheet
   return @{snapshot=$observed.snapshot;health=$observed.health;
    brokerObservation=(New-No11UnavailableBrokerObservation 'BROKER_WORKBOOK_UNAVAILABLE')}
  }
 }finally{
  foreach($o in @($idSheet,$idBook,$sheet,$book,$excel)){
   if($null -ne $o -and [Runtime.InteropServices.Marshal]::IsComObject($o)){
    try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($o)}catch{}
   }
  }
 }
}
$capture=LoadPinnedCapture
if($OfflineSelfTest){
 $fakeA=[pscustomobject]@{Exception=[Exception]::new('RSS_INITIAL_STATUS_INVALID:L1')}
 Need ((Sanitized-No11AccountReason $fakeA) -ceq 'NO11_ACCOUNT_CAPTURE_RSS_INITIAL_STATUS_INVALID_L1') 'REASON_KNOWN'
 $fakeB=[pscustomobject]@{Exception=[Exception]::new('private-account=123456; password=secret')}
 Need ((Sanitized-No11AccountReason $fakeB) -ceq 'NO11_ACCOUNT_CAPTURE_UNEXPECTED_EXCEPTION') 'REASON_REDACTED'
 Write-Host 'NO11_ACCOUNT_CAPTURE_SAFE_REASON_SELFTEST=PASS'
 $text=$capture.ToString()
 Need ($text.Contains('Read-BulkRange') -and $text.Contains('account=(Trim-Value (Bulk-Value $ordersBlock $idx 4))')) 'OFFLINE_CAPTURE_SHAPE'
 Need (-not $text.Contains('NO_VERIFIED_BROKER_POSITIONS')) 'EMPTY_ACCOUNT_NOT_SUPPORTED'
 Need ($text.Contains('Convert-No11ExecutionDate (Bulk-Value $executionsBlock $idx 0)') -and
   -not $text.Contains('$date=Trim-Value ($sheet.Cells.Item($row,27).Text)')) 'BULK_EXECUTION_DATE_REQUIRED'
 Need (-not ($text -match '(?i)Workbooks\.Add|Workbooks\.Open|\.Save\(|\.SaveAs\(|RssStockOrder\(|RssCancelOrder\(')) 'OFFLINE_NOT_READONLY'
 Test-No11BrokerSnapshotOffline
 # Execute the pinned legacy parser against a mock Excel sheet. Cells.Text is
 # intentionally absent: this catches reintroduction of mixed-time row reads.
 $ranges=@{}
 foreach($d in @(
  @('L1','=RssCapacityList(L2:L2)','完了'),@('N1','=RssOrderList(N2:W2,0,1)','配信中'),
  @('AA1','=RssExecutionList(AA2:AI2,1)','配信中'),@('AL1','=RssPositionList()','配信中'))){
  $ranges[$d[0]]=[pscustomobject]@{HasFormula=$true;Formula=$d[1];Value2=$d[2];Text=$d[2]}
 }
 $ranges['L2']=[pscustomobject]@{Value2='現物買付可能額'};$ranges['L3']=[pscustomobject]@{Value2=100000.0}
 $specs=@(
  @{header='N2:W2';data='N3:W301';rows=299;labels=@('注文番号','通常注文状況','銘柄コード','銘柄名称','口座区分','売買','取引','執行条件','注文数量','約定数量');values=@('123','約定','7203','SYNTHETIC','特定','買付','現物','本日中',100.0,100.0)},
  @{header='AA2:AI2';data='AA3:AI301';rows=299;labels=@('約定日','銘柄コード','銘柄名称','口座区分','市場名称','取引','売買','約定数量','約定単価');values=@(([datetime]'2026-10-26T09:30:04').ToOADate(),'7203','SYNTHETIC','特定','東証','現物','買付',100.0,1000.1)},
  @{header='AL2:BC2';data='AL3:BC201';rows=199;labels=@('銘柄コード','銘柄名称','口座区分','保有数量','発注数量','平均取得価額','時価','前日比','前日比率','時価評価額','評価損益額','評価損益率','銘柄情報等','JAX時価','JNX時価','PER','PBR','配当利回り');values=@('7203','SYNTHETIC','特定',100.0,0.0,1000.1,1000.1,0.0,0.0,100010.0,0.0,0.0,'-',1000.1,1000.1,10.0,1.0,1.0)}
 )
 foreach($s in $specs){
  $h=[array]::CreateInstance([object],[int[]]@(1,$s.labels.Count),[int[]]@(1,1))
  $data=[array]::CreateInstance([object],[int[]]@($s.rows,$s.labels.Count),[int[]]@(1,1))
  for($c=1;$c -le $s.labels.Count;$c++){$h[1,$c]=$s.labels[$c-1];$data[1,$c]=$s.values[$c-1]}
  $ranges[$s.header]=[pscustomobject]@{Value2=$h};$ranges[$s.data]=[pscustomobject]@{Value2=$data}
 }
 $mock=[pscustomobject]@{Ranges=$ranges}
 $mock | Add-Member -MemberType ScriptMethod -Name Range -Value {param($address) if(-not $this.Ranges.ContainsKey($address)){throw 'UNEXPECTED_MOCK_RANGE'};return $this.Ranges[$address]}
 $parsed=& $capture $mock
 Need ($parsed.snapshot.executions.Count -eq 1 -and $parsed.snapshot.executions[0].executionDate -ceq '2026/10/26 09:30:04' -and
  $parsed.snapshot.executions[0].market -ceq '東証' -and $parsed.snapshot.executions[0].trade -ceq '現物') 'PINNED_MOCK_EXECUTION_FIELDS'
 Need ($parsed.snapshot.orders[0].account -ceq '特定' -and $parsed.snapshot.orders[0].trade -ceq '現物') 'PINNED_MOCK_ORDER_FIELDS'
 Write-Host 'NO11_ACCOUNT_CAPTURE_OFFLINE_SELFTEST=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$lock=$null;$failed=$false;$out=$null
try{
 Need ([TimeZoneInfo]::Local.GetUtcOffset([datetime]::Now).TotalHours -eq 9) 'PC_TIMEZONE_NOT_JST'
 Need ([IO.Path]::IsPathRooted($WorkbookPath) -and (Test-Path -LiteralPath $WorkbookPath -PathType Leaf)) 'ACCOUNT_FILE_REQUIRED'
 $target=[IO.Path]::GetFullPath($WorkbookPath)
 $out=PrivatePath $OutputFile
 $stop=PrivatePath $StopFile $true
 Need (-not $out.Equals($stop,[StringComparison]::OrdinalIgnoreCase)) 'OUTPUT_STOP_COLLISION'
 $lockFile=PrivatePath ($out+'.lock')
 $lock=[IO.File]::Open($lockFile,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 $run=[guid]::NewGuid().ToString('N')
 for($i=1;$i -le $Samples;$i++){
  if(Test-Path -LiteralPath $stop -PathType Leaf){break}
  $value=[ordered]@{schemaId='ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1';runId=$run;sequence=$i;
    status='BLOCKED';readOnly=$true;productionReady=$false;orderTransmission=$false}
  try{
   $observed=CaptureAccount $target $capture
   $value.status='OBSERVED';$value.snapshot=$observed.snapshot;$value.health=$observed.health
   $value.brokerObservation=$observed.brokerObservation
  }catch{
   $value.reason=Sanitized-No11AccountReason $_
  }
  Publish $out $value
  if($i -lt $Samples){
   $until=[datetime]::UtcNow.AddSeconds($PollSeconds)
   while([datetime]::UtcNow -lt $until){
    if(Test-Path -LiteralPath $stop -PathType Leaf){break}
    Start-Sleep -Milliseconds 250
   }
  }
 }
}catch{
 $failed=$true
 Write-Host 'NO11_ACCOUNT_CAPTURE=BLOCKED'
}finally{
 if($null -ne $lock){$lock.Dispose()}
 if($null -ne $out){
  try{Publish ($out+'.closed.json') ([ordered]@{schemaId='ARK_NO11_ACCOUNT_OBSERVER_CLOSED_V1';processId=$PID;
   excelModified=$false;failed=$failed;productionReady=$false;orderTransmission=$false})}catch{$failed=$true}
 }
 Write-Host 'ORDER_TRANSMISSION=False'
}
if($failed){exit 2}
exit 0