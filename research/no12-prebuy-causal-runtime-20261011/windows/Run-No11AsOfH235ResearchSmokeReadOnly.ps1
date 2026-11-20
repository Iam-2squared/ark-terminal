# H2/H3/H5 historical research model smoke on Windows, offline only.
# No Excel, no RSS, no network calls, no account or broker functions, no orders.
param([switch]$OfflineSelfTest,[string]$ResearchKit)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$bundleHash='c932fafa4a50746a2ce7852f5825b4627ac7c7a9c442a30a042709a9c886c46e'
$scoreRel='research/no12-prebuy-causal-runtime-20261011/tools/no11_asof_research_score_offline.py'
$scoreBlob='65bb08e49c0cc10cb9efdef4094e610e9eef9f1a'
$manifestRel='private/BUNDLE_MANIFEST.json'
$fixtureRel='private/fixture/known_2025_buy_intent_feature.json'
$heads=@('H2','H3','H5')

if($OfflineSelfTest){
 if($heads.Count -ne 3 -or $bundleHash.Length -ne 64 -or
    $scoreBlob.Length -ne 40 -or $scoreRel -notlike 'research/*' -or
    $manifestRel -ne 'private/BUNDLE_MANIFEST.json'){
   throw 'NO11_ASOF_RESEARCH_SMOKE_SELFTEST_INVALID'
 }
 Write-Host 'NO11_ASOF_RESEARCH_SMOKE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_LIVE_DATA_ACCESSED=False'
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}

if([string]::IsNullOrWhiteSpace($ResearchKit) -or
   -not (Test-Path -LiteralPath $ResearchKit -PathType Leaf)){
 throw 'NO11_ASOF_RESEARCH_SMOKE_KIT_MISSING'
}
$actualHash=(Get-FileHash -LiteralPath $ResearchKit -Algorithm SHA256).Hash.ToLowerInvariant()
if($actualHash -cne $bundleHash){throw 'NO11_ASOF_RESEARCH_SMOKE_KIT_HASH_INVALID'}

$repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path
$scorer=Join-Path $repo $scoreRel
if(-not (Test-Path -LiteralPath $scorer -PathType Leaf)){
 throw 'NO11_ASOF_RESEARCH_SMOKE_SCORER_MISSING'
}
$blob=git -C $repo hash-object "--path=$scoreRel" $scorer
if($LASTEXITCODE -ne 0 -or $blob -cne $scoreBlob){
 throw 'NO11_ASOF_RESEARCH_SMOKE_SCORER_BLOB_MISMATCH'
}

# Files are created only inside a fresh local PRIVATE directory.
$base=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\research-h235-smoke'
[void][IO.Directory]::CreateDirectory($base)
$stage=Join-Path $base ('offline-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($stage)
Expand-Archive -LiteralPath $ResearchKit -DestinationPath $stage -ErrorAction Stop

$manifestPath=Join-Path $stage $manifestRel
$manifest=Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if($manifest.schemaId -cne 'ARK_NO11_ASOF_H235_RESEARCH_SHADOW_SMOKE_BUNDLE_V1' -or
   $manifest.productionReady -ne $false -or $manifest.orderTransmission -ne $false -or
   $manifest.modelFrom2026Data -ne $false -or
   $manifest.originalFrozenReplaced -ne $false -or
   $manifest.githubScoreFile -cne $scoreRel -or
   $manifest.githubScoreFileBlob -cne $scoreBlob){
 throw 'NO11_ASOF_RESEARCH_SMOKE_MANIFEST_UNEXPECTED'
}
$hashes=@($manifest.sourceFilesSHA256.PSObject.Properties)
if($hashes.Count -ne 4){throw 'NO11_ASOF_RESEARCH_SMOKE_SOURCE_COUNT_INVALID'}
foreach($entry in $hashes){
 $relative=[string]$entry.Name
 if($relative -notmatch '^private/(models|fixture)/[A-Za-z0-9_./-]+\.json$' -or
    $relative.Contains('..')){
  throw 'NO11_ASOF_RESEARCH_SMOKE_UNSAFE_PATH'
 }
 $file=Join-Path $stage $relative
 if(-not (Test-Path -LiteralPath $file -PathType Leaf)){
  throw 'NO11_ASOF_RESEARCH_SMOKE_SOURCE_MISSING'
 }
 $expectedHash=[string]$entry.Value
 if((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expectedHash){
  throw 'NO11_ASOF_RESEARCH_SMOKE_SOURCE_HASH_INVALID'
 }
}

$fixture=Join-Path $stage $fixtureRel
foreach($head in $heads){
 $model=Join-Path $stage ('private/models/{0}_ASOF_2025_DEV.json' -f $head)
 $receipt=Join-Path $stage ('private/{0}_score_result.json' -f $head)
 & py -3.12 -B $scorer --mode OFFLINE_RESEARCH_ONLY --model $model --features $fixture --output $receipt
 if($LASTEXITCODE -ne 0){throw ('NO11_ASOF_RESEARCH_SMOKE_SCORER_FAILED_'+$head)}
 $payload=Get-Content -LiteralPath $receipt -Raw -Encoding UTF8 | ConvertFrom-Json
 $expected=[double]$manifest.expectedOfflineResearchProbabilities.PSObject.Properties[$head].Value
 if($payload.mode -cne 'OFFLINE_RESEARCH_ONLY' -or
    $payload.productionReady -ne $false -or $payload.orderTransmission -ne $false -or
    $payload.head -cne $head -or
    [math]::Abs([double]$payload.research_probability-$expected) -gt 1e-10){
  throw ('NO11_ASOF_RESEARCH_SMOKE_SCORE_PARITY_FAILED_'+$head)
 }
 Write-Host ('NO11_ASOF_RESEARCH_SMOKE_{0}=PASS|P={1:f12}' -f $head,[double]$payload.research_probability)
}
Write-Host 'NO11_ASOF_RESEARCH_SMOKE=PASS_DEVELOPMENT_ONLY'
Write-Host ('NO11_ASOF_RESEARCH_SMOKE_PRIVATE_DIR='+$stage)
Write-Host 'NO11_NATIVE_SELECTOR_AND_ENTRY_CONNECTED=False'
Write-Host 'NO11_PRODUCTION_READY=False'
Write-Host 'ORDER_TRANSMISSION=False'
