# Prepare the already observed Oct27 47/47 real RSS review queue, without Excel.
# Safe to run while a DIFFERENT read-only chart collector uses the physical
# Excel session: this wrapper touches only immutable private files.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [string]$LocalRoot='',
 [string]$ReferenceFile='',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_DAY_REVIEW_'+$reason)}
}
function PrivateFile([string]$p) {
 Need (-not [string]::IsNullOrWhiteSpace($p) -and [IO.Path]::IsPathRooted($p)) 'ABSOLUTE_SOURCE_REQUIRED'
 $full=[IO.Path]::GetFullPath($p)
 Need (Test-Path -LiteralPath $full -PathType Leaf) 'SOURCE_FILE_MISSING'
 $cursor=$full
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  Need (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'SOURCE_REPARSE'
  $next=Split-Path -Parent $cursor
  if($next -ceq $cursor){break}
  $cursor=$next
 }
 return $full
}
if($OfflineSelfTest){
 Need ('2026-10-27' -cne '2026-10-28') 'DATE_CONTRACT'
 Write-Host 'NO11_DAY_REVIEW_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_DAY_REVIEW_EXCEL_OPENED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 if([string]::IsNullOrWhiteSpace($LocalRoot)){
  $LocalRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
 }
 Need ([IO.Path]::IsPathRooted($LocalRoot) -and (Test-Path -LiteralPath $LocalRoot -PathType Container)) 'LOCAL_ROOT_MISSING'
 $local=[IO.Path]::GetFullPath($LocalRoot)
 $seed=Join-Path $local 'daily-trend-capture\daily-2026-10-26-e84a2ec53b0fdf41'
 $plan=PrivateFile (Join-Path $seed 'no11-chart50-private-a9d57cdb4eccb107.json')
 $mask=PrivateFile (Join-Path $seed 'no11-observed-pass-watch-ce769aac846cf1b4.json')
 $referenceDir=Join-Path $local 'session-reference\2026-10-27'
 Need (Test-Path -LiteralPath $referenceDir -PathType Container) 'REFERENCE_DIRECTORY_MISSING'
 if([string]::IsNullOrWhiteSpace($ReferenceFile)){
  $options=@(Get-ChildItem -LiteralPath $referenceDir -Filter 'session-reference-*.json' -File |
   Sort-Object LastWriteTime -Descending)
  Need ($options.Count -gt 0) 'NO_REFERENCE_RECEIPT'
  $ReferenceFile=$options[0].FullName
 }
 $reference=PrivateFile $ReferenceFile
 $root=[IO.Path]::GetFullPath((Join-Path $EngineRoot '..\..\..'))
 Need (-not $reference.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) 'REFERENCE_IN_REPOSITORY'
 $python=Join-Path $local 'frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
 $python=PrivateFile $python
 $review=PrivateFile (Join-Path $EngineRoot 'tools\no11_review_queue_from_actual_rss.py')
 $diagnostic=PrivateFile (Join-Path $EngineRoot 'tools\no11_reference_fields_diagnostic.mjs')
 [void](Get-Command node -ErrorAction Stop)
 $lines=@(& node $diagnostic --reference $reference --session 2026-10-27)
 Need ($LASTEXITCODE -eq 0 -and
  $lines -contains 'NO11_REFERENCE_DIAG_ROWS_COMPLETE=47/47' -and
  $lines -contains 'NO11_REFERENCE_DIAG_STATUS=FIELDS_PRESENT_NOT_EXTERNALLY_REVIEWED' -and
  $lines -contains 'NO11_REFERENCE_DIAG_MARKET_SECTION_RECOGNIZED=47/47') 'PREVIOUS_REFERENCE_NOT_47_COMPLETE'
 $result=@(& $python -B $review --reference $reference --plan $plan --mask $mask --output-root $referenceDir)
 Need ($LASTEXITCODE -eq 0 -and $result -contains 'NO11_RSS_REFERENCE_FIELDS_PRESENT=47' -and
  $result -contains 'NO11_RSS_REFERENCE_FIELDS_MISSING=0') 'UNREVIEWED_QUEUE_NOT_COMPLETE'
 $receipts=@($result | Where-Object {([string]$_).StartsWith('NO11_RSS_REVIEW_QUEUE=',[StringComparison]::Ordinal)})
 Need ($receipts.Count -eq 1) 'REVIEW_QUEUE_OUTPUT_AMBIGUOUS'
 $reviewPath=([string]$receipts[0]).Substring('NO11_RSS_REVIEW_QUEUE='.Length)
 [void](PrivateFile $reviewPath)
 $queue=Get-Content -LiteralPath $reviewPath -Raw -Encoding UTF8 | ConvertFrom-Json
 Need ($queue.schemaId -ceq 'ARK_NO11_20261027_EXTERNAL_SECURITY_REVIEW_QUEUE_UNREVIEWED_V1' -and
  $queue.selectedCount -eq 47 -and $queue.independentlyClearedCount -eq 0 -and
  $queue.corporateActionReviewPerformed -eq $false -and
  $queue.datedMasterCreated -eq $false -and
  $queue.productionReady -eq $false -and $queue.orderTransmission -eq $false) 'REVIEW_QUEUE_FLAGS_CHANGED'
 Write-Host 'NO11_DAY_REVIEW_RSS_REFERENCE=47/47'
 Write-Host 'NO11_DAY_REVIEW_MARKET_SECTION=47/47'
 Write-Host ('NO11_DAY_REVIEW_UNREVIEWED_QUEUE='+$reviewPath)
 Write-Host 'NO11_DAY_REVIEW_EXTERNAL_DOCUMENTS_NEEDED=YES'
 Write-Host 'NO11_DAY_REVIEW_EVIDENCE_NOT_CERTIFIED=True'
 Write-Host 'NO11_DAY_REVIEW_EXCEL_OPENED=False'
 Write-Host 'NO11_DAY_REVIEW_FROZEN_OR_CAPITAL_MODIFIED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_DAY_REVIEW_[A-Z0-9_]+$'){$reason='NO11_DAY_REVIEW_SOURCE_OR_ENVIRONMENT_FAILURE'}
 Write-Host ('NO11_DAY_REVIEW=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
