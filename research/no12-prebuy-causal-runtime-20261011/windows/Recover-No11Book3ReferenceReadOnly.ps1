# Salvage the real 2026-10-27 RssMarket reference already visible in Excel Book3.
# NEVER starts another collector, changes a workbook or contacts broker orders.
# Requires EXACT three books (the two originals + the orphaned unsaved Book3).
# The original frozen scope validator supplies the exact selected 47 symbols.
# CapturedAtJst is the *current bulk read* time, NEVER the earlier hung script.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [string]$DailyRun='',
 [string]$OutputRoot='',
 [string]$PythonExecutable='',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$ci=[Globalization.CultureInfo]::InvariantCulture
if(-not $DailyRun){$DailyRun=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\daily-trend-capture\daily-2026-10-26-e84a2ec53b0fdf41'}
if(-not $OutputRoot){$OutputRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\session-reference\2026-10-27'}
if(-not $PythonExecutable){$PythonExecutable=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'}
$planFile=Join-Path $DailyRun 'no11-chart50-private-a9d57cdb4eccb107.json'
$maskFile=Join-Path $DailyRun 'no11-observed-pass-watch-ce769aac846cf1b4.json'
$archive=Join-Path $EngineRoot 'tools\no11_previous_archive_context.py'
$queue=Join-Path $EngineRoot 'tools\no11_review_queue_from_actual_rss.py'
$fields=@('銘柄コード','市場コード','現在日付','前日日付','前日終値','当日基準値','市場部名称','単位株数','権利落日','配当落日','中配落日')
function Need([bool]$ok,[string]$name){
 if(-not $ok){throw ('NO11_BOOK3_'+$name)}
}
function Stamp {
 [datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz',$ci)
}
function SourcePath([string]$p,[bool]$dir=$false){
 Need ([IO.Path]::IsPathRooted($p)) 'ABSOLUTE_PATH_REQUIRED'
 $full=[IO.Path]::GetFullPath($p)
 $i=Get-Item -LiteralPath $full -Force -ErrorAction Stop
 Need ([bool]$i.PSIsContainer -eq $dir) 'SOURCE_TYPE_INVALID'
 $cur=$full
 while(-not [string]::IsNullOrWhiteSpace($cur)){
  $item=Get-Item -LiteralPath $cur -Force
  Need (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'SOURCE_REPARSE_FORBIDDEN'
  $parent=Split-Path -Parent $cur
  if($parent -ceq $cur){break};$cur=$parent
 }
 return $full
}
function DateValue($v){
 if($null -eq $v){return $null}
 if($v -is [datetime]){return $v.ToString('yyyy-MM-dd',$ci)}
 if($v -is [ValueType]){
  $n=[double]$v
  if($n -ge 30000 -and $n -le 80000){return [datetime]::FromOADate($n).ToString('yyyy-MM-dd',$ci)}
  return $null
 }
 $d=[datetime]::MinValue
 if([datetime]::TryParseExact(([string]$v).Replace('/','-'),'yyyy-MM-dd',$ci,
  [Globalization.DateTimeStyles]::None,[ref]$d)){return $d.ToString('yyyy-MM-dd',$ci)}
 return $null
}
function NumberValue($v){
 if($null -eq $v -or $v -isnot [ValueType]){return $null}
 $n=[double]$v
 if([double]::IsNaN($n) -or [double]::IsInfinity($n)){return $null}
 return $n
}
function Formula([string]$s,[string]$f){
 Need ($s -cmatch '^[0-9A-Z]{4}\.T$' -and $f -cin $fields) 'INVALID_FORMULA_SOURCE'
 return '=RssMarket("'+$s+'","'+$f+'")'
}
function ExpectedArray([object]$v,[int]$rows,[int]$columns,[string]$label){
 Need ($v -is [array] -and $v.Rank -eq 2) ($label+'_NOT_2D')
 Need ($v.GetLength(0) -eq $rows -and $v.GetLength(1) -eq $columns) ($label+'_SHAPE')
}
function PathFromLines([object[]]$lines,[string]$token){
 $m=@($lines|Where-Object {([string]$_).StartsWith($token,[StringComparison]::Ordinal)})
 Need ($m.Count -eq 1) 'ORIGINAL_SCOPE_OUTPUT_MISSING'
 $p=([string]$m[0]).Substring($token.Length)
 return (SourcePath $p)
}
function SaveReference([object]$record,[string]$root){
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes(
  (ConvertTo-Json -InputObject $record -Depth 10 -Compress)+[char]10)
 $algorithm=[Security.Cryptography.SHA256]::Create()
 try{$digest=([BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}
 finally{$algorithm.Dispose()}
 $file=Join-Path $root ('session-reference-'+$digest+'.json')
 if([IO.File]::Exists($file)){
  Need ([Linq.Enumerable]::SequenceEqual([byte[]]([IO.File]::ReadAllBytes($file)),[byte[]]$bytes)) 'EXISTING_REFERENCE_CHANGED'
 }else{
  $stream=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}
  finally{$stream.Dispose()}
 }
 return $file
}
if($OfflineSelfTest){
 Need ((Formula '7203.T' '前日終値') -ceq '=RssMarket("7203.T","前日終値")') 'FORMULA_SELFTEST_FAILED'
 $blocked=$false
 try{[void](Formula '7203.T");FORGED' '前日終値')}catch{$blocked=$true}
 Need $blocked 'FORMULA_INJECTION_SELFTEST_FAILED'
 Need ((DateValue '2026/10/27') -ceq '2026-10-27') 'DATE_SELFTEST_FAILED'
 Write-Host 'NO11_BOOK3_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_BOOK3_EXCEL_ACCESSED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$excel=$null;$book=$null;$sheet=$null;$formulaRange=$null;$valueRange=$null
$stage='PRECHECK'
try{
 $jst=(Stamp).Substring(0,10)
 Need ($jst -ceq '2026-10-27') 'SESSION_DAY_INVALID'
 $base=SourcePath $EngineRoot $true
 $run=SourcePath $DailyRun $true
 [void](SourcePath $planFile)
 [void](SourcePath $maskFile)
 [void](SourcePath $archive)
 [void](SourcePath $queue)
 [void](SourcePath $PythonExecutable)
 $output=[IO.Path]::GetFullPath($OutputRoot)
 $privateRoot=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'))
 Need ($output.StartsWith($privateRoot+'\',[StringComparison]::OrdinalIgnoreCase)) 'OUTPUT_OUTSIDE_PRIVATE_ROOT'
 if(-not [IO.Directory]::Exists($output)){[void][IO.Directory]::CreateDirectory($output)}
 [void](SourcePath $output $true)
 Need (@(Get-Process EXCEL -ErrorAction SilentlyContinue).Count -eq 1) 'EXCEL_PROCESS_NOT_UNIQUE'
 # A live competing collector may mutate or close Book3 during our read.
 $running=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop |
  Where-Object {
   $_.ProcessId -ne $PID -and
   [string]$_.CommandLine -match '(?i)(Capture-No11SessionReferenceReadOnly|Probe-No11Chart50(?:Continuous|Diagnosed)ReadOnly|Run-No11ReceivedSessionReadOnly)\.ps1'
  })
 Need ($running.Count -eq 0) 'COMPETING_COLLECTOR_STILL_RUNNING'
 $stage='VALIDATE_FROZEN_SCOPE'
 $export=@('-B',$archive,'--plan',$planFile,'--mask',$maskFile,
  '--output-root',$output,'--symbols-only')
 $lines=@(& $PythonExecutable @export)
 Need ($LASTEXITCODE -eq 0) 'ORIGINAL_SCOPE_VALIDATION_FAILED'
 $symbolFile=PathFromLines $lines 'NO11_PREVIOUS_SYMBOLS_FILE='
 $symbols=@(Get-Content -LiteralPath $symbolFile -Encoding UTF8 | Where-Object {$_})
 Need ($symbols.Count -eq 47 -and
  @($symbols|Select-Object -Unique).Count -eq 47) 'ORIGINAL_SCOPE_NOT_47'
 $plan=Get-Content -LiteralPath $planFile -Raw -Encoding UTF8|ConvertFrom-Json
 Need (($symbols -join '|') -ceq (@($plan.chartPlan.selectorInputSymbols) -join '|') -and
  $plan.chartPlan.orderTransmission -eq $false -and
  $plan.chartPlan.productionReady -eq $false) 'ORIGINAL_SCOPE_CHANGED'
 $stage='EXCEL_ATTACH'
 $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
 Need ($excel.Workbooks.Count -eq 3) 'EXACTLY_THREE_BOOKS_REQUIRED'
 $a=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx')
 $m=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')
 Need ($a.Worksheets.Item('ARK_ACCOUNT_READONLY').Name -ceq 'ARK_ACCOUNT_READONLY' -and
  $m.Worksheets.Item('ARK_MARKET_READONLY').Name -ceq 'ARK_MARKET_READONLY') 'ORIGINAL_BOOKS_INVALID'
 $book=$excel.Workbooks.Item('Book3')
 Need ($book.Name -ceq 'Book3' -and [string]$book.Path -ceq '' -and
  $book.Worksheets.Count -eq 1) 'UNSAVED_BOOK3_IDENTITY_INVALID'
 $sheet=$book.Worksheets.Item(1)
 Need ($sheet.Name -ceq 'Sheet1' -and
  [long]$sheet.UsedRange.CountLarge -le 1000) 'BOOK3_LAYOUT_UNEXPECTED'
 $range='A1:L47'
 $stage='FORMULA_BULK_READ'
 $formulaRange=$sheet.Range($range)
 $formulas=$formulaRange.Formula
 ExpectedArray $formulas 47 12 'FORMULA'
 $fr=$formulas.GetLowerBound(0);$fc=$formulas.GetLowerBound(1)
 for($i=0;$i -lt 47;$i++){
  $s=[string]$symbols[$i]
  Need (([string]$formulas.GetValue($fr+$i,$fc)).Trim() -ceq $s) 'BOOK3_SYMBOL_ORDER_INVALID'
  for($j=0;$j -lt 11;$j++){
   Need (([string]$formulas.GetValue($fr+$i,$fc+$j+1)) -ceq (Formula $s $fields[$j])) 'BOOK3_ORIGINAL_RSS_FORMULA_DIFFERENT'
  }
 }
 $stage='VALUES_BULK_READ'
 Write-Host 'NO11_BOOK3_SCOPE_AND_FORMULAS=VERIFIED_47_OF_47'
 $start=Stamp
 $valueRange=$sheet.Range($range)
 $values=$valueRange.Value2
 $end=Stamp
 ExpectedArray $values 47 12 'RSS_VALUES'
 Need (([datetimeoffset]::Parse($end)-[datetimeoffset]::Parse($start)).TotalSeconds -lt 30) 'RSS_BULK_READ_TIMED_OUT_30S'
 $r0=$values.GetLowerBound(0);$c0=$values.GetLowerBound(1)
 $rows=@()
 for($i=0;$i -lt 47;$i++){
  $s=[string]$symbols[$i];$r=$r0+$i
  Need ([string]$values.GetValue($r,$c0) -ceq $s) 'VALUE_SYMBOL_MISMATCH'
  Need ([string]$values.GetValue($r,$c0+1) -ceq $s.Substring(0,4)) 'VENDOR_SYMBOL_MISMATCH'
  $rows+=@([ordered]@{
   symbol=$s;marketCode=([string]$values.GetValue($r,$c0+2)).Trim();
   marketDate=(DateValue $values.GetValue($r,$c0+3));
   previousDate=(DateValue $values.GetValue($r,$c0+4));
   previousClose=(NumberValue $values.GetValue($r,$c0+5));
   dayBasePrice=(NumberValue $values.GetValue($r,$c0+6));
   marketSection=([string]$values.GetValue($r,$c0+7)).Trim();
   lotShares=(NumberValue $values.GetValue($r,$c0+8));
   exRightsDateRaw=[string]$values.GetValue($r,$c0+9);
   exDividendDateRaw=[string]$values.GetValue($r,$c0+10);
   interimExDividendDateRaw=[string]$values.GetValue($r,$c0+11)
  })
 }
 $record=[ordered]@{
  schemaId='ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1';
  sessionDate=$jst;source='RssMarket_SELECTED_REFERENCE_READONLY';
  capturedAtJst=$start;completedAtJst=$end;
  chartPlanSha256=$plan.chartPlan.planSha256;
  selectedSymbols=@($symbols);rows=@($rows);
  corporateActionReviewPerformed=$false;
  readOnly=$true;productionReady=$false;orderTransmission=$false
 }
 $stage='SAVE_IMMUTABLE_REFERENCE'
 $sourceFile=SaveReference $record $output
 Write-Host 'NO11_BOOK3_SALVAGE=HASHED_REAL_RSS_VALUES'
 Write-Host ('NO11_BOOK3_REFERENCE_FILE='+$sourceFile)
 Write-Host 'NO11_BOOK3_REFERENCE_ROWS=47'
 $stage='UNREVIEWED_SECURITY_QUEUE'
 $reviewArgs=@('-B',$queue,'--reference',$sourceFile,'--plan',$planFile,
  '--mask',$maskFile,'--output-root',$output)
 $queueLines=@(& $PythonExecutable @reviewArgs)
 $status=$LASTEXITCODE
 foreach($line in $queueLines){if(([string]$line) -match '^NO11_|^ORDER_TRANSMISSION='){Write-Host $line}}
 Need ($status -eq 0) 'REVIEW_QUEUE_VALIDATION_FAILED'
 Write-Host 'NO11_BOOK3_REFERENCE=CAPTURED_UNREVIEWED_NOT_MASTER'
 Write-Host 'NO11_BOOK3_TEMPORARY_BOOK=LEFT_OPEN_UNSAVED'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $errorCode=$_.Exception.Message
 if($errorCode -cnotmatch '^NO11_BOOK3_[A-Z0-9_]+$'){$errorCode='NO11_BOOK3_PRIVATE_OR_COM_OPERATION_FAILED'}
 Write-Host ('NO11_BOOK3_SALVAGE=BLOCKED|'+$errorCode)
 Write-Host ('NO11_BOOK3_STAGE='+$stage)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 foreach($obj in @($formulaRange,$valueRange,$sheet,$book,$excel)){
  if($null -ne $obj -and [Runtime.InteropServices.Marshal]::IsComObject($obj)){
   try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($obj)}catch{}
  }
 }
}
exit 0
