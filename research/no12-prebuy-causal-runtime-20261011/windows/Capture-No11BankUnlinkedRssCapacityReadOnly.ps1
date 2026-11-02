# Exact Ark account RSS RssCapacityList observation. No workbook edits,
# formulas, order calls, bank/account mutations or brokerage connections.
# The operator explicitly attests that no bank link/autosweep exists.
# IMPORTANT: RSS buying power is NOT proof of a cash balance; no LIVE permit.
param(
 [switch]$OfflineSelfTest,
 [switch]$IConfirmNoBankLink,
 [switch]$IConfirmAutoSweepOff,
 [ValidateSet('一般')][string]$Account='一般',
 [string]$OutputRoot=''
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$script:stage='INIT'
function Need([bool]$test,[string]$reason){
 if(-not $test){throw ('NO11_RSS_CAPACITY_'+$reason)}
}
function Stamp {
 return [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString(
 'yyyy-MM-ddTHH:mm:ss.fffzzz',[Globalization.CultureInfo]::InvariantCulture)
}
function PlainInteger($v) {
 if($null -eq $v -or $v -is [bool]) {throw 'NO11_RSS_CAPACITY_AMOUNT_UNAVAILABLE'}
 if($v -is [ValueType]) {
  $n=[decimal]::Parse([string]$v,[Globalization.CultureInfo]::InvariantCulture)
 }else{
  $text=([string]$v).Trim().Replace(',','').Replace('￥','').Replace('¥','')
  Need ($text -cmatch '^(?:0|[1-9][0-9]{0,13})$') 'AMOUNT_FORMAT'
  $n=[decimal]::Parse($text,[Globalization.CultureInfo]::InvariantCulture)
 }
 Need ($n -ge 0 -and $n -lt 100000000000000 -and $n -eq [decimal]::Truncate($n)) 'AMOUNT_NOT_INTEGER'
 return $n.ToString('0',[Globalization.CultureInfo]::InvariantCulture)
}
function JsonString([string]$value) {
 $b=New-Object System.Text.StringBuilder
 [void]$b.Append([char]34)
 foreach($c in $value.ToCharArray()){
  $k=[int]$c
  if($k -eq 34){[void]$b.Append('\"')}
  elseif($k -eq 92){[void]$b.Append('\\')}
  elseif($k -eq 8){[void]$b.Append('\b')}
  elseif($k -eq 9){[void]$b.Append('\t')}
  elseif($k -eq 10){[void]$b.Append('\n')}
  elseif($k -eq 12){[void]$b.Append('\f')}
  elseif($k -eq 13){[void]$b.Append('\r')}
  elseif($k -lt 32){[void]$b.Append(('\u'+$k.ToString('x4')))}
  else{[void]$b.Append($c)}
 }
 [void]$b.Append([char]34)
 return $b.ToString()
}
function Hash([byte[]]$b) {
 $h=[Security.Cryptography.SHA256]::Create()
 try{return ([BitConverter]::ToString($h.ComputeHash($b))).Replace('-','').ToLowerInvariant()}
 finally{$h.Dispose()}
}
if($OfflineSelfTest){
 Need ((PlainInteger 0) -ceq '0' -and
       (PlainInteger 150000.0) -ceq '150000' -and
       (PlainInteger '1,000') -ceq '1000') 'SELFTEST_NUMERIC'
 $reject=$false;try{PlainInteger 'N/A'|Out-Null}catch{$reject=$true}
 Need $reject 'SELFTEST_REJECT_NA'
 $probe=('a"'+[char]10+'東証\')
 $roundtrip=('{"test":'+(JsonString $probe)+'}'|ConvertFrom-Json)
 Need ($roundtrip.test -ceq $probe) 'SELFTEST_JSON'
 Write-Host 'NO11_RSS_CAPACITY_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$excel=$null;$account=$null;$sheet=$null;$failed=$false
try{
 $script:stage='OPERATOR_SCOPE'
 Need ($IConfirmNoBankLink.IsPresent -and $IConfirmAutoSweepOff.IsPresent) 'UNLINKED_BANK_AND_OFF_SWEEP_ATTESTATION_REQUIRED'
 Need ([string]::IsNullOrWhiteSpace($OutputRoot) -eq $false) 'PRIVATE_ROOT_REQUIRED'
 Need ([IO.Path]::IsPathRooted($OutputRoot) -and (Test-Path -LiteralPath $OutputRoot -PathType Container)) 'PRIVATE_ROOT_NOT_FOUND'
 $root=[IO.Path]::GetFullPath($OutputRoot)
 $cursor=$root
 while(-not [string]::IsNullOrWhiteSpace($cursor)) {
  if(Test-Path -LiteralPath $cursor){
   Need (((Get-Item -LiteralPath $cursor -Force).Attributes -band
     [IO.FileAttributes]::ReparsePoint) -eq 0) 'PRIVATE_ROOT_LINK'
  }
  $next=Split-Path -Parent $cursor
  if($next -ceq $cursor){break}
  $cursor=$next
 }
 $today=(Stamp).Substring(0,10)
 Need ($today -ceq '2026-11-02') 'SESSION_DATE'
 $script:stage='EXCEL_VISIBLE_PIN'
 $visible=@(Get-Process EXCEL -ErrorAction SilentlyContinue|
   Where-Object {$_.MainWindowHandle -ne [IntPtr]::Zero})
 Need ($visible.Count -eq 1) 'EXCEL_WINDOW_NOT_UNIQUE'
 if(-not ('No11CashRssWindow' -as [type])){
  Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class No11CashRssWindow {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,Callback cb,IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h,StringBuilder b,int n);
 [DllImport("oleacc.dll")] public static extern int AccessibleObjectFromWindow(IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object o);
}
'@ -ErrorAction Stop
 }
 $script:excelChildren=@()
 $callback=[No11CashRssWindow+Callback]{
  param($h,$p)
  $name=New-Object System.Text.StringBuilder 128
  [void][No11CashRssWindow]::GetClassName($h,$name,128)
  if($name.ToString() -ceq 'EXCEL7'){$script:excelChildren+=@($h)}
  return $true
 }
 [void][No11CashRssWindow]::EnumChildWindows(
    $visible[0].MainWindowHandle,$callback,[IntPtr]::Zero)
 Need ($script:excelChildren.Count -eq 1) 'EXCEL7_NOT_UNIQUE'
 $iid=[guid]'00020400-0000-0000-C000-000000000046'
 $windowObject=$null
 $hr=[No11CashRssWindow]::AccessibleObjectFromWindow(
  $script:excelChildren[0],[uint32]4294967280,[ref]$iid,[ref]$windowObject)
 Need ($hr -eq 0 -and $null -ne $windowObject) 'EXCEL_ATTACH_FAILED'
 $excel=$windowObject.Application
 $account=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx')
 $sheet=$account.Worksheets.Item('ARK_ACCOUNT_READONLY')
 Need ($sheet.Name -ceq 'ARK_ACCOUNT_READONLY') 'ACCOUNT_SHEET_IDENTITY'
 Write-Host 'NO11_RSS_CAPACITY_STAGE=EXISTING_ORIGINAL_ACCOUNT_BOOK_PINNED'
 $script:stage='FIND_ORIGINAL_RSS_CAPACITY_FORMULA'
 $used=$sheet.UsedRange
 Need ([long]$used.CountLarge -le 10000 -and
       [long]$used.CountLarge -ge 1) 'ACCOUNT_USED_RANGE_LIMIT'
 # Formula scan is read-only and has already been confirmed to finish on this PC.
 $formula=$used.Formula
 $anchors=@()
 if($formula -is [array] -and $formula.Rank -eq 2){
  $r0=$formula.GetLowerBound(0);$c0=$formula.GetLowerBound(1)
  for($i=0;$i -lt $formula.GetLength(0);$i++){
   for($j=0;$j -lt $formula.GetLength(1);$j++){
    if(([string]$formula.GetValue($r0+$i,$c0+$j)) -match '(?i)^=\s*RssCapacityList\s*\('){
     $anchors+=@([pscustomobject]@{row=[int]$used.Row+$i;col=[int]$used.Column+$j})
    }
   }
  }
 }elseif(([string]$formula) -match '(?i)^=\s*RssCapacityList\s*\(') {
  $anchors+=@([pscustomobject]@{row=[int]$used.Row;col=[int]$used.Column})
 }
 Need ($anchors.Count -eq 1) 'EXACT_ONE_ORIGINAL_RSS_CAPACITY_FORMULA_REQUIRED'
 $anchor=$anchors[0]
 $headerRow=[int]$anchor.row+1
 $firstCol=[int]$anchor.col
 $script:stage='READ_RSS_CAPACITY_HEADER'
 $first=$sheet.Cells.Item($headerRow,$firstCol)
 $last=$sheet.Cells.Item($headerRow,$firstCol+6)
 $headers=$sheet.Range($first,$last).Value2
 Need ($headers -is [array] -and $headers.Rank -eq 2 -and
       $headers.GetLength(0) -eq 1 -and $headers.GetLength(1) -eq 7) 'RSS_CAPACITY_HEADER_SHAPE'
 $col=-1;$hits=0
 for($i=0;$i -lt 7;$i++){
  $label=([string]$headers.GetValue($headers.GetLowerBound(0),$headers.GetLowerBound(1)+$i)).Replace(' ','').Replace('　','').Trim()
  if($label -ceq '現物買付可能額'){$col=$firstCol+$i;$hits++}
 }
 Need ($hits -eq 1) 'RSS_CAPACITY_FIELD_MISSING_OR_AMBIGUOUS'
 $script:stage='READ_EXISTING_RSS_CAPACITY'
 Write-Host 'NO11_RSS_CAPACITY_STAGE=READ_ONLY_VALUE2_BEGIN'
 $raw=$sheet.Cells.Item($headerRow+1,$col).Value2
 Write-Host 'NO11_RSS_CAPACITY_STAGE=READ_ONLY_VALUE2_RETURNED'
 $amount=PlainInteger $raw
 $readAt=Stamp
 Need ($readAt.Substring(0,10) -ceq $today) 'RSS_OBSERVATION_DATE_CHANGED'
 $script:stage='WRITE_PRIVATE_UNAPPROVED_RECEIPT'
 $properties=[ordered]@{
  schemaId='ARK_NO11_BANK_UNLINKED_RSS_CAPACITY_OBSERVATION_V1'
  sessionDate=$today
  source='RssCapacityList'
  sourceWorkbook='Ark_No11_MSII_RSS.xlsx'
  sourceSheet='ARK_ACCOUNT_READONLY'
  sourceField='現物買付可能額'
  observedAtJst=$readAt
  observedBuyingPowerJpy=$amount
  account=$Account
  bankNotLinkedOperatorConfirmed='true'
  autoSweepOffOperatorConfirmed='true'
  rssVendorAsOfTimeCertified='false'
  securitiesCashBalanceCertified='false'
  reviewMode='OPERATOR_ATTESTED_BANK_UNLINKED_RSS_BUYING_POWER'
  orderTransmission='false'
  liveApproved='false'
 }
 $kv=New-Object 'System.Collections.Generic.List[string]'
 foreach($key in @($properties.Keys)){
  if($key -cin @('bankNotLinkedOperatorConfirmed',
                'autoSweepOffOperatorConfirmed','rssVendorAsOfTimeCertified',
                'securitiesCashBalanceCertified','orderTransmission','liveApproved')){
   $v=[string]$properties[$key]
  }else{
   $v=JsonString ([string]$properties[$key])
  }
  $kv.Add((JsonString ([string]$key))+':'+$v)
 }
 $json='{'+[string]::Join(',',$kv.ToArray())+'}'
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes($json+[char]10)
 Need ($bytes.Length -gt 350 -and $bytes.Length -lt 4000) 'RECEIPT_BYTES_INVALID'
 $digest=Hash $bytes
 $file=Join-Path $root ('bank-unlinked-rss-capacity-'+$digest+'.json')
 if(Test-Path -LiteralPath $file){
  Need (([Convert]::ToBase64String([IO.File]::ReadAllBytes($file))) -ceq
       ([Convert]::ToBase64String($bytes))) 'RECEIPT_CONFLICT'
 }else{
  $stream=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}
  finally{$stream.Dispose()}
 }
 Write-Host 'NO11_RSS_CAPACITY=READ_ONLY_OBSERVED'
 Write-Host ('NO11_RSS_CAPACITY_OBSERVATION_FILE='+$file)
 Write-Host 'NO11_RSS_CAPACITY_BANK_LINK=OPERATOR_ATTESTED_NOT_INDEPENDENTLY_PROVED'
 Write-Host 'NO11_RSS_CAPACITY_LIVE_OPENING_LEDGER=NOT_ACTIVATED'
}catch{
 $failed=$true
 $msg=[string]$_.Exception.Message
 if($msg -cnotmatch '^NO11_RSS_CAPACITY_[A-Z0-9_]+$'){$msg='NO11_RSS_CAPACITY_SOURCE_OR_EXCEL_FAILURE'}
 Write-Host ('NO11_RSS_CAPACITY_FAILED_STAGE='+$script:stage)
 Write-Host ('NO11_RSS_CAPACITY=BLOCKED|'+$msg)
}finally{
 foreach($o in @($sheet,$account,$excel)){
  if($null -ne $o -and [Runtime.InteropServices.Marshal]::IsComObject($o)){
   try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($o)}catch{}
  }
 }
 Write-Host 'ORDER_TRANSMISSION=False'
}
if($failed){exit 2}
exit 0
