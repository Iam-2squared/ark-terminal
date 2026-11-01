# Friday 429 only. One-shot local migration from a running 5-symbol
# READ-ONLY collector to adaptive max 47 with 3 Excel safety slots reserved.
# Remote sources are pinned, downloaded and offline-tested BEFORE stopping a
# collector. Only the known 429 read-only powershell worker is stopped.
# Journaled captures (30, 78, 168, ...) are never modified, saved or deleted.
param(
 [string]$InstallRoot='C:\ArkTerminal\no11-unified-2026-10-30',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='97ca86890f9cca52a77ecfdfa4f154e9a765a199'
$rootHead='24b906e19a2623e45701311ca3fbb20dafe11c80'
$prefix='research/no12-prebuy-causal-runtime-20261011/'
$baseExpected=[ordered]@{
 ($prefix+'windows/Run-No11WeeklyCandidateRefreshReadOnly.ps1')='d305f1062a536fe35caad7f8b3ba81bfa1ffc927'
 ($prefix+'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1')='d098a958f6364ed0aebdf1e8d4fd2a0c01a53c93'
 ($prefix+'tests/no11_weekly_g1_refresh.test.mjs')='f4f7649a6ba6eb766c13d2c8ba54c24d16f0ee09'
}
$targetExpected=[ordered]@{
 ($prefix+'windows/Run-No11WeeklyCandidateRefreshReadOnly.ps1')='57f22c23ce9f32202d2c16a26b86585120c2141c'
 ($prefix+'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1')='636eedc0e678ca924d3c5f634918cf230e707035'
 ($prefix+'tests/no11_weekly_g1_refresh.test.mjs')='052b64183c6345910fc3c577eed16d5d9477f7b2'
}
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_MAX47_'+$code)}}
function GitBlob([string]$file){
 $value=@(& git hash-object --no-filters $file)
 Need ($LASTEXITCODE -eq 0 -and $value.Count -eq 1) 'GIT_HASH_FAILED'
 return [string]$value[0]
}
function CanonicalBlob([string]$file){
 # Preserve source text and any BOM. Normalize Windows CRLF only.
 $strict=[Text.UTF8Encoding]::new($false,$true)
 $text=$strict.GetString([IO.File]::ReadAllBytes($file))
 $normalized=$text.Replace(([string][char]13+[char]10),[string][char]10)
 $bytes=$strict.GetBytes($normalized)
 $head=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length+[char]0))
 $combine=New-Object byte[] ($head.Length+$bytes.Length)
 [Array]::Copy($head,0,$combine,0,$head.Length)
 [Array]::Copy($bytes,0,$combine,$head.Length,$bytes.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($combine))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
if($OfflineSelfTest){
 Need ($revision -match '^[a-f0-9]{40}$' -and
       $baseExpected.Count -eq 3 -and $targetExpected.Count -eq 3) 'PINS'
 $sample=Join-Path $env:TEMP ('ark47-selftest-'+[guid]::NewGuid().ToString('N'))
 try{
  $utf8=[Text.UTF8Encoding]::new($false)
  [IO.File]::WriteAllBytes($sample,$utf8.GetBytes(('max47'+[char]10)))
  $one=CanonicalBlob $sample
  [IO.File]::WriteAllBytes($sample,$utf8.GetBytes(('max47'+[char]13+[char]10)))
  Need ((CanonicalBlob $sample) -ceq $one) 'CRLF_NORMALIZATION'
 }finally{if(Test-Path -LiteralPath $sample){Remove-Item -LiteralPath $sample -Force}}
 Write-Host 'NO11_MAX47_SWITCH_OFFLINE_SELFTEST=PASS_NO_EXCEL_NO_ORDERS'
 exit 0
}
$stage=''
$backups=@{}
$updated=@()
$workerStopped=$false
try{
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command node -ErrorAction Stop)
 Need (Test-Path -LiteralPath $InstallRoot -PathType Container) 'INSTALL_ROOT_MISSING'
 $root=[IO.Path]::GetFullPath($InstallRoot)
 $actualHead=([string](& git -C $root rev-parse HEAD)).Trim()
 Need ($LASTEXITCODE -eq 0 -and $actualHead -ceq $rootHead) 'PINNED_WORKTREE_HEAD_CHANGED'
 foreach($item in $baseExpected.GetEnumerator()){
  $f=Join-Path $root $item.Key
  Need (Test-Path -LiteralPath $f -PathType Leaf) 'REQUIRED_READER_NOT_PRESENT'
  $observed=CanonicalBlob $f
  Need ($observed -ceq [string]$item.Value -or
        $observed -ceq [string]$targetExpected[$item.Key]) 'LOCAL_CODE_DIFF_REVIEW_REQUIRED'
 }
 # Download and self-test all proposed files before touching any running job.
 $stage=Join-Path $env:TEMP ('ArkFridayMAX47-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($stage)
 $staged=@{}
 $i=0
 foreach($entry in $targetExpected.GetEnumerator()){
  $i++
  $file=Join-Path $stage ('stage-'+$i+[IO.Path]::GetExtension($entry.Key))
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+'/'+$entry.Key
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $file
  Need ((GitBlob $file) -ceq [string]$entry.Value) 'REMOTE_BLOB_MISMATCH'
  $staged[$entry.Key]=$file
 }
 $readerRel=$prefix+'windows/Run-No11WeeklyCandidateRefreshReadOnly.ps1'
 $runnerRel=$prefix+'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1'
 $testsRel=$prefix+'tests/no11_weekly_g1_refresh.test.mjs'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $staged[$readerRel] -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'NEW_READER_OFFLINE_TEST_FAILED'
 # The runner validates its sibling tools before OfflineSelfTest, so its
 # offline test runs only AFTER staging into the verified pinned worktree.

 # Reject running broker/another scan; only the exact Friday429 read-only
 # collector may be interrupted. Stop the child first, then its parent.
 $powershell=@(Get-CimInstance Win32_Process | Where-Object {
  $_.Name -in @('powershell.exe','pwsh.exe') -and -not [string]::IsNullOrWhiteSpace($_.CommandLine)
 })
 $unsafe=@($powershell | Where-Object {
  $_.CommandLine -match '(Run-No11ReceivedSessionOperatorLive|Run-No11RssDailyTrendCensusReadOnly|Prepare-No11PreviousArchiveReadOnly)[.]ps1'
 })
 Need ($unsafe.Count -eq 0) 'OTHER_READER_OR_LIVE_PROCESS_ACTIVE'
 $controllers=@($powershell | Where-Object {
  $_.CommandLine -match 'Prepare-No11WeeklyAfterCloseReadOnly[.]ps1' -and
  $_.CommandLine -match '[-]WeekendFridayLimited'
 })
 $workers=@($powershell | Where-Object {
  $_.CommandLine -match 'Run-No11WeeklyCandidateRefreshReadOnly[.]ps1' -and
  $_.CommandLine -match '[-]FirstBuyFridayLimited'
 })
 $otherWeekly=@($powershell | Where-Object {
  $_.CommandLine -match '(Prepare-No11WeeklyAfterCloseReadOnly|Run-No11WeeklyCandidateRefreshReadOnly)[.]ps1' -and
  $_.CommandLine -notmatch '[-](WeekendFridayLimited|FirstBuyFridayLimited)'
 })
 Need ($controllers.Count -le 1 -and $workers.Count -le 1 -and
       $otherWeekly.Count -eq 0) 'MULTIPLE_OR_WRONG_COLLECTORS_PRESENT'
 foreach($proc in $workers){
  Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
  $workerStopped=$true
 }
 foreach($proc in $controllers){
  Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
  $workerStopped=$true
 }
 Start-Sleep -Seconds 3
 $remainingWorkers=@(Get-CimInstance Win32_Process | Where-Object {
  $_.Name -in @('powershell.exe','pwsh.exe') -and
  $_.CommandLine -match '(Prepare-No11WeeklyAfterCloseReadOnly|Run-No11WeeklyCandidateRefreshReadOnly)[.]ps1'
 })
 Need ($remainingWorkers.Count -eq 0) 'COLLECTOR_NOT_FULLY_STOPPED'
 # The original account and market Excel workbooks are NEVER modified.
 $excelProcesses=@(Get-Process EXCEL -ErrorAction SilentlyContinue)
 Need ($excelProcesses.Count -eq 1) 'EXCEL_PROCESS_NOT_UNIQUE'
 $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
 try{
  $required=@('Ark_No11_MSII_RSS.xlsx','Ark_No11_MARKET_RSS.xlsx')
  $all=@(for($j=1;$j -le $excel.Workbooks.Count;$j++){
   [string]$excel.Workbooks.Item($j).Name
  })
  $extra=@($all | Where-Object { $_ -notin $required })
  Need ($extra.Count -le 1 -and $all -contains $required[0] -and
        $all -contains $required[1]) 'EXCEL_ORIGINALS_NOT_UNIQUE'
  if($extra.Count -eq 1){
   $temporary=$excel.Workbooks.Item($extra[0])
   $sheetNames=@(for($j=1;$j -le $temporary.Worksheets.Count;$j++){
    [string]$temporary.Worksheets.Item($j).Name
   })
   $daily=@($sheetNames | Where-Object {$_ -match '^DAILY_[0-9A-Z]{4}_T$'})
   $alien=@($sheetNames | Where-Object {
    $_ -notmatch '^DAILY_[0-9A-Z]{4}_T$' -and $_ -notmatch '^(Sheet|シート)[0-9]+$'
   })
   Need ($extra[0] -match '^(Book|ブック)[0-9]+$' -and $daily.Count -ge 1 -and
         $alien.Count -eq 0) 'UNRECOGNIZED_EXTRA_BOOK_CLOSE_MANUALLY'
   $temporary.Close($false)
   Write-Host 'NO11_MAX47_PRIOR_ARK_TEMP_BOOK_CLOSED_WITHOUT_SAVING=True'
  }
  Need ($excel.Workbooks.Count -eq 2) 'EXCEL_BOOKS_NOT_TWO_AFTER_CLEANUP'
 }finally{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}
 # Verify COMPLETE hashes of existing private receipts. Does not write or
 # backdate any Friday D100 capture; existing immutable files stay untouched.
 $engine=Join-Path $root $prefix
 $tool=Join-Path $engine 'tools/no11_weekly_g1_refresh.mjs'
 $seed=Join-Path $env:LOCALAPPDATA 'ArkTerminal/No12/daily-trend-capture/daily-2026-10-26-e84a2ec53b0fdf41'
 $refreshRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal/No12/weekly-pool-refresh'
 $planOutput=@(& node $tool plan --weekly-run $seed --root $refreshRoot --first-buy-friday-limited true)
 Need ($LASTEXITCODE -eq 0 -and $planOutput.Count -eq 1) 'SAVED_RECEIPTS_VERIFICATION_FAILED'
 $plan=[string]$planOutput[0]|ConvertFrom-Json
 Need ($plan.plan.asOfSession -ceq '2026-10-30' -and
       @($plan.plan.symbols).Count -eq 429 -and
       $plan.resumed -ge 78 -and $plan.resumed -le 429) 'SAVED_RECEIPTS_NOT_EXPECTED_429'
 Write-Host ('NO11_MAX47_SAVED_HASH_VERIFIED='+$plan.resumed+'/429')
 if($plan.resumed -eq 429){
  Write-Host 'NO11_MAX47=CAPTURES_ALREADY_COMPLETE_DO_NOT_RESTART'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 # Pin originals, back up in a private local directory, then install.
 $backupDir=Join-Path $env:LOCALAPPDATA 'ArkTerminal/No12/unified-launcher/backups'
 [void][IO.Directory]::CreateDirectory($backupDir)
 $tag=[guid]::NewGuid().ToString('N')
 foreach($entry in $targetExpected.GetEnumerator()){
  $dest=Join-Path $root $entry.Key
  $backup=Join-Path $backupDir ('MAX47-'+$tag+'-'+[IO.Path]::GetFileName($dest)+'.bak')
  [IO.File]::Copy($dest,$backup,$false)
  $backups[$dest]=$backup
 }
 foreach($entry in $targetExpected.GetEnumerator()){
  $dest=Join-Path $root $entry.Key
  [IO.File]::Copy([string]$staged[$entry.Key],$dest,$true)
  $updated+=@($dest)
  Need ((CanonicalBlob $dest) -ceq [string]$entry.Value) 'LOCAL_INSTALL_VERIFY_FAILED'
 }
 & node --test (Join-Path $root $testsRel)
 Need ($LASTEXITCODE -eq 0) 'MAX47_WEEKLY_TEST_FAILED'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root $readerRel) -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'MAX47_INSTALLED_READER_TEST_FAILED'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root $runnerRel) -OfflineSelfTest -WeekendFridayLimited -RefreshBatchSize 47 -RefreshAutoMaxThroughput
 Need ($LASTEXITCODE -eq 0) 'MAX47_INSTALLED_RUNNER_TEST_FAILED'
 # No parallel launch or workbook modification. Read-only Friday429 ONLY.
 $logs=Join-Path $env:LOCALAPPDATA 'ArkTerminal/No12/unified-launcher/logs'
 [void][IO.Directory]::CreateDirectory($logs)
 $runId=[guid]::NewGuid().ToString('N')
 $out=Join-Path $logs ('FRIDAY429-MAX47-'+$runId+'.log')
 $err=Join-Path $logs ('FRIDAY429-MAX47-'+$runId+'.err')
 $runner=Join-Path $root $runnerRel
 $psArgs='-NoProfile -ExecutionPolicy Bypass -File "'+$runner+'" -WeekendFridayLimited -RefreshBatchSize 47 -RefreshAutoMaxThroughput -RefreshWaitSeconds 60'
 $process=Start-Process powershell.exe -ArgumentList $psArgs -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
 Need ($null -ne $process -and $process.Id -gt 0) 'MAX47_PROCESS_LAUNCH_FAILED'
 Write-Host 'NO11_MAX47=ADAPTIVE_RAMP_5_10_20_40_47_STARTED'
 Write-Host ('NO11_MAX47_PID='+$process.Id)
 Write-Host ('NO11_MAX47_LOG='+$out)
 Write-Host 'NO11_MAX47_CHART_LIMIT=47_WITH_3_RESERVED'
 Write-Host 'NO11_MAX47_ORIGINAL_WORKBOOKS_MODIFIED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 foreach($dest in $updated){
  if($backups.ContainsKey($dest)){
   try{[IO.File]::Copy([string]$backups[$dest],$dest,$true)}catch{}
  }
 }
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_MAX47_[A-Z0-9_]+$'){
  $reason='NO11_MAX47_SETUP_OR_COM_FAILURE'
 }
 Write-Host ('NO11_MAX47=BLOCKED|'+$reason)
 Write-Host ('NO11_MAX47_READONLY_WORKER_STOPPED='+$workerStopped)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if($stage -and (Test-Path -LiteralPath $stage -PathType Container)){
  Remove-Item -LiteralPath $stage -Recurse -Force
 }
}
