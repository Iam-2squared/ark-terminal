# Selected-symbol session reference only. One unsaved temporary book; no orders.
param([string]$SymbolsFile,[string]$ChartPlanFile,[string]$OutputRoot,
 [ValidateRange(5,60)][int]$WarmupSeconds=20,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$ci=[Globalization.CultureInfo]::InvariantCulture
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$fields=@('銘柄コード','市場コード','現在日付','前日日付','前日終値','当日基準値','市場部名称','単位株数','権利落日','配当落日','中配落日')
function Need([bool]$x,[string]$c){if(-not $x){throw ('NO11_REFERENCE_'+$c)}}
function Formula([string]$s,[string]$f){
 Need ($s -cmatch '^[0-9A-Z]{4}\.T$' -and $f -cin $fields) 'FORMULA_INVALID'
 return '=RssMarket("'+$s+'","'+$f+'")'
}
function DateValue($v){
 if($null -eq $v){return $null}
 if($v -is [datetime]){return $v.ToString('yyyy-MM-dd',$ci)}
 if($v -is [ValueType]){
  $n=[double]$v;if($n -ge 30000 -and $n -le 80000){return [datetime]::FromOADate($n).ToString('yyyy-MM-dd',$ci)}
  return $null
 }
 $d=[datetime]::MinValue
 if([datetime]::TryParseExact(([string]$v).Replace('/','-'),'yyyy-MM-dd',$ci,[Globalization.DateTimeStyles]::None,[ref]$d)){
  return $d.ToString('yyyy-MM-dd',$ci)
 }
 return $null
}
function NumberValue($v){
 if($null -eq $v -or $v -isnot [ValueType]){return $null}
 $n=[double]$v;if([double]::IsNaN($n) -or [double]::IsInfinity($n)){return $null};return $n
}
function Stamp{return [datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz',$ci)}
if($OfflineSelfTest){
 Need ((Formula '7203.T' '前日終値') -ceq '=RssMarket("7203.T","前日終値")') 'SELFTEST_FORMULA'
 Need ((DateValue '2026/10/23') -ceq '2026-10-23') 'SELFTEST_DATE'
 $reject=$false;try{Formula '7203.T")' '前日終値'|Out-Null}catch{$reject=$true}
 Need $reject 'SELFTEST_INJECTION'
 Write-Host 'NO11_REFERENCE_OFFLINE_SELFTEST=PASS';Write-Host 'ORDER_TRANSMISSION=False';exit 0
}
$excel=$null;$book=$null;$sheet=$null;$failed=$false
try{
 foreach($file in @($SymbolsFile,$ChartPlanFile)){
  Need ([IO.Path]::IsPathRooted($file) -and (Test-Path -LiteralPath $file -PathType Leaf)) 'SOURCE_FILE_REQUIRED'
  Need ((Get-Item -LiteralPath $file).Length -lt 1000000) 'SOURCE_TOO_LARGE'
 }
 Need ([IO.Path]::IsPathRooted($OutputRoot) -and (Test-Path -LiteralPath $OutputRoot -PathType Container)) 'OUTPUT_ROOT_REQUIRED'
 $root=[IO.Path]::GetFullPath($OutputRoot)
 Need (-not ($root.Equals($repo,[StringComparison]::OrdinalIgnoreCase) -or $root.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase))) 'OUTPUT_MUST_BE_PRIVATE'
 $cursor=$root
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  Need (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'OUTPUT_REPARSE'
  $next=Split-Path -Parent $cursor;if($next -ceq $cursor){break};$cursor=$next
 }
 $symbols=@(Get-Content -LiteralPath $SymbolsFile -Encoding UTF8 | Where-Object {-not [string]::IsNullOrWhiteSpace($_)})
 Need ($symbols.Count -ge 1 -and $symbols.Count -le 50 -and @($symbols|Select-Object -Unique).Count -eq $symbols.Count) 'SYMBOL_COUNT'
 $receipt=Get-Content -LiteralPath $ChartPlanFile -Raw -Encoding UTF8|ConvertFrom-Json
 $plan=$receipt.chartPlan;$session=(Stamp).Substring(0,10)
 Need ($receipt.schemaId -ceq 'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1' -and
   $plan.sessionDate -ceq $session -and $plan.productionReady -eq $false -and $plan.orderTransmission -eq $false) 'PLAN_SESSION'
 Need (($symbols -join '|') -ceq (@($plan.selectorInputSymbols) -join '|')) 'SELECTED_SCOPE_DIFFERS'
 foreach($symbol in $symbols){Need ($symbol -cmatch '^[0-9A-Z]{4}\.T$') 'SYMBOL_INVALID'}
 # Bind the single visible original Excel window. Avoid an ambiguous/stale ROT
 # GetActiveObject pointer, which cannot identify the intended physical window.
 $visible=@(Get-Process EXCEL -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne [IntPtr]::Zero})
 $ark=@($visible | Where-Object {$_.MainWindowTitle -like 'Ark_No11_*'})
 $selected=@()
 if($ark.Count -eq 1){$selected=@($ark)}
 elseif($ark.Count -eq 0 -and $visible.Count -eq 1){$selected=@($visible)}
 Need ($selected.Count -eq 1) 'EXCEL_WINDOW_NOT_UNIQUE'
 if(-not ('No11ReferenceWindow' -as [type])){
  Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class No11ReferenceWindow {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,Callback cb,IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h,StringBuilder b,int n);
 [DllImport("oleacc.dll")] public static extern int AccessibleObjectFromWindow(IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object o);
}
'@ -ErrorAction Stop
 }
 $script:referenceWindows=@()
 $callback=[No11ReferenceWindow+Callback]{
  param($h,$p)
  $buffer=New-Object Text.StringBuilder 128
  [void][No11ReferenceWindow]::GetClassName($h,$buffer,128)
  if($buffer.ToString() -ceq 'EXCEL7'){$script:referenceWindows+=@($h)}
  return $true
 }
 [void][No11ReferenceWindow]::EnumChildWindows($selected[0].MainWindowHandle,$callback,[IntPtr]::Zero)
 Need ($script:referenceWindows.Count -eq 1) 'EXCEL7_NOT_UNIQUE'
 $iid=[guid]'00020400-0000-0000-C000-000000000046'
 $windowObject=$null
 $hresult=[No11ReferenceWindow]::AccessibleObjectFromWindow(
  $script:referenceWindows[0],[uint32]4294967280,[ref]$iid,[ref]$windowObject)
 Need ($hresult -eq 0 -and $null -ne $windowObject) 'EXCEL_WINDOW_COM_ATTACH_FAILED'
 $excel=$windowObject.Application
 Need ($excel.Workbooks.Count -eq 2) 'TWO_ORIGINAL_BOOKS_REQUIRED'
 $account=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx')
 $market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')
 Need ($account.Worksheets.Item('ARK_ACCOUNT_READONLY').Name -ceq 'ARK_ACCOUNT_READONLY' -and
       $market.Worksheets.Item('ARK_MARKET_READONLY').Name -ceq 'ARK_MARKET_READONLY') 'ORIGINAL_BOOK_IDENTITY'
 $existing=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
 $unknown=0
 foreach($wb in @($account,$market)){foreach($ws in $wb.Worksheets){
  Need ([long]$ws.UsedRange.CountLarge -le 100000) 'FORMULA_SCAN_LIMIT'
  $cells=$null;try{$cells=$ws.UsedRange.SpecialCells(-4123)}catch [Runtime.InteropServices.COMException]{
   if($_.Exception.HResult -ne -2146827284){throw}
  }
  if($null -ne $cells){foreach($cell in $cells.Cells){
   $f=[string]$cell.Formula
   if($f -match '(?i)RssMarket\s*\('){
    if($f -match '(?i)RssMarket\s*\(\s*"([0-9A-Z]{4}\.T)"\s*,'){[void]$existing.Add($Matches[1])}else{$unknown++}
   }
  }}
 }}
 foreach($symbol in $symbols){[void]$existing.Add($symbol)}
 Need ($existing.Count+$unknown -le 500) 'MARKET_CAPACITY_EXCEEDED'
 $book=$excel.Workbooks.Add();$sheet=$book.Worksheets.Item(1)
 $grid=[array]::CreateInstance([object],$symbols.Count,12)
 for($i=0;$i -lt $symbols.Count;$i++){
  $grid.SetValue($symbols[$i],$i,0)
  for($j=0;$j -lt $fields.Count;$j++){$grid.SetValue((Formula $symbols[$i] $fields[$j]),$i,$j+1)}
 }
 $range='A1:L'+$symbols.Count
 $sheet.Range($range).Formula=$grid
 Start-Sleep -Seconds $WarmupSeconds
 $start=Stamp;$values=$sheet.Range($range).Value2;$end=Stamp
 Need ($values -is [array] -and $values.Rank -eq 2 -and $values.GetLength(0) -eq $symbols.Count -and $values.GetLength(1) -eq 12) 'READ_SHAPE'
 $rows=@();$r0=$values.GetLowerBound(0);$c0=$values.GetLowerBound(1)
 for($i=0;$i -lt $symbols.Count;$i++){
  $r=$r0+$i
  Need ([string]$values.GetValue($r,$c0) -ceq $symbols[$i]) 'REQUEST_SYMBOL_CHANGED'
  $vendor=([string]$values.GetValue($r,$c0+1)).Trim()
  Need ($vendor -ceq $symbols[$i].Substring(0,4)) 'VENDOR_SYMBOL_MISMATCH'
  $rows+=@([ordered]@{symbol=$symbols[$i];marketCode=([string]$values.GetValue($r,$c0+2)).Trim();
   marketDate=(DateValue $values.GetValue($r,$c0+3));previousDate=(DateValue $values.GetValue($r,$c0+4));
   previousClose=(NumberValue $values.GetValue($r,$c0+5));dayBasePrice=(NumberValue $values.GetValue($r,$c0+6));
   marketSection=([string]$values.GetValue($r,$c0+7)).Trim();lotShares=(NumberValue $values.GetValue($r,$c0+8));
   exRightsDateRaw=[string]$values.GetValue($r,$c0+9);exDividendDateRaw=[string]$values.GetValue($r,$c0+10);
   interimExDividendDateRaw=[string]$values.GetValue($r,$c0+11)})
 }
 $obj=[ordered]@{schemaId='ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1';sessionDate=$session;
  source='RssMarket_SELECTED_REFERENCE_READONLY';capturedAtJst=$start;completedAtJst=$end;
  chartPlanSha256=$plan.planSha256;selectedSymbols=@($symbols);rows=@($rows);
  corporateActionReviewPerformed=$false;readOnly=$true;productionReady=$false;orderTransmission=$false}
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $obj -Depth 10 -Compress)+[char]10)
 $hash=[Security.Cryptography.SHA256]::Create()
 try{$sha=([BitConverter]::ToString($hash.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}finally{$hash.Dispose()}
 $file=Join-Path $root ('session-reference-'+$sha+'.json')
 $stream=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 Write-Host ('NO11_SESSION_REFERENCE_FILE='+$file)
 Write-Host ('NO11_SESSION_REFERENCE_ROWS='+$rows.Count)
}catch{$failed=$true;Write-Host 'NO11_SESSION_REFERENCE=BLOCKED'}finally{
 if($null -ne $book){try{$book.Close($false)}catch{$failed=$true}}
 foreach($o in @($sheet,$book,$excel)){if($null -ne $o -and [Runtime.InteropServices.Marshal]::IsComObject($o)){
  try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($o)}catch{}
 }}
 Write-Host 'ORDER_TRANSMISSION=False'
}
if($failed){exit 2}
exit 0
