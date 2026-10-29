# A genuine broker RSS snapshot, not synthetic orders or Shadow fills.
# -Prepare creates a read-only third workbook if absent. Open it manually
# alongside the two original Ark books in the SAME Excel application.
# Default mode reads exactly one real RSS account/order/execution snapshot.
param([string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [switch]$Prepare,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_PHYSICAL_ACCOUNT_'+$code)}}
function Safe([string]$p,[bool]$directory=$false){
 Need ([IO.Path]::IsPathRooted($p)) 'ABSOLUTE_PATH'
 $p=[IO.Path]::GetFullPath($p)
 Need (Test-Path -LiteralPath $p -PathType $(if($directory){'Container'}else{'Leaf'})) 'SOURCE_NOT_FOUND'
 $cur=$p
 while(-not [string]::IsNullOrEmpty($cur)){
  Need (((Get-Item -LiteralPath $cur -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_POINT'
  $next=Split-Path -Parent $cur;if($next -ceq $cur){break};$cur=$next
 }
 return $p
}
if($OfflineSelfTest){
 Write-Host 'NO11_PHYSICAL_ACCOUNT_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_PHYSICAL_ACCOUNT_EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 $engine=Safe $EngineRoot $true
 $new=Safe (Join-Path $engine 'windows\New-No11BrokerReadOnlyWorkbook.ps1')
 $observe=Safe (Join-Path $engine 'windows\Observe-No11AccountReadOnly.ps1')
 [void](Safe (Join-Path $engine 'windows\Read-No11BrokerSnapshot.ps1'))
 $diag=Safe (Join-Path $engine 'tools\no11_account_connection_diagnostic_readonly.mjs')
 [void](Get-Command node -ErrorAction Stop)
 $base=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\physical-account'
 [void][IO.Directory]::CreateDirectory($base);$base=Safe $base $true
 $helper=Join-Path $base 'Ark_No11_BROKER_READONLY.xlsx'
 if($Prepare){
  if(-not (Test-Path -LiteralPath $helper -PathType Leaf)){
   & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $new -OutputPath $helper
   Need ($LASTEXITCODE -eq 0) 'BOOK_CREATION_FAILED'
  }
  [void](Safe $helper)
  Write-Host ('NO11_PHYSICAL_ACCOUNT_OPEN_THIRD_BOOK='+$helper)
  Write-Host 'NO11_PHYSICAL_ACCOUNT_NEXT=OPEN_IN_SAME_EXCEL_AND_RUN_WITHOUT_PREPARE'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 [void](Safe $helper)
 $running=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop|
  Where-Object {$_.ProcessId -ne $PID -and
   [string]$_.CommandLine -match '(?i)(Capture-No11SessionReferenceReadOnly|Run-No11WeeklyCandidateRefreshReadOnly|Run-No11Oct29D100RecoveryReadOnly|Prepare-No11PreviousArchiveReadOnly|Observe-No11AccountReadOnly)\.ps1'})
 Need ($running.Count -eq 0) 'OTHER_RSS_READER_RUNNING'
 $excelProcesses=@(Get-Process EXCEL -ErrorAction SilentlyContinue)
 Need ($excelProcesses.Count -eq 1) 'EXCEL_PROCESS_NOT_UNIQUE'
 $excel=$null
 try{
  $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
  Need ($excel.Workbooks.Count -eq 3) 'REQUIRE_TWO_ORIGINAL_BOOKS_AND_ONE_BROKER_BOOK'
  $account=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx')
  $market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')
  $ids=$excel.Workbooks.Item('Ark_No11_BROKER_READONLY.xlsx')
  Need ([string]$account.Worksheets.Item('ARK_ACCOUNT_READONLY').Name -ceq 'ARK_ACCOUNT_READONLY' -and
   [string]$market.Worksheets.Item('ARK_MARKET_READONLY').Name -ceq 'ARK_MARKET_READONLY' -and
   [string]$ids.Worksheets.Item('ARK_ORDER_IDS_READONLY').Name -ceq 'ARK_ORDER_IDS_READONLY') 'ORIGINAL_BOOKS_INVALID'
  Need ([IO.Path]::GetFullPath([string]$ids.FullName).Equals($helper,[StringComparison]::OrdinalIgnoreCase)) 'BROKER_BOOK_PATH_INVALID'
  $accountPath=[IO.Path]::GetFullPath([string]$account.FullName)
 }finally{
  if($null -ne $excel -and [Runtime.InteropServices.Marshal]::IsComObject($excel)){
   [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
  }
 }
 $stamp=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyyMMdd-HHmmss')
 $id=[guid]::NewGuid().ToString('N')
 $output=Join-Path $base ('observed-'+$stamp+'-'+$id+'.json')
 $stop=Join-Path $base ('stop-'+$id+'.stop')
 Write-Host 'NO11_PHYSICAL_ACCOUNT_STAGE=REAL_RSS_ACCOUNT_READ'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $observe -WorkbookPath $accountPath -OrderIdWorkbookPath $helper -OutputFile $output -StopFile $stop -Samples 1 -PollSeconds 2
 Need ($LASTEXITCODE -eq 0) 'OBSERVER_RUNTIME_FAILED'
 $envelope=Get-Content -LiteralPath (Safe $output) -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($envelope.schemaId -ceq 'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1' -and
  $envelope.status -ceq 'OBSERVED' -and
  $envelope.brokerObservation.status -ceq 'OBSERVED') 'REAL_BROKER_ORDER_AND_ACCOUNT_NOT_VERIFIED'
 Write-Host 'NO11_PHYSICAL_ACCOUNT_STAGE=REAL_ORDER_EXECUTION_HOLDINGS_CROSSCHECK'
 & node $diag --observer-file $output
 Need ($LASTEXITCODE -eq 0) 'DIAGNOSTIC_FAILED'
 Write-Host 'NO11_PHYSICAL_ACCOUNT=REAL_RSS_BROKER_READ_PASS_NOT_ORDER_AUTHORIZED'
 Write-Host 'NO11_PHYSICAL_ACCOUNT_PRIVATE_ACCOUNT_DATA=LOCAL_ONLY'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $code=$_.Exception.Message
 if($code -cnotmatch '^NO11_PHYSICAL_ACCOUNT_[A-Z0-9_]+$'){$code='NO11_PHYSICAL_ACCOUNT_LOCAL_SOURCE_OR_RSS_FAILURE'}
 Write-Host ('NO11_PHYSICAL_ACCOUNT=BLOCKED|'+$code)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}