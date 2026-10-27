# Oct28 daytime direct read-only Shadow path: 27-close weekly G1 -> 28 original.
# Default: inspect only. -CaptureReference reads RSS once. -Preflight / -StartShadow
# require genuine external review and use original model/portfolio coordinator.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [string]$LocalRoot='',
 [string]$ReferenceFile='',
 [string]$SecurityEvidence='',
 [string]$EvidenceDocuments='',
 [string]$BootstrapTemplate='',
 [string]$PreviousCaptureDir='',
 [string]$SeedRun='',
 [string]$RefreshRun='',
 [switch]$CaptureReference,[switch]$Preflight,[switch]$StartShadow,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$yes,[string]$code){if(-not $yes){throw ('NO11_TODAY_SHADOW_'+$code)}}
function P([string]$filename,[bool]$folder=$false,[string]$role='SOURCE'){
 Need (-not [string]::IsNullOrWhiteSpace($filename) -and [IO.Path]::IsPathRooted($filename)) 'ABSOLUTE_PATH'
 $name=[IO.Path]::GetFullPath($filename)
 if(-not (Test-Path -LiteralPath $name -PathType $(if($folder){'Container'}else{'Leaf'}))){
  Write-Host ('NO11_TODAY_SHADOW_MISSING_PATH='+$role+'|'+$name)
  Need $false ('MISSING_'+$role)
 }
 $cursor=$name
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  Need (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_SOURCE'
  $next=Split-Path -Parent $cursor;if($next -ceq $cursor){break};$cursor=$next
 }
 return $name
}
function Single([string]$folder,[string]$pattern,[string]$code,[bool]$directories=$false){
 $list=@(Get-ChildItem -LiteralPath (P $folder $true) -Filter $pattern -ErrorAction Stop |
  Where-Object {if($directories){$_.PSIsContainer}else{-not $_.PSIsContainer}})
 Need ($list.Count -eq 1) $code
 return [string]$list[0].FullName
}
function ResolveDailySource([string]$base,[string]$explicit,[string]$pattern,
 [string]$session,[int]$members,[string]$role){
 if(-not [string]::IsNullOrWhiteSpace($explicit)){
  $folder=P $explicit $true $role
  $planFile=P (Join-Path $folder 'plan.json') $false ('PLAN_'+$role)
  $plan=Get-Content -LiteralPath $planFile -Raw -Encoding UTF8|ConvertFrom-Json
  Need ([string]$plan.asOfSession -ceq $session -and @($plan.symbols).Count -eq $members) ('WRONG_'+$role+'_SESSION_OR_SCOPE')
  return $folder
 }
 if(-not (Test-Path -LiteralPath $base -PathType Container)){
  Write-Host ('NO11_TODAY_SHADOW_MISSING='+$role+'_ROOT')
  Write-Host ('NO11_TODAY_SHADOW_LOOKED_IN='+$base)
  Need $false ('MISSING_'+$role+'_ROOT')
 }
 $entries=@(Get-ChildItem -LiteralPath $base -Directory -Filter $pattern -ErrorAction Stop)
 $valid=@()
 foreach($entry in $entries){
  $planFile=Join-Path $entry.FullName 'plan.json'
  if(-not (Test-Path -LiteralPath $planFile -PathType Leaf)){continue}
  try{
   $plan=Get-Content -LiteralPath $planFile -Raw -Encoding UTF8 | ConvertFrom-Json
   if([string]$plan.asOfSession -cne $session -or @($plan.symbols).Count -ne $members){continue}
   $sources=Join-Path $entry.FullName 'sources'
   if(-not (Test-Path -LiteralPath $sources -PathType Container)){continue}
   # This is only discovery. Original immutable SHA and full observation
   # checks are performed by the mandatory weekly verifier later.
   $valid+=@($entry.FullName)
  }catch{continue}
 }
 if($valid.Count -ne 1){
  Write-Host ('NO11_TODAY_SHADOW_DISCOVERY_'+$role+'='+$valid.Count+'|CANDIDATES='+$entries.Count)
  if($valid.Count -gt 1){Write-Host ('NO11_TODAY_SHADOW_'+$role+'_AMBIGUOUS_REQUIRE_EXPLICIT_PATH=True')}
  else{Write-Host ('NO11_TODAY_SHADOW_MISSING='+$role+'_COMPLETE_PLAN')}
  Need $false ('UNRESOLVED_'+$role)
 }
 Write-Host ('NO11_TODAY_SHADOW_FOUND_'+$role+'='+$valid[0])
 return P $valid[0] $true $role
}
function FromOutput([object[]]$lines,[string]$prefix){
 $match=@($lines|Where-Object {([string]$_).StartsWith($prefix,[StringComparison]::Ordinal)})
 Need ($match.Count -eq 1) 'RECEIPT_PATH_NOT_UNIQUE'
 return P (([string]$match[0]).Substring($prefix.Length))
}
if($OfflineSelfTest){
 Need (-not ($Preflight -and $StartShadow)) 'DOUBLE_LAUNCH'
 Write-Host 'NO11_TODAY_SHADOW_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_TODAY_SHADOW_EXCEL_OPENED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need (-not ($Preflight -and $StartShadow)) 'DOUBLE_LAUNCH'
 $date=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-dd')
 Need ($date -ceq '2026-10-28') 'SESSION_NOT_OCT28'
 if(-not $LocalRoot){$LocalRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'}
 $root=P $LocalRoot $true;$engine=P $EngineRoot $true
 [void](Get-Command node -ErrorAction Stop)
 $python=P (Join-Path $root 'frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe') $false 'PINNED_PYTHON'
 $seed=ResolveDailySource (Join-Path $root 'daily-trend-capture') $SeedRun 'daily-2026-10-26-*' '2026-10-26' 4328 'SEED_20261026'
 $run=ResolveDailySource (Join-Path $root 'weekly-pool-refresh') $RefreshRun 'weekly-refresh-2026-10-27-*' '2026-10-27' 429 'REFRESH_20261027'
 $mask=Single $run 'no11-observed-pass-watch-*.json' 'G1_MASK_MISSING_OR_AMBIGUOUS'
 $chart=Single $run 'no11-chart50-private-*.json' 'CHART_PLAN_MISSING_OR_AMBIGUOUS'
 $verify=P (Join-Path $engine 'tools\no11_verified_weekly_shadow_scope.mjs')
 $verified=@(& node $verify --run-dir $run --weekly-source-run $seed --mask $mask --chart $chart --session '2026-10-28')
 Need ($LASTEXITCODE -eq 0 -and $verified -contains 'NO11_WEEKLY_SHADOW_SCOPE=PASS_OBSERVED_NOT_EXTERNALLY_REVIEWED') 'WEEKLY_G1_CHART_NOT_VERIFIED'
 Write-Host 'NO11_TODAY_SHADOW_G1_CHART=PASS_FROM_ACTUAL_OCT27'
 $prior=Join-Path $root 'previous-source\2026-10-28'
 $stageFiles=@(Get-ChildItem -LiteralPath $prior -Filter 'previous-archive-stage-*.json' -File -ErrorAction SilentlyContinue)
 if($stageFiles.Count -eq 1){Write-Host 'NO11_TODAY_SHADOW_PREVIOUS_ARCHIVE=STAGED_NOT_MASTER'}
 else{Write-Host 'NO11_TODAY_SHADOW_MISSING=PREVIOUS_MINUTE_STAGE'}
 $refRoot=Join-Path $root 'session-reference\2026-10-28'
 if(-not (Test-Path -LiteralPath $refRoot)){[void][IO.Directory]::CreateDirectory($refRoot)}
 $refRoot=P $refRoot $true
 if($CaptureReference){
  Need (-not ($StartShadow -or $Preflight)) 'CAPTURE_AND_LAUNCH_CONFLICT'
  $clock=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('HH:mm:ss')
  Need ($clock -cge '09:00:00' -and $clock -cle '15:20:00') 'MARKET_NOT_OPEN'
  Need (@(Get-ChildItem -LiteralPath $refRoot -Filter 'session-reference-*.json' -File).Count -eq 0) 'REFERENCE_ALREADY_EXISTS'
  $scope=P (Join-Path $engine 'tools\no11_previous_archive_context.py')
  $symbolsOutput=@(& $python -B $scope --plan $chart --mask $mask --output-root $refRoot --symbols-only)
  Need ($LASTEXITCODE -eq 0) 'ORIGINAL_SYMBOL_SCOPE_INVALID'
  $symbols=FromOutput $symbolsOutput 'NO11_PREVIOUS_SYMBOLS_FILE='
  $collector=P (Join-Path $engine 'windows\Capture-No11SessionReferenceReadOnly.ps1')
  $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$collector,
   '-SymbolsFile',$symbols,'-ChartPlanFile',$chart,'-OutputRoot',$refRoot)
  $output=@(& powershell.exe @args)
  Need ($LASTEXITCODE -eq 0) 'ACTUAL_RSS_REFERENCE_FAILED'
  $reference=FromOutput $output 'NO11_SESSION_REFERENCE_FILE='
  $diag=P (Join-Path $engine 'tools\no11_reference_fields_diagnostic.mjs')
  $audit=@(& node $diag --reference $reference --session '2026-10-28')
  Need ($LASTEXITCODE -eq 0 -and
   $audit -contains 'NO11_REFERENCE_DIAG_STATUS=FIELDS_PRESENT_NOT_EXTERNALLY_REVIEWED') 'REFERENCE_UNVERIFIED'
  $audit|Where-Object {$_ -match '^(NO11_REFERENCE_DIAG_ROWS_COMPLETE=|NO11_REFERENCE_DIAG_MARKET_SECTION_RECOGNIZED=|NO11_REFERENCE_DIAG_STATUS=)'}|ForEach-Object{Write-Host $_}
  Write-Host 'NO11_TODAY_SHADOW_REFERENCE=OBSERVED_NOT_EXTERNALLY_REVIEWED'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 if(-not ($Preflight -or $StartShadow)){
  Write-Host 'NO11_TODAY_SHADOW_MODE=DISK_INSPECT_ONLY'
  $saved=@(Get-ChildItem -LiteralPath $refRoot -Filter 'session-reference-*.json' -File)
  if($saved.Count -eq 1){Write-Host 'NO11_TODAY_SHADOW_REFERENCE=FILE_PRESENT_NOT_EXTERNALLY_REVIEWED'}
  else{Write-Host 'NO11_TODAY_SHADOW_MISSING=ACTUAL_TODAY_REFERENCE'}
  if(-not $SecurityEvidence){Write-Host 'NO11_TODAY_SHADOW_MISSING=INDEPENDENT_SECURITY_EVIDENCE'}
  if(-not $EvidenceDocuments){Write-Host 'NO11_TODAY_SHADOW_MISSING=INDEPENDENT_SOURCE_DOCUMENTS'}
  if(-not $BootstrapTemplate){Write-Host 'NO11_TODAY_SHADOW_MISSING=EXISTING_SHADOW_BOOTSTRAP_TEMPLATE'}
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 Need ($stageFiles.Count -eq 1) 'PREVIOUS_STAGE_REQUIRED'
 if(-not $ReferenceFile){$ReferenceFile=Single $refRoot 'session-reference-*.json' 'REFERENCE_RECEIPT_REQUIRED'}
 $reference=P $ReferenceFile
 $evidence=P $SecurityEvidence
 $documents=P $EvidenceDocuments $true
 $template=P $BootstrapTemplate
 if(-not $PreviousCaptureDir){
  $captureDirs=@(Get-ChildItem -LiteralPath (P $prior $true) -Directory -Filter 'rss-*' |
   Where-Object {@(Get-ChildItem -LiteralPath $_.FullName -File -Filter 'progress-*.json').Count -gt 0})
  Need ($captureDirs.Count -eq 1) 'PREVIOUS_CAPTURE_DIR_AMBIGUOUS'
  $PreviousCaptureDir=$captureDirs[0].FullName
 }
 $captures=P $PreviousCaptureDir $true
 $config=Get-Content -LiteralPath $template -Raw -Encoding UTF8 | ConvertFrom-Json
 Need ($config.schemaId -ceq 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1' -and
  $config.productionReady -eq $false -and $config.orderTransmission -eq $false) 'TEMPLATE_NOT_READONLY'
 $config.sessionDate='2026-10-28'
 $config.dailyRun=$run
 if('pinsFile' -in $config.PSObject.Properties.Name){$config.PSObject.Properties.Remove('pinsFile')}
 foreach($pair in @(@('precomputedChartReceipt',$chart),@('precomputedG1Mask',$mask),@('weeklySourceRun',$seed))){
  if($pair[0] -in $config.PSObject.Properties.Name){$config.($pair[0])=$pair[1]}
  else{$config|Add-Member -NotePropertyName $pair[0] -NotePropertyValue $pair[1]}
 }
 $private=Join-Path $root 'fast-shadow-2026-10-28'
 [void][IO.Directory]::CreateDirectory($private)
 $templateOut=Join-Path $private 'weekly-bootstrap-template.json'
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $config -Depth 32 -Compress)+[char]10)
 if(Test-Path -LiteralPath $templateOut){
  Need ([Convert]::ToBase64String([IO.File]::ReadAllBytes($templateOut)) -ceq [Convert]::ToBase64String($bytes)) 'BOOTSTRAP_TEMPLATE_COLLISION'
 }else{
  $stream=[IO.File]::Open($templateOut,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 }
 $assemble=P (Join-Path $engine 'tools\no11_prepare_received_inputs.py')
 $assembly=@(& $python -B $assemble --plan $chart --mask $mask --reference-file $reference --security-evidence $evidence --evidence-documents $documents --previous-capture-dir $captures --bootstrap-config $templateOut --output-root $private)
 Need ($LASTEXITCODE -eq 0) 'MASTER_PREVIOUS_CONTEXT_ASSEMBLY_FAILED'
 $ready=FromOutput $assembly 'NO11_INPUTS_PREPARED_CONFIG='
 $runner=P (Join-Path $engine 'windows\Run-No11ReceivedSessionReadOnly.ps1')
 $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,'-ConfigFile',$ready,'-PythonExecutable',$python)
 if($Preflight){$args+=@('-PreflightOnly')}
 & powershell.exe @args
 Need ($LASTEXITCODE -eq 0) 'ORIGINAL_SHADOW_PREFLIGHT_OR_RUN_FAILED'
 Write-Host ('NO11_TODAY_SHADOW_RESULT='+$(if($Preflight){'ORIGINAL_PREFLIGHT_PASS'}else{'ORIGINAL_SHADOW_COMPLETED'}))
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_TODAY_SHADOW_[A-Z0-9_]+$'){$reason='NO11_TODAY_SHADOW_PRIVATE_SOURCE_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_TODAY_SHADOW=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
