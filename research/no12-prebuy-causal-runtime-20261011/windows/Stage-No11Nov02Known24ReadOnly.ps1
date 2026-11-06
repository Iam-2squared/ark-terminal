# Derive an exact 24-candidate Monday source scope from the verified Friday
# Chart47/previous archive. Known JPX month-end class is NOT same-day clearance.
# Never modifies the original 429 captures, 47/47 archives, broker or order.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='12cbffea51dae8ba38c4d606e67434272459a924'
$sha='f83e49a73889632b389ebfbbf8b680489e78815f'
$toolRel='research/no12-prebuy-causal-runtime-20261011/tools/no11_stage_nov02_provisional_24_readonly.mjs'
$engine=Join-Path 'C:\ArkTerminal\no11-unified-2026-10-30' 'research\no12-prebuy-causal-runtime-20261011'
$root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
$run=Join-Path $root 'weekly-pool-refresh\weekly-refresh-2026-10-30-862f03a3cdfa7d8f'
$seed=Join-Path $root 'daily-trend-capture\daily-2026-10-26-e84a2ec53b0fdf41'
$oldStage=Join-Path $root 'previous-source\2026-11-02\previous-archive-stage-a245534d49410828240d96674a151a51251bdb75f3f006c6741a3e308d9fcf8f.json'
$jpx=Join-Path $root 'jpx-month-end-reference\2026-10-30\jpx-monthly-equity-reference-2c8176654719a18f7a63fec24d8b7dbca894a3df5dda6dba14debd1cc7279979.json'
$capture=Join-Path $root 'previous-source\2026-11-02\rss-9dae5a81d0134568b22d06e28fb90d21'
$python=Join-Path $root 'frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
$output=Join-Path $root 'previous-source\2026-11-02\provisional-24'
function Need([bool]$ok,[string]$reason){if(-not $ok){throw ('NO11_NOV02_24_WINDOWS_'+$reason)}}
function UniqueLine([string[]]$lines,[string]$prefix){
 $hit=@($lines | Where-Object { ([string]$_).StartsWith($prefix,[StringComparison]::Ordinal) })
 Need ($hit.Count -eq 1) 'RESULT_NOT_UNIQUE'
 return ([string]$hit[0]).Substring($prefix.Length)
}
if($OfflineSelfTest){
 Need ($revision -match '^[a-f0-9]{40}$' -and
       $sha -match '^[a-f0-9]{40}$' -and
       $toolRel -like '*.mjs') 'STATIC_PINS_INVALID'
 Write-Host 'NO11_NOV02_24_WINDOWS_OFFLINE_SELFTEST=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$temp=''
try{
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command node -ErrorAction Stop)
 foreach($p in @($engine,$run,$seed,$capture)){
  Need (Test-Path -LiteralPath $p -PathType Container) 'PREVIOUS_SOURCE_DIRECTORY_MISSING'
 }
 foreach($p in @($oldStage,$jpx,$python)){
  Need (Test-Path -LiteralPath $p -PathType Leaf) 'PREVIOUS_VERIFIED_FILE_MISSING'
 }
 Need (Test-Path -LiteralPath (Join-Path $engine 'tools\no11_previous_archive_context.py') -PathType Leaf) 'ARCHIVE_CONVERTER_MISSING'
 $expected=(Get-FileHash -LiteralPath $oldStage -Algorithm SHA256).Hash.ToLowerInvariant()
 Need ($expected -ceq 'a245534d49410828240d96674a151a51251bdb75f3f006c6741a3e308d9fcf8f') 'PREVIOUS_STAGE_DIGEST_CHANGED'
 $previous=Get-Content -LiteralPath $oldStage -Raw -Encoding UTF8 | ConvertFrom-Json
 Need (@($previous.selectedSymbols).Count -eq 47 -and
       $previous.sessionDate -ceq '2026-11-02' -and
       $previous.orderTransmission -eq $false) 'PREVIOUS_47_SOURCE_CHANGED'
 $temp=Join-Path $env:TEMP ('Ark-24-Nov02-'+[guid]::NewGuid().ToString('N')+'.mjs')
 Invoke-WebRequest -UseBasicParsing -Uri ('https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+'/'+$toolRel) -OutFile $temp
 $blob=@(& git hash-object --no-filters $temp)
 Need ($LASTEXITCODE -eq 0 -and $blob.Count -eq 1 -and [string]$blob[0] -ceq $sha) 'DOWNLOADED_HELPER_BLOB_MISMATCH'
 $lines=@(& node $temp --engine $engine --run $run --seed $seed --stage $oldStage --jpx $jpx)
 $status=$LASTEXITCODE
 $lines | ForEach-Object {Write-Host $_}
 Need ($status -eq 0) 'SCOPE_HELPER_FAILED'
 $chart=UniqueLine $lines 'NO11_NOV02_24_CHART='
 $mask=UniqueLine $lines 'NO11_NOV02_24_MASK='
 Need ((Test-Path -LiteralPath $chart -PathType Leaf) -and
       (Test-Path -LiteralPath $mask -PathType Leaf)) 'SCOPED_CHART_FILES_MISSING'
 [void][IO.Directory]::CreateDirectory($output)
 $archiveTool=Join-Path $engine 'tools\no11_previous_archive_context.py'
 $prior=@(& $python -B $archiveTool --plan $chart --mask $mask --output-root $output --capture-dir $capture)
 $code=$LASTEXITCODE
 $prior | ForEach-Object {Write-Host $_}
 Need ($code -eq 0 -and
       ($prior -contains 'NO11_PREVIOUS_ARCHIVE_USABLE=24') -and
       ($prior -contains 'NO11_PREVIOUS_ARCHIVE_MISSING=0')) '24_PREVIOUS_DATA_NOT_USABLE'
 Write-Host 'NO11_NOV02_24=SCOPED_24_AND_PREVIOUS_ARCHIVES_READY'
 Write-Host 'NO11_NOV02_24_EXTERNAL_CURRENT_SESSION_REVIEW=NOT_DONE'
 Write-Host 'NO11_NOV02_24_LIVE_BOOTSTRAP=NOT_CREATED'
 Write-Host 'NO11_NOV02_24_EXISTING_47_ARCHIVE_MODIFIED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 $message=$_.Exception.Message
 if($message -cnotmatch '^NO11_NOV02_24_WINDOWS_[A-Z0-9_]+$'){
  $message='NO11_NOV02_24_WINDOWS_SOURCE_OR_LOCAL_VALIDATION_FAILED'
 }
 Write-Host ('NO11_NOV02_24=BLOCKED|'+$message)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if($temp -and (Test-Path -LiteralPath $temp -PathType Leaf)){
  Remove-Item -LiteralPath $temp -Force
 }
}
