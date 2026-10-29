# Separate explicit Windows LIVE operator entry for ordinary MAX3 No.1.1.
# The existing Run-No11ReceivedSessionReadOnly.ps1 remains permanently OFF.
param(
 [string]$ConfigFile='',
 [string]$AccountWorkbookPath='',
 [string]$OrderIdWorkbookPath='',
 [string]$PythonExecutable='',
 [string]$ResumeRun='',
 [switch]$PreflightOnly,
 [switch]$IApproveFullArkLiveOrdersForThisSession,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$engine=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$controller=Join-Path $engine 'tools\no11_received_session_controller.py'
$observer=Join-Path $PSScriptRoot 'Observe-No11AccountReadOnly.ps1'
$repo=[IO.Path]::GetFullPath((Join-Path $engine '..\..'))
$root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
function Need([bool]$yes,[string]$reason){
 if(-not $yes){throw ('NO11_OPERATOR_LIVE_'+$reason)}
}
function Private([string]$value,[bool]$directory=$false){
 Need (-not [string]::IsNullOrWhiteSpace($value) -and [IO.Path]::IsPathRooted($value)) 'PRIVATE_ABSOLUTE_PATH_REQUIRED'
 $p=[IO.Path]::GetFullPath($value)
 Need (-not $p.Equals($repo,[StringComparison]::OrdinalIgnoreCase) -and
       -not $p.StartsWith(($repo+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)) 'PATH_IN_REPOSITORY'
 if($directory){Need (Test-Path -LiteralPath $p -PathType Container) 'PRIVATE_DIRECTORY_MISSING'}
 else{Need (Test-Path -LiteralPath $p -PathType Leaf) 'PRIVATE_SOURCE_MISSING'}
 $cur=$p
 while(-not [string]::IsNullOrWhiteSpace($cur)){
  $obj=Get-Item -LiteralPath $cur -Force
  Need (($obj.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  $next=Split-Path -Parent $cur
  if($next -ceq $cur){break}
  $cur=$next
 }
 return $p
}
function Quote([string]$value){
 Need (-not $value.Contains('"') -and
       -not $value.Contains([char]13) -and -not $value.Contains([char]10)) 'ARGUMENT_QUOTE'
 return '"'+$value+'"'
}
if($OfflineSelfTest){
 Need (-not $IApproveFullArkLiveOrdersForThisSession -and -not $PreflightOnly) 'SELFTEST_REQUIRES_NO_APPROVAL'
 Need (Test-Path -LiteralPath $controller -PathType Leaf) 'CONTROLLER_SOURCE_MISSING'
 Need (Test-Path -LiteralPath $observer -PathType Leaf) 'OBSERVER_SOURCE_MISSING'
 $text=Get-Content -LiteralPath $controller -Raw -Encoding UTF8
 Need ($text.Contains('--operator-approved-broker-live') -and
       $text.Contains('allow_explicit_live=allow_explicit_live')) 'LIVE_CONTROLLER_NOT_INSTALLED'
 Write-Host 'NO11_OPERATOR_LIVE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_OPERATOR_LIVE_MAX3_NOT_LIMITED_TO_ONE=True'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$child=$null;$stop='';$exitCode=2
$originalEnv=[Environment]::GetEnvironmentVariable('ARK_NO11_ACCOUNT_OBSERVATION_FILE','Process')
try{
 Need $IApproveFullArkLiveOrdersForThisSession.IsPresent 'SAME_DAY_OPERATOR_APPROVAL_REQUIRED'
 Need ([TimeZoneInfo]::Local.GetUtcOffset([datetime]::Now).TotalHours -eq 9) 'PC_TIMEZONE_NOT_JST'
 $now=[DateTimeOffset]::Now.ToOffset([timespan]::FromHours(9))
 $today=$now.ToString('yyyy-MM-dd')
 $ConfigFile=Private $ConfigFile
 $AccountWorkbookPath=Private $AccountWorkbookPath
 $OrderIdWorkbookPath=Private $OrderIdWorkbookPath
 Need ($AccountWorkbookPath -cne $OrderIdWorkbookPath -and
       $AccountWorkbookPath.EndsWith('.xlsx',[StringComparison]::OrdinalIgnoreCase) -and
       $OrderIdWorkbookPath.EndsWith('.xlsx',[StringComparison]::OrdinalIgnoreCase)) 'WORKBOOK_PAIR_INVALID'
 $cfg=Get-Content -LiteralPath $ConfigFile -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($cfg.schemaId -ceq 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1' -and
       $cfg.sessionDate -ceq $today -and
       $cfg.orderTransmission -eq $false -and
       $cfg.productionReady -eq $false) 'BOOTSTRAP_SESSION_OR_MODE'
 Need ([IO.Path]::GetFullPath([string]$cfg.orderIdWorkbookPath).Equals(
        $OrderIdWorkbookPath,[StringComparison]::OrdinalIgnoreCase)) 'ORDER_ID_WORKBOOK_IDENTITY'
 $privateRoot=Private ([string]$cfg.privateRoot) $true
 Need ([string]$cfg.h235ModelRoot -ne '' -and
       [string]$cfg.brokerExecutionConfig -ne '') 'ORIGINAL_H235_AND_BROKER_REQUIRED'
 $brokerFile=Private ([string]$cfg.brokerExecutionConfig)
 $broker=Get-Content -LiteralPath $brokerFile -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($broker.schemaId -ceq 'ARK_NO11_BROKER_EXECUTION_CONFIG_V1' -and
       $broker.sessionDate -ceq $today -and
       $broker.evidenceMode -ceq 'BROKER_OBSERVATION' -and
       $broker.orderTransmission -eq $true) 'BROKER_LIVE_CONFIG_REQUIRED'
 Need ($broker.transport.mode -ceq 'LIVE' -and
       $broker.transport.orderTransmission -eq $true -and
       $broker.transport.operatorEnabled -eq $true -and
       $broker.transport.approvedForSession -eq $true -and
       $broker.transport.sessionDate -ceq $today) 'TRANSPORT_SESSION_APPROVAL'
 Need ($broker.ledger.maxSymbols -eq 3 -and
       $broker.ledger.lotSize -eq 100 -and
       $broker.ledger.allocatedCashJpy -ceq 'AUTO_SECURITIES_ACCOUNT_CASH_ONLY') 'MAX3_AND_SECURITIES_CASH'
 $cash=Get-Content -LiteralPath (Private ([string]$broker.securitiesCashEvidenceFile)) -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($cash.sessionDate -ceq $today -and
       $cash.operatorReviewed -eq $true -and
       $cash.bankBridgeExcluded -eq $true -and
       $cash.autoSweepDisabledConfirmed -eq $true -and
       $cash.marginAndCreditExcluded -eq $true) 'REVIEWED_SECURITIES_ONLY_CASH'
 $python=if($PythonExecutable){Private $PythonExecutable}else{
  Private (Join-Path $root 'frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe')
 }
 Need ((Get-Item -LiteralPath $python).Name -ieq 'python.exe') 'PINNED_PYTHON_BINARY'
 Need ((Test-Path -LiteralPath $controller -PathType Leaf) -and
       (Test-Path -LiteralPath $observer -PathType Leaf)) 'LIVE_RUNTIME_NOT_INSTALLED'
 $source=Get-Content -LiteralPath $controller -Raw -Encoding UTF8
 Need ($source.Contains('--operator-approved-broker-live') -and
       $source.Contains('allow_explicit_live=allow_explicit_live')) 'LIVE_CONTROLLER_NOT_STAGED'
 if(-not $PreflightOnly){
  Need ($now.ToString('HH:mm:ss') -ge '09:00:00' -and
        $now.ToString('HH:mm:ss') -le '15:20:00') 'MARKET_SESSION_REQUIRED'
  Need (@(Get-Process EXCEL -ErrorAction SilentlyContinue).Count -eq 1) 'EXCEL_PROCESS_NOT_UNIQUE'
 }
 $args=@('-B',$controller,'--config',$ConfigFile,'--operator-approved-broker-live')
 if($PreflightOnly){$args+=@('--preflight-only')}
 if($ResumeRun){
  $saved=Private $ResumeRun $true
  Need ($saved.StartsWith(($privateRoot+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)) 'RESUME_NOT_PRIVATE_RUN'
  $args+=@('--resume-run',$saved)
 }
 if($PreflightOnly){
  & $python @args
  $exitCode=$LASTEXITCODE
  Need ($exitCode -eq 0) 'FULL_FROZEN_PREFLIGHT_BLOCKED'
  Write-Host 'NO11_OPERATOR_LIVE_PREFLIGHT=MODELS_AND_CONFIG_ONLY'
  Write-Host 'ORDER_TRANSMISSION=False'
 }else{
  $id=[guid]::NewGuid().ToString('N')
  $sourceFile=Join-Path $privateRoot ('account-source-'+$today+'.json')
  $stop=Join-Path $privateRoot ('operator-live-observer-'+$id+'.stop')
  $obsArgs=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
    '-File',(Quote $observer),'-WorkbookPath',(Quote $AccountWorkbookPath),
    '-OrderIdWorkbookPath',(Quote $OrderIdWorkbookPath),
    '-OutputFile',(Quote $sourceFile),'-StopFile',(Quote $stop))
  $child=Start-Process -FilePath 'powershell.exe' -ArgumentList $obsArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $privateRoot ('operator-observer-'+$id+'.log')) -RedirectStandardError (Join-Path $privateRoot ('operator-observer-'+$id+'.err'))
  [Environment]::SetEnvironmentVariable('ARK_NO11_ACCOUNT_OBSERVATION_FILE',$sourceFile,'Process')
  Write-Host 'NO11_OPERATOR_LIVE_ACCOUNT_OBSERVER=READ_ONLY_RUNNING'
  Write-Host 'NO11_OPERATOR_LIVE_MAX_ARK_POSITIONS=3'
  Write-Host 'NO11_OPERATOR_LIVE_TRANSMISSION=ONLY_WHEN_FROZEN_SIGNAL_AND_ALL_GATES_PASS'
  & $python @args
  $exitCode=$LASTEXITCODE
 }
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_OPERATOR_LIVE_[A-Z0-9_]+$'){
  $reason='NO11_OPERATOR_LIVE_PRIVATE_SESSION_OR_RUNTIME_BLOCKED'
 }
 Write-Host ('NO11_OPERATOR_LIVE=BLOCKED|'+$reason)
 $exitCode=2
}finally{
 if($null -ne $child){
  try{
   [IO.File]::WriteAllText($stop,'STOP',[Text.UTF8Encoding]::new($false))
   if(-not $child.WaitForExit(30000)){
    Write-Host 'NO11_OPERATOR_LIVE_OBSERVER_STOP=UNCONFIRMED_NO_EXCEL_KILL'
    $exitCode=2
   }elseif($child.ExitCode -ne 0){
    Write-Host 'NO11_OPERATOR_LIVE_OBSERVER_EXIT=FAILED'
    $exitCode=2
   }
  }catch{
   Write-Host 'NO11_OPERATOR_LIVE_OBSERVER_STOP=UNCONFIRMED_NO_EXCEL_KILL'
   $exitCode=2
  }
 }
 [Environment]::SetEnvironmentVariable('ARK_NO11_ACCOUNT_OBSERVATION_FILE',$originalEnv,'Process')
}
if($exitCode -ne 0){exit 2}
exit 0
