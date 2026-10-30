# Public market data capture only. Never opens, saves, edits, or reads account values.
# Existing account workbook identities and formulas are inspected for capacity only.
param(
 [switch]$OfflineSelfTest,
 [string]$SymbolsFile,
 [string]$PrivateRoot,
 [ValidateRange(1,20)][int]$BatchSize=20,
 [ValidateRange(5,60)][int]$WaitSeconds=25,
 [ValidateRange(20,3000)][int]$Bars=3000,
 [ValidateRange(0,5000)][int]$MaxSymbols=0,
 [ValidateSet('1M','5M')][string]$Period='1M'
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$headers=@('銘柄名称','市場名称','足種','日付','時刻','始値','高値','安値','終値','出来高')
function Test-Code([string]$s){return $s -cmatch '^[0-9A-Z]{4}\.T$'}
function New-ChartFormula([string]$s,[string]$p,[int]$n){
 if(-not (Test-Code $s) -or $p -cnotin @('1M','5M') -or $n -lt 20 -or $n -gt 3000){throw 'NO11_BATCH_FORMULA_REJECTED'}
 return ('=RssChart($A$2:$J$2,"{0}","{1}",{2})' -f $s,$p,$n)
}
function Convert-ChartDate([object]$v){
 if($null -eq $v){return $null}
 if($v -is [datetime]){return $v.ToString('yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)}
 if($v -is [ValueType]){
  $n=[double]$v
  if([double]::IsNaN($n) -or [double]::IsInfinity($n) -or $n -lt 30000 -or $n -gt 80000){return $null}
  return [datetime]::FromOADate($n).ToString('yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)
 }
 $s=[string]$v
 if($s -match '^20\d\d[/\-]\d\d[/\-]\d\d$'){return $s.Replace('/','-')}
 return $null
}
function Convert-ChartTime([object]$v){
 if($null -eq $v){return $null}
 if($v -is [datetime]){return $v.ToString('HH:mm',[Globalization.CultureInfo]::InvariantCulture)}
 if($v -is [ValueType]){
  $n=[double]$v
  if([double]::IsNaN($n) -or [double]::IsInfinity($n) -or $n -lt 0 -or $n -ge 1){return $null}
  return [datetime]::FromOADate($n).ToString('HH:mm',[Globalization.CultureInfo]::InvariantCulture)
 }
 $s=[string]$v
 if($s -match '^([01]\d|2[0-3]):[0-5]\d(?::00)?$'){return $s.Substring(0,5)}
 return $null
}
function Read-Bar([object]$v,[int]$r,[int]$c,[datetimeoffset]$observed,[string]$period){
 $d=Convert-ChartDate $v.GetValue($r,$c+3)
 $t=Convert-ChartTime $v.GetValue($r,$c+4)
 if($null -eq $d -or $null -eq $t){return $null}
 $at=[datetimeoffset]::MinValue;$label=$d+'T'+$t+':00+09:00'
 if(-not [datetimeoffset]::TryParseExact($label,'yyyy-MM-ddTHH:mm:sszzz',[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$at)){return $null}
 if($at -gt $observed){return $null}
 $m=$at.Hour*60+$at.Minute
 if(-not (($m -ge 540 -and $m -le 690) -or ($m -ge 750 -and $m -le 930))){return $null}
 if($period -ceq '5M' -and $m%5 -ne 0){return $null}
 $p=@()
 for($j=5;$j -le 8;$j++){
  $x=$v.GetValue($r,$c+$j)
  if($x -isnot [ValueType]){return $null}
  $n=[double]$x
  if([double]::IsNaN($n) -or [double]::IsInfinity($n) -or $n -le 0){return $null}
  $p+=@($n)
 }
 $x=$v.GetValue($r,$c+9)
 if($x -isnot [ValueType]){return $null}
 $vol=[double]$x
 if([double]::IsNaN($vol) -or [double]::IsInfinity($vol) -or $vol -lt 0 -or $vol -gt 9007199254740991 -or $vol -ne [Math]::Floor($vol)){return $null}
 if($p[2] -gt [Math]::Min($p[0],$p[3]) -or $p[1] -lt [Math]::Max($p[0],$p[3])){return $null}
 return [pscustomobject]@{label=$label;open=$p[0];high=$p[1];low=$p[2];close=$p[3];volume=[long]$vol}
}
function Write-Immutable([string]$file,[object]$value){
 $json=ConvertTo-Json -InputObject $value -Depth 10 -Compress
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes($json+[char]10)
 $f=$null
 try{
  $f=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  $f.Write($bytes,0,$bytes.Length);$f.Flush($true)
 }finally{if($null -ne $f){$f.Dispose()}}
 return (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
}
if($OfflineSelfTest){
 if((New-ChartFormula '7203.T' '1M' 3000) -cne '=RssChart($A$2:$J$2,"7203.T","1M",3000)'){throw 'NO11_BATCH_FORMULA_SELFTEST'}
 if(Test-Code '7203.T");X('){throw 'NO11_BATCH_CODE_INJECTION'}
 $bad=$false;try{[void](New-ChartFormula 'BAD' '1M' 3000)}catch{$bad=$true}
 if(-not $bad){throw 'NO11_BATCH_BAD_CODE_ACCEPTED'}
 $a=[Array]::CreateInstance([object],1,10)
 $a.SetValue('2026/10/13',0,3);$a.SetValue('09:10',0,4)
 $a.SetValue([double]100,0,5);$a.SetValue([double]102,0,6);$a.SetValue([double]99,0,7)
 $a.SetValue([double]101,0,8);$a.SetValue([double]300,0,9)
 $now=[datetimeoffset]::Parse('2026-10-13T21:00:00+09:00')
 $r=Read-Bar $a 0 0 $now '1M'
 if($null -eq $r -or $r.close -ne 101){throw 'NO11_BATCH_OHLCV_SELFTEST'}
 $a.SetValue([double]90,0,6)
 if($null -ne (Read-Bar $a 0 0 $now '1M')){throw 'NO11_BATCH_BAD_HIGH_ACCEPTED'}
 $a.SetValue([double]102,0,6);$a.SetValue('09:11',0,4)
 if($null -ne (Read-Bar $a 0 0 $now '5M')){throw 'NO11_BATCH_5M_MISALIGNMENT_ACCEPTED'}
 $a.SetValue('2026/10/14',0,3)
 if($null -ne (Read-Bar $a 0 0 $now '1M')){throw 'NO11_BATCH_FUTURE_ACCEPTED'}
 Write-Host 'NO11_TRAINING_BATCH_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_LIVE_DATA_ACCESSED=False'
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
if(-not (Test-Path -LiteralPath $SymbolsFile -PathType Leaf)){throw 'NO11_BATCH_SYMBOL_FILE_REQUIRED'}
$symbols=@(Get-Content -LiteralPath $SymbolsFile -Encoding UTF8 | Where-Object {$_.Trim() -ne ''} | ForEach-Object {$_.Trim()})
if($symbols.Count -lt 1 -or $symbols.Count -gt 5000 -or @($symbols | Select-Object -Unique).Count -ne $symbols.Count){throw 'NO11_BATCH_SYMBOL_LIST_INVALID'}
foreach($s in $symbols){if(-not (Test-Code $s)){throw 'NO11_BATCH_CODE_REJECTED'}}
if($MaxSymbols -gt 0){$symbols=@($symbols | Select-Object -First $MaxSymbols)}
if([string]::IsNullOrWhiteSpace($PrivateRoot)){$PrivateRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\training-capture'}
if(-not [IO.Path]::IsPathRooted($PrivateRoot)){throw 'NO11_BATCH_ABSOLUTE_PRIVATE_ROOT_REQUIRED'}
[void][IO.Directory]::CreateDirectory($PrivateRoot)
if((Get-Item -LiteralPath $PrivateRoot).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'NO11_BATCH_REPARSE_ROOT_REJECTED'}
$run=Join-Path $PrivateRoot ('rss-'+[Guid]::NewGuid().ToString('N'));[void][IO.Directory]::CreateDirectory($run)
$excel=$null;$book=$null;$sheets=@();$received=0;$totalRows=0;$unavailable=0;$ledger=New-Object System.Collections.ArrayList
$stage='PRECHECK'
try{
 $tcp=New-Object System.Net.Sockets.TcpClient;$active=$false
 try{$tcp.Connect('127.0.0.1',8767);$active=$tcp.Connected}catch [System.Net.Sockets.SocketException]{$active=$false}finally{$tcp.Close()}
 if($active){throw 'NO11_ACCOUNT_UI_MUST_BE_STOPPED_FIRST'}
 # Ignore background/headless EXCEL instances; attach only to the unique Ark-labelled visible window.
 # Other processes are never killed. COM validates both original workbook identities below.
 $stage='EXCEL_WINDOW_DISCOVERY'
 # Excel changes MainWindowTitle when the active workbook switches.
 # Prefer one uniquely Ark-labelled visible process, or fall back to the
 # single visible Excel process. Original workbook/sheet COM checks remain
 # mandatory before creating a temporary book.
 $visible=@(Get-Process EXCEL -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne [IntPtr]::Zero})
 $arkNamed=@($visible | Where-Object {$_.MainWindowTitle -like 'Ark_No11_*'})
 $processes=@()
 if($arkNamed.Count -eq 1){$processes=@($arkNamed)}
 elseif($arkNamed.Count -eq 0 -and $visible.Count -eq 1){$processes=@($visible)}
 Write-Host ('NO11_BATCH_EXCEL_DISCOVERY=VISIBLE_{0}|ARK_NAMED_{1}|SELECTED_{2}' -f $visible.Count,$arkNamed.Count,$processes.Count)
 if($processes.Count -ne 1){throw 'NO11_BATCH_EXCEL_IDENTITY_NOT_UNIQUE'}
 if(-not ('No11TrainingBatchWindow' -as [type])){
 Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class No11TrainingBatchWindow {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,Callback cb,IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h,StringBuilder b,int n);
 [DllImport("oleacc.dll")] public static extern int AccessibleObjectFromWindow(IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object o);
}
'@ -ErrorAction Stop
 }
 $script:windows=@();$cb=[No11TrainingBatchWindow+Callback]{param($h,$p) $n=New-Object Text.StringBuilder 128;[void][No11TrainingBatchWindow]::GetClassName($h,$n,128);if($n.ToString() -ceq 'EXCEL7'){$script:windows+=@($h)};return $true}
 [void][No11TrainingBatchWindow]::EnumChildWindows($processes[0].MainWindowHandle,$cb,[IntPtr]::Zero)
 if($script:windows.Count -ne 1){throw 'NO11_BATCH_EXCEL7_NOT_UNIQUE'}
 $iid=[Guid]'00020400-0000-0000-C000-000000000046';$obj=$null
 $hr=[No11TrainingBatchWindow]::AccessibleObjectFromWindow($script:windows[0],[uint32]4294967280,[ref]$iid,[ref]$obj)
 if($hr -ne 0 -or $null -eq $obj){throw 'NO11_BATCH_COM_ATTACH_FAILED'}
 $stage='EXCEL_COM_ATTACH'
 $excel=$obj.Application
 if($excel.Workbooks.Count -ne 2){throw 'NO11_BATCH_ONLY_TWO_ORIGINAL_WORKBOOKS_REQUIRED'}
 $account=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx');$market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')
 if($account.Worksheets.Item('ARK_ACCOUNT_READONLY').Name -cne 'ARK_ACCOUNT_READONLY' -or $market.Worksheets.Item('ARK_MARKET_READONLY').Name -cne 'ARK_MARKET_READONLY'){throw 'NO11_BATCH_WORKBOOK_IDENTITY_INVALID'}
 $stage='EXISTING_CHART_CAPACITY'
 # Count only existing chart formulas; no account values are read or exported.
 $existing=0
 foreach($wb in @($account,$market)){
  for($i=1;$i -le $wb.Worksheets.Count;$i++){
   $used=$wb.Worksheets.Item($i).UsedRange
   if([long]$used.CountLarge -gt 100000){throw 'NO11_BATCH_CAPACITY_SCAN_TOO_LARGE'}
   $formulaCells=$null
   try{$formulaCells=$used.SpecialCells(-4123)}catch [Runtime.InteropServices.COMException]{
    if($_.Exception.HResult -ne -2146827284){throw}
   }
   if($null -ne $formulaCells){
    foreach($cell in $formulaCells.Cells){
     $formula=[string]$cell.Formula
     if($formula -match '(?i)Rss(?:Chart|Trend)[A-Za-z]*\s*\('){$existing++}
    }
   }
  }
 }
 if($existing+$BatchSize -gt 50){throw 'NO11_BATCH_CHART_CAPACITY_EXCEEDED'}
 $watch=[Diagnostics.Stopwatch]::StartNew()
 for($offset=0;$offset -lt $symbols.Count;$offset+=$BatchSize){
  $batch=@($symbols[$offset..([Math]::Min($offset+$BatchSize-1,$symbols.Count-1))])
  $stage=('BATCH_{0:D5}_WORKBOOK_CREATE' -f ($offset+1))
  $book=$excel.Workbooks.Add();$sheets=@()
  $stage=('BATCH_{0:D5}_FORMULAS' -f ($offset+1))
  foreach($s in $batch){
   $ws=$book.Worksheets.Add();$ws.Name='ARK_'+$s.Replace('.','_')
   for($j=0;$j -lt $headers.Count;$j++){$ws.Cells.Item(2,$j+1).Value2=$headers[$j]}
   $ws.Range('A1').Formula=(New-ChartFormula $s $Period $Bars)
   $sheets+=@($ws)
  }
  $stage=('BATCH_{0:D5}_WAIT' -f ($offset+1))
  Start-Sleep -Seconds $WaitSeconds
  $stage=('BATCH_{0:D5}_READ_AND_WRITE' -f ($offset+1))
  $batchReceived=0
  for($k=0;$k -lt $batch.Count;$k++){
   $s=$batch[$k];$ws=$sheets[$k]
   if([string]$ws.Range('A1').Formula -cne (New-ChartFormula $s $Period $Bars)){throw 'NO11_BATCH_FORMULA_CHANGED'}
   $v=$ws.Range(('A3:J{0}' -f ($Bars+2))).Value2
   $at=[TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([datetimeoffset]::UtcNow,'Tokyo Standard Time')
   $rows=New-Object System.Collections.ArrayList;$seen=New-Object 'System.Collections.Generic.HashSet[string]';$bad=0;$dup=0;$numeric=0
   if($v -is [array] -and $v.Rank -eq 2){
    $r0=$v.GetLowerBound(0);$c0=$v.GetLowerBound(1)
    for($r=$r0;$r -lt $r0+$Bars;$r++){
     $close=$v.GetValue($r,$c0+8)
     if($close -isnot [ValueType] -or [double]$close -le 0){continue}
     $numeric++;$b=Read-Bar $v $r $c0 $at $Period
     if($null -eq $b){$bad++;continue}
     if(-not $seen.Add($b.label)){$dup++;continue}
     [void]$rows.Add($b)
    }
   }
   $status=if($numeric -eq 0){'SOURCE_UNAVAILABLE'}elseif($bad -gt 0 -or $dup -gt 0){'ROW_AUDIT_FAILED'}else{'OBSERVED_ARCHIVE_NOT_TRAINING_CERTIFIED'}
   $payload=[ordered]@{schemaId='ARK_NO11_RSS_TRAINING_SYMBOL_ARCHIVE_V1';symbol=$s;period=$Period;sourceFunction='RssChart';evidenceMode='OBSERVED_READ_ONLY';observedAt=$at.ToString('o');requestedBars=$Bars;numericRows=$numeric;validRows=$rows.Count;invalidRows=$bad;duplicateRows=$dup;status=$status;rows=@($rows.ToArray());privateAccountDataIncluded=$false;vendorLabelCertified=$false;actualHistoricalKnownAtCertified=$false;vendorDecimalTokenCertified=$false;nativeSelectorProduced=$false;modelTrainingReady=$false;productionReady=$false;orderTransmission=$false}
   $name=('{0:D5}-{1}-{2}.json' -f ($offset+$k+1),$s.Replace('.','_'),$Period)
   $sha=Write-Immutable (Join-Path $run $name) $payload
   [void]$ledger.Add([ordered]@{symbol=$s;file=$name;sha256=$sha;status=$status;rows=$rows.Count})
   if($status -ceq 'OBSERVED_ARCHIVE_NOT_TRAINING_CERTIFIED'){$received++;$batchReceived++;$totalRows+=$rows.Count}else{$unavailable++}
  }
  # Destroy the previous temporary workbook and release subscriptions before next wave.
  $stage=('BATCH_{0:D5}_CLOSE' -f ($offset+1))
  $book.Close($false)
  foreach($ws in $sheets){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($ws)}catch{}}
  $sheets=@();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book);$book=$null
  $stage=('BATCH_{0:D5}_CHECKPOINT' -f ($offset+1))
  $receipt=[ordered]@{schemaId='ARK_NO11_RSS_TRAINING_CAPTURE_PROGRESS_V1';completed=$ledger.Count;requested=$symbols.Count;observedSymbols=$received;unavailableSymbols=$unavailable;rows=$totalRows;elapsedSeconds=[Math]::Round($watch.Elapsed.TotalSeconds,2);files=@($ledger.ToArray());productionReady=$false;orderTransmission=$false}
  [void](Write-Immutable (Join-Path $run ('progress-{0:D5}.json' -f $ledger.Count)) $receipt)
  Write-Host ('NO11_RSS_BATCH_PROGRESS={0}/{1}|OBSERVED={2}|UNAVAILABLE={3}|ROWS={4}' -f $ledger.Count,$symbols.Count,$received,$unavailable,$totalRows)
  if($batchReceived -eq 0){throw 'NO11_BATCH_NO_USABLE_SYMBOL_IN_WAVE'}
 }
 Write-Host 'NO11_RSS_TRAINING_CAPTURE=COMPLETE_SOURCE_ONLY'
 Write-Host ('NO11_RSS_TRAINING_CAPTURE_DIR='+$run)
 Write-Host ('NO11_RSS_TRAINING_CAPTURE_ROWS='+$totalRows)
 Write-Host 'NO11_MODEL_TRAINING_READY=False'
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 # Emit safe exception metadata and stage, not broker/account values or raw COM messages.
 Write-Host ('NO11_BATCH_DIAGNOSTIC_STAGE='+$stage)
 Write-Host ('NO11_BATCH_DIAGNOSTIC_EXCEPTION='+$_.Exception.GetType().FullName)
 Write-Host ('NO11_BATCH_DIAGNOSTIC_HRESULT='+$_.Exception.HResult)
 if($null -ne $_.Exception.InnerException){
  Write-Host ('NO11_BATCH_DIAGNOSTIC_INNER='+$_.Exception.InnerException.GetType().FullName)
  Write-Host ('NO11_BATCH_DIAGNOSTIC_INNER_HRESULT='+$_.Exception.InnerException.HResult)
 }
 $reason=$_.Exception.Message
 if($reason -notmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_BATCH_COM_OR_IO_FAILURE'}
 Write-Host ('NO11_RSS_TRAINING_CAPTURE=BLOCKED|'+$reason)
 Write-Host ('NO11_RSS_TRAINING_CAPTURE_DIR='+$run)
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if($null -ne $book){try{$book.Close($false)}catch{}}
 foreach($ws in $sheets){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($ws)}catch{}}
 if($null -ne $book){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book)}catch{}}
 if($null -ne $excel){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}catch{}}
}
