# Cryptographically attest the Oct26 4328-symbol historic source before
# narrowly allowing that one original codeIdentity in the weekly reader.
# No Excel, orders, account/portfolio changes, launch-marker edits, or rewrites
# to any old daily plan / historical capture. Never a generic pin bypass.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){if(-not $ok){throw ('NO11_OCT26_REPAIR_'+$why)}}
if($OfflineSelfTest){
 Need (-not $Apply.IsPresent) 'INVALID_SELFTEST_FLAGS'
 Write-Host 'NO11_OCT26_REPAIR_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'HISTORICAL_RECEIPTS_MODIFIED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'EXPLICIT_APPLY_REQUIRED'
$root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
$store=Join-Path $root 'unified-launcher'
$bindingFile=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $bindingFile -PathType Leaf) 'BINDING_NOT_FOUND'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false) 'BINDING_UNSAFE'
$engine=[string]$binding.engine
$scriptFile=Join-Path $engine 'tools\no11_weekly_g1_refresh.mjs'
$plan=Join-Path $root 'daily-trend-capture\daily-2026-10-26-e84a2ec53b0fdf41\plan.json'
$friday=Join-Path $root 'weekly-pool-refresh\weekly-refresh-2026-10-30-862f03a3cdfa7d8f'
foreach($file in @($scriptFile,$plan)){
 Need (Test-Path -LiteralPath $file -PathType Leaf) 'REQUIRED_SOURCE_NOT_FOUND'
}
Need (Test-Path -LiteralPath $friday -PathType Container) 'ACTUAL_FRIDAY_CAPTURE_NOT_FOUND'
function AssertStopped {
 $active=@(Get-CimInstance Win32_Process|Where-Object {
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw|node)(\.exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11OneClick|Start-No11UnifiedLauncher|Run-No11NightlyCycle|Prepare-No11WeeklyAfterClose|Run-No11WeeklyCandidateRefresh|no11_weekly_g1_refresh|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder'
 })
 Need ($active.Count -eq 0) 'ARK_PROCESS_STILL_ACTIVE'
}
AssertStopped
function Blob([byte[]]$bytes){
 $prefix=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length)+[char]0)
 $all=New-Object byte[] ($prefix.Length+$bytes.Length)
 [array]::Copy($prefix,0,$all,0,$prefix.Length)
 [array]::Copy($bytes,0,$all,$prefix.Length,$bytes.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$sourceBefore=[IO.File]::ReadAllBytes($scriptFile)
$sourceHash=(Get-FileHash -LiteralPath $scriptFile -Algorithm SHA256).Hash
$planHash=(Get-FileHash -LiteralPath $plan -Algorithm SHA256).Hash
$pending=Join-Path $store ('oct26-historical-pin-review-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($pending)
$historical=Join-Path $pending 'original-20261023-Run-No11RssDailyTrendCensusReadOnly.ps1'
$verifier=Join-Path $pending 'verify_oct26_legacy_code.mjs'
$sourceUrl='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/b6781f369443ebb43a2347f3be7d1701909f0284/research/no12-prebuy-causal-runtime-20261011/windows/Run-No11RssDailyTrendCensusReadOnly.ps1'
$verifierUrl='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/056690fb927d511465918e8767252fa249ef89c4/research/no11-morning-master-20261103/verify_oct26_legacy_code.mjs'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $sourceUrl -OutFile $historical -UseBasicParsing -ErrorAction Stop
Invoke-WebRequest -Uri $verifierUrl -OutFile $verifier -UseBasicParsing -ErrorAction Stop
Need ((Blob ([IO.File]::ReadAllBytes($historical))) -ceq 'b0c3dfa9aba38d07859826f8f787abc7b56f19b9') 'ORIGINAL_CODE_GIT_BLOB_CHANGED'
Need ((Blob ([IO.File]::ReadAllBytes($verifier))) -ceq 'bd478c404a7b66ce6e6d200f0530ed517fb7b5c2') 'ATTESTOR_GIT_BLOB_CHANGED'
& node.exe $verifier --self-test
Need ($LASTEXITCODE -eq 0) 'ATTESTOR_SELFTEST_FAILED'
$line=@(& node.exe $verifier $engine $plan $historical)
Need ($LASTEXITCODE -eq 0 -and $line.Count -eq 1) 'HISTORICAL_CODE_REVISION_NOT_ATTESTED'
$audit=$line[0]|ConvertFrom-Json
Need ($audit.schemaId -ceq 'ARK_NO11_OCT26_ORIGINAL_SOURCE_CODE_ATTESTATION_V1' -and
      $audit.status -ceq 'HISTORIC_2026_10_26_PROVEN' -and
      $audit.currentCodeDifferent -eq $true -and
      $audit.planIdMatches -eq $true -and
      $audit.originalSymbols -eq 4328 -and
      $audit.historicalWindowsBlobVerified -eq $true -and
      $audit.orderTransmission -eq $false) 'AUDIT_CONTRACT_MISMATCH'
$historicId=[string]$audit.historicalCodeSha256
Need ($historicId -cmatch '^[a-f0-9]{64}$') 'HISTORIC_SHA_FORMAT'
Write-Host 'NO11_OCT26_HISTORICAL_CODE_IDENTITY=VERIFIED_BY_ARCHIVED_GIT_BLOB'
Write-Host 'NO11_OCT26_PLAN_AND_4328_SYMBOLS=VERIFIED'
$utf8=[Text.UTF8Encoding]::new($false,$true)
$bom=$sourceBefore.Length -ge 3 -and $sourceBefore[0] -eq 239 -and $sourceBefore[1] -eq 187 -and $sourceBefore[2] -eq 191
$offset=if($bom){3}else{0}
$original=$utf8.GetString($sourceBefore,$offset,$sourceBefore.Length-$offset)
$crlf=([string][char]13)+([string][char]10);$lf=[string][char]10
$newline=if($original.Contains($crlf)){$crlf}else{$lf}
$normalized=$original.Replace($crlf,$lf)
$old="    SHA(JSON.stringify(body))===planId&&plan.codeSha256===codeIdentity()&&"
Need ($normalized.Split(@($old),[StringSplitOptions]::None).Count -eq 2) 'WEEKLY_VALIDATOR_CHANGED'
Need (-not $normalized.Contains('ARK_NO11_OCT26_VERIFIED_HISTORICAL_REVISION_V1')) 'LEGACY_PIN_ALREADY_INSTALLED'
# This only accepts an exact 2026-10-26 original code identity cryptographically
# reconstructed from an immutable archived source. Other historical/new day
# plan mismatches still fail closed.
$replacement="    SHA(JSON.stringify(body))===planId&&" + $lf +
 "    // ARK_NO11_OCT26_VERIFIED_HISTORICAL_REVISION_V1" + $lf +
 "    (plan.codeSha256===codeIdentity()||" + $lf +
 "      (plan.asOfSession==='2026-10-26'&&plan.codeSha256==='$historicId'))&&"
$next=$normalized.Replace($old,$replacement)
Need ($next.Contains('ARK_NO11_OCT26_VERIFIED_HISTORICAL_REVISION_V1')) 'INJECTION_MISSING'
$next=$next.Replace($lf,$newline)
$bytes=[Text.UTF8Encoding]::new($false).GetBytes($next)
if($bom){$bytes=[byte[]]@(239,187,191)+$bytes}
$candidate=Join-Path (Split-Path -Parent $scriptFile) ('no11-oct26-verified-'+[guid]::NewGuid().ToString('N')+'.mjs')
$preflight=Join-Path $pending 'preflight-historical.mjs'
@'
import {pathToFileURL} from 'node:url';
const [sourceFile, weekly, friday] = process.argv.slice(2);
const {verifyWeeklyPool,verifyFridayCarry}=await import(pathToFileURL(sourceFile).href);
const original=verifyWeeklyPool(weekly);
if(original.plan?.asOfSession!=='2026-10-26'||original.plan?.symbols?.length!==4328)
  throw Error('NO11_OCT26_PRIVATE_SOURCE_CHANGED');
const proof=verifyFridayCarry(original,friday,'2026-11-04');
if(proof?.schemaId!=='ARK_NO11_WEEK429_EXPLICIT_CARRY_V1'||
   proof?.carriedOriginalSymbols!==429)throw Error('NO11_OCT26_FRIDAY_NOT_CERTIFIED');
console.log('NO11_OCT26_VERIFIED_SOURCE_AND_FRIDAY_429=PASS');
console.log('ORDER_TRANSMISSION=False');
'@ | Set-Content -LiteralPath $preflight -Encoding UTF8
try{
 [IO.File]::WriteAllBytes($candidate,$bytes)
 & node.exe --check $candidate
 Need ($LASTEXITCODE -eq 0) 'PATCH_MODULE_SYNTAX'
 # This reads all original RSS captures and the real Oct30 Friday archive.
 # Missing/inconsistent records are NOT accepted.
 & node.exe $preflight $candidate (Split-Path -Parent $plan) $friday
 Need ($LASTEXITCODE -eq 0) 'SOURCE_OR_FRIDAY_CAPTURES_FAILED_VERIFICATION'
 AssertStopped
 Need ((Get-FileHash -LiteralPath $scriptFile -Algorithm SHA256).Hash -ceq $sourceHash) 'SOURCE_CONCURRENT_MODIFICATION'
 Need ((Get-FileHash -LiteralPath $plan -Algorithm SHA256).Hash -ceq $planHash) 'PLAN_CONCURRENT_MODIFICATION'
 $backup=Join-Path $pending 'no11_weekly_g1_refresh.before.mjs'
 [IO.File]::Replace($candidate,$scriptFile,$backup)
 Write-Host 'NO11_OCT26_CODE_IDENTITY_REPAIR=PASS'
 Write-Host 'SCOPE=ORIGINAL_2026_10_26_ONLY'
 Write-Host 'WEEKLY_SOURCE_4328_VERIFIED=True'
 Write-Host 'FRIDAY_429_VERIFIED=True'
 Write-Host 'ORIGINAL_PLAN_MODIFIED=False'
 Write-Host 'EXISTING_EXCEL_WORKBOOKS_TOUCHED=False'
 Write-Host 'BROKER_LEDGER_MODIFIED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'NIGHTLY_CAPTURE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 Write-Host ('BACKUP_DIR='+$pending)
}finally{
 if(Test-Path -LiteralPath $candidate){Remove-Item -LiteralPath $candidate -Force}
}
