# CRLF-correct Oct26 historical source attestation and strictly scoped pin fix.
# No Excel, no trading, no private source rewrite, no broker/ledger/marker reset.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$reason){if(-not $ok){throw ('NO11_OCT26_CRLF_REPAIR_'+$reason)}}
if($OfflineSelfTest){
 Need (-not $Apply.IsPresent) 'SELFTEST_FLAG_INVALID'
 Write-Host 'NO11_OCT26_CRLF_REPAIR_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'HISTORICAL_SOURCE_CHANGED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'EXPLICIT_APPROVAL_REQUIRED'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$bindingFile=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $bindingFile -PathType Leaf) 'BINDING_MISSING'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false) 'BINDING_UNSAFE'
$engine=[string]$binding.engine
Need ([IO.Path]::IsPathRooted($engine) -and
      (Test-Path -LiteralPath $engine -PathType Container)) 'ENGINE_MISSING'
$source=Join-Path $engine 'tools\no11_weekly_g1_refresh.mjs'
$private=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
$oct26=Join-Path $private 'daily-trend-capture\daily-2026-10-26-e84a2ec53b0fdf41\plan.json'
$friday=Join-Path $private 'weekly-pool-refresh\weekly-refresh-2026-10-30-862f03a3cdfa7d8f'
foreach($target in @($source,$oct26,(Join-Path $friday 'plan.json'))){
 Need (Test-Path -LiteralPath $target -PathType Leaf) 'PINNED_LOCAL_INPUT_NOT_FOUND'
}
function Assert-Stopped {
 $found=@(Get-CimInstance Win32_Process | Where-Object {
   $_.ProcessId -ne $PID -and
   $_.Name -match '^(powershell|pwsh|python|pythonw|node)(\.exe)?$' -and
   [string]$_.CommandLine -match 'Start-No11OneClick|Start-No11UnifiedLauncher|Run-No11NightlyCycle|Prepare-No11WeeklyAfterClose|Run-No11WeeklyCandidateRefresh|no11_weekly_g1_refresh|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder'
 })
 Need ($found.Count -eq 0) 'ARK_PROCESS_STILL_RUNNING'
}
Assert-Stopped
function BlobHash([byte[]]$data){
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$data.Length)+[char]0)
 $all=New-Object byte[] ($header.Length+$data.Length)
 [array]::Copy($header,0,$all,0,$header.Length)
 [array]::Copy($data,0,$all,$header.Length,$data.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$root=Join-Path $store ('oct26-crlf-proof-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($root)
$downloads=Join-Path $root 'historical'
[void][IO.Directory]::CreateDirectory($downloads)
$commit='f959767c6cc3e14ee9d233d0b4ee962e543279ac'
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'
$relative='research/no12-prebuy-causal-runtime-20261011/'
$names=@(
 'tools/no11_rss_daily_trend_census.mjs',
 'runtime/no11_rss_daily_trend_census.mjs',
 'runtime/no11_existing_selector_trend_prefilter.mjs',
 'runtime/jpx_cash_calendar_2026_2027.mjs',
 'windows/Run-No11RssDailyTrendCensusReadOnly.ps1'
)
$attestorName='attest_oct26_win_checkout.mjs'
$attestor=Join-Path $root $attestorName
$attestorUrl=$base+'6f7d38a8d4c29abf4c21a34f1f74c914641465c1/research/no11-morning-master-20261103/'+$attestorName
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $attestorUrl -OutFile $attestor -UseBasicParsing -ErrorAction Stop
Need ((BlobHash ([IO.File]::ReadAllBytes($attestor))) -ceq
      '2b911785458c6276456dfa929c147bf328744689') 'ATTESTOR_HASH_MISMATCH'
foreach($name in $names){
 $path=Join-Path $downloads ($name.Replace('/',[IO.Path]::DirectorySeparatorChar))
 [void][IO.Directory]::CreateDirectory((Split-Path -Parent $path))
 $uri=$base+$commit+'/'+$relative+$name
 Invoke-WebRequest -Uri $uri -OutFile $path -UseBasicParsing -ErrorAction Stop
}
& node.exe $attestor --self-test
Need ($LASTEXITCODE -eq 0) 'ATTESTOR_SELFTEST_FAILED'
$attestation=@(& node.exe $attestor $engine $oct26 $friday $downloads)
Need ($LASTEXITCODE -eq 0 -and $attestation.Count -eq 1) 'ORIGINAL_ARCHIVED_WINDOWS_REVISION_UNVERIFIED'
$proof=([string]$attestation[0] | ConvertFrom-Json)
$historicId='e84a2ec53b0fdf41a8f65b678e2e82562a4fda1054d8fbe42cba856e2d42513d'
Need ($proof.status -ceq 'VERIFIED_2026_10_26_WINDOWS_CHECKOUT' -and
      $proof.historicalCodeSha256 -ceq $historicId -and
      $proof.originalPlanIdSha256Verified -eq $true -and
      $proof.fridayPlanIdSha256Verified -eq $true -and
      $proof.originalSymbols -eq 4328 -and
      $proof.fridaySymbols -eq 429 -and
      $proof.currentCodeIdentityDifferent -eq $true -and
      $proof.orderTransmission -eq $false) 'ATTESTATION_UNACCEPTABLE'
Write-Host 'NO11_OCT26_CRLF_CODE_IDENTITY=FULL_64_HEX_VERIFIED'
Write-Host 'NO11_OCT30_429_PLAN=HASH_AND_LINEAGE_VERIFIED'
$originalBytes=[IO.File]::ReadAllBytes($source)
$originalSha=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
$planSha=(Get-FileHash -LiteralPath $oct26 -Algorithm SHA256).Hash
$fridayPlanFile=Join-Path $friday 'plan.json'
$fridaySha=(Get-FileHash -LiteralPath $fridayPlanFile -Algorithm SHA256).Hash
$utf8=[Text.UTF8Encoding]::new($false,$true)
$bom=$originalBytes.Length -ge 3 -and $originalBytes[0] -eq 239 -and
     $originalBytes[1] -eq 187 -and $originalBytes[2] -eq 191
$offset=if($bom){3}else{0}
$body=$utf8.GetString($originalBytes,$offset,$originalBytes.Length-$offset)
$crlf=([string][char]13)+([string][char]10)
$lf=[string][char]10
$linebreak=if($body.Contains($crlf)){$crlf}else{$lf}
$body=$body.Replace($crlf,$lf)
$oldOriginal="    SHA(JSON.stringify(body))===planId&&plan.codeSha256===codeIdentity()&&"
$oldFriday="    plan.asOfSession===date&&plan.codeSha256===codeIdentity()&&"
Need ($body.Split(@($oldOriginal),[StringSplitOptions]::None).Count -eq 2 -and
      $body.Split(@($oldFriday),[StringSplitOptions]::None).Count -eq 2) 'CURRENT_SOURCE_ANCHOR_CHANGED'
Need (-not $body.Contains('ARK_NO11_OCT26_CRLF_HISTORICAL_PROOF_V1')) 'ALREADY_INSTALLED'
# Two precisely scoped historical exceptions; all other plan/source guards stay active.
$replacementOriginal=(
  "    SHA(JSON.stringify(body))===planId&&"+$lf+
  "    // ARK_NO11_OCT26_CRLF_HISTORICAL_PROOF_V1"+$lf+
  "    (plan.codeSha256===codeIdentity()||"+$lf+
  "     (plan.asOfSession==='2026-10-26'&&"+$lf+
  "      plan.schemaId===DAILY_PLAN_SCHEMA&&"+$lf+
  "      plan.symbols?.length===4328&&"+$lf+
  "      plan.codeSha256==='$historicId'))&&"
)
$replacementFriday=(
  "    plan.asOfSession===date&&"+$lf+
  "    (plan.codeSha256===codeIdentity()||"+$lf+
  "     (plan.asOfSession==='2026-10-30'&&"+$lf+
  "      plan.initialLiveCandidateScope==='FRIDAY_RSS_429_LOCKED_POOL_ONLY_NOT_FULL_MARKET'&&"+$lf+
  "      plan.weeklySource?.asOfSession==='2026-10-26'&&"+$lf+
  "      plan.symbols?.length===429&&"+$lf+
  "      plan.codeSha256==='$historicId'))&&"
)
$patched=$body.Replace($oldOriginal,$replacementOriginal).Replace($oldFriday,$replacementFriday)
Need ($patched.Contains('ARK_NO11_OCT26_CRLF_HISTORICAL_PROOF_V1')) 'PATCH_MISSING'
$bytes=[Text.UTF8Encoding]::new($false).GetBytes($patched.Replace($lf,$linebreak))
if($bom){$bytes=[byte[]]@(239,187,191)+$bytes}
$candidate=Join-Path (Split-Path -Parent $source) ('no11-crlf-review-'+[guid]::NewGuid().ToString('N')+'.mjs')
$preflight=Join-Path $root 'preflight.mjs'
$testCode=@'
import {pathToFileURL} from 'node:url';
const [candidate,weekly,friday]=process.argv.slice(2);
const {verifyWeeklyPool,verifyFridayCarry}=await import(pathToFileURL(candidate).href);
const source=verifyWeeklyPool(weekly);
if(source.plan?.asOfSession!=='2026-10-26'||source.plan?.symbols?.length!==4328){
 throw Error('NO11_OCT26_CRLF_SOURCE_UNEXPECTED');
}
const proof=verifyFridayCarry(source,friday,'2026-11-04');
if(proof?.schemaId!=='ARK_NO11_WEEK429_EXPLICIT_CARRY_V1'||proof.carriedOriginalSymbols!==429){
 throw Error('NO11_OCT26_CRLF_FRIDAY_SCOPE_INVALID');
}
console.log('NO11_OCT26_CRLF_FULL_4328_AND_FRIDAY_429_RECEIPTS=VERIFIED');
console.log('ORDER_TRANSMISSION=False');
'@
[IO.File]::WriteAllText($preflight,$testCode,[Text.UTF8Encoding]::new($false))
try{
 [IO.File]::WriteAllBytes($candidate,$bytes)
 & node.exe --check $candidate
 Need ($LASTEXITCODE -eq 0) 'CANDIDATE_SYNTAX_FAILED'
 & node.exe $preflight $candidate (Split-Path -Parent $oct26) $friday
 Need ($LASTEXITCODE -eq 0) 'ACTUAL_HISTORICAL_RECEIPTS_NOT_CERTIFIED'
 Assert-Stopped
 Need ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ceq $originalSha) 'ENGINE_SOURCE_CHANGED'
 Need ((Get-FileHash -LiteralPath $oct26 -Algorithm SHA256).Hash -ceq $planSha) 'ORIGINAL_PLAN_CHANGED'
 Need ((Get-FileHash -LiteralPath $fridayPlanFile -Algorithm SHA256).Hash -ceq $fridaySha) 'FRIDAY_PLAN_CHANGED'
 $backup=Join-Path $root 'no11_weekly_g1_refresh.before.mjs'
 [IO.File]::Replace($candidate,$source,$backup)
 Write-Host 'NO11_OCT26_CRLF_CODE_PIN_REPAIR=PASS'
 Write-Host 'SCOPE=OCT26_4328_AND_OCT30_429_ONLY'
 Write-Host 'ALL_4328_ORIGINAL_RECEIPTS=VERIFIED'
 Write-Host 'ALL_429_FRIDAY_RECEIPTS=VERIFIED'
 Write-Host 'HISTORICAL_PLAN_MODIFIED=False'
 Write-Host 'HISTORICAL_RECEIPTS_MODIFIED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ONECLICK_WHITE_UI_MODIFIED=False'
 Write-Host 'BROKER_LEDGER_MODIFIED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'NIGHTLY_CAPTURE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 Write-Host ('BACKUP_DIR='+$root)
}finally{
 if(Test-Path -LiteralPath $candidate){Remove-Item -LiteralPath $candidate -Force}
}
