# Same-day helper: reuse validated Classic configuration, never stale stock prices.
# Optional new private synthetic 2026-10-28 config keeps prior virtual cash
# unchanged, but never creates/approves external security evidence or orders.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [string]$SecurityEvidence='',
 [string]$EvidenceDocuments='',
 [string]$BootstrapTemplate='',
 [switch]$CaptureReference,[switch]$Preflight,[switch]$StartShadow,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$name){if(-not $ok){throw ('NO11_QUICKSTART_'+$name)}}
function FreshFile([string]$p,$value){
 $raw=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $value -Depth 32 -Compress)+[char]10)
 if(Test-Path -LiteralPath $p){
  Need ([Convert]::ToBase64String([IO.File]::ReadAllBytes($p)) -ceq
   [Convert]::ToBase64String($raw)) 'IMMUTABLE_CONFIG_CHANGED'
 }else{
  $f=[IO.File]::Open($p,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$f.Write($raw,0,$raw.Length);$f.Flush($true)}finally{$f.Dispose()}
 }
 return $p
}
if($OfflineSelfTest){
 Need (-not ($Preflight -and $StartShadow)) 'MODE_CONFLICT'
 Write-Host 'NO11_OCT28_QUICKSTART_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_OCT28_QUICKSTART_EXCEL_ACCESSED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need (-not ($Preflight -and $StartShadow)) 'MODE_CONFLICT'
 $today=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-dd')
 Need ($today -ceq '2026-10-28') 'WRONG_SESSION_DATE'
 $root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
 $runner=Join-Path $EngineRoot 'windows\Run-No11Oct28AfternoonShadowReadOnly.ps1'
 Need (Test-Path -LiteralPath $runner -PathType Leaf) 'WEEKLY_BRIDGE_NOT_INSTALLED'
 if($CaptureReference){
  Need (-not ($Preflight -or $StartShadow)) 'CAPTURE_MODE_CONFLICT'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner -CaptureReference
  exit $LASTEXITCODE
 }
 if(-not ($Preflight -or $StartShadow)){
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner
  exit $LASTEXITCODE
 }
 $candidates=@(
  (Join-Path $root 'shadow-oneclick-classic\launcher-settings.json'),
  (Join-Path $root 'shadow-oneclick\launcher-settings.json')
 )
 if(-not $SecurityEvidence -or -not $EvidenceDocuments -or -not $BootstrapTemplate){
  $found=@($candidates|Where-Object {Test-Path -LiteralPath $_ -PathType Leaf})
  Need ($found.Count -eq 1) 'CLASSIC_SETTINGS_NOT_UNIQUE_OR_MISSING'
  $settings=Get-Content -LiteralPath $found[0] -Raw -Encoding UTF8|ConvertFrom-Json
  Need ($settings.schemaId -ceq 'ARK_SHADOW_ONECLICK_SETTINGS_V1' -and
   $settings.orderTransmission -eq $false) 'CLASSIC_SETTINGS_NOT_READONLY'
  if(-not $SecurityEvidence){$SecurityEvidence=[string]$settings.securityEvidenceFile}
  if(-not $EvidenceDocuments){$EvidenceDocuments=[string]$settings.evidenceDocumentsDir}
  if(-not $BootstrapTemplate){$BootstrapTemplate=[string]$settings.bootstrapTemplateFile}
 }
 Need ($SecurityEvidence -and (Test-Path -LiteralPath $SecurityEvidence -PathType Leaf)) 'EXTERNAL_REVIEW_SOURCE_MISSING'
 Need ($EvidenceDocuments -and (Test-Path -LiteralPath $EvidenceDocuments -PathType Container)) 'EXTERNAL_DOCUMENTS_MISSING'
 Need ($BootstrapTemplate -and (Test-Path -LiteralPath $BootstrapTemplate -PathType Leaf)) 'ORIGINAL_TEMPLATE_MISSING'
 $data=Get-Content -LiteralPath $BootstrapTemplate -Raw -Encoding UTF8 | ConvertFrom-Json
 Need ($data.schemaId -ceq 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1' -and
  $data.productionReady -eq $false -and $data.orderTransmission -eq $false -and
  $data.sessionDate -in @('2026-10-27','2026-10-28')) 'ORIGINAL_TEMPLATE_CONTRACT'
 $names=@($data.PSObject.Properties.Name)
 Need ('h235ModelRoot' -in $names -and 'shadowAccountConfig' -in $names -and
  'brokerExecutionConfig' -notin $names -and 'orderIdWorkbookPath' -notin $names) 'FULL_SYNTHETIC_H235_CAPITAL_EXIT_REQUIRED'
 Need (Test-Path -LiteralPath ([string]$data.shadowAccountConfig) -PathType Leaf) 'SIM_ACCOUNT_CONFIG_MISSING'
 $sim=Get-Content -LiteralPath ([string]$data.shadowAccountConfig) -Raw -Encoding UTF8 | ConvertFrom-Json
 Need ($sim.schemaId -ceq 'ARK_NO11_OBSERVED_SHADOW_ACCOUNT_V1' -and
  $sim.syntheticAccountOnly -eq $true -and $sim.productionReady -eq $false -and
  $sim.orderTransmission -eq $false -and
  $sim.fillPolicy -ceq 'NEXT_FRESH_RECEIVED_CLOSE_SIMULATION' -and
  $sim.sessionDate -in @('2026-10-27','2026-10-28')) 'SYNTHETIC_ACCOUNT_SOURCE_INVALID'
 $out=Join-Path $root 'fast-shadow-2026-10-28'
 [void][IO.Directory]::CreateDirectory($out)
 $sim.sessionDate='2026-10-28'
 $updated=FreshFile (Join-Path $out 'simulated-shadow-account-2026-10-28.json') $sim
 $data.sessionDate='2026-10-28'
 $data.shadowAccountConfig=$updated
 $template=FreshFile (Join-Path $out 'original-settings-2026-10-28.json') $data
 Write-Host 'NO11_OCT28_QUICKSTART_SIMULATOR_SESSION=COPIED_SAME_FUNDS_SYNTHETIC_ONLY'
 Write-Host 'NO11_OCT28_QUICKSTART_SECURITY_EVIDENCE=SUPPLIED_NOT_CERTIFIED_BY_WRAPPER'
 $mode=if($Preflight){'-Preflight'}else{'-StartShadow'}
 $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,
  '-BootstrapTemplate',$template,'-SecurityEvidence',$SecurityEvidence,
  '-EvidenceDocuments',$EvidenceDocuments,$mode)
 & powershell.exe @args
 exit $LASTEXITCODE
}catch{
 $code=$_.Exception.Message
 if($code -cnotmatch '^NO11_QUICKSTART_[A-Z0-9_]+$'){$code='NO11_QUICKSTART_PRIVATE_SOURCE_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_OCT28_QUICKSTART=BLOCKED|'+$code)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
