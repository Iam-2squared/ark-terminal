# Separate 2026-10-29 evidence-only D100 recovery of 2026-10-28 G1.
# ORIGINAL 429 receipt files are NEVER overwritten. New raw RSS D/100 source
# must independently pass all 76 target sessions and the original G1 inspector.
# Subsequent-day D100 rows (2026-10-29) are SKIPPED BEFORE numeric validation.
# No orders, no model edits, no backdated observation timestamps.
# Base: Git blob 9b2d6f4e5876c1692406f4a2dcff3000dbd515b3.
# Weekly-pool restricted DAILY RSS refresh. Original Excel books are never
# modified/saved. A complete pinned weekly all-universe scan is prerequisite.
# The old full-market source collector is unchanged; no orders or model fits.
param(
 [switch]$OfflineSelfTest,
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [string]$WeeklyRun,
 [string]$PrivateRoot,
 [string]$PinsFile,
 [string]$CatchUpAsOf='2026-10-28',
 [switch]$ConfirmYahooFridayRss,
 # Logical progress every 100 or 50 symbols. Physical RSS calls never exceed
 # the observed 50-function Excel cap, minus three reserved safety slots.
 [ValidateSet(50,100)][int]$GroupSize=100,
 [ValidateRange(1,47)][int]$BatchSize=15,
 [ValidateRange(5,60)][int]$WaitSeconds=35,
 [ValidateRange(0,5000)][int]$MaxSymbols=0
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$ci=[Globalization.CultureInfo]::InvariantCulture
# Unicode constructed at runtime so Windows PowerShell 5.1 also reads this UTF-8 file safely.
$headers=@(
 (-join [char[]]@(0x9298,0x67c4,0x540d,0x79f0)),(-join [char[]]@(0x5e02,0x5834,0x540d,0x79f0)),
 (-join [char[]]@(0x8db3,0x7a2e)),(-join [char[]]@(0x65e5,0x4ed8)),(-join [char[]]@(0x6642,0x523b)),
 (-join [char[]]@(0x59cb,0x5024)),(-join [char[]]@(0x9ad8,0x5024)),(-join [char[]]@(0x5b89,0x5024)),
 (-join [char[]]@(0x7d42,0x5024)),(-join [char[]]@(0x51fa,0x6765,0x9ad8))
)
function SafePhysicalBatch([int]$originalCharts,[int]$requested){
 if($originalCharts -lt 0 -or $originalCharts -gt 50 -or
    $requested -lt 1 -or $requested -gt 47){throw 'NO11_DAILY_CHART_BUDGET_ARGS_INVALID'}
 # Reserve three chart functions for unrelated, held and recovery use.
 # Each temporary workbook is closed before opening the next wave.
 $capacity=50-$originalCharts-3
 if($capacity -lt 1){throw 'NO11_DAILY_CHART_CAPACITY_EXHAUSTED'}
 return [Math]::Min($requested,$capacity)
}
function NextWaveEnd([int]$offset,[int]$remaining,[int]$groupSize,[int]$physical){
 if($offset -lt 0 -or $remaining -lt 1 -or $offset -ge $remaining -or
    $groupSize -notin @(50,100) -or $physical -lt 1 -or $physical -gt 47){
  throw 'NO11_DAILY_WAVE_ARGUMENT_INVALID'
 }
 $groupEnd=[int]([Math]::Floor($offset/$groupSize)+1)*$groupSize
 return [Math]::Min($remaining,[Math]::Min($offset+$physical,$groupEnd))
}
function New-DailyFormula([string]$symbol){
 if($symbol -cnotmatch '^[0-9A-Z]{4}\.T$'){throw 'NO11_DAILY_SYMBOL_INVALID'}
 return ('=RssChart($A$2:$J$2,"{0}","D",100)' -f $symbol)
}
function Now-Jst {return [datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz',$ci)}
function Number-Token([object]$value){
 if($value -isnot [double] -and $value -isnot [int] -and $value -isnot [long] -and $value -isnot [decimal]){return $null}
 $n=[double]$value
 if([double]::IsNaN($n) -or [double]::IsInfinity($n) -or $n -lt 0){return $null}
 # Explicitly Excel Value2 round-trip, not vendor decimal-token certification.
 return $n.ToString('R',$ci)
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
function Read-DailyRows([object]$values,[string]$asOf){
 $rows=New-Object System.Collections.ArrayList;$invalid=0
 if($values -is [array] -and $values.Rank -eq 2){
  $r0=$values.GetLowerBound(0);$c0=$values.GetLowerBound(1)
  for($r=$r0;$r -lt $r0+$values.GetLength(0);$r++){
   $dateValue=$values.GetValue($r,$c0+3)
   if($null -eq $dateValue -or [string]::IsNullOrWhiteSpace([string]$dateValue)){continue}
   $day=Date-Token $dateValue
   if($null -eq $day){$invalid++;continue}
   # Date is parsed BEFORE checking numerical values. A new current-session
   # candle is not part of the previous-session daily G1 source.
   if($day -cgt $asOf){continue}
   $p=@();for($j=5;$j -le 9;$j++){$p+=@(Number-Token $values.GetValue($r,$c0+$j))}
   if($p.Count -ne 5 -or @($p | Where-Object {$null -eq $_}).Count -gt 0){$invalid++;continue}
   [void]$rows.Add([ordered]@{session=$day;open=$p[0];high=$p[1];low=$p[2];close=$p[3];volume=$p[4]})
  }
 }
 return [pscustomobject]@{rows=@($rows.ToArray());invalidRows=$invalid}
}
function Save-Capture([string]$directory,[object]$payload){
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $payload -Depth 10 -Compress)+[char]10)
 $algorithm=[Security.Cryptography.SHA256]::Create()
 try{$sha=([BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}finally{$algorithm.Dispose()}
 $final=Join-Path $directory ($payload.symbol+'-'+$sha+'.json')
 $temp=Join-Path $directory ([guid]::NewGuid().ToString('N')+'.pending');$stream=$null
 try{
  $stream=[IO.File]::Open($temp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  $stream.Write($bytes,0,$bytes.Length);$stream.Flush($true);$stream.Dispose();$stream=$null
  [IO.File]::Move($temp,$final)
 }finally{if($null -ne $stream){$stream.Dispose()}}
}
if($OfflineSelfTest){
 if((New-DailyFormula '7203.T') -cne '=RssChart($A$2:$J$2,"7203.T","D",100)'){throw 'NO11_DAILY_FORMULA_SELFTEST'}
 $blocked=$false;try{[void](New-DailyFormula '7203.T");BAD(')}catch{$blocked=$true}
 if(-not $blocked){throw 'NO11_DAILY_FORMULA_INJECTION'}
 $a=[Array]::CreateInstance([object],1,10);$a.SetValue('2026/10/23',0,3)
 foreach($j in 5..8){$a.SetValue([double]101.5,0,$j)};$a.SetValue([double]200,0,9)
 $r=Read-DailyRows $a '2026-10-28'
 if($r.rows.Count -ne 1 -or $r.rows[0].close -cne '101.5' -or $r.rows[0].session -cne '2026-10-23'){throw 'NO11_DAILY_PARSE_SELFTEST'}
 $a.SetValue('BAD',0,8);$r=Read-DailyRows $a '2026-10-28'
 if($r.invalidRows -ne 1){throw 'NO11_DAILY_INVALID_SELFTEST'}
 # The same bad numeric data are not allowed to disqualify the preceding
 # as-of session if their date is in the NEXT cash session.
 $a.SetValue('2026/10/29',0,3)
 $r=Read-DailyRows $a '2026-10-28'
 if($r.invalidRows -ne 0 -or $r.rows.Count -ne 0){throw 'NO11_D100_NEXT_DAY_ROW_SKIPPED_SELFTEST'}
 $a.SetValue('2026/10/28',0,3)
 $r=Read-DailyRows $a '2026-10-28'
 if($r.invalidRows -ne 1){throw 'NO11_D100_PREVIOUS_DAY_MALFORMED_NOT_REJECTED_SELFTEST'}
 $a.SetValue('BAD_DATE',0,3)
 $r=Read-DailyRows $a '2026-10-28'
 if($r.invalidRows -ne 1){throw 'NO11_D100_INVALID_DATE_NOT_REJECTED_SELFTEST'}
 $a.SetValue('2026/10/23',0,3);$a.SetValue([double]101.5,0,8)
 if($null -ne (Date-Token '2026/02/30') -or $null -ne (Number-Token ([double]::NaN))){throw 'NO11_DAILY_TOKEN_SELFTEST'}
 if((SafePhysicalBatch 0 47) -ne 47 -or (SafePhysicalBatch 19 47) -ne 28 -or
    (SafePhysicalBatch 39 30) -ne 8 -or
    (NextWaveEnd 90 429 100 30) -ne 100 -or
    (NextWaveEnd 100 429 100 30) -ne 130 -or
    (NextWaveEnd 400 429 100 30) -ne 429){
  throw 'NO11_DAILY_GROUP_CAPACITY_SELFTEST_FAILED'
 }
 $selftestOffset=0;$selftestSizes=@()
 while($selftestOffset -lt 429){
  $finish=NextWaveEnd $selftestOffset 429 100 30
  if($finish -le $selftestOffset -or $finish-$selftestOffset -gt 30){
   throw 'NO11_DAILY_GROUP_COVERAGE_SELFTEST_FAILED'
  }
  $selftestSizes+=@($finish-$selftestOffset)
  $selftestOffset=$finish
 }
 if($selftestOffset -ne 429 -or ($selftestSizes|Measure-Object -Sum).Sum -ne 429){
  throw 'NO11_DAILY_GROUP_COVERAGE_SELFTEST_FAILED'
 }
 Write-Host 'NO11_D100_RECOVERY_DATE_AWARE_SELFTEST=PASS'
 Write-Host 'NO11_D100_RECOVERY_ORIGINAL_RECEIPTS_MODIFIED=False'
 Write-Host 'NO11_DAILY_AUTO_100_GROUP_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_DAILY_OFFLINE_SELFTEST=PASS';Write-Host 'ORDER_TRANSMISSION=False';exit 0
}
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_D100_RECOVERY_'+$code)}}
$today=[datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9))
Need ($today.ToString('yyyy-MM-dd') -ceq '2026-10-29' -and
 $today.ToString('HH:mm') -cge '08:30' -and
 $today.ToString('HH:mm') -clt '18:00') 'ONLY_GENUINE_OCT29_DAYTIME'
Need ($CatchUpAsOf -ceq '2026-10-28') 'HISTORICAL_TARGET_LOCKED'
Need ([IO.Path]::IsPathRooted($EngineRoot)) 'ENGINE_ABSOLUTE_REQUIRED'
$tool=Join-Path $EngineRoot 'tools\no11_weekly_g1_refresh.mjs'
Need (Test-Path -LiteralPath $tool -PathType Leaf) 'ORIGINAL_TOOL_NOT_FOUND'
[void](Get-Command git -ErrorAction Stop)
$blob=@(& git hash-object --no-filters $tool)
Need ($LASTEXITCODE -eq 0 -and $blob.Count -eq 1 -and
  [string]$blob[0] -cin @('26cb29af530e5b7a0f736c728fd96e156d3e840a',
   '577882a0aa18c747734b905316a1bbbbeff1145e')) 'ORIGINAL_TOOL_VERSION_NOT_PINNED'
if(-not (Test-Path -LiteralPath $tool -PathType Leaf)){throw 'NO11_DAILY_TOOL_MISSING'}
[void](Get-Command node -ErrorAction Stop)
if([string]::IsNullOrWhiteSpace($WeeklyRun) -or -not [IO.Path]::IsPathRooted($WeeklyRun) -or
  -not (Test-Path -LiteralPath $WeeklyRun -PathType Container)){
 throw 'NO11_WEEKLY_FULL_SCAN_RUN_REQUIRED'
}
$isolated=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\d100-recovery-2026-10-29'
if([string]::IsNullOrWhiteSpace($PrivateRoot)){$PrivateRoot=$isolated}
Need ([IO.Path]::GetFullPath($PrivateRoot).Equals([IO.Path]::GetFullPath($isolated),
 [StringComparison]::OrdinalIgnoreCase)) 'REFUSE_ORIGINAL_429_DATA_ROOT'
$originalRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\weekly-pool-refresh'
Need (Test-Path -LiteralPath $originalRoot -PathType Container) 'ORIGINAL_429_ROOT_NOT_FOUND'
if(-not [string]::IsNullOrWhiteSpace($PinsFile) -and
  (-not [IO.Path]::IsPathRooted($PinsFile) -or
   -not (Test-Path -LiteralPath $PinsFile -PathType Leaf))){
 throw 'NO11_WEEKLY_PINS_FILE_INVALID'
}
# Prove all original 429 receipts still have their original immutable hashes and
# plan lineage; do not call report, write mask or touch original capture sources.
$originalPlanArgs=@('plan','--weekly-run',$WeeklyRun,'--root',$originalRoot,
 '--catch-up-asof',$CatchUpAsOf)
# Never race any concurrent Excel RSS collector.
$active=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop |
 Where-Object {$_.ProcessId -ne $PID -and
  [string]$_.CommandLine -match '(?i)(Run-No11WeeklyCandidateRefreshReadOnly|Run-No11Oct29D100RecoveryReadOnly|Capture-No11RssTrainingBatchReadOnly|Capture-No11SessionReferenceReadOnly|Run-No11Oct29ReferenceOneShotReadOnly|Prepare-No11PreviousArchiveReadOnly)\.ps1'})
Need ($active.Count -eq 0) 'ANOTHER_RSS_COLLECTOR_RUNNING'
$originalText=@(& node $tool @originalPlanArgs)
Need ($LASTEXITCODE -eq 0 -and $originalText.Count -eq 1) 'ORIGINAL_429_VERIFICATION_FAILED'
$originalState=([string]$originalText[0]|ConvertFrom-Json)
Need ($originalState.resumed -eq 429 -and
 @($originalState.remaining).Count -eq 0 -and
 @($originalState.plan.symbols).Count -eq 429 -and
 $originalState.plan.asOfSession -ceq $CatchUpAsOf) 'ORIGINAL_429_INCOMPLETE'
Write-Host 'NO11_D100_RECOVERY_ORIGINAL_429=HASH_AND_LINEAGE_VERIFIED_NO_WRITES'

function Get-Plan {
 $planArgs=@('plan','--weekly-run',$WeeklyRun,'--root',$PrivateRoot)
 if(-not [string]::IsNullOrWhiteSpace($CatchUpAsOf)){
  if($CatchUpAsOf -cnotmatch '^20\d{2}-\d{2}-\d{2}$'){throw 'NO11_DAILY_CATCHUP_DAY_INVALID'}
  $planArgs+=@('--catch-up-asof',$CatchUpAsOf)
 }
 if($ConfirmYahooFridayRss){$planArgs+=@('--yahoo-friday-rss-confirm','true')}
 $text=(& node $tool @planArgs | Out-String)
 if($LASTEXITCODE -ne 0){throw 'NO11_WEEKLY_REFRESH_PLAN_FAILED'}
 return ($text | ConvertFrom-Json)
}
$work=Get-Plan;$run=$work.run;$lock=$null;$excel=$null;$book=$null;$sheets=@();$failed=$false;$stage='LOCK'
try{
 # File sharing lock is released by the OS after a crash; no stale PID bypass needed.
 $lock=[IO.File]::Open((Join-Path $run 'capture.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 $work=Get-Plan
 if($work.run -cne $run){throw 'NO11_DAILY_TARGET_CHANGED_RESTART'}
 $remaining=@($work.remaining);if($MaxSymbols -gt 0){$remaining=@($remaining | Select-Object -First $MaxSymbols)}
 Write-Host ('NO11_DAILY_TARGET='+$work.plan.asOfSession)
 Write-Host ('NO11_DAILY_RESUME_VERIFIED='+$work.resumed+'/'+$work.plan.symbols.Count)
 if($remaining.Count -gt 0){
  $tcp=New-Object Net.Sockets.TcpClient;$active=$false
  try{$tcp.Connect('127.0.0.1',8767);$active=$tcp.Connected}catch [Net.Sockets.SocketException]{}finally{$tcp.Close()}
  if($active){throw 'NO11_DAILY_ARK_UI_MUST_BE_STOPPED'}
  $stage='EXCEL_WINDOW'
  # Excel changes MainWindowTitle when the active workbook switches.
  # Prefer one uniquely Ark-labelled visible process, or fall back to the
  # single visible Excel process. Original workbook/sheet COM checks remain
  # mandatory before creating a temporary book.
  $visible=@(Get-Process EXCEL -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne [IntPtr]::Zero})
  $arkNamed=@($visible | Where-Object {$_.MainWindowTitle -like 'Ark_No11_*'})
  $processes=@()
  if($arkNamed.Count -eq 1){$processes=@($arkNamed)}
  elseif($arkNamed.Count -eq 0 -and $visible.Count -eq 1){$processes=@($visible)}
  Write-Host ('NO11_DAILY_EXCEL_DISCOVERY=VISIBLE_{0}|ARK_NAMED_{1}|SELECTED_{2}' -f $visible.Count,$arkNamed.Count,$processes.Count)
  if($processes.Count -ne 1){throw 'NO11_DAILY_EXCEL_IDENTITY_NOT_UNIQUE'}
  if(-not ('No11DailyWindow' -as [type])){
   Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class No11DailyWindow {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,Callback cb,IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h,StringBuilder b,int n);
 [DllImport("oleacc.dll")] public static extern int AccessibleObjectFromWindow(IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object o);
}
'@ -ErrorAction Stop
  }
  $script:dailyWindows=@();$callback=[No11DailyWindow+Callback]{param($h,$p) $n=New-Object Text.StringBuilder 128;[void][No11DailyWindow]::GetClassName($h,$n,128);if($n.ToString() -ceq 'EXCEL7'){$script:dailyWindows+=@($h)};return $true}
  [void][No11DailyWindow]::EnumChildWindows($processes[0].MainWindowHandle,$callback,[IntPtr]::Zero)
  if($script:dailyWindows.Count -ne 1){throw 'NO11_DAILY_EXCEL7_NOT_UNIQUE'}
  $iid=[guid]'00020400-0000-0000-C000-000000000046';$obj=$null
  $hr=[No11DailyWindow]::AccessibleObjectFromWindow($script:dailyWindows[0],[uint32]4294967280,[ref]$iid,[ref]$obj)
  if($hr -ne 0 -or $null -eq $obj){throw 'NO11_DAILY_COM_ATTACH_FAILED'}
  $excel=$obj.Application
  if($excel.Workbooks.Count -ne 2){throw 'NO11_DAILY_ONLY_TWO_ORIGINAL_WORKBOOKS_REQUIRED'}
  $account=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx');$market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')
  if($account.Worksheets.Item('ARK_ACCOUNT_READONLY').Name -cne 'ARK_ACCOUNT_READONLY' -or $market.Worksheets.Item('ARK_MARKET_READONLY').Name -cne 'ARK_MARKET_READONLY'){throw 'NO11_DAILY_WORKBOOK_IDENTITY_INVALID'}
  $stage='CAPACITY';$existing=0
  foreach($wb in @($account,$market)){
   for($i=1;$i -le $wb.Worksheets.Count;$i++){
    $used=$wb.Worksheets.Item($i).UsedRange
    if([long]$used.CountLarge -gt 100000){throw 'NO11_DAILY_CAPACITY_SCAN_TOO_LARGE'}
    $cells=$null
    try{$cells=$used.SpecialCells(-4123)}catch [Runtime.InteropServices.COMException]{if($_.Exception.HResult -ne -2146827284){throw}}
    if($null -ne $cells){foreach($cell in $cells.Cells){if([string]$cell.Formula -match '(?i)Rss(?:Chart|Trend)[A-Za-z]*\s*\('){$existing++}}}
   }
  }
  $physical=SafePhysicalBatch $existing $BatchSize
  $verifiedNew=0
  $ceiling=$physical;$fullWaves=0
  Write-Host ('NO11_DAILY_BATCH_POLICY=GROUP_{0}|PHYSICAL_MAX_{1}|ORIGINAL_CHARTS_{2}|RESERVE_3|LIMIT_50' -f $GroupSize,$ceiling,$existing)
  for($offset=0;$offset -lt $remaining.Count;){
   $waveEnd=NextWaveEnd $offset $remaining.Count $GroupSize $physical
   $batch=@($remaining[$offset..($waveEnd-1)]);$sheets=@();$stage='TEMPORARY_WORKBOOK'
   $book=$excel.Workbooks.Add()
   foreach($symbol in $batch){
    $ws=$book.Worksheets.Add();$ws.Name='DAILY_'+$symbol.Replace('.','_')
    for($j=0;$j -lt 10;$j++){$ws.Cells.Item(2,$j+1).Value2=$headers[$j]}
    $ws.Range('A1').Formula=(New-DailyFormula $symbol);$sheets+=@($ws)
   }
   $stage='WAIT_FOR_RSS';Start-Sleep -Seconds $WaitSeconds
   $emptyRetry=0
   do{
    $payloads=New-Object System.Collections.ArrayList;$usable=0;$complete=0;$stage='DAILY_CAPTURE'
    $eligible=New-Object 'System.Collections.Generic.HashSet[string]'
   for($k=0;$k -lt $batch.Count;$k++){
    $symbol=$batch[$k];$ws=$sheets[$k];$formula=New-DailyFormula $symbol
    if([string]$ws.Range('A1').Formula -cne $formula){throw 'NO11_DAILY_FORMULA_CHANGED'}
    $start=Now-Jst;$values=$ws.Range('A3:J102').Value2;$end=Now-Jst;$parsed=Read-DailyRows $values ([string]$work.plan.asOfSession)
    $status=if($parsed.rows.Count -gt 0){'OBSERVED'}else{'UNAVAILABLE'}
    $dates=@($parsed.rows | ForEach-Object {$_.session})
    $has76=(@($work.plan.expectedSessions | Where-Object {$_ -notin $dates}).Count -eq 0)
    if($parsed.rows.Count -gt 0 -and $parsed.invalidRows -eq 0 -and $has76){
     $usable++;$complete++;[void]$eligible.Add($symbol)
    }
    [void]$payloads.Add([ordered]@{
     schemaId='ARK_NO11_RSS_DAILY_CAPTURE_V1';planId=$work.plan.planId;symbol=$symbol;asOfSession=$work.plan.asOfSession;
     period='D';formula=$formula;status=$status;observedStartJst=$start;observedEndJst=$end;
     rows=$parsed.rows;invalidRows=$parsed.invalidRows;priceBasis='RSS_CHART_UNVERIFIED';
     decimalProvenance='EXCEL_VALUE2_ROUNDTRIP';corporateActionsCleared=$false;originalVendorDecimalCertified=$false;
     productionReady=$false;orderTransmission=$false
    })
   }
    if($usable -gt 0 -or $emptyRetry -ge 2){break}
    $emptyRetry++
    $extraWait=[Math]::Min(60,$WaitSeconds*(1+$emptyRetry))
    Write-Host ('NO11_DAILY_EMPTY_WAVE_RETRY={0}/2|WAIT_SECONDS={1}|PERSISTED=False' -f $emptyRetry,$extraWait)
    $stage='WAIT_FOR_RSS';Start-Sleep -Seconds $extraWait
   }while($true)
   # Never checkpoint an entirely empty wave, even after retries.
   if($usable -eq 0){throw 'NO11_DAILY_ALL_EMPTY_WAVE_RETRY_AFTER_RECONNECT'}
   # Persist ONLY independently re-received fully valid 76-session sources.
   # The 26 old unavailable receipts and any new invalid ones never become
   # completed source receipts; an interrupted invocation is safely resumable.
   foreach($payload in $payloads){
    if($eligible.Contains([string]$payload.symbol)){
     Save-Capture (Join-Path $run 'sources') $payload
     $verifiedNew++
    }
   }
   Write-Host ('NO11_D100_RECOVERY_VERIFIED={0}/429|THIS_RUN_NEW={1}' -f ($work.resumed+$verifiedNew),$verifiedNew)
   $book.Close($false);foreach($ws in $sheets){[void][Runtime.InteropServices.Marshal]::ReleaseComObject($ws)}
   $sheets=@();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book);$book=$null
   Write-Host ('NO11_DAILY_PROGRESS={0}/{1}|WAVE_OBSERVED={2}|WAVE_FULL76={3}' -f ($work.resumed+$waveEnd),$work.plan.symbols.Count,$usable,$complete)
   # Canary runs automatically; avoid collecting thousands of unusable snapshots.
   if($complete -eq 0){throw 'NO11_DAILY_NO_FULL_HISTORY_IN_WAVE_REVIEW_PARTIAL_REPORT'}
   $offset=$waveEnd
   # An RSS partial wave is an observed source gap, NOT a success for its
   # missing symbols. Reduce concurrency for subsequent waves; ramp back up
   # only after repeated fully observed waves.
   if($usable -lt $batch.Count){
    $fullWaves=0
    $physical=[Math]::Max(1,[int][Math]::Floor($physical/2))
    Write-Host ('NO11_DAILY_BATCH_TUNE=PARTIAL_REDUCED_TO_{0}|MISSING_NOT_G1_PASS' -f $physical)
   }elseif($physical -lt $ceiling){
    $fullWaves++
    if($fullWaves -ge 2){
     $physical=[Math]::Min($ceiling,$physical+5)
     $fullWaves=0
     Write-Host ('NO11_DAILY_BATCH_TUNE=FULL_WAVES_RAISED_TO_{0}' -f $physical)
    }
   }
   if($offset -eq $remaining.Count -or $offset % $GroupSize -eq 0){
    Write-Host ('NO11_DAILY_GROUP_COMPLETE={0}/{1}|GROUP_SIZE={2}|NEXT_WAVE_AUTO=True' -f ($work.resumed+$offset),$work.plan.symbols.Count,$GroupSize)
   }
  }
 }
}catch{
 $failed=$true;$reason=$_.Exception.Message
 if($reason -notmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_DAILY_COM_OR_IO_FAILURE'}
 Write-Host ('NO11_DAILY_CAPTURE=BLOCKED|'+$reason);Write-Host ('NO11_DAILY_STAGE='+$stage)
 Write-Host ('NO11_DAILY_HRESULT='+$_.Exception.HResult)
}finally{
 if($null -ne $book){try{$book.Close($false)}catch{}}
 foreach($ws in $sheets){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($ws)}catch{}}
 if($null -ne $book){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book)}catch{}}
 if($null -ne $excel){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}catch{}}
 if($null -ne $lock){$lock.Dispose()}
}
$final=Get-Plan
if($final.resumed -ne 429 -or @($final.remaining).Count -ne 0){
 Write-Host ('NO11_D100_RECOVERY=PARTIAL_VERIFIED|RECEIPTS='+$final.resumed+'/429')
 Write-Host 'NO11_D100_RECOVERY_ORIGINAL_429_RECEIPTS=UNTOUCHED'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
Write-Host 'NO11_D100_RECOVERY_FULL_SOURCE=429/429_REOBSERVED_DATE_AWARE'
$reportArgs=@('report','--run',$run,'--weekly-run',$WeeklyRun)
if(-not [string]::IsNullOrWhiteSpace($CatchUpAsOf)){
 $reportArgs+=@('--catch-up-asof',$CatchUpAsOf)
}
if($ConfirmYahooFridayRss){$reportArgs+=@('--yahoo-friday-rss-confirm','true')}
if(-not [string]::IsNullOrWhiteSpace($PinsFile)){$reportArgs+=@('--pins-file',$PinsFile)}
$output=@(& node $tool @reportArgs)
$reportExit=$LASTEXITCODE
$output|ForEach-Object {Write-Host $_}
if($failed -or $reportExit -ne 0){exit 2}
if(-not [string]::IsNullOrWhiteSpace($CatchUpAsOf)){
 Write-Host 'NO11_WEEKLY_DAILY_CAPTURE=HISTORICAL_ASOF_WITH_REAL_CURRENT_RECEIPT'
}
Write-Host 'NO11_D100_RECOVERY=COMPLETE_ISOLATED_429_REOBSERVED'
Write-Host 'NO11_D100_RECOVERY_ORIGINAL_429_RECEIPTS=UNTOUCHED'
Write-Host 'NO11_WEEKLY_DAILY_REFRESH=COMPLETE_NOT_FULL_UNIVERSE'
Write-Host 'ORDER_TRANSMISSION=False'
exit 0
