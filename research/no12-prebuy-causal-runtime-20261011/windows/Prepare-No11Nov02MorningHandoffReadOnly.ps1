# Exact Nov 2 source-only handoff. Tonight: seal 24 selected codes and known
# input paths. On the actual trading day: opt-in read-only RSS market reference.
# NEVER creates broker config, dated master, review clearance or order approval.
# No original source mutation, Excel COM during staging or model training.
param(
 [switch]$OfflineSelfTest,
 [switch]$CaptureTodayReadOnly
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$session='2026-11-02'
$prior='2026-10-30'
$root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
$inventory=Join-Path $root 'nov02-24-prelive\source-inventory-87e6e7c6eeb79cc2f0db02c5fca13c68d0f6161505722958d46930e9d26029c7.json'
$previousStage=Join-Path $root 'previous-source\2026-11-02\provisional-24\previous-archive-stage-d3ca36e05f2156ff82f74cbffd536b78704ae4a44dfe53533f97bca3098a3962.json'
$engine=Join-Path 'C:\ArkTerminal\no11-unified-2026-10-30' 'research\no12-prebuy-causal-runtime-20261011'
$output=Join-Path $root 'nov02-24-prelive'
$expected=@('3753.T','4478.T','2002.T','8163.T','5273.T','2810.T',
 '1914.T','7678.T','9245.T','2705.T','9900.T','7581.T',
 '4733.T','8070.T','2004.T','4502.T','4565.T','4544.T',
 '7083.T','6532.T','7821.T','219A.T','8923.T','3023.T')
$step='INIT'
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_NOV02_HANDOFF_'+$reason)}
}
function Sha([byte[]]$bytes){
 $h=[Security.Cryptography.SHA256]::Create()
 try{return ([BitConverter]::ToString($h.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}
 finally{$h.Dispose()}
}
function HashedJson([string]$f,[string]$prefix,[int]$digestSize){
 Need ([IO.Path]::IsPathRooted($f) -and
       (Test-Path -LiteralPath $f -PathType Leaf)) 'SOURCE_MISSING'
 $info=Get-Item -LiteralPath $f -Force
 Need ($info.Length -gt 1 -and $info.Length -le 8000000 -and
       ($info.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'SOURCE_FILE_UNSAFE'
 $name=[IO.Path]::GetFileName($f)
 $match=[regex]::Match($name,('^'+[regex]::Escape($prefix)+'-([a-f0-9]{'+$digestSize+'})\.json$'))
 Need ($match.Success) 'SOURCE_NAME_INVALID'
 $bytes=[IO.File]::ReadAllBytes($f)
 $digest=Sha $bytes
 Need ($digest.StartsWith($match.Groups[1].Value,[StringComparison]::Ordinal)) 'SOURCE_HASH_CHANGED'
 return @{value=(Get-Content -LiteralPath $f -Raw -Encoding UTF8 | ConvertFrom-Json);sha=$digest}
}
function Sealed([string]$prefix,[byte[]]$bytes,[string]$ext){
 $digest=Sha $bytes
 $p=Join-Path $output ($prefix+'-'+$digest+$ext)
 if(Test-Path -LiteralPath $p){
  Need (([Convert]::ToBase64String([IO.File]::ReadAllBytes($p))) -ceq
        ([Convert]::ToBase64String($bytes))) 'IMMUTABLE_OUTPUT_CHANGED'
 }else{
  $f=[IO.File]::Open($p,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}
  finally{$f.Dispose()}
 }
 return $p
}
function JsonBytes([object]$obj){
 return [Text.UTF8Encoding]::new($false).GetBytes(
  (ConvertTo-Json -InputObject $obj -Depth 12 -Compress)+[char]10)
}
if($OfflineSelfTest){
 Need (-not $CaptureTodayReadOnly -and $expected.Count -eq 24 -and
  @($expected|Select-Object -Unique).Count -eq 24) 'STATIC_SELECTED_SCOPE'
 $sample=JsonBytes ([ordered]@{mode='SOURCE_ONLY';orderTransmission=$false})
 Need ((Sha $sample) -cmatch '^[a-f0-9]{64}$' -and
   ([Text.Encoding]::UTF8.GetString($sample)).Contains('"orderTransmission":false')) 'SOURCE_ONLY_SEAL_SELFTEST'
 Write-Host 'NO11_NOV02_HANDOFF_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 $step='PINNED_SOURCE_INVENTORY'
 $receipt=HashedJson $inventory 'source-inventory' 64
 $input=$receipt.value
 Need ($input.schemaId -ceq 'ARK_NO11_NOV02_24_PRELIVE_INVENTORY_V1' -and
  $input.targetSession -ceq $session -and
  $input.status -ceq 'INPUTS_PINNED_ONLY_NOT_A_TRADING_CONFIG' -and
  $input.readyForLiveTrading -eq $false -and
  $input.productionReady -eq $false -and
  $input.orderTransmission -eq $false -and
  $input.archivedCount -eq 24) 'INVENTORY_CONTRACT_CHANGED'
 $step='CHART_AND_ARCHIVE'
 $chart=HashedJson ([string]$input.chartReceipt) 'no11-chart50-private' 16
 $mask=HashedJson ([string]$input.passMask) 'no11-observed-pass-watch' 16
 $stage=HashedJson $previousStage 'previous-archive-stage' 64
 Need ($chart.sha -ceq [string]$input.chartSha256 -and
  $mask.sha -ceq [string]$input.maskSha256 -and
  $stage.sha -ceq [string]$input.stageSha256) 'INVENTORY_SOURCE_HASH_MISMATCH'
 $plan=$chart.value.chartPlan
 $symbols=@($plan.selectorInputSymbols)
 Need ($symbols.Count -eq 24 -and
   @($symbols|Select-Object -Unique).Count -eq 24 -and
   (@($symbols | Where-Object {$_ -notin $expected}).Count -eq 0) -and
   (@($expected | Where-Object {$_ -notin $symbols}).Count -eq 0) -and
   (($symbols -join '|') -ceq (@($stage.value.selectedSymbols) -join '|')) -and
   $plan.planSha256 -ceq $stage.value.chartPlanSha256 -and
   $plan.sessionDate -ceq $session -and
   $mask.value.asOfSession -ceq $prior -and
   $plan.orderTransmission -eq $false -and
   $stage.value.orderTransmission -eq $false) '24_SELECTED_SOURCE_MISMATCH'
 $stored=@($stage.value.symbols.PSObject.Properties|ForEach-Object {$_.Name})
 $omitted=@($stage.value.omittedSymbols.PSObject.Properties|ForEach-Object {$_.Name})
 Need ($stored.Count -eq 24 -and $omitted.Count -eq 0 -and
       @($symbols|Where-Object {$_ -notin $stored}).Count -eq 0) '24_ARCHIVE_INCOMPLETE'
 Need (Test-Path -LiteralPath $engine -PathType Container) 'PINNED_ENGINE_NOT_FOUND'
 $referenceScript=Join-Path $engine 'windows\Capture-No11SessionReferenceReadOnly.ps1'
 Need (Test-Path -LiteralPath $referenceScript -PathType Leaf) 'RSS_REFERENCE_COLLECTOR_NOT_FOUND'
 $step='PRESTAGE_LOCAL_FILES'
 [void][IO.Directory]::CreateDirectory($output)
 $symbolBytes=[Text.UTF8Encoding]::new($false).GetBytes(($symbols -join [char]10)+[char]10)
 $symbolsFile=Sealed 'selected-24' $symbolBytes '.txt'
 $handoff=[ordered]@{
  schemaId='ARK_NO11_NOV02_SOURCE_ONLY_HANDOFF_V1'
  sessionDate=$session
  previousSession=$prior
  sourceInventory=$inventory
  sourceInventorySha256=$receipt.sha
  chartPlanReceipt=[string]$input.chartReceipt
  chartPlanSha256=[string]$plan.planSha256
  passMask=[string]$input.passMask
  previousArchiveStage=$previousStage
  capturedMinuteArchiveCount=24
  selectedSymbols=$symbols
  selectedSymbolsFile=$symbolsFile
  dailyRun=([IO.Path]::GetDirectoryName([string]$input.chartReceipt))
  weeklySourceRun=[string]$input.weeklySourceRun
  accountWorkbookPath=[string]$input.sourceAccountWorkbook
  marketWorkbookPath=[string]$input.sourceMarketWorkbook
  orderIdWorkbookPath=[string]$input.supplementalOrderIdWorkbook
  referenceCollector=$referenceScript
  morningCaptureRequiresOnlyTwoOriginalBooks=$true
  draftBootstrapKnownFields=[ordered]@{
   schemaId='ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1'
   sessionDate=$session
   dailyRun=([IO.Path]::GetDirectoryName([string]$input.chartReceipt))
   precomputedChartReceipt=[string]$input.chartReceipt
   precomputedG1Mask=[string]$input.passMask
   weeklySourceRun=[string]$input.weeklySourceRun
   orderIdWorkbookPath=[string]$input.supplementalOrderIdWorkbook
   productionReady=$false
   orderTransmission=$false
  }
  missingBeforeOperationalBootstrap=@(
   'INDEPENDENT_DAY_OF_COMMON_EQUITY_AND_CORPORATE_ACTION_REVIEW',
   'CURRENT_DAY_PRICE_BASIS_REVIEW',
   'CURRENT_SESSION_DATED_MASTER',
   'PREVIOUS_CONTEXT_FROM_REVIEWED_MASTER',
   'VERIFIED_FROZEN_RUNTIME_ROOT_AND_H235_24_MODEL_ROOT',
   'BROKER_LIVE_CONFIG_REAL_EXCEL_PIN_AND_TRANSPORT_PREFLIGHT',
   'SECURITIES_ONLY_OPENING_CASH_AND_FRESH_BUYING_POWER',
   'EXPLICIT_SAME_DAY_HUMAN_LIVE_APPROVAL'
  )
  tradingAuthorized=$false
  productionReady=$false
  orderTransmission=$false
 }
 $handoffFile=Sealed 'morning-handoff' (JsonBytes $handoff) '.json'
 Write-Host 'NO11_NOV02_HANDOFF_24=PINNED'
 Write-Host 'NO11_NOV02_HANDOFF_PREVIOUS=24_OF_24'
 Write-Host ('NO11_NOV02_HANDOFF_SYMBOLS_FILE='+$symbolsFile)
 Write-Host ('NO11_NOV02_HANDOFF_FILE='+$handoffFile)
 Write-Host 'NO11_NOV02_HANDOFF_BOOTSTRAP=SOURCE_FIELDS_ONLY_NOT_AN_ACTIVATED_CONFIG'
 if(-not $CaptureTodayReadOnly){
  Write-Host 'NO11_NOV02_HANDOFF_TODAY_REFERENCE=NOT_REQUESTED'
  Write-Host 'EXCEL_TOUCHED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 $step='ACTUAL_SESSION_GUARD'
 $now=[DateTimeOffset]::UtcNow.ToOffset([timespan]::FromHours(9))
 Need ($now.ToString('yyyy-MM-dd') -ceq $session -and
  $now.ToString('HH:mm:ss') -ge '09:00:00' -and
  $now.ToString('HH:mm:ss') -le '15:20:00') 'SESSION_REFERENCE_REQUIRES_ACTUAL_MARKET_DAY'
 $step='ACTUAL_RSS_REFERENCE_ONLY'
 # The reference script demands exactly the account and market original books;
 # close the order-ID book by hand if open. Never close any workbook here.
 $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$referenceScript,
  '-SymbolsFile',$symbolsFile,'-ChartPlanFile',[string]$input.chartReceipt,
  '-OutputRoot',$output)
 $refLines=@(& powershell.exe @args)
 $refExit=$LASTEXITCODE
 $refLines|ForEach-Object {Write-Host $_}
 Need ($refExit -eq 0) 'ACTUAL_RSS_REFERENCE_BLOCKED'
 $hits=@($refLines|Where-Object {([string]$_).StartsWith('NO11_SESSION_REFERENCE_FILE=',[StringComparison]::Ordinal)})
 Need ($hits.Count -eq 1) 'RSS_REFERENCE_OUTPUT_NOT_UNIQUE'
 $refFile=([string]$hits[0]).Substring('NO11_SESSION_REFERENCE_FILE='.Length)
 $ref=HashedJson $refFile 'session-reference' 64
 $rows=@($ref.value.rows)
 Need ($ref.value.schemaId -ceq 'ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1' -and
  $ref.value.sessionDate -ceq $session -and
  $ref.value.chartPlanSha256 -ceq $plan.planSha256 -and
  $ref.value.readOnly -eq $true -and
  $ref.value.orderTransmission -eq $false -and
  $rows.Count -eq 24 -and
  (($rows|ForEach-Object {[string]$_.symbol}) -join '|') -ceq ($symbols -join '|')) 'DAY_OF_REFERENCE_CONTRACT'
 $worklist=@(foreach($row in $rows){
  $structure=($row.marketCode -ceq 'T' -and
   $row.marketDate -ceq $session -and $row.previousDate -ceq $prior -and
   $row.lotShares -eq 100 -and $null -ne $row.previousClose -and
   [double]$row.previousClose -gt 0 -and
   $null -ne $row.dayBasePrice -and [double]$row.dayBasePrice -gt 0)
  [pscustomobject]@{
   Symbol=[string]$row.symbol
   RssFields=if($structure){'OBSERVED_NOT_INDEPENDENTLY_REVIEWED'}else{'MISSING_OR_DIFFERENT'}
   PreviousClose=[string]$row.previousClose
   DayBasePrice=[string]$row.dayBasePrice
   MarketSection=[string]$row.marketSection
   LotShares=[string]$row.lotShares
   ExRightsRaw=[string]$row.exRightsDateRaw
   ExDividendRaw=[string]$row.exDividendDateRaw
   CorporateActionsCleared='NOT_REVIEWED'
   PriceBasisVerified='NOT_REVIEWED'
   CommonEquitySameDay='NOT_REVIEWED'
  }
 })
 $audit=[ordered]@{
  schemaId='ARK_NO11_NOV02_RSS_REFERENCE_WORKLIST_UNREVIEWED_V1'
  sessionDate=$session
  chartPlanSha256=[string]$plan.planSha256
  rssReferenceFile=$refFile
  rssReferenceSha256=$ref.sha
  selectedCount=24
  fieldsObservedCount=@($worklist|Where-Object {$_.RssFields -eq 'OBSERVED_NOT_INDEPENDENTLY_REVIEWED'}).Count
  missingOrDifferentCount=@($worklist|Where-Object {$_.RssFields -eq 'MISSING_OR_DIFFERENT'}).Count
  independentSecurityReviewPerformed=$false
  datedMasterCreated=$false
  productionReady=$false
  orderTransmission=$false
  rows=$worklist
 }
 $auditFile=Sealed 'day-reference-unreviewed' (JsonBytes $audit) '.json'
 Write-Host ('NO11_NOV02_RSS_REFERENCE_ROWS='+$rows.Count)
 Write-Host ('NO11_NOV02_RSS_FIELDS_OBSERVED='+$audit.fieldsObservedCount)
 Write-Host ('NO11_NOV02_RSS_FIELDS_MISSING_OR_DIFFERENT='+$audit.missingOrDifferentCount)
 Write-Host ('NO11_NOV02_RSS_REVIEW_WORKLIST='+$auditFile)
 Write-Host 'NO11_NOV02_RSS_SECURITY_REVIEW=NOT_YET_CLEARED'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 $err=$_.Exception.Message
 if($err -cnotmatch '^NO11_NOV02_HANDOFF_[A-Z0-9_]+$'){
  $err='NO11_NOV02_HANDOFF_SOURCE_OR_RUNTIME_FAILURE'
 }
 Write-Host ('NO11_NOV02_HANDOFF_FAILED_STAGE='+$step)
 Write-Host ('NO11_NOV02_HANDOFF=BLOCKED|'+$err)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
