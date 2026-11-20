# No11 current observed G1 -> original chart -> REAL previous 1m source audit.
# INSTALLS ONLY ONE NEW JS AUDIT FILE, never modifies existing Ark/Frozen code.
# Any proposal is NOT a chart plan, no market/account/Excel COM or order I/O.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='290fa86a0c508dcadb715fc3b5a3d2af5486fd14'
$source='no11_equity_type_prescreen_audit.mjs'
$expected='ace7e9d9257a53ae213a45be5ae38c43b1ef733b'
$root='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011'
$local=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
$seed=Join-Path $local 'daily-trend-capture\daily-2026-10-26-e84a2ec53b0fdf41'
$daily=Join-Path $local 'weekly-pool-refresh\weekly-refresh-2026-10-29-862f03a3cdfa7d8f'
$previous=Join-Path $local 'previous-source\2026-10-30'
$output=Join-Path $local 'external-security-review\2026-10-30'
function Need([bool]$ok,[string]$code) {
 if(-not $ok){throw ('NO11_EQUITY_STAGE_'+$code)}
}
function Blob([string]$p){
 $h=@(& git hash-object --no-filters $p)
 Need ($LASTEXITCODE -eq 0 -and $h.Count -eq 1 -and $h[0] -match '^[a-f0-9]{40}$') 'HASH_FAILED'
 return [string]$h[0]
}
function UniqueFile([string]$dir,[string]$filter) {
 Need (Test-Path -LiteralPath $dir -PathType Container) 'DATA_FOLDER_MISSING'
 $matches=@(Get-ChildItem -LiteralPath $dir -File -Filter $filter -ErrorAction Stop)
 Need ($matches.Count -eq 1) 'SOURCE_RECEIPT_MISSING_OR_AMBIGUOUS'
 return [string]$matches[0].FullName
}
if($OfflineSelfTest){
 Need ($expected -match '^[a-f0-9]{40}$' -and $revision -match '^[a-f0-9]{40}$') 'PIN_CONTRACT'
 Write-Host 'NO11_EQUITY_TYPE_STAGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_EQUITY_TYPE_REVIEW_APPROVED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$installed=$false
$target=''
try{
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command node -ErrorAction Stop)
 Need (Test-Path -LiteralPath $seed -PathType Container) 'PINNED_G1_SEED_MISSING'
 Need (Test-Path -LiteralPath $daily -PathType Container) 'PINNED_DAILY_G1_MISSING'
 Need (Test-Path -LiteralPath $output -PathType Container) 'PRIVATE_REVIEW_ROOT_MISSING'
 $mask=UniqueFile $daily 'no11-observed-pass-watch-*.json'
 $chart=UniqueFile $daily 'no11-chart50-private-*.json'
 $stage=UniqueFile $previous 'previous-archive-stage-*.json'
 $tools=Join-Path $root 'tools'
 Need (Test-Path -LiteralPath $tools -PathType Container) 'ORIGINAL_TOOLS_MISSING'
 foreach($name in @('no11_verified_weekly_shadow_scope.mjs',
    'no11_weekly_g1_refresh.mjs','no11_rss_daily_trend_census.mjs')){
  Need (Test-Path -LiteralPath (Join-Path $tools $name) -PathType Leaf) 'AUDIT_DEPENDENCY_MISSING'
 }
 $target=Join-Path $tools $source
 if(Test-Path -LiteralPath $target){
  Need (Test-Path -LiteralPath $target -PathType Leaf) 'OUTPUT_ALREADY_DIRECTORY'
  Need ((Blob $target) -ceq $expected) 'LOCAL_AUDIT_FILE_CHANGED_NO_OVERWRITE'
  Write-Host 'NO11_EQUITY_TYPE_SOURCE=EXACT_ALREADY_INSTALLED'
 }else{
  $temp=Join-Path $env:TEMP ('no11-equity-type-'+[guid]::NewGuid().ToString('N')+'.mjs')
  try{
   $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
     '/research/no12-prebuy-causal-runtime-20261011/tools/'+$source
   Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $temp
   Need ((Blob $temp) -ceq $expected) 'GITHUB_SOURCE_HASH_MISMATCH'
   & node --check $temp
   Need ($LASTEXITCODE -eq 0) 'NODE_PARSE_FAILED'
   [IO.File]::Copy($temp,$target,$false)
   $installed=$true
   Need ((Blob $target) -ceq $expected) 'INSTALLED_HASH_CHANGED'
   Write-Host 'NO11_EQUITY_TYPE_SOURCE=PINNED_NEW_AUDIT_ONLY'
  }finally{
   if(Test-Path -LiteralPath $temp -PathType Leaf){[IO.File]::Delete($temp)}
  }
 }
 & node $target --seed-dir $seed --daily-run $daily --mask $mask --chart $chart --previous-stage $stage --output-root $output
 Need ($LASTEXITCODE -eq 0) 'AUDIT_SOURCE_OR_RANKING_FAILED'
 Write-Host 'NO11_EQUITY_TYPE_STAGE=PASS_PROVISIONAL_ONLY'
 Write-Host 'NO11_EQUITY_TYPE_ORIGINAL_CHART_MODIFIED=False'
 Write-Host 'NO11_EQUITY_TYPE_PREVIOUS_RSS_RECOLLECTED=False'
 Write-Host 'NO11_EQUITY_TYPE_REVIEW_APPROVED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 if($installed -and $target -and (Test-Path -LiteralPath $target -PathType Leaf)){
  [IO.File]::Delete($target)
 }
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_EQUITY_STAGE_[A-Z0-9_]+$'){$reason='NO11_EQUITY_STAGE_PRIVATE_SOURCE_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_EQUITY_TYPE_STAGE=BLOCKED|'+$reason)
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
