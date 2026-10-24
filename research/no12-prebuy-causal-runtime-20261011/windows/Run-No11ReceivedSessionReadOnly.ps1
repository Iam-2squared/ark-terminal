# Start saved-source preparation + RSS collector + inference consumer, READ ONLY.
# No installation, model fitting, Excel order permission or broker transmission.
param(
 [string]$ConfigFile,
 [string]$PythonExecutable,
 [switch]$PreflightOnly,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$bootstrap=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\tools\no11_received_session_bootstrap.py'))
function BootstrapArguments([string]$config,[bool]$preflight){
 $result=@('-B',$bootstrap,'--config',$config)
 if($preflight){$result+=@('--preflight-only')}
 return $result
}
function RuntimeReady([string]$exe,[string[]]$prefix){
 $code="import sys;from importlib.metadata import version;assert sys.version_info[:2]==(3,12);assert all(version(k)==v for k,v in [('numpy','2.3.5'),('scipy','1.17.0'),('scikit-learn','1.8.0')]);import numpy,scipy,sklearn"
 try{
  & $exe @prefix -B -c $code 2>$null | Out-Null
  return ($LASTEXITCODE -eq 0)
 }catch{return $false}
}
if($OfflineSelfTest){
 if(-not (Test-Path -LiteralPath $bootstrap -PathType Leaf)){throw 'NO11_BOOTSTRAP_SCRIPT_MISSING'}
 $a=@(BootstrapArguments 'C:\private path\config.json' $true)
 $b=@(BootstrapArguments 'C:\private path\config.json' $false)
 if($a.Count -ne 5 -or $b.Count -ne 4 -or $a[2] -cne '--config' -or
    $a[3] -cne 'C:\private path\config.json' -or $a[4] -cne '--preflight-only'){
  throw 'NO11_BOOTSTRAP_ARGUMENT_SELFTEST_FAILED'
 }
 Write-Host 'NO11_BOOTSTRAP_WINDOWS_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_BOOTSTRAP_COLLECTOR_STARTED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 if([string]::IsNullOrWhiteSpace($ConfigFile) -or
    -not [IO.Path]::IsPathRooted($ConfigFile) -or
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
 $exe='';$prefix=@()
 if(-not [string]::IsNullOrWhiteSpace($PythonExecutable)){
  if(-not [IO.Path]::IsPathRooted($PythonExecutable) -or
     -not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)){
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
   if((Test-Path -LiteralPath $candidate -PathType Leaf) -and (RuntimeReady $candidate @())){
    $exe=$candidate;break
   }
  }
  if([string]::IsNullOrWhiteSpace($exe) -and (Get-Command py -ErrorAction SilentlyContinue)){
   if(RuntimeReady 'py' @('-3.12')){$exe='py';$prefix=@('-3.12')}
  }
 }
 if([string]::IsNullOrWhiteSpace($exe)){throw 'NO11_BOOTSTRAP_EXISTING_PINNED_RUNTIME_NOT_FOUND'}
 $arguments=@(BootstrapArguments $ConfigFile ([bool]$PreflightOnly))
 & $exe @prefix @arguments
 $code=$LASTEXITCODE
 Write-Host 'ORDER_TRANSMISSION=False'
 exit $code
}catch{
 $reason=$_.Exception.Message
 if($reason -notmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_BOOTSTRAP_WINDOWS_PRIVATE_INPUT_FAILURE'}
 Write-Host ('NO11_BOOTSTRAP=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
