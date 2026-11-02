# Recover the REAL 2026-10-28 D100 daily G1 pool on 2026-10-29.
# This only updates a known ORIGINAL pre-Yahoo Node G1 CLI that lacked
# --catch-up-asof, and resumes the SAME preexisting private 429-member run.
# It never rewrites plan.json, sources, original Excel books, Frozen code,
# shadow ledgers or broker settings. No orders.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [string]$WeeklyRun='',
 [string]$PrivateRoot='',
 [ValidateSet(50,100)][int]$GroupSize=100,
 [ValidateRange(1,20)][int]$BatchSize=15,
 [ValidateRange(5,60)][int]$WaitSeconds=35,
 [switch]$OfflineSelfTest,
 [switch]$RepairOnly
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$oldBlobs=@(
 'cb552dc9997ce072bdf535293adfc08178a1d266',
 '8b9d1ed70284be8fb2a41aec711482417c1e15a7',
 'c6ac1700595b8025838862151c699e1c1ff6258c',
 '9e01a5e826730661455050c865dd2e0a1a0d8fc3',
 '2f61dd9d14180f50040d6350607768fee97aca87'
)
$targetBlob='26cb29af530e5b7a0f736c728fd96e156d3e840a'
$latestBlob='577882a0aa18c747734b905316a1bbbbeff1145e'
$revision='a007e77587a4a3ee5c7ef413f290567b3ab5910d'
$targetAsOf='2026-10-28'
function Need([bool]$ok,[string]$code){
 if(-not $ok){throw ('NO11_OCT29_RESUME_'+$code)}
}
function Blob([string]$p){
 $lines=@(& git hash-object --no-filters $p)
 Need ($LASTEXITCODE -eq 0 -and $lines.Count -eq 1 -and
   [string]$lines[0] -cmatch '^[0-9a-f]{40}$') 'HASH_UNAVAILABLE'
 return ([string]$lines[0])
}
function SafePath([string]$path,[bool]$directory=$false){
 Need (-not [string]::IsNullOrWhiteSpace($path) -and [IO.Path]::IsPathRooted($path)) 'ABSOLUTE_PATH_REQUIRED'
 $p=[IO.Path]::GetFullPath($path)
 Need (Test-Path -LiteralPath $p -PathType $(if($directory){'Container'}else{'Leaf'})) 'SOURCE_NOT_FOUND'
 $cur=$p
 while(-not [string]::IsNullOrWhiteSpace($cur)){
  Need (((Get-Item -LiteralPath $cur -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_SOURCE_FORBIDDEN'
  $next=Split-Path -Parent $cur
  if($next -ceq $cur){break}
  $cur=$next
 }
 return $p
}
function AssertReservedScope($plan,[string]$run,[string]$seedPlanId){
 Need ($plan.schemaId -ceq 'ARK_NO11_RSS_DAILY_CENSUS_PLAN_V1' -and
  $plan.refreshSchemaId -ceq 'ARK_NO11_WEEKLY_G1_DAILY_REFRESH_PLAN_V1' -and
  $plan.asOfSession -ceq $targetAsOf -and
  @($plan.symbols).Count -eq 429 -and
  $plan.weeklySource.originalPlanId -ceq $seedPlanId -and
  $plan.productionReady -eq $false -and $plan.orderTransmission -eq $false) 'EXISTING_PLAN_IDENTITY_INVALID'
 Need (Test-Path -LiteralPath (Join-Path $run 'sources') -PathType Container) 'EXISTING_SOURCES_MISSING'
 $files=@(Get-ChildItem -LiteralPath (Join-Path $run 'sources') -File -Filter '*.json' -ErrorAction Stop)
 Need ($files.Count -ge 260 -and $files.Count -le 429) 'EXISTING_260_RECEIPTS_MISSING'
 return $files.Count
}
if($OfflineSelfTest){
 Need ($targetBlob -cmatch '^[0-9a-f]{40}$' -and $targetBlob -cnotin $oldBlobs -and
  $oldBlobs.Count -eq 5 -and $BatchSize -le 20 -and
  $targetAsOf -ceq '2026-10-28') 'STATIC_SAFE_CONFIG_INVALID'
 Write-Host 'NO11_OCT29_RESUME_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_OCT29_RESUME_EXCEL_TOUCHED=False'
 Write-Host 'NO11_OCT29_RESUME_RECEIPTS_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command node -ErrorAction Stop)
 [void](Get-Command powershell.exe -ErrorAction Stop)
 $today=[datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9))
 Need ($today.ToString('yyyy-MM-dd') -ceq '2026-10-29' -and
  $today.ToString('HH:mm') -cge '08:30' -and $today.ToString('HH:mm') -clt '18:00') 'RECOVERY_WINDOW_CLOSED'
 $engine=SafePath $EngineRoot $true
 $tool=SafePath (Join-Path $engine 'tools\no11_weekly_g1_refresh.mjs')
 $collector=SafePath (Join-Path $engine 'windows\Run-No11WeeklyCandidateRefreshReadOnly.ps1')
 if(-not $WeeklyRun){
  $WeeklyRun=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\daily-trend-capture\daily-2026-10-26-e84a2ec53b0fdf41'
 }
 if(-not $PrivateRoot){
  $PrivateRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\weekly-pool-refresh'
 }
 $seed=SafePath $WeeklyRun $true
 $root=SafePath $PrivateRoot $true
 $seedPlan=Get-Content -LiteralPath (SafePath (Join-Path $seed 'plan.json')) -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($seedPlan.schemaId -ceq 'ARK_NO11_RSS_DAILY_CENSUS_PLAN_V1' -and
  $seedPlan.asOfSession -ceq '2026-10-26' -and
  @($seedPlan.symbols).Count -eq 4328 -and
  [string]$seedPlan.planId -cmatch '^[0-9a-f]{64}$') 'ORIGINAL_WEEKLY_SEED_MISMATCH'
 $existingRun=SafePath (Join-Path $root ('weekly-refresh-2026-10-28-'+$seedPlan.planId.Substring(0,16))) $true
 $plan=Get-Content -LiteralPath (SafePath (Join-Path $existingRun 'plan.json')) -Raw -Encoding UTF8|ConvertFrom-Json
 $n=AssertReservedScope $plan $existingRun ([string]$seedPlan.planId)
 Write-Host ('NO11_OCT29_RESUME_EXISTING_RECEIPTS='+$n+'/429')
 # Do not change code while another collection is live.
 $busy=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop |
  Where-Object { $_.ProcessId -ne $PID -and
    [string]$_.CommandLine -match '(?i)(Run-No11WeeklyCandidateRefreshReadOnly|Run-No11WeeklyCandidateCatchUpReadOnly|Prepare-No11WeeklyAfterCloseReadOnly|Run-No11Oct28CatchUpReadOnly)\.ps1' })
 Need ($busy.Count -eq 0) 'RSS_COLLECTOR_ALREADY_RUNNING'
 $current=Blob $tool
 Write-Host ('NO11_OCT29_RESUME_LOCAL_TOOL_BLOB='+$current)
 Need ($current -cin ($oldBlobs+@($targetBlob,$latestBlob))) 'LOCAL_TOOL_HAS_UNREVIEWED_CHANGES_NO_OVERWRITE'
 if($current -cin $oldBlobs){
  $job=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\oct29-morning-catchup-fix\'+[guid]::NewGuid().ToString('N'))
  $stage=Join-Path $job 'staged'
  $backups=Join-Path $job 'backups'
  [void][IO.Directory]::CreateDirectory($stage)
  [void][IO.Directory]::CreateDirectory($backups)
  $new=Join-Path $stage 'no11_weekly_g1_refresh.mjs'
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
    '/research/no12-prebuy-causal-runtime-20261011/tools/no11_weekly_g1_refresh.mjs'
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $new
  Need ((Blob $new) -ceq $targetBlob) 'PINNED_DOWNLOAD_HASH_MISMATCH'
  & node --check $new
  Need ($LASTEXITCODE -eq 0) 'NODE_PARSE_FAILED'
  $backup=Join-Path $backups 'no11_weekly_g1_refresh.mjs.bak'
  [IO.File]::Copy($tool,$backup,$false)
  try{
   [IO.File]::Copy($new,$tool,$true)
   Need ((Blob $tool) -ceq $targetBlob) 'INSTALLED_TOOL_HASH_MISMATCH'
  }catch{
   [IO.File]::Copy($backup,$tool,$true)
   throw
  }
  Write-Host 'NO11_OCT29_RESUME_CATCHUP_TOOL=PINNED_COMPATIBILITY_PATCH_APPLIED'
  Write-Host ('NO11_OCT29_RESUME_CODE_BACKUP='+$backup)
 }else{
  Write-Host 'NO11_OCT29_RESUME_CATCHUP_TOOL=ALREADY_SUPPORTED'
 }
 # Read the original 429-member source with the CURRENT receipt clocks.
 # The original plan and all 260 saved receipts remain immutable.
 $args=@('plan','--weekly-run',$seed,'--root',$root,
  '--catch-up-asof',$targetAsOf)
 $json=@(& node $tool @args)
 Need ($LASTEXITCODE -eq 0 -and $json.Count -eq 1) 'CATCHUP_PLAN_FAILED'
 $result=[string]$json[0]|ConvertFrom-Json
 Need ([IO.Path]::GetFullPath([string]$result.run).Equals($existingRun,[StringComparison]::OrdinalIgnoreCase) -and
  $result.plan.asOfSession -ceq $targetAsOf -and
  $result.resumed -ge 260 -and $result.resumed -le 429 -and
  @($result.remaining).Count -eq (429-[int]$result.resumed)) 'RESUMED_PLAN_NOT_SAME_260_RECEIPTS'
 Write-Host ('NO11_OCT29_RESUME_VERIFIED='+$result.resumed+'/429|REMAINING='+@($result.remaining).Count)
 if($RepairOnly){
  Write-Host 'NO11_OCT29_RESUME=PLAN_READY_REQUIRES_RUN'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 $powershellArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',
   $collector,'-WeeklyRun',$seed,'-PrivateRoot',$root,
   '-CatchUpAsOf',$targetAsOf,
   '-GroupSize',[string]$GroupSize,
   '-BatchSize',[string]$BatchSize,
   '-WaitSeconds',[string]$WaitSeconds)
 & powershell.exe @powershellArgs
 $collectorExit=$LASTEXITCODE
 Need ($collectorExit -eq 0) 'RSS_FAILED_RECEIPTS_PRESERVED'
 Write-Host 'NO11_OCT29_RESUME=COMPLETE_PRIOR_CASH_DAY_NOT_REAL_TRADE_CERTIFIED'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_OCT29_RESUME_[A-Z0-9_]+$'){$reason='NO11_OCT29_RESUME_PRIVATE_OR_RUNTIME_FAILED'}
 Write-Host ('NO11_OCT29_RESUME=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
