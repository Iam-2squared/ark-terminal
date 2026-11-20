# Sample exactly FIVE real RssChart D/100 grids, without persisting/printing
# symbols or prices. Explains whether the one rejected row is after the real
# as-of session, invalid within history, or has an unknown date.
# This is DIAGNOSTIC ONLY: NEVER recertifies existing immutable 429 receipts.
param(
 [string]$RunDir='',
 [ValidateRange(5,60)][int]$WarmupSeconds=30,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$asOf='2026-10-28'
$today='2026-10-29'
$ci=[Globalization.CultureInfo]::InvariantCulture
function Need([bool]$ok,[string]$code){
 if(-not $ok){throw ('NO11_RAW_CANARY_'+$code)}
}
function Checked([string]$p,[bool]$dir=$false){
 Need (-not [string]::IsNullOrWhiteSpace($p) -and [IO.Path]::IsPathRooted($p)) 'ABSOLUTE_PATH'
 $p=[IO.Path]::GetFullPath($p)
 Need (Test-Path -LiteralPath $p -PathType $(if($dir){'Container'}else{'Leaf'})) 'PATH_MISSING'
 $cur=$p
 while(-not [string]::IsNullOrWhiteSpace($cur)){
  Need (((Get-Item -LiteralPath $cur -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'LINK_FORBIDDEN'
  $next=Split-Path -Parent $cur;if($next -ceq $cur){break};$cur=$next
 }
 return $p
}
function Date-Token([object]$value){
 if($null -eq $value){return $null}
 if($value -is [datetime]){return $value.ToString('yyyy-MM-dd',$ci)}
 if($value -is [double] -or $value -is [int]){
  $n=[double]$value
  if([double]::IsNaN($n) -or [double]::IsInfinity($n) -or $n -lt 30000 -or $n -gt 80000){return $null}
  return [datetime]::FromOADate($n).ToString('yyyy-MM-dd',$ci)
 }
 $s=([string]$value).Replace('/','-');$d=[datetime]::MinValue
 if([datetime]::TryParseExact($s,'yyyy-MM-dd',$ci,[Globalization.DateTimeStyles]::None,[ref]$d)){return $d.ToString('yyyy-MM-dd',$ci)}
 return $null
}
function Number-Token([object]$value){
 if($value -isnot [double] -and $value -isnot [int] -and $value -isnot [long] -and $value -isnot [decimal]){return $null}
 $n=[double]$value
 if([double]::IsNaN($n) -or [double]::IsInfinity($n) -or $n -lt 0){return $null}
 return $n.ToString('R',$ci)
}
function Scan-Grid([object]$grid,[string]$referenceAsOf,[object[]]$expectedDays){
 $result=[ordered]@{validRows=0;validRequired=0;invalidFuture=0;invalidInWindowOrEarlier=0;invalidDate=0;validLater=0;missingRequired=0}
 $seen=New-Object 'System.Collections.Generic.HashSet[string]'
 $wanted=New-Object 'System.Collections.Generic.HashSet[string]'
 foreach($d in $expectedDays){[void]$wanted.Add([string]$d)}
 Need ($grid -is [array] -and $grid.Rank -eq 2 -and $grid.GetLength(1) -eq 10) 'GRID_SHAPE'
 $r0=$grid.GetLowerBound(0);$c0=$grid.GetLowerBound(1)
 for($r=$r0;$r -lt $r0+$grid.GetLength(0);$r++){
  $rawDate=$grid.GetValue($r,$c0+3)
  if($null -eq $rawDate -or [string]::IsNullOrWhiteSpace([string]$rawDate)){continue}
  $day=Date-Token $rawDate
  if($null -eq $day){$result.invalidDate++;continue}
  $nums=@()
  for($j=5;$j -le 9;$j++){$nums+=@(Number-Token $grid.GetValue($r,$c0+$j))}
  if(@($nums|Where-Object {$null -eq $_}).Count -gt 0){
   if($day -cgt $referenceAsOf){$result.invalidFuture++}
   else{$result.invalidInWindowOrEarlier++}
   continue
  }
  $result.validRows++
  if($day -cgt $referenceAsOf){$result.validLater++}
  if($wanted.Contains($day)){[void]$seen.Add($day)}
 }
 $result.validRequired=$seen.Count
 $result.missingRequired=$wanted.Count-$seen.Count
 return [pscustomobject]$result
}
function Formulas([object]$snapshot){
 if($null -eq $snapshot){return @()}
 if($snapshot -is [array]){return @($snapshot)}
 return @($snapshot)
}
if($OfflineSelfTest){
 $a=[Array]::CreateInstance([object],3,10)
 $a.SetValue('2026/10/28',0,3)
 $a.SetValue('2026/10/29',1,3)
 $a.SetValue('2026/10/27',2,3)
 foreach($r in @(0,2)){foreach($j in 5..9){$a.SetValue([double]100,$r,$j)}}
 $s=Scan-Grid $a $asOf @('2026-10-28')
 Need ($s.validRows -eq 2 -and $s.validRequired -eq 1 -and
  $s.invalidFuture -eq 1 -and $s.invalidDate -eq 0) 'SCAN_SELFTEST'
 $a.SetValue('BAD',2,8);$s=Scan-Grid $a $asOf @('2026-10-28')
 Need ($s.invalidInWindowOrEarlier -eq 1) 'IN_WINDOW_SELFTEST'
 Write-Host 'NO11_RAW_CANARY_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_RAW_CANARY_EXCEL_TOUCHED=False'
 Write-Host 'NO11_RAW_CANARY_EXISTING_RECEIPTS_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$excel=$null;$book=$null;$sheets=@();$stage='LOCAL_SOURCES'
try{
 $current=[datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9))
 Need ($current.ToString('yyyy-MM-dd') -ceq $today) 'ONLY_GENUINE_OCT29_CANARY'
 [void](Get-Command node -ErrorAction Stop)
 if(-not $RunDir){
  $parent=Checked (Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\weekly-pool-refresh') $true
  $matches=@(Get-ChildItem -LiteralPath $parent -Directory -Filter 'weekly-refresh-2026-10-28-*')
  Need ($matches.Count -eq 1) 'RUN_NOT_UNIQUE'
  $RunDir=$matches[0].FullName
 }
 $run=Checked $RunDir $true
 $plan=Get-Content -LiteralPath (Checked (Join-Path $run 'plan.json')) -Raw -Encoding UTF8 | ConvertFrom-Json
 Need ($plan.schemaId -ceq 'ARK_NO11_RSS_DAILY_CENSUS_PLAN_V1' -and
  $plan.refreshSchemaId -ceq 'ARK_NO11_WEEKLY_G1_DAILY_REFRESH_PLAN_V1' -and
  $plan.asOfSession -ceq $asOf -and @($plan.symbols).Count -eq 429 -and
  @($plan.expectedSessions).Count -eq 76 -and
  $plan.productionReady -eq $false -and $plan.orderTransmission -eq $false) 'PLAN_NOT_OCT28_429'
 $files=@(Get-ChildItem -LiteralPath (Checked (Join-Path $run 'sources') $true) -File -Filter '*.json' | Sort-Object Name)
 Need ($files.Count -eq 429) 'CAPTURE_COUNT_NOT_429'
 $candidates=New-Object 'System.Collections.Generic.List[string]'
 foreach($f in $files){
  Need ($f.Name -cmatch '^([0-9A-Z]{4}\.T)-([a-f0-9]{64})\.json$') 'SOURCE_FILENAME'
  $s=[string]$Matches[1];$sha=[string]$Matches[2]
  Need ((Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $sha) 'SOURCE_SHA'
  $v=Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
  Need ($v.schemaId -ceq 'ARK_NO11_RSS_DAILY_CAPTURE_V1' -and
   $v.symbol -ceq $s -and $v.planId -ceq $plan.planId -and
   $v.asOfSession -ceq $asOf -and $v.orderTransmission -eq $false) 'SOURCE_SCOPE'
  if($v.status -ceq 'OBSERVED' -and $v.invalidRows -eq 1 -and
   @($v.rows).Count -eq 99){$candidates.Add($s)}
 }
 Need ($candidates.Count -eq 403) 'EXPECT_EXACT_403_WITH_ONE_INVALID'
 # Spread 5 canaries across the existing immutable 403-source collection.
 $idx=@(0,101,201,301,402)
 $symbols=@($idx|ForEach-Object {$candidates[$_]})
 Write-Host 'NO11_RAW_CANARY_SAVED_RECEIPTS=429|MALFORMED_SOURCE_ROWS=403|UNAVAILABLE=26'
 $stage='EXCEL_DISCOVERY'
 $busy=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop|
  Where-Object {$_.ProcessId -ne $PID -and [string]$_.CommandLine -match '(?i)(Run-No11WeeklyCandidateRefreshReadOnly|Capture-No11RssTrainingBatchReadOnly|Capture-No11SessionReferenceReadOnly|Run-No11Oct29ReferenceOneShotReadOnly)\.ps1'})
 Need ($busy.Count -eq 0) 'OTHER_COLLECTOR_RUNNING'
 $tcp=New-Object Net.Sockets.TcpClient;$ui=$false
 try{$tcp.Connect('127.0.0.1',8767);$ui=$tcp.Connected}catch [Net.Sockets.SocketException]{}finally{$tcp.Close()}
 Need (-not $ui) 'ARK_UI_MUST_BE_STOPPED'
 $processes=@(Get-Process EXCEL -ErrorAction SilentlyContinue|Where-Object {$_.MainWindowHandle -ne [IntPtr]::Zero})
 Need ($processes.Count -eq 1) 'EXCEL_NOT_UNIQUE'
 if(-not ('No11RawCanaryWindow' -as [type])){
  Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class No11RawCanaryWindow {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,Callback cb,IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h,StringBuilder b,int n);
 [DllImport("oleacc.dll")] public static extern int AccessibleObjectFromWindow(IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object o);
}
'@ -ErrorAction Stop
 }
 $script:children=@();$callback=[No11RawCanaryWindow+Callback]{param($h,$p)
  $n=New-Object Text.StringBuilder 128
  [void][No11RawCanaryWindow]::GetClassName($h,$n,128)
  if($n.ToString() -ceq 'EXCEL7'){$script:children+=@($h)}
  return $true
 }
 [void][No11RawCanaryWindow]::EnumChildWindows($processes[0].MainWindowHandle,$callback,[IntPtr]::Zero)
 Need ($script:children.Count -eq 1) 'EXCEL7_NOT_UNIQUE'
 $iid=[guid]'00020400-0000-0000-C000-000000000046';$obj=$null
 $hr=[No11RawCanaryWindow]::AccessibleObjectFromWindow($script:children[0],[uint32]4294967280,[ref]$iid,[ref]$obj)
 Need ($hr -eq 0 -and $null -ne $obj) 'EXCEL_COM_UNAVAILABLE'
 $excel=$obj.Application
 Need ($excel.Workbooks.Count -eq 2) 'TWO_ORIGINAL_WORKBOOKS_REQUIRED'
 $acc=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx')
 $market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')
 Need ($acc.Worksheets.Item('ARK_ACCOUNT_READONLY').Name -ceq 'ARK_ACCOUNT_READONLY' -and
  $market.Worksheets.Item('ARK_MARKET_READONLY').Name -ceq 'ARK_MARKET_READONLY') 'ORIGINAL_BOOK_NAMES'
 $stage='CHART_CAPACITY'
 $existing=0
 foreach($wb in @($acc,$market)){
  foreach($ws in $wb.Worksheets){
   $range=$ws.UsedRange
   Need ([long]$range.CountLarge -le 100000) 'FORMULA_SCAN_LIMIT'
   foreach($f in (Formulas $range.Formula)){
    if([string]$f -match '(?i)Rss(?:Chart|Trend)[A-Za-z]*\s*\('){$existing++}
   }
  }
 }
 Need ($existing+5+3 -le 50) 'CHART_CAPACITY'
 $stage='EXCEL_CANARY'
 $book=$excel.Workbooks.Add()
 $headers=@(
  (-join [char[]]@(0x9298,0x67c4,0x540d,0x79f0)),(-join [char[]]@(0x5e02,0x5834,0x540d,0x79f0)),
  (-join [char[]]@(0x8db3,0x7a2e)),(-join [char[]]@(0x65e5,0x4ed8)),(-join [char[]]@(0x6642,0x523b)),
  (-join [char[]]@(0x59cb,0x5024)),(-join [char[]]@(0x9ad8,0x5024)),(-join [char[]]@(0x5b89,0x5024)),
  (-join [char[]]@(0x7d42,0x5024)),(-join [char[]]@(0x51fa,0x6765,0x9ad8)))
 for($i=0;$i -lt $symbols.Count;$i++){
  $ws=$book.Worksheets.Add()
  $ws.Name='PROBE_'+$i
  for($j=0;$j -lt 10;$j++){$ws.Cells.Item(2,$j+1).Value2=$headers[$j]}
  $ws.Range('A1').Formula=('=RssChart($A$2:$J$2,"{0}","D",100)' -f $symbols[$i])
  $sheets+=@($ws)
 }
 Start-Sleep -Seconds $WarmupSeconds
 $result=[ordered]@{samples=5;full76=0;validRows=0;invalidFuture=0;invalidInWindowOrEarlier=0;invalidDate=0;validLater=0}
 for($i=0;$i -lt $sheets.Count;$i++){
  $ws=$sheets[$i]
  Need ([string]$ws.Range('A1').Formula -ceq ('=RssChart($A$2:$J$2,"{0}","D",100)' -f $symbols[$i])) 'FORMULA_CHANGED'
  $grid=$ws.Range('A3:J102').Value2
  $s=Scan-Grid $grid $asOf @($plan.expectedSessions)
  if($s.missingRequired -eq 0){$result.full76++}
  $result.validRows+=$s.validRows
  $result.invalidFuture+=$s.invalidFuture
  $result.invalidInWindowOrEarlier+=$s.invalidInWindowOrEarlier
  $result.invalidDate+=$s.invalidDate
  $result.validLater+=$s.validLater
 }
 Write-Host ('NO11_RAW_CANARY_SAMPLE_AGGREGATE='+($result|ConvertTo-Json -Compress))
 Write-Host 'NO11_RAW_CANARY_HISTORICAL_403_RECEIPTS=UNCHANGED_NOT_CERTIFIED'
 Write-Host 'NO11_RAW_CANARY_SHADOW=BLOCKED_PENDING_VERIFIED_SOURCE'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_RAW_CANARY_[A-Z0-9_]+$'){$reason='NO11_RAW_CANARY_LOCAL_EXCEL_OR_SOURCE_FAILURE'}
 Write-Host ('NO11_RAW_CANARY=BLOCKED|'+$reason)
 Write-Host ('NO11_RAW_CANARY_STAGE='+$stage)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if($null -ne $book){try{$book.Close($false)}catch{}}
 foreach($ws in $sheets){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($ws)}catch{}}
 if($null -ne $book){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book)}catch{}}
 if($null -ne $excel){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}catch{}}
}
