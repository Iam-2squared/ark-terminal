# Session-2026-11-02 private PRE-LIVE dependency inventory from the user-
# verified 24-only Chart50 and 24/24 real Friday RSS minute archive.
# No Excel COM, no model inference, account reads, broker transport, order
# permission changes, bank transactions, credential access or fabricated
# dated-master/evidence.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$session='2026-11-02'
$root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
$run=Join-Path $root 'weekly-pool-refresh\weekly-refresh-2026-10-30-862f03a3cdfa7d8f'
$sourceChart=Join-Path $run 'no11-chart50-private-ea9c8d5481ba3ac8.json'
$sourceMask=Join-Path $run 'no11-observed-pass-watch-c1e2b27af8d32c00.json'
$previous=Join-Path $root 'previous-source\2026-11-02\provisional-24\previous-archive-stage-d3ca36e05f2156ff82f74cbffd536b78704ae4a44dfe53533f97bca3098a3962.json'
$weekly=Join-Path $root 'daily-trend-capture\daily-2026-10-26-e84a2ec53b0fdf41'
$settings=Join-Path $root 'unified-launcher\settings.json'
$p1=Join-Path $root 'frozen-p1-replay\verified\68d33ac71f90563f'
$expected=@('3753.T','4478.T','2002.T','8163.T','5273.T','2810.T',
 '1914.T','7678.T','9245.T','2705.T','9900.T','7581.T','4733.T',
 '8070.T','2004.T','4502.T','4565.T','4544.T','7083.T','6532.T',
 '7821.T','219A.T','8923.T','3023.T')
$knownExcluded=@('1690.T','2014.T','2038.T','4347.T','5029.T','2612.T')
function Need([bool]$value,[string]$reason){
 if(-not $value){throw ('NO11_NOV02_PRELIVE_'+$reason)}
}
function HashFile([string]$file){
 Need (Test-Path -LiteralPath $file -PathType Leaf) 'PRIVATE_SOURCE_MISSING'
 Need (((Get-Item -LiteralPath $file -Force).Attributes -band
   [IO.FileAttributes]::ReparsePoint) -eq 0) 'SOURCE_SYMLINK'
 return (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
}
function PrivateJson([string]$file){
 return (Get-Content -LiteralPath $file -Encoding UTF8 -Raw | ConvertFrom-Json)
}
function CheckReceipt([string]$file,[string]$prefix,[int]$size){
 $name=[IO.Path]::GetFileName($file)
 $sha=HashFile $file
 $pattern='^'+[regex]::Escape($prefix)+'-([a-f0-9]{'+$size+'})\.json$'
 Need ($name -cmatch $pattern) 'RECEIPT_FILENAME_INVALID'
 Need ($sha.StartsWith([string]$Matches[1],[StringComparison]::Ordinal)) 'RECEIPT_SHA256_MISMATCH'
 return $sha
}
if($OfflineSelfTest){
 Need ($session -ceq '2026-11-02' -and $expected.Count -eq 24 -and
  @($expected|Select-Object -Unique).Count -eq 24 -and
  @($expected|Where-Object {$_ -notmatch '^[0-9A-Z]{4}\.T$'}).Count -eq 0 -and
  @($expected|Where-Object {$_ -in $knownExcluded}).Count -eq 0) 'STATIC_SCOPE'
 $empty=[pscustomobject]@{}
 $emptyNames=@($empty.PSObject.Properties | ForEach-Object { $_.Name })
 $populated=[pscustomobject]@{ '7203.T'=1 }
 $names=@($populated.PSObject.Properties | ForEach-Object { $_.Name })
 Need ($emptyNames.Count -eq 0 -and $names.Count -eq 1 -and $names[0] -ceq '7203.T') 'EMPTY_PROPERTIES_STRICTMODE'
 Write-Host 'NO11_NOV02_PRELIVE_EMPTY_ARCHIVE_PROPERTIES_SELFTEST=PASS'
 Write-Host 'NO11_NOV02_PRELIVE_OFFLINE_SELFTEST=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
 $step='RECEIPT_HASH_VALIDATION'
try{
 $chartHash=CheckReceipt $sourceChart 'no11-chart50-private' 16
 $maskHash=CheckReceipt $sourceMask 'no11-observed-pass-watch' 16
 $stageHash=CheckReceipt $previous 'previous-archive-stage' 64
 $step='SOURCE_JSON_CONTRACTS'
 $chart=PrivateJson $sourceChart
 $mask=PrivateJson $sourceMask
 $stage=PrivateJson $previous
 Need ($chart.schemaId -ceq 'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1' -and
   $chart.chartPlan.sessionDate -ceq $session -and
   $chart.chartPlan.orderTransmission -eq $false -and
   $chart.productionReady -eq $false -and
   $chart.orderTransmission -eq $false) 'CHART_CONTRACT'
 Need ($mask.orderTransmission -eq $false -and
   $mask.asOfSession -ceq '2026-10-30' -and
   $mask.planId -ceq $chart.chartPlan.sourcePlanId) 'MASK_CONTRACT'
 Need ($stage.schemaId -ceq 'ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1' -and
   $stage.sessionDate -ceq $session -and
   $stage.previousSession -ceq '2026-10-30' -and
   $stage.productionReady -eq $false -and
   $stage.orderTransmission -eq $false -and
   $stage.chartPlanSha256 -ceq $chart.chartPlan.planSha256) 'STAGE_CONTRACT'
 $step='SELECTED_24_MEMBERSHIP'
 $selected=@($chart.chartPlan.selectorInputSymbols)
 Need ($selected.Count -eq 24 -and
   (($selected -join '|') -ceq (@($stage.selectedSymbols) -join '|')) -and
   (@($selected|Where-Object {$_ -notin $expected}).Count -eq 0) -and
   (@($expected|Where-Object {$_ -notin $selected}).Count -eq 0) -and
   (@($selected|Where-Object {$_ -in $knownExcluded}).Count -eq 0)) 'SCOPE_NOT_EXACT_24'
 # PS 5.1 StrictMode does not safely enumerate .Name on a zero-member
 # PSObject.Properties collection. The archive is expected to have zero omitted.
 $step='EMPTY_SAFE_ARCHIVE_MEMBERSHIP'
 $archived=@($stage.symbols.PSObject.Properties | ForEach-Object { $_.Name })
 $missed=@($stage.omittedSymbols.PSObject.Properties | ForEach-Object { $_.Name })
 Need ($archived.Count -eq 24 -and $missed.Count -eq 0 -and
   @($selected | Where-Object {$_ -notin $archived}).Count -eq 0) 'ARCHIVE_NOT_24_OF_24'
 Need (Test-Path -LiteralPath $weekly -PathType Container) 'PINNED_WEEKLY_SOURCE_MISSING'
 $step='LAUNCHER_SETTINGS'
 $cfg=PrivateJson $settings
 Need ($cfg.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
   $cfg.normalMaxPositions -eq 3 -and
   $cfg.sameDayApprovalRequired -eq $true -and
   $cfg.automaticOrderAuthorization -eq $false -and
   $cfg.orderTransmission -eq $false) 'UNIFIED_SETTINGS_UNSAFE'
 $orderIdExists=([string]$cfg.orderIdWorkbookPath -ne '' -and
   (Test-Path -LiteralPath $cfg.orderIdWorkbookPath -PathType Leaf))
 $accountExists=(Test-Path -LiteralPath $cfg.accountWorkbookPath -PathType Leaf)
 $marketExists=(Test-Path -LiteralPath $cfg.marketWorkbookPath -PathType Leaf)
 Need ($orderIdExists -and $accountExists -and $marketExists) 'BROKER_WORKBOOK_SOURCE_MISSING'
 $step='LIVE_ENGINE_FILES'
 $engine=Join-Path 'C:\ArkTerminal\no11-unified-2026-10-30' 'research\no12-prebuy-causal-runtime-20261011'
 $required=@('tools\no11_received_session_controller.py',
  'tools\no11_received_session_bootstrap.py',
  'tools\no11_broker_execution_service.py',
  'windows\Run-No11ReceivedSessionOperatorLive.ps1',
  'windows\Observe-No11AccountReadOnly.ps1',
  'tools\no11_previous_archive_context.py')
 $missing=@($required | Where-Object {-not (Test-Path -LiteralPath (Join-Path $engine $_) -PathType Leaf)})
 Need ($missing.Count -eq 0) 'LIVE_SOURCE_NOT_INSTALLED'
 $p1Exists=Test-Path -LiteralPath $p1 -PathType Container
 $step='PRIVATE_INVENTORY_WRITE'
 $privateOut=Join-Path $root 'nov02-24-prelive'
 [void][IO.Directory]::CreateDirectory($privateOut)
 $body=[ordered]@{
  schemaId='ARK_NO11_NOV02_24_PRELIVE_INVENTORY_V1'
  targetSession=$session
  status='INPUTS_PINNED_ONLY_NOT_A_TRADING_CONFIG'
  chartReceipt=$sourceChart
  chartSha256=$chartHash
  passMask=$sourceMask
  maskSha256=$maskHash
  archiveStage=$previous
  stageSha256=$stageHash
  selectedSymbols=$selected
  archivedCount=$archived.Count
  weeklySourceRun=$weekly
  pinnedP1Root=$(if($p1Exists){$p1}else{$null})
  sourceAccountWorkbook=$cfg.accountWorkbookPath
  sourceMarketWorkbook=$cfg.marketWorkbookPath
  supplementalOrderIdWorkbook=$cfg.orderIdWorkbookPath
  liveEngineFilesPresent=$true
  missingSameSessionFacts=@('INDEPENDENT_ORDINARY_EQUITY_CORPORATE_ACTION_PRICE_BASIS',
   'DATED_MASTER_FROM_ACTUAL_SESSION_REFERENCE',
   'PREVIOUS_CONTEXT_ASSEMBLED_FROM_VALID_MASTER',
   'VERIFIED_H235_RUNTIME_PATH_AND_ORIGINAL_CAPITAL_ARRIVAL',
   'BROKER_LIVE_TRANSPORT_CONFIGURATION_WITH_REAL_EXCEL_SESSION',
   'ACTUAL_SECURITIES_ACCOUNT_ONLY_CASH_EVIDENCE',
   'FRESH_RSS_BUYING_POWER_REFRESH_PROOF',
   'INTEGRATED_FROZEN_PREFLIGHT_AND_PHYSICAL_DISPATCH_GATES',
   'EXPLICIT_SAME_SESSION_OPERATOR_APPROVAL')
  readyForLiveTrading=$false
  physicalBrokerOrderVerified=$false
  productionReady=$false
  orderTransmission=$false
 }
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes(
  (ConvertTo-Json -InputObject $body -Depth 8 -Compress)+[char]10)
 $hash=[Security.Cryptography.SHA256]::Create()
 try{$digest=([BitConverter]::ToString($hash.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}
 finally{$hash.Dispose()}
 $dest=Join-Path $privateOut ('source-inventory-'+$digest+'.json')
 if(Test-Path -LiteralPath $dest -PathType Leaf){
  Need (([Convert]::ToBase64String([IO.File]::ReadAllBytes($dest))) -ceq ([Convert]::ToBase64String($bytes))) 'PRIVATE_OUTPUT_CHANGED'
 }else{
  $f=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}
  finally{$f.Dispose()}
 }
 Write-Host 'NO11_PRELIVE_SOURCE_24=HASH_AND_SCOPE_PASS'
 Write-Host 'NO11_PRELIVE_ARCHIVE=24_OF_24'
 Write-Host 'NO11_PRELIVE_ACCOUNT_BOOK=FOUND'
 Write-Host 'NO11_PRELIVE_MARKET_BOOK=FOUND'
 Write-Host 'NO11_PRELIVE_ORDER_ID_BOOK=FOUND'
 Write-Host 'NO11_PRELIVE_LIVE_SOURCES=6_OF_6'
 Write-Host ('NO11_PRELIVE_P1_ROOT_EXISTS='+$p1Exists)
 Write-Host ('NO11_PRELIVE_LIVE_CONFIG_EXISTS='+([bool]($cfg.bootstrapConfigFile -and (Test-Path -LiteralPath $cfg.bootstrapConfigFile -PathType Leaf))))
 Write-Host ('NO11_PRELIVE_SAFE_SOURCE_INVENTORY='+$dest)
 Write-Host 'NO11_PRELIVE_SAME_DAY_MASTER=REQUIRED'
 Write-Host 'NO11_PRELIVE_SECURITIES_CASH=REQUIRED'
 Write-Host 'NO11_PRELIVE_BUYING_POWER_REFRESH=REQUIRED'
 Write-Host 'NO11_PRELIVE_TRADING_AUTHORIZED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_NOV02_PRELIVE_[A-Z0-9_]+$'){
  $reason='NO11_NOV02_PRELIVE_PRIVATE_SOURCE_OR_RUNTIME_FAILED'
 }
 Write-Host ('NO11_PRELIVE_FAILED_STAGE='+$step)
 Write-Host ('NO11_PRELIVE_FAILURE_TYPE='+$_.Exception.GetType().Name)
 Write-Host ('NO11_PRELIVE_FAILURE_LINE='+[int]$_.InvocationInfo.ScriptLineNumber)
 Write-Host ('NO11_PRELIVE=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
