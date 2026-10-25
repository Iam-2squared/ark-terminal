# Start/resume existing received-data Shadow, optionally observe the account book.
# No installation, fitting, workbook changes, order permission or broker sending.
param(
 [string]$ConfigFile,[string]$PythonExecutable,[string]$ResumeRun,
 [string]$AccountWorkbookPath,[string]$OrderIdWorkbookPath,
 [switch]$PreflightOnly,[switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$bootstrap=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\tools\no11_received_session_controller.py'))
function BootstrapArguments([string]$config,[bool]$preflight,[string]$resume=''){
 $result=@('-B',$bootstrap,'--config',$config)
 if($preflight){$result+=@('--preflight-only')}
 if(-not [string]::IsNullOrWhiteSpace($resume)){$result+=@('--resume-run',$resume)}
 return $result
}
function RuntimeReady([string]$exe,[string[]]$prefix){
 $check="import sys;from importlib.metadata import version;assert sys.version_info[:2]==(3,12);assert all(version(k)==v for k,v in [('numpy','2.3.5'),('scipy','1.17.0'),('scikit-learn','1.8.0')]);import numpy,scipy,sklearn"
 try{& $exe @prefix -B -c $check 2>$null | Out-Null;return ($LASTEXITCODE -eq 0)}catch{return $false}
}
function QuotedFile([string]$value){
 if($value.Contains('"') -or $value.Contains("`r") -or $value.Contains("`n")){
  throw 'NO11_BOOTSTRAP_ARGUMENT_INVALID'
 }
 return '"'+$value+'"'
}
function AssertWorkbookPair([string]$accountFile,[string]$idFile){
 if(-not [string]::IsNullOrWhiteSpace($idFile) -and [string]::IsNullOrWhiteSpace($accountFile)){
  throw 'NO11_BOOTSTRAP_ORDER_IDS_REQUIRE_ACCOUNT_WORKBOOK'
 }
}
function ConfiguredOrderIdPath([string]$configuredFile,[string]$explicitFile){
 if([string]::IsNullOrWhiteSpace($configuredFile)){
  if(-not [string]::IsNullOrWhiteSpace($explicitFile)){throw 'NO11_BOOTSTRAP_ORDER_ID_CONFIG_MATCH_REQUIRED'}
  return ''
 }
 if(-not [IO.Path]::IsPathRooted($configuredFile) -or [IO.Path]::GetExtension($configuredFile) -ine '.xlsx'){
  throw 'NO11_BOOTSTRAP_ORDER_ID_WORKBOOK_REQUIRED'
 }
 $full=[IO.Path]::GetFullPath($configuredFile)
 if(-not [string]::IsNullOrWhiteSpace($explicitFile)){
  if(-not [IO.Path]::IsPathRooted($explicitFile) -or
     -not $full.Equals([IO.Path]::GetFullPath($explicitFile),[StringComparison]::OrdinalIgnoreCase)){
   throw 'NO11_BOOTSTRAP_ORDER_ID_CONFIG_MATCH_REQUIRED'
  }
 }
 return $full
}
function AccountObserverArguments([string]$scriptFile,[string]$accountFile,[string]$outputFile,[string]$stopFile,[string]$idFile=''){
 AssertWorkbookPair $accountFile $idFile
 $result=@('-NoProfile','-ExecutionPolicy','Bypass','-File',(QuotedFile $scriptFile),
  '-WorkbookPath',(QuotedFile $accountFile),'-OutputFile',(QuotedFile $outputFile),
  '-StopFile',(QuotedFile $stopFile))
 if(-not [string]::IsNullOrWhiteSpace($idFile)){$result+=@('-OrderIdWorkbookPath',(QuotedFile $idFile))}
 return $result
}
function AssertAccountConfig($value){
 $names=@($value.PSObject.Properties.Name)
 if('h235ModelRoot' -notin $names -or
    ('shadowAccountConfig' -notin $names -and 'brokerExecutionConfig' -notin $names)){
  throw 'NO11_BOOTSTRAP_ACCOUNT_REQUIRES_PORTFOLIO_CONFIG'
 }
}
if($OfflineSelfTest){
 if(-not (Test-Path -LiteralPath $bootstrap -PathType Leaf)){throw 'NO11_BOOTSTRAP_SCRIPT_MISSING'}
 $a=@(BootstrapArguments 'C:\private path\config.json' $true)
 $b=@(BootstrapArguments 'C:\private path\config.json' $false)
 $r=@(BootstrapArguments 'C:\private path\config.json' $false 'C:\private path\same-run')
 if($a.Count -ne 5 -or $b.Count -ne 4 -or $a[2] -cne '--config' -or
    $a[3] -cne 'C:\private path\config.json' -or $a[4] -cne '--preflight-only' -or
    $r.Count -ne 6 -or $r[4] -cne '--resume-run' -or $r[5] -cne 'C:\private path\same-run'){
  throw 'NO11_BOOTSTRAP_ARGUMENT_SELFTEST_FAILED'
 }
 if((QuotedFile 'C:\private path\account.xlsx') -cne '"C:\private path\account.xlsx"'){
  throw 'NO11_BOOTSTRAP_QUOTED_ARGUMENT_FAILED'
 }
 $old=@(AccountObserverArguments 'observer.ps1' 'C:\private path\account.xlsx' 'out.json' 'stop')
 $ids=@(AccountObserverArguments 'observer.ps1' 'C:\private path\account.xlsx' 'out.json' 'stop' 'C:\private path\ids.xlsx')
 if($old.Count -ne 11 -or $old -contains '-OrderIdWorkbookPath' -or
    $ids.Count -ne 13 -or $ids[11] -cne '-OrderIdWorkbookPath' -or
    $ids[12] -cne '"C:\private path\ids.xlsx"'){
  throw 'NO11_BOOTSTRAP_ORDER_ID_ARGUMENT_SELFTEST_FAILED'
 }
 $blocked=$false;try{AssertWorkbookPair '' 'ids.xlsx'}catch{
  if($_.Exception.Message -ceq 'NO11_BOOTSTRAP_ORDER_IDS_REQUIRE_ACCOUNT_WORKBOOK'){$blocked=$true}else{throw}
 }
 if(-not $blocked){throw 'NO11_BOOTSTRAP_ORDER_ID_PAIR_SELFTEST_FAILED'}
 AssertAccountConfig ([pscustomobject]@{h235ModelRoot='model';shadowAccountConfig='shadow.json'})
 AssertAccountConfig ([pscustomobject]@{h235ModelRoot='model';brokerExecutionConfig='broker.json'})
 $blocked=$false;try{AssertAccountConfig ([pscustomobject]@{brokerExecutionConfig='broker.json'})}catch{
  if($_.Exception.Message -ceq 'NO11_BOOTSTRAP_ACCOUNT_REQUIRES_PORTFOLIO_CONFIG'){$blocked=$true}else{throw}
 }
 if(-not $blocked){throw 'NO11_BOOTSTRAP_ORDER_ID_CONFIG_SELFTEST_FAILED'}
 $configured=Join-Path ([IO.Path]::GetTempPath()) 'ark synthetic ids.xlsx'
 if((ConfiguredOrderIdPath $configured $configured) -cne ([IO.Path]::GetFullPath($configured)) -or
    (ConfiguredOrderIdPath $configured '') -cne ([IO.Path]::GetFullPath($configured)) -or
    (ConfiguredOrderIdPath '' '') -cne ''){throw 'NO11_BOOTSTRAP_ORDER_ID_CONFIG_PATH_SELFTEST_FAILED'}
 foreach($mismatch in @(@('',$configured),@($configured,(Join-Path ([IO.Path]::GetTempPath()) 'different.xlsx')))){
  $blocked=$false;try{ConfiguredOrderIdPath $mismatch[0] $mismatch[1] | Out-Null}catch{
   if($_.Exception.Message -ceq 'NO11_BOOTSTRAP_ORDER_ID_CONFIG_MATCH_REQUIRED'){$blocked=$true}else{throw}
  }
  if(-not $blocked){throw 'NO11_BOOTSTRAP_ORDER_ID_CONFIG_MATCH_SELFTEST_FAILED'}
 }
 Write-Host 'NO11_BOOTSTRAP_WINDOWS_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_BOOTSTRAP_RESUME_ARGUMENT_SELFTEST=PASS'
 Write-Host 'NO11_BOOTSTRAP_ORDER_ID_ARGUMENT_SELFTEST=PASS'
 Write-Host 'NO11_BOOTSTRAP_COLLECTOR_STARTED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$observer=$null;$stop=$null;$code=2
$oldSource=[Environment]::GetEnvironmentVariable('ARK_NO11_ACCOUNT_OBSERVATION_FILE','Process')
try{
 AssertWorkbookPair $AccountWorkbookPath $OrderIdWorkbookPath
 if([string]::IsNullOrWhiteSpace($ConfigFile) -or -not [IO.Path]::IsPathRooted($ConfigFile) -or
    -not (Test-Path -LiteralPath $ConfigFile -PathType Leaf)){
  throw 'NO11_BOOTSTRAP_CONFIG_FILE_REQUIRED'
 }
 $ConfigFile=[IO.Path]::GetFullPath($ConfigFile)
 if((Get-Item -LiteralPath $ConfigFile).Length -gt 100000){throw 'NO11_BOOTSTRAP_CONFIG_TOO_LARGE'}
 $config=Get-Content -LiteralPath $ConfigFile -Raw -Encoding UTF8 | ConvertFrom-Json
 if($config.schemaId -cne 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1' -or
    $config.productionReady -ne $false -or $config.orderTransmission -ne $false){
  throw 'NO11_BOOTSTRAP_CONFIG_NOT_READONLY'
 }
 $configuredIds=''
 if('orderIdWorkbookPath' -in $config.PSObject.Properties.Name){$configuredIds=[string]$config.orderIdWorkbookPath}
 $OrderIdWorkbookPath=ConfiguredOrderIdPath $configuredIds $OrderIdWorkbookPath
 AssertWorkbookPair $AccountWorkbookPath $OrderIdWorkbookPath
 if(-not [string]::IsNullOrWhiteSpace($OrderIdWorkbookPath)){
  if(-not (Test-Path -LiteralPath $OrderIdWorkbookPath -PathType Leaf)){throw 'NO11_BOOTSTRAP_ORDER_ID_WORKBOOK_REQUIRED'}
  if(-not [IO.Path]::IsPathRooted($AccountWorkbookPath) -or -not (Test-Path -LiteralPath $AccountWorkbookPath -PathType Leaf)){
   throw 'NO11_BOOTSTRAP_ACCOUNT_WORKBOOK_REQUIRED'
  }
 }
 if(-not [string]::IsNullOrWhiteSpace($ResumeRun)){
  if(-not [IO.Path]::IsPathRooted($ResumeRun) -or -not (Test-Path -LiteralPath $ResumeRun -PathType Container)){
   throw 'NO11_BOOTSTRAP_RESUME_RUN_REQUIRED'
  }
  $ResumeRun=[IO.Path]::GetFullPath($ResumeRun)
 }
 $exe='';$prefix=@()
 if(-not [string]::IsNullOrWhiteSpace($PythonExecutable)){
  if(-not [IO.Path]::IsPathRooted($PythonExecutable) -or -not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)){
   throw 'NO11_BOOTSTRAP_EXPLICIT_PYTHON_MISSING'
  }
  if(-not (RuntimeReady $PythonExecutable @())){throw 'NO11_BOOTSTRAP_PINNED_RUNTIME_REQUIRED'}
  $exe=$PythonExecutable
 }else{
  $candidates=@()
  if(-not [string]::IsNullOrWhiteSpace([string]$config.runtimeRoot)){
   $candidates+=@(Join-Path ([string]$config.runtimeRoot) 'runtime-py312-sklearn180\Scripts\python.exe')
  }
  if(-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)){
   $candidates+=@(Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe')
  }
  foreach($candidate in @($candidates | Select-Object -Unique)){
   if((Test-Path -LiteralPath $candidate -PathType Leaf) -and (RuntimeReady $candidate @())){$exe=$candidate;break}
  }
  if([string]::IsNullOrWhiteSpace($exe) -and (Get-Command py -ErrorAction SilentlyContinue)){
   if(RuntimeReady 'py' @('-3.12')){$exe='py';$prefix=@('-3.12')}
  }
 }
 if([string]::IsNullOrWhiteSpace($exe)){throw 'NO11_BOOTSTRAP_EXISTING_PINNED_RUNTIME_NOT_FOUND'}
 if(-not [string]::IsNullOrWhiteSpace($AccountWorkbookPath) -and -not $PreflightOnly){
  if(-not [IO.Path]::IsPathRooted($AccountWorkbookPath) -or -not (Test-Path -LiteralPath $AccountWorkbookPath -PathType Leaf)){
   throw 'NO11_BOOTSTRAP_ACCOUNT_WORKBOOK_REQUIRED'
  }
  AssertAccountConfig $config
  $private=[IO.Path]::GetFullPath([string]$config.privateRoot)
  $repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
  if(-not (Test-Path -LiteralPath $private -PathType Container) -or
     $private.Equals($repo,[StringComparison]::OrdinalIgnoreCase) -or
     $private.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){
   throw 'NO11_BOOTSTRAP_ACCOUNT_PRIVATE_ROOT_REQUIRED'
  }
  $cursor=$private
  while(-not [string]::IsNullOrWhiteSpace($cursor)){
   if(((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
    throw 'NO11_BOOTSTRAP_ACCOUNT_PRIVATE_REPARSE'
   }
   $next=Split-Path -Parent $cursor;if($next -ceq $cursor){break};$cursor=$next
  }
  if([string]$config.sessionDate -cnotmatch '^20\d{2}-\d{2}-\d{2}$'){throw 'NO11_BOOTSTRAP_ACCOUNT_SESSION_INVALID'}
  $source=Join-Path $private ('account-source-'+[string]$config.sessionDate+'.json')
  if(Test-Path -LiteralPath $source){
   if(((Get-Item -LiteralPath $source -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'NO11_BOOTSTRAP_ACCOUNT_SOURCE_REPARSE'}
  }
  $token=[guid]::NewGuid().ToString('N')
  $stop=Join-Path $private ('account-observer-'+$token+'.stop')
  $script=Join-Path $PSScriptRoot 'Observe-No11AccountReadOnly.ps1'
  $observerArgs=@(AccountObserverArguments $script ([IO.Path]::GetFullPath($AccountWorkbookPath)) $source $stop $OrderIdWorkbookPath)
  $env:ARK_NO11_ACCOUNT_OBSERVATION_FILE=$source
  $observer=Start-Process -FilePath 'powershell.exe' -ArgumentList $observerArgs -PassThru -WindowStyle Hidden `
   -RedirectStandardOutput (Join-Path $private ('account-'+$token+'.log')) `
   -RedirectStandardError (Join-Path $private ('account-'+$token+'.err'))
  Write-Host 'NO11_BOOTSTRAP_ACCOUNT_OBSERVER_STARTED=True'
 }
 $arguments=@(BootstrapArguments $ConfigFile ([bool]$PreflightOnly) $ResumeRun)
 & $exe @prefix @arguments
 $code=$LASTEXITCODE
}catch{
 $reason=$_.Exception.Message
 if($reason -notmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_BOOTSTRAP_WINDOWS_PRIVATE_INPUT_FAILURE'}
 Write-Host ('NO11_BOOTSTRAP=BLOCKED|'+$reason)
 $code=2
}finally{
 if($null -ne $observer){
  try{
   [IO.File]::WriteAllText($stop,'STOP',[Text.UTF8Encoding]::new($false))
   if(-not $observer.WaitForExit(30000)){
    Write-Host 'NO11_ACCOUNT_OBSERVER_STOP=UNCONFIRMED_NO_EXCEL_KILL';$code=2
   }elseif($observer.ExitCode -ne 0){Write-Host 'NO11_ACCOUNT_OBSERVER_EXIT=FAILED';$code=2}
  }catch{Write-Host 'NO11_ACCOUNT_OBSERVER_STOP=UNCONFIRMED_NO_EXCEL_KILL';$code=2}
 }
 [Environment]::SetEnvironmentVariable('ARK_NO11_ACCOUNT_OBSERVATION_FILE',$oldSource,'Process')
 Write-Host 'ORDER_TRANSMISSION=False'
}
exit $code
