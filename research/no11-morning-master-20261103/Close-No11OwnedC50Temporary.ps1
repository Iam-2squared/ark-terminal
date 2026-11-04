# Close ONLY the exact, uniquely tokened UNSAVED temporary Chart50 workbook
# left behind by a FAILED collector after it exits. Never close/save original
# account, market, order ID workbooks. Never change an original receipt.
param(
 [string]$Bootstrap='',
 [string]$RunRoot='',
 [string]$Python='',
 [string]$Finalizer='',
 [switch]$Apply,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){if(-not $ok){throw ('NO11_OWNED_TEMP_'+$why)}}
function Identical([string]$a,[string]$b){
 return [IO.Path]::GetFullPath($a).Equals([IO.Path]::GetFullPath($b),
                                     [StringComparison]::OrdinalIgnoreCase)
}
if($OfflineSelfTest){
 Need (-not $Apply) 'SELFTEST_MODE'
 Write-Host 'NO11_OWNED_TEMP_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO_ORIGINAL_BOOK_CLOSED=True'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'EXPLICIT_OPERATOR_ACTION_REQUIRED'
$today=[DateTimeOffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-dd')
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$settingsPath=Join-Path $store 'settings.json'
Need ((Test-Path -LiteralPath $settingsPath -PathType Leaf) -and
      [IO.Path]::IsPathRooted($Bootstrap) -and
      (Test-Path -LiteralPath $Bootstrap -PathType Leaf) -and
      [IO.Path]::IsPathRooted($RunRoot) -and
      (Test-Path -LiteralPath $RunRoot -PathType Container) -and
      [IO.Path]::IsPathRooted($Python) -and
      (Test-Path -LiteralPath $Python -PathType Leaf) -and
      [IO.Path]::IsPathRooted($Finalizer) -and
      (Test-Path -LiteralPath $Finalizer -PathType Leaf)) 'INPUT_PATHS'
$settings=Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8|ConvertFrom-Json
$binding=Get-Content -LiteralPath (Join-Path $store 'automatic-inputs.json') -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false -and
      [IO.Path]::IsPathRooted([string]$binding.engine)) 'ENGINE_BINDING_UNSAFE'
$cfg=Get-Content -LiteralPath $Bootstrap -Raw -Encoding UTF8|ConvertFrom-Json
Need ($settings.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
      $settings.orderTransmission -eq $false -and
      $settings.sameDayApprovalRequired -eq $true -and
      $cfg.schemaId -ceq 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1' -and
      $cfg.sessionDate -ceq $today -and
      $cfg.orderTransmission -eq $false -and
      $cfg.productionReady -eq $false) 'SOURCE_SCOPE'
$root=[IO.Path]::GetFullPath([string]$cfg.privateRoot)
$run=[IO.Path]::GetFullPath($RunRoot)
Need ((Test-Path -LiteralPath $root -PathType Container) -and
      [IO.Path]::GetDirectoryName($run) -ieq $root -and
      [IO.Path]::GetFileName($run) -cmatch ('^session-'+$today+'-[a-f0-9]{32}$')) 'RUN_ROOT'
$attempts=@(Get-ChildItem -LiteralPath $run -Directory -Filter 'attempt-*'|Sort-Object Name)
Need ($attempts.Count -ge 1 -and $attempts.Count -le 16) 'FAILED_ATTEMPT_REQUIRED'
$attemptPath=$attempts[-1].FullName
$attempt=Get-Content -LiteralPath (Join-Path $attemptPath 'attempt.json') -Raw -Encoding UTF8|ConvertFrom-Json
$ready=Get-Content -LiteralPath (Join-Path $attemptPath 'collector-ready.json') -Raw -Encoding UTF8|ConvertFrom-Json
$closed=Get-Content -LiteralPath (Join-Path $attemptPath 'collector-ready.json.closed.json') -Raw -Encoding UTF8|ConvertFrom-Json
$descriptor=$ready.temporaryWorkbook
Need ($attempt.schemaId -ceq 'ARK_NO11_RECEIVED_ATTEMPT_V1' -and
      $attempt.sessionDate -ceq $today -and
      $attempt.status -ceq 'CONNECTED' -and
      $attempt.runRoot -ceq $run -and
      [int]$attempt.pid -gt 0 -and
      $ready.schemaId -ceq 'ARK_NO11_C50_COLLECTOR_READY_V1' -and
      $ready.sessionDate -ceq $today -and
      [int]$ready.processId -eq [int]$attempt.pid -and
      $closed.schemaId -ceq 'ARK_NO11_C50_COLLECTOR_CLOSED_V1' -and
      $closed.sessionDate -ceq $today -and
      [int]$closed.processId -eq [int]$attempt.pid -and
      $closed.temporaryWorkbookClosed -eq $false -and
      $closed.collectorFailed -eq $true -and
      $closed.orderTransmission -eq $false -and
      [string]$descriptor.identitySheet -ceq 'ARK_NO11_CUMULATIVE' -and
      [string]$descriptor.identityCell -ceq 'G1' -and
      [string]$descriptor.identityValue -cmatch '^ARK_NO11_C50_TEMP_[a-f0-9]{32}$') 'COLLECTOR_PROOF'
# An outstanding PID could be another process with a recycled ID; either
# way it is NOT safe to treat the owned collector as fully finished.
$livePid=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$attempt.pid)
Need ($null -eq $livePid) 'COLLECTOR_PID_STILL_PRESENT'
Need (@(Get-Process EXCEL -ErrorAction SilentlyContinue).Count -eq 1) 'EXCEL_PROCESS_NOT_UNIQUE'
$expected=@(
 [IO.Path]::GetFullPath([string]$settings.accountWorkbookPath),
 [IO.Path]::GetFullPath([string]$settings.marketWorkbookPath),
 [IO.Path]::GetFullPath([string]$settings.orderIdWorkbookPath)
)
Need (@($expected | Sort-Object -Unique).Count -eq 3 -and
      @($expected | Where-Object {Test-Path -LiteralPath $_ -PathType Leaf}).Count -eq 3) 'ORIGINAL_BOOK_PATHS'
$excel=$null
$owned=$null
try{
 $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
 Need ($null -ne $excel -and $excel.Workbooks.Count -eq 4) 'EXCEL_BOOK_COUNT'
 $original=@()
 $found=@()
 foreach($book in $excel.Workbooks){
  $path=[string]$book.Path
  if($path -cne ''){
   $full=[IO.Path]::GetFullPath([string]$book.FullName)
   Need (@($expected|Where-Object{$_ -ieq $full}).Count -eq 1) 'UNKNOWN_OPEN_SAVED_BOOK'
   $original+=,$full
  }else{$found+=,$book}
 }
 Need ($original.Count -eq 3 -and $found.Count -eq 1 -and
       @($original|Sort-Object -Unique).Count -eq 3) 'ORIGINALS_OR_TEMP_UNRECOGNIZED'
 $owned=$found[0]
 Need ([string]$owned.Name -ceq [string]$descriptor.name -and
       [string]$owned.Path -ceq '' -and
       $owned.Worksheets.Count -eq @($descriptor.worksheetNames).Count) 'TEMP_BOOK_IDENTITY'
 $sheets=@($owned.Worksheets | ForEach-Object {[string]$_.Name}|Sort-Object)
 Need (($sheets -join '|') -ceq (@($descriptor.worksheetNames|Sort-Object) -join '|') -and
       $sheets -contains 'ARK_NO11_CUMULATIVE') 'TEMP_SHEETS'
 $sheet=$owned.Worksheets.Item('ARK_NO11_CUMULATIVE')
 Need ([string]$sheet.Range('G1').Value2 -ceq [string]$descriptor.identityValue) 'TEMP_TOKEN'
 # Closing a UNIQUE UNSAVED temporary workbook, never a user original.
 $owned.Close($false)
 $owned=$null
 Need ($excel.Workbooks.Count -eq 3) 'TEMP_CLOSE_NOT_CONFIRMED'
 $after=@($excel.Workbooks | ForEach-Object {[IO.Path]::GetFullPath([string]$_.FullName)}|Sort-Object)
 Need (($after -join '|') -ceq (@($expected|Sort-Object) -join '|')) 'ORIGINAL_BOOK_INVENTORY_CHANGED'
}finally{
 if($null -ne $owned -and [Runtime.InteropServices.Marshal]::IsComObject($owned)){
  try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($owned)}catch{}
 }
 if($null -ne $excel -and [Runtime.InteropServices.Marshal]::IsComObject($excel)){
  try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}catch{}
 }
}
$reportFile=Join-Path $attemptPath 'owned-temp-closure-observed.json'
Need (-not (Test-Path -LiteralPath $reportFile)) 'CLOSURE_ALREADY_RECORDED'
$body=[ordered]@{
 schemaId='ARK_NO11_C50_OWNED_TEMP_CLOSURE_OBSERVED_V1'
 sessionDate=$today
 collectorPid=[int]$attempt.pid
 ownedTemporaryToken=[string]$descriptor.identityValue
 ownedUnsavedWorkbookClosed=$true
 originalBooksUnchanged=$true
 collectorProcessNotRunning=$true
 noBrokerOrdersTouched=$true
 orderTransmission=$false
 verifiedAtJst=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $body -Compress -Depth 8)+[char]10)
$f=[IO.File]::Open($reportFile,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
& $Python -B -X utf8 $Finalizer --bootstrap $Bootstrap --run $run --report $reportFile --engine ([string]$binding.engine) --operator-approved
Need ($LASTEXITCODE -eq 0) 'POSTMORTEM_FINALIZATION_FAILED'
Write-Host 'NO11_OWNED_C50_CLEANUP=PASS'
Write-Host 'ORIGINAL_EXCEL_BOOKS_CLOSED=False'
Write-Host 'ORIGINAL_COLLECTOR_RECEIPTS_CHANGED=False'
Write-Host 'ENTRY_HALT_CLEARED=False'
Write-Host 'ORDER_TRANSMISSION=False'
