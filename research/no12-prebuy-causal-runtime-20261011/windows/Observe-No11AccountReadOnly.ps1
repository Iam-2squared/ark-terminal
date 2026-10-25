# Observe the existing account book alongside the market/temporary books.
# Uses byte-pinned original parsing. Never creates/changes/saves an Excel book.
param(
 [string]$WorkbookPath,[string]$OutputFile,[string]$StopFile,
 [ValidateRange(1,10000)][int]$Samples=5000,
 [ValidateRange(2,30)][int]$PollSeconds=5,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$original=Join-Path $repo 'integration\no1-1-msii\windows\Ark-No11-CaptureReadOnly-v3-CANDIDATE.ps1'
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_ACCOUNT_CAPTURE_'+$code)}}
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
  if([IO.File]::Exists($file)){[IO.File]::Replace($tmp,$file,$null)}else{[IO.File]::Move($tmp,$file)}
 }finally{if([IO.File]::Exists($tmp)){[IO.File]::Delete($tmp)}}
}
function CaptureAccount([string]$target,[scriptblock]$capture){
 Need (@(Get-Process EXCEL -ErrorAction SilentlyContinue).Count -eq 1) 'EXCEL_PROCESS_NOT_UNIQUE'
 $excel=$null;$book=$null;$sheet=$null
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
  $sheet=$book.Worksheets.Item(1)
  Need ([string]$sheet.Name -ceq 'ARK_ACCOUNT_READONLY') 'ACCOUNT_SHEET_IDENTITY'
  return (& $capture $sheet)
 }finally{
  foreach($o in @($sheet,$book,$excel)){
   if($null -ne $o -and [Runtime.InteropServices.Marshal]::IsComObject($o)){
    try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($o)}catch{}
   }
  }
 }
}
$capture=LoadPinnedCapture
if($OfflineSelfTest){
 $text=$capture.ToString()
 Need ($text.Contains('Read-BulkRange') -and $text.Contains('account=(Trim-Value (Bulk-Value $ordersBlock $idx 4))')) 'OFFLINE_CAPTURE_SHAPE'
 Need (-not $text.Contains('NO_VERIFIED_BROKER_POSITIONS')) 'EMPTY_ACCOUNT_NOT_SUPPORTED'
 Need (-not ($text -match '(?i)Workbooks\.Add|Workbooks\.Open|\.Save\(|\.SaveAs\(|RssStockOrder\(|RssCancelOrder\(')) 'OFFLINE_NOT_READONLY'
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
  }catch{$value.reason='ACCOUNT_CAPTURE_UNAVAILABLE'}
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
