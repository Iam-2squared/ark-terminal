# Only the existing Windows clipboard text, NOT Excel COM or another collector.
# Copy exactly A1:L47 of the unsaved MarketSpeed II RSS workbook in Excel first.
# The saved date-time is when the clipboard was READ, not quote update time.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [string]$DailyRun='',
 [string]$OutputRoot='',
 [string]$PythonExecutable='',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if(-not $DailyRun){$DailyRun=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\daily-trend-capture\daily-2026-10-26-e84a2ec53b0fdf41'}
if(-not $OutputRoot){$OutputRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\session-reference\2026-10-27'}
if(-not $PythonExecutable){$PythonExecutable=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'}
$plan=Join-Path $DailyRun 'no11-chart50-private-a9d57cdb4eccb107.json'
$mask=Join-Path $DailyRun 'no11-observed-pass-watch-ce769aac846cf1b4.json'
$importer=Join-Path $EngineRoot 'tools\no11_import_clipboard_reference_readonly.py'
$review=Join-Path $EngineRoot 'tools\no11_review_queue_from_actual_rss.py'
$ci=[Globalization.CultureInfo]::InvariantCulture
function Stamp {
 [datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz',$ci)
}
function Need([bool]$yes,[string]$reason) {
 if(-not $yes){throw ('NO11_CLIPBOARD_LAUNCH_'+$reason)}
}
function PathSafe([string]$value,[bool]$dir=$false) {
 Need ([IO.Path]::IsPathRooted($value)) 'ABSOLUTE_PATH_REQUIRED'
 $p=[IO.Path]::GetFullPath($value)
 $item=Get-Item -LiteralPath $p -Force -ErrorAction Stop
 Need ([bool]$item.PSIsContainer -eq $dir) 'INPUT_TYPE_INVALID'
 while(-not [string]::IsNullOrWhiteSpace($p)) {
  $part=Get-Item -LiteralPath $p -Force -ErrorAction Stop
  Need (($part.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_INPUT_REJECTED'
  $parent=Split-Path -Parent $p
  if($parent -ceq $p){break};$p=$parent
 }
}
function SaveBytes([string]$dest,[byte[]]$bytes) {
 if([IO.File]::Exists($dest)) {
  $old=[IO.File]::ReadAllBytes($dest)
  Need (([Convert]::ToBase64String($old)) -ceq ([Convert]::ToBase64String($bytes))) 'CLIPBOARD_RECEIPT_CHANGED'
 }else{
  $stream=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 }
}
try {
 if($OfflineSelfTest) {
  $sample='7203.T'+[char]9+'7203'+[char]9+'T'
  Need ($sample -match '^[0-9A-Z]{4}\.T\t[0-9A-Z]{4}\tT') 'REGEX_SELFTEST'
  Need ((Stamp) -match '^20\d\d-\d\d-\d\dT') 'CLOCK_SELFTEST'
  Write-Host 'NO11_CLIPBOARD_LAUNCH_OFFLINE_SELFTEST=PASS'
  Write-Host 'NO11_CLIPBOARD_EXCEL_COM_ACCESSED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 Need ((Stamp).StartsWith('2026-10-27')) 'NOT_TODAYS_SESSION'
 foreach($file in @($plan,$mask,$importer,$review,$PythonExecutable)) {PathSafe $file}
 PathSafe $EngineRoot $true
 PathSafe $DailyRun $true
 $root=[IO.Path]::GetFullPath($OutputRoot)
 $private=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'))
 Need ($root.StartsWith($private+'\',[StringComparison]::OrdinalIgnoreCase)) 'OUTPUT_NOT_PRIVATE'
 if(-not [IO.Directory]::Exists($root)){[void][IO.Directory]::CreateDirectory($root)}
 PathSafe $root $true

 $clipCmd=Get-Command Get-Clipboard -ErrorAction SilentlyContinue
 Need ($null -ne $clipCmd) 'CLIPBOARD_READER_NOT_AVAILABLE'
 Write-Host 'NO11_CLIPBOARD_LAUNCH=READING_EXCEL_COPY_ONLY'
 $start=Stamp
 $text=[string](Get-Clipboard -Raw -Format Text -ErrorAction Stop)
 $end=Stamp
 Need ($text.Length -ge 100 -and $text.Length -le 200000) 'COPIED_RANGE_TEXT_SIZE'
 Need ($text -match '^[0-9A-Z]{4}\.T\t') 'COPIED_RANGE_FIRST_CELL_IS_NOT_TICKER'
 Need (([datetimeoffset]::Parse($end)-[datetimeoffset]::Parse($start)).TotalSeconds -le 30) 'CLIPBOARD_READ_TOO_SLOW'
 $record=[ordered]@{
  schemaId='ARK_NO11_LOCAL_RSS_CLIPBOARD_CAPTURE_V1'
  sessionDate='2026-10-27'
  capturedAtJst=$start
  completedAtJst=$end
  clipboardTabularText=$text
  copiedFromExcelByUser=$true
  actualRssSourceTimeCertified=$false
  independentCorporateActionReviewPerformed=$false
  readOnly=$true
  productionReady=$false
  orderTransmission=$false
 }
 $data=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $record -Depth 7 -Compress)+[char]10)
 $h=[Security.Cryptography.SHA256]::Create()
 try{$digest=([BitConverter]::ToString($h.ComputeHash($data))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()}
 $source=Join-Path $root ('clipboard-source-'+$digest+'.json')
 SaveBytes $source $data
 Write-Host 'NO11_CLIPBOARD_LOCAL_RECEIPT=IMMUTABLE_SAVED'
 $args=@('-B',$importer,'--clipboard-file',$source,
  '--plan',$plan,'--mask',$mask,'--engine-root',$EngineRoot,
  '--output-root',$root)
 & $PythonExecutable @args
 Need ($LASTEXITCODE -eq 0) 'REFERENCE_VALIDATION_FAILED'
 Write-Host 'NO11_CLIPBOARD_LAUNCH=VERIFIED_REAL_CLIPBOARD_ONLY'
 Write-Host 'NO11_CLIPBOARD_REAL_RSS_SOURCE_TIMESTAMP_CERTIFIED=False'
 Write-Host 'NO11_CLIPBOARD_MODEL_OR_ORDERS_EXECUTED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $msg=$_.Exception.Message
 if($msg -cnotmatch '^NO11_CLIPBOARD_LAUNCH_[A-Z0-9_]+$'){$msg='NO11_CLIPBOARD_LAUNCH_CLIPBOARD_OR_PRIVATE_RUNTIME_FAILURE'}
 Write-Host ('NO11_CLIPBOARD_LAUNCH=BLOCKED|'+$msg)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
exit 0
