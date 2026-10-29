# Restore ONLY the 5 newly suggested previous-day 1m sources. This NEVER
# creates a trading Chart50 plan, never approves security-product eligibility,
# and never modifies original saved 47-symbol RSS archive or original books.
# The true-source 47/47 RSS completion and 5 provisional absences came from
# the separately SHA-pinned, disk-only G1 preselection audit.
param([switch]$OfflineSelfTest,[switch]$PreflightOnly)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$local=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
$repo='C:\ArkTerminal\no12-launcher'
$engine=Join-Path $repo 'research\no12-prebuy-causal-runtime-20261011'
$sourceRel='research/no12-prebuy-causal-runtime-20261011/windows/Capture-No11RssTrainingBatchReadOnly.ps1'
$originalCollector=Join-Path $repo ($sourceRel.Replace('/','\'))
$collectorPin='efc73171ba24a1879541bf1714ba5e5f7d284bda'
$collectorRevision='06c4039a01b219b269122d0cea76161dcee13cc3'
# Runs a separate pinned copy, never executes or edits locally patched collector.
$collector=Join-Path $local 'equity-type-backfill\2026-10-30\pinned-original\Capture-No11RssTrainingBatchReadOnly.ps1'
$report=Join-Path $local 'external-security-review\2026-10-30\equity-type-provisional-304f08b2eed20c63.json'
$stageFolder=Join-Path $local 'previous-source\2026-10-30'
$daily=Join-Path $local 'weekly-pool-refresh\weekly-refresh-2026-10-29-862f03a3cdfa7d8f'
$base=Join-Path $local 'equity-type-backfill\2026-10-30'
$prefix='304f08b2eed20c63'
$phase='START'
function Need([bool]$pass,[string]$code){
 if(-not $pass){throw ('NO11_EQUITY_FIVE_'+$code)}
}
function One([string]$dir,[string]$filter){
 Need (Test-Path -LiteralPath $dir -PathType Container) 'SOURCE_DIRECTORY_MISSING'
 $files=@(Get-ChildItem -LiteralPath $dir -Filter $filter -File -ErrorAction Stop)
 Need ($files.Count -eq 1) 'SOURCE_FILE_NOT_UNIQUE'
 return [string]$files[0].FullName
}
function Json([string]$file){
 Need (Test-Path -LiteralPath $file -PathType Leaf) 'SOURCE_FILE_MISSING'
 return (Get-Content -LiteralPath $file -Raw -Encoding UTF8|ConvertFrom-Json)
}
function Hash([string]$file){
 return (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
}
# Windows PowerShell 5.1 under StrictMode does not reliably expose Count as
# a member on an empty PSObject property collection. Enumerate explicitly.
function JsonKeys([object]$value){
 Need ($null -ne $value -and $value -is [pscustomobject]) 'EXPECTED_JSON_OBJECT'
 foreach($entry in $value.PSObject.Properties){
  [string]$entry.Name
 }
}
if($OfflineSelfTest){
 Need (-not $PreflightOnly) 'MODES_CONFLICT'
 $fixture='{"symbols":{"7203.T":{}},"omittedSymbols":{}}' | ConvertFrom-Json
 $syntheticPresent=@(JsonKeys $fixture.symbols)
 $syntheticEmpty=@(JsonKeys $fixture.omittedSymbols)
 Need ($syntheticPresent.Count -eq 1 -and $syntheticPresent[0] -ceq '7203.T' -and
       $syntheticEmpty.Count -eq 0) 'EMPTY_OBJECT_STRICTMODE_SELFTEST'
 Need ($collectorPin -cmatch '^[a-f0-9]{40}$' -and
       $prefix -cmatch '^[a-f0-9]{16}$') 'STATIC_CONTRACT'
 Write-Host 'NO11_EQUITY_FIVE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_EQUITY_FIVE_ORIGINAL_RSS_CHANGED=False'
 Write-Host 'NO11_EQUITY_FIVE_TRADING_PLAN_CREATED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 $phase='COMMANDS'
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command powershell.exe -ErrorAction Stop)
 # The existing collector may carry essential Excel window-discovery fixes.
 # Never overwrite, reset or execute that unknown modified source. Instead
 # retrieve the exact audited GitHub source as a standalone private script.
 # The original collector has no PSScriptRoot imports or sibling dependencies.
 Need (Test-Path -LiteralPath $originalCollector -PathType Leaf) 'LOCAL_ORIGINAL_COLLECTOR_MISSING'
 $localStatus=@(& git -C $repo status --porcelain -- $sourceRel)
 Need ($LASTEXITCODE -eq 0) 'LOCAL_GIT_STATUS_FAILED'
 Write-Host ('NO11_EQUITY_FIVE_LOCAL_COLLECTOR_CHANGED='+($localStatus.Count -gt 0))
 $phase='PINNED_COLLECTOR_STAGING'
 $stageRoot=Join-Path $base 'pinned-original'
 [void][IO.Directory]::CreateDirectory($stageRoot)
 $rootInfo=Get-Item -LiteralPath $stageRoot -Force
 Need (($rootInfo.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'PRIVATE_PIN_DIRECTORY_REPARSE'
 $sourceTmp=Join-Path $stageRoot ('source-'+[guid]::NewGuid().ToString('N')+'.tmp')
 if(-not (Test-Path -LiteralPath $collector -PathType Leaf)){
  Need (-not (Test-Path -LiteralPath $collector -PathType Container)) 'PRIVATE_COLLECTOR_IS_DIRECTORY'
  try{
   $uri='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$collectorRevision+'/'+$sourceRel
   Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $sourceTmp
   $newHash=@(& git hash-object --no-filters $sourceTmp)
   Need ($LASTEXITCODE -eq 0 -and $newHash.Count -eq 1 -and
       [string]$newHash[0] -ceq $collectorPin) 'DOWNLOADED_COLLECTOR_HASH_MISMATCH'
   $tokens=$null;$parseErrors=$null
   [void][Management.Automation.Language.Parser]::ParseFile($sourceTmp,[ref]$tokens,[ref]$parseErrors)
   Need ($parseErrors.Count -eq 0) 'PINNED_SOURCE_PARSE_FAILED'
   [IO.File]::Copy($sourceTmp,$collector,$false)
  }finally{
   if(Test-Path -LiteralPath $sourceTmp -PathType Leaf){[IO.File]::Delete($sourceTmp)}
  }
 }
 Need (Test-Path -LiteralPath $collector -PathType Leaf) 'PRIVATE_COLLECTOR_MISSING'
 $collectorInfo=Get-Item -LiteralPath $collector -Force
 Need (($collectorInfo.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'PRIVATE_COLLECTOR_REPARSE'
 $blob=@(& git hash-object --no-filters $collector)
 Need ($LASTEXITCODE -eq 0 -and $blob.Count -eq 1 -and
       [string]$blob[0] -ceq $collectorPin) 'PINNED_PRIVATE_COLLECTOR_CHANGED'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $collector -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'PINNED_COLLECTOR_SELFTEST_FAILED'
 Write-Host 'NO11_EQUITY_FIVE_COLLECTOR=PINNED_PRIVATE_COPY_LOCAL_SOURCE_PRESERVED'
 $phase='REVIEW_FILES_DISCOVERY'
 $stageFile=One $stageFolder 'previous-archive-stage-*.json'
 $chartFile=One $daily 'no11-chart50-private-*.json'
 $phase='REVIEW_FILES_PARSE'
 $review=Json $report
 $stage=Json $stageFile
 $chart=Json $chartFile
 $phase='PREVIEW_AND_SOURCE_PINS'
 Need ((Hash $report).StartsWith($prefix) -and
       (Hash $stageFile) -ceq $review.sourceStageSha256 -and
       $review.sourceChartPlanSha256 -ceq $chart.chartPlan.planSha256 -and
       $review.schemaId -ceq 'ARK_NO11_PROVISIONAL_EQUITY_TYPE_PRESCREEN_V1' -and
       $review.status -ceq 'PROVISIONAL_REVIEW_REQUIRED_NOT_A_TRADING_PLAN' -and
       $review.sessionDate -ceq '2026-10-30' -and
       $review.previousSession -ceq '2026-10-29' -and
       $review.actualCommonEquityIndependentlyReviewed -eq $false -and
       $review.executableChartPlanProduced -eq $false -and
       $review.productionReady -eq $false -and
       $review.orderTransmission -eq $false -and
       $review.originalSelectedCount -eq 47 -and
       $review.provisionalSelectedCount -eq 47 -and
       $stage.sessionDate -ceq '2026-10-30' -and
       $stage.chartPlanSha256 -ceq $review.sourceChartPlanSha256 -and
       $stage.orderTransmission -eq $false) 'PROVISIONAL_REPORT_NOT_PINNED'
 $phase='FIVE_SYMBOLS'
 $extra=@($review.replacementPriorArchiveMissing|ForEach-Object {[string]$_})
 $alternates=@($review.provisionalReplacementCandidates|ForEach-Object {[string]$_})
 $excluded=@($review.knownExcludedFromG1|ForEach-Object {[string]$_})
 $originalExcluded=@($review.knownExcludedFromOriginal|ForEach-Object {[string]$_})
 $stagedSymbols=@(JsonKeys $stage.symbols)
 $stagedOmitted=@(JsonKeys $stage.omittedSymbols)
 Need ($extra.Count -eq 5 -and
       @($extra|Select-Object -Unique).Count -eq 5 -and
       @($alternates|Select-Object -Unique).Count -eq 5 -and
       @($extra|Where-Object {$_ -notin $alternates -or $_ -in $excluded -or
          $_ -notmatch '^[0-9A-Z]{4}\.T$'}).Count -eq 0 -and
       $originalExcluded.Count -eq 5 -and
       $stagedSymbols.Count -eq 47 -and
       $stagedOmitted.Count -eq 0 -and
       @($extra|Where-Object {$_ -in $stagedSymbols}).Count -eq 0
      ) 'FIVE_NEW_SOURCES_NOT_PROVEN'
 # Do not overlap prior account observation, chart collection, or an existing
 # market reader. The original collector separately enforces Excel workbook
 # identity, RSS formula capacity, and local account UI shutdown.
 $phase='WORKER_AND_EXCEL_PROCESS_GUARDS'
 $running=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop |
   Where-Object {$_.ProcessId -ne $PID -and [string]$_.CommandLine -match
    '(?i)(Capture-No11RssTrainingBatchReadOnly|Prepare-No11PreviousArchiveReadOnly|Run-No11WeeklyCandidateRefreshReadOnly|Probe-No11Chart50ContinuousReadOnly|Run-No11ReceivedSessionReadOnly|Observe-No11AccountReadOnly)\.ps1'})
 Need ($running.Count -eq 0) 'OTHER_RSS_READER_ALREADY_RUNNING'
 Need (@(Get-Process EXCEL -ErrorAction SilentlyContinue).Count -eq 1) 'EXCEL_PROCESS_NOT_UNIQUE'
 $phase='CAPTURE_ATTEMPT_CHECKPOINT'
 [void][IO.Directory]::CreateDirectory($base)
 $done=Join-Path $base ('capture-complete-'+$prefix+'.json')
 $marker=Join-Path $base ('capture-started-'+$prefix+'.json')
 if(Test-Path -LiteralPath $done -PathType Leaf){
  $prior=Json $done
  Need ($prior.status -ceq 'COMPLETE_SOURCE_ONLY' -and
        $prior.originalReportSha256 -ceq (Hash $report) -and
        (Test-Path -LiteralPath $prior.captureDir -PathType Container)) 'PRIOR_COMPLETION_CHANGED'
  Write-Host 'NO11_EQUITY_FIVE=ALREADY_COMPLETED_NO_NEW_RSS'
  Write-Host 'NO11_EQUITY_FIVE_TRADING_PLAN_CREATED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 Need (-not (Test-Path -LiteralPath $marker)) 'PREVIOUS_ATTEMPT_REQUIRES_REVIEW'
 if($PreflightOnly){
  Write-Host 'NO11_EQUITY_FIVE_PREFLIGHT=PASS_NO_EXCEL_COM_NO_RSS_NO_ORDERS'
  Write-Host 'NO11_EQUITY_FIVE_REQUIRED_SYMBOLS=5'
  Write-Host 'NO11_EQUITY_FIVE_EXISTING_CAPTURE_MODIFIED=False'
  Write-Host 'EXCEL_TOUCHED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 $phase='PREPARING_FIVE_SOURCE_LIST'
 $names=Join-Path $base ('missing-five-'+$prefix+'.txt')
 $list=([string]::Join([char]10,$extra)+[char]10)
 if(Test-Path -LiteralPath $names -PathType Leaf){
  Need (([IO.File]::ReadAllText($names,[Text.UTF8Encoding]::new($false))) -ceq $list) 'PREVIOUS_MISSING_LIST_CHANGED'
 }else{
  [IO.File]::WriteAllText($names,$list,[Text.UTF8Encoding]::new($false))
 }
 $receipt=[ordered]@{schemaId='ARK_NO11_PROVISIONAL_FIVE_CAPTURE_REQUEST_V1'
  sourceReportSha256=(Hash $report);sourceStageSha256=(Hash $stageFile)
  expected=5;startedAtJst=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('o')
  productionReady=$false;orderTransmission=$false}
 $data=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $receipt -Compress)+[char]10)
 $phase='CAPTURE_ATTEMPT_COMMIT'
 $stream=[IO.File]::Open($marker,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($data,0,$data.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 Write-Host 'NO11_EQUITY_FIVE=START_REAL_RSS_PREVIOUS_1M_ONLY'
 Write-Host 'NO11_EQUITY_FIVE_COUNT=5'
 Write-Host 'NO11_EQUITY_FIVE_BATCH=5'
 Write-Host 'ORDER_TRANSMISSION=False'
 # Stream all original collector progress; NEVER buffer the entire Excel COM
 # work before the operator can see a progress receipt.
 $lines=@()
 $phase='RUNNING_FIVE_RSS_COLLECTOR'
 & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $collector -SymbolsFile $names -PrivateRoot $base -BatchSize 5 -WaitSeconds 25 -Bars 3000 -Period '1M' | Tee-Object -Variable lines
 $code=$LASTEXITCODE
 Need ($code -eq 0) 'COLLECTOR_FAILED_KEEP_RECEIPTS_FOR_REVIEW'
 $paths=@($lines|Where-Object {([string]$_).StartsWith('NO11_RSS_TRAINING_CAPTURE_DIR=')})
 Need ($paths.Count -eq 1) 'CAPTURE_DIR_NOT_REPORTED'
 $dir=([string]$paths[0]).Substring('NO11_RSS_TRAINING_CAPTURE_DIR='.Length)
 $fullDir=[IO.Path]::GetFullPath($dir)
 $fullBase=[IO.Path]::GetFullPath($base).TrimEnd([char]'\\')
 $isPrivate=$fullDir.StartsWith(($fullBase+'\\'),[StringComparison]::OrdinalIgnoreCase)
 Need ([IO.Path]::IsPathRooted($dir) -and $isPrivate -and
       (Test-Path -LiteralPath $dir -PathType Container)) 'CAPTURE_DIR_NOT_PRIVATE'
 $file=Join-Path $dir 'progress-00005.json'
 $phase='CAPTURE_RECEIPT_PROOF'
 $progress=Json $file
 Need ($progress.schemaId -ceq 'ARK_NO11_RSS_TRAINING_CAPTURE_PROGRESS_V1' -and
       $progress.completed -eq 5 -and $progress.requested -eq 5 -and
       $progress.observedSymbols -eq 5 -and $progress.unavailableSymbols -eq 0 -and
       $progress.productionReady -eq $false -and $progress.orderTransmission -eq $false -and
       (@($progress.files).Count -eq 5)) 'CAPTURE_CHECKPOINT_NOT_COMPLETE'
 $totalPriorRows=0
 $phase='FIVE_PREVIOUS_SESSION_ROW_PROOF'
 foreach($item in $progress.files){
  Need ($item.symbol -in $extra -and $item.status -ceq 'OBSERVED_ARCHIVE_NOT_TRAINING_CERTIFIED') 'ARCHIVE_MEMBER_STATUS'
  $f=Join-Path $dir ([string]$item.file)
  $a=Json $f
  Need ((Hash $f) -ceq $item.sha256 -and
    $a.schemaId -ceq 'ARK_NO11_RSS_TRAINING_SYMBOL_ARCHIVE_V1' -and
    $a.symbol -ceq $item.symbol -and $a.period -ceq '1M' -and
    $a.productionReady -eq $false -and $a.orderTransmission -eq $false) 'ARCHIVE_MEMBER_SHA_OR_SCHEMA'
  $n=@($a.rows|Where-Object {([string]$_.label).StartsWith('2026-10-29T')}).Count
  Need ($n -ge 2) 'PREVIOUS_SESSION_MINUTES_INSUFFICIENT'
  $totalPriorRows+=$n
 }
 $completed=[ordered]@{schemaId='ARK_NO11_PROVISIONAL_FIVE_CAPTURE_COMPLETE_V1'
   originalReportSha256=(Hash $report);captureDir=$dir
   previousSession='2026-10-29';symbols=5;previousMinuteRows=$totalPriorRows
   status='COMPLETE_SOURCE_ONLY';productionReady=$false;orderTransmission=$false}
 $doneBytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $completed -Compress)+[char]10)
 $phase='COMPLETION_COMMIT'
 $out=[IO.File]::Open($done,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$out.Write($doneBytes,0,$doneBytes.Length);$out.Flush($true)}finally{$out.Dispose()}
 Write-Host 'NO11_EQUITY_FIVE=CAPTURE_COMPLETE_FIVE_PRIOR_MINUTES_PRESENT'
 Write-Host ('NO11_EQUITY_FIVE_PREVIOUS_MINUTE_ROWS='+$totalPriorRows)
 Write-Host ('NO11_EQUITY_FIVE_CAPTURE_DIR='+$dir)
 Write-Host 'NO11_EQUITY_FIVE_OLD_47_RECOLLECTED=False'
 Write-Host 'NO11_EQUITY_FIVE_TRADING_PLAN_CREATED=False'
 Write-Host 'EXCEL_ORIGINALS_SAVED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_EQUITY_FIVE_[A-Z0-9_]+$'){
  $reason='NO11_EQUITY_FIVE_LOCAL_SOURCE_OR_RUNTIME_FAILURE'
 }
 # Diagnostic outputs disclose only a stage name and exception class.
 $kind=$_.Exception.GetType().Name
 if($kind -cnotmatch '^[A-Za-z0-9_]{1,80}$'){$kind='UNRECOGNIZED_EXCEPTION'}
 Write-Host ('NO11_EQUITY_FIVE_FAILURE_STAGE='+$phase)
 Write-Host ('NO11_EQUITY_FIVE_FAILURE_KIND='+$kind)
 Write-Host ('NO11_EQUITY_FIVE=BLOCKED|'+$reason)
 Write-Host 'NO11_EQUITY_FIVE_NO_RETRY_WITHOUT_REVIEW=True'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
