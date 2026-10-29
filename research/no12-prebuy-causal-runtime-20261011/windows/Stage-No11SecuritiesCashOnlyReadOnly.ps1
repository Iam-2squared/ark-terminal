# Two distinct Windows roots:
# 1) physical-account-overlay = isolated 10-file RSS READ-ONLY observer.
#    It deliberately has NO broker_execution_service.py. Install ONLY the
#    offline securities-cash evidence helper here; never add a fake engine.
# 2) C:\ArkTerminal\no12-launcher = optional existing FULL No12 runtime.
#    Upgrade the two pinned Python cash-guard files ONLY when its original
#    broker service + all required neighboring dependencies are present.
# No Excel/MarketSpeed II, order permission, broker ledger or original Freeze
# touched. An unavailable or changed full engine remains explicitly NOT_READY.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$revision='667d2a8fe6110fce2f994e4e7c4894353bdffc02'
$helper=[pscustomobject]@{
 Name='New-No11SecuritiesCashEvidenceReadOnly.ps1';Sub='windows';Old='';
 New='16ca163370b016b2b6eb3c0e3e40cccb37ddf99e'
}
$live=@(
 [pscustomobject]@{Name='no11_broker_execution_service.py';Sub='tools';
  Old='370b27c98a7ee776dfa8fb9b4c7f99a4c05cd090';New='defd247735eec987b53fcf9852668be760b27a40'},
 [pscustomobject]@{Name='no11_securities_cash_only.py';Sub='tools';
  Old='';New='fe1b1d401f7545512afe43641abceca5b4bd5ab0'}
)
$dependencies=@(
 'no11_broker_execution_ledger.py',
 'no11_broker_fill_attribution.py',
 'no11_broker_decision_bridge.py',
 'no11_h235_asof_forward_shadow.py',
 'no11_h235_capital_v5_shadow.py',
 'no11_rss_state9_p1_runner.py',
 'no11_observed_execution_shadow.py',
 'no11_broker_bridge.mjs',
 'no11_msii_transport.mjs'
)
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_SECURITIES_CASH_STAGE_'+$reason)}
}
function Blob([string]$file){
 $h=@(& git hash-object --no-filters $file)
 Need ($LASTEXITCODE -eq 0 -and $h.Count -eq 1 -and [string]$h[0] -cmatch '^[0-9a-f]{40}$') 'GIT_HASH_UNAVAILABLE'
 return [string]$h[0]
}
function Safe([string]$file){
 $p=[IO.Path]::GetFullPath($file);$cursor=$p
 while(-not [string]::IsNullOrEmpty($cursor)){
  if(Test-Path -LiteralPath $cursor){
   Need (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  }
  $parent=Split-Path -Parent $cursor
  if($parent -ceq $cursor){break}
  $cursor=$parent
 }
 return $p
}
function Test-PinnedExisting($file,$oldHash,$newHash){
 if(-not (Test-Path -LiteralPath $file -PathType Leaf)){
  return ($oldHash -ceq '')
 }
 $hash=Blob $file
 return ($hash -ceq $newHash -or ($oldHash -cne '' -and $hash -ceq $oldHash))
}
function Add-Candidate([System.Collections.ArrayList]$result,$engine,$pin,$scope){
 $target=Safe (Join-Path (Join-Path $engine $pin.Sub) $pin.Name)
 Need (Test-Path -LiteralPath (Split-Path -Parent $target) -PathType Container) 'TARGET_PARENT_MISSING'
 Need (-not (Test-Path -LiteralPath $target -PathType Container)) 'DESTINATION_IS_DIRECTORY'
 $exists=Test-Path -LiteralPath $target -PathType Leaf
 $hash=if($exists){Blob $target}else{'MISSING'}
 Write-Host ('NO11_SECURITIES_CASH_SOURCE_'+$scope+'_'+$pin.Name+'='+$hash)
 Need (Test-PinnedExisting $target $pin.Old $pin.New) 'LOCAL_FILE_CHANGED_NO_OVERWRITE'
 if($hash -ceq $pin.New){return}
 [void]$result.Add([pscustomobject]@{scope=$scope;pin=$pin;target=$target;oldHash=$hash})
}
if($OfflineSelfTest){
 Need ($revision -cmatch '^[a-f0-9]{40}$' -and $live.Count -eq 2 -and
  $helper.New -cmatch '^[a-f0-9]{40}$' -and $dependencies.Count -eq 9) 'STATIC_PINS'
 Need ($helper.Old -ceq '' -and $live[0].Old -cmatch '^[a-f0-9]{40}$' -and
  $live[1].Old -ceq '') 'ROOT_SEPARATION'
 # The 10-file RSS overlay intentionally lacks the service. It is legitimate
 # to stage ONLY an evidence helper without pretending a LIVE engine exists.
 Need ($helper.Name -like '*.ps1' -and
  @($live | Where-Object {$_.Name -like '*.py'}).Count -eq 2) 'ISOLATED_SCOPE'
 Write-Host 'NO11_SECURITIES_CASH_STAGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_SECURITIES_CASH_STAGE_OVERLAY_IS_READONLY_NOT_FULL_ENGINE=True'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command powershell.exe -ErrorAction Stop)
 $base=Safe (Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12')
 $isolated=Safe (Join-Path $base 'physical-account-overlay\source\research\no12-prebuy-causal-runtime-20261011')
 Need (Test-Path -LiteralPath $isolated -PathType Container) 'ISOLATED_OBSERVER_ROOT_MISSING'
 $oneShot=Safe (Join-Path $isolated 'windows\Run-No11PhysicalAccountOneShotReadOnly.ps1')
 Need (Test-Path -LiteralPath $oneShot -PathType Leaf) 'PINNED_READONLY_OBSERVER_MISSING'
 Need ((Blob $oneShot) -ceq '89ea56ab1ee7c25fad8cebb36a5043e3a853ded3') 'READONLY_OBSERVER_CHANGED'
 $active=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
  Where-Object {$_.ProcessId -ne $PID -and [string]$_.CommandLine -match
   '(?i)(no11_broker_execution_service|no11_received_session_controller|Run-No11ReceivedSessionReadOnly|Run-No11PhysicalAccountOneShotReadOnly|Observe-No11AccountReadOnly)'} )
 Need ($active.Count -eq 0) 'BROKER_OR_ACCOUNT_WORKER_RUNNING'
 $plans=New-Object System.Collections.ArrayList
 Add-Candidate $plans $isolated $helper 'READONLY_OVERLAY'
 # Never copy a partially functional real-order engine into the intentionally
 # isolated 10-file observer. Detect the separate full runtime instead.
 $full=Safe 'C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011'
 $fullState='NOT_FOUND'
 if(Test-Path -LiteralPath $full -PathType Container){
  $service=Safe (Join-Path $full 'tools\no11_broker_execution_service.py')
  if(-not (Test-Path -LiteralPath $service -PathType Leaf)){
   $fullState='SERVICE_NOT_INSTALLED'
  }elseif(@($dependencies | Where-Object {
    -not (Test-Path -LiteralPath (Join-Path $full 'tools' $_) -PathType Leaf)
   }).Count -gt 0){
   $fullState='DEPENDENCIES_MISSING'
  }elseif(-not (Test-PinnedExisting $service $live[0].Old $live[0].New)){
   $fullState='CUSTOM_SERVICE_HASH_NO_OVERWRITE'
  }else{
   $cash=Safe (Join-Path $full 'tools\no11_securities_cash_only.py')
   if(-not (Test-PinnedExisting $cash $live[1].Old $live[1].New)){
    $fullState='CUSTOM_CASH_MODULE_NO_OVERWRITE'
   }else{
    foreach($pin in $live){Add-Candidate $plans $full $pin 'FULL_ENGINE'}
    $fullState='PINNED_FULL_ENGINE_READY_TO_STAGE'
   }
  }
 }
 $folder=Safe (Join-Path $base ('securities-cash-upgrade\'+[guid]::NewGuid().ToString('N')))
 $downloads=Join-Path $folder 'downloads'
 $backups=Join-Path $folder 'backups'
 [void][IO.Directory]::CreateDirectory($downloads)
 [void][IO.Directory]::CreateDirectory($backups)
 # Full download/parse/hash verification BEFORE any source file changes.
 $prepared=New-Object System.Collections.ArrayList
 foreach($plan in $plans){
  $pin=$plan.pin
  $download=Safe (Join-Path $downloads $pin.Name)
  $uri='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
    '/research/no12-prebuy-causal-runtime-20261011/'+$pin.Sub+'/'+$pin.Name
  Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $download
  Need ((Blob $download) -ceq $pin.New) 'PINNED_DOWNLOAD_CHANGED'
  if($pin.Name -like '*.ps1'){
   $tokens=$null;$errors=$null
   [void][Management.Automation.Language.Parser]::ParseFile($download,[ref]$tokens,[ref]$errors)
   Need ($errors.Count -eq 0) 'POWERSHELL_PARSE_FAILED'
  }else{
   [void](Get-Command py -ErrorAction Stop)
   & py -3.12 -B -c 'import ast,sys;ast.parse(open(sys.argv[1],encoding="utf-8-sig").read())' $download
   Need ($LASTEXITCODE -eq 0) 'PYTHON_PARSE_FAILED'
  }
  $backup=Join-Path $backups ($plan.scope+'-'+$pin.Name+'.bak')
  [void]$prepared.Add([pscustomobject]@{plan=$plan;new=$download;backup=$backup})
 }
 # Verify installed source again after network work, before touching it.
 foreach($r in $prepared){
  $p=$r.plan
  Need (Test-PinnedExisting $p.target $p.pin.Old $p.pin.New) 'SOURCE_CHANGED_DURING_DOWNLOAD'
  $old=if(Test-Path -LiteralPath $p.target -PathType Leaf){Blob $p.target}else{'MISSING'}
  Need ($old -ceq $p.oldHash) 'SOURCE_CHANGED_DURING_DOWNLOAD'
  if($old -cne 'MISSING'){[IO.File]::Copy($p.target,$r.backup,$false)}
 }
 $done=New-Object System.Collections.ArrayList
 try{
  foreach($r in $prepared){
   [void]$done.Add($r)
   [IO.File]::Copy($r.new,$r.plan.target,($r.plan.oldHash -cne 'MISSING'))
   Need ((Blob $r.plan.target) -ceq $r.plan.pin.New) 'COPIED_BLOB_CHANGED'
  }
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $isolated 'windows\New-No11SecuritiesCashEvidenceReadOnly.ps1') -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'EVIDENCE_HELPER_TEST_FAILED'
 }catch{
  for($i=$done.Count-1;$i -ge 0;$i--){
   $item=$done[$i]
   if($item.plan.oldHash -ceq 'MISSING'){
    if(Test-Path -LiteralPath $item.plan.target -PathType Leaf){[IO.File]::Delete($item.plan.target)}
   }else{
    [IO.File]::Copy($item.backup,$item.plan.target,$true)
   }
  }
  throw
 }
 $installedState=if($fullState -ceq 'PINNED_FULL_ENGINE_READY_TO_STAGE'){
  'PINNED_FULL_ENGINE_CASH_GUARD_STAGED'
 }else{'FULL_ENGINE_NOT_CHANGED'}
 Write-Host ('NO11_SECURITIES_CASH_STAGE=PASS_READONLY_EVIDENCE_HELPER')
 Write-Host ('NO11_SECURITIES_CASH_STAGE_FULL_ENGINE='+$fullState)
 Write-Host ('NO11_SECURITIES_CASH_STAGE_ENGINE_RESULT='+$installedState)
 Write-Host ('NO11_SECURITIES_CASH_STAGE_BACKUP='+$backups)
 Write-Host 'NO11_SECURITIES_CASH_STAGE_FULL_LIVE_AUTHORIZED=False'
 Write-Host 'NO11_SECURITIES_CASH_STAGE_ORIGINAL_ARK_TOUCHED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_SECURITIES_CASH_STAGE_[A-Z0-9_]+$'){
  $reason='NO11_SECURITIES_CASH_STAGE_LOCAL_OR_RUNTIME_FAILURE'
 }
 Write-Host ('NO11_SECURITIES_CASH_STAGE=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
