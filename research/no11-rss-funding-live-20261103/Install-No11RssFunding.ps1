param(
 [string]$Root='C:\ArkTerminal\no11-unified-2026-10-30',
 [string]$PythonExecutable='',
 [switch]$Apply
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if(-not (Test-Path -LiteralPath $Root -PathType Container)){throw 'NO11_RSS_INSTALL_ROOT_MISSING'}
$running=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
 $_.ProcessId -ne $PID -and $_.Name -match '^(pythonw?|powershell|pwsh|node)(\.exe)?$' -and
 [string]$_.CommandLine -match '(?i)(Start-No11UnifiedLauncher|Run-No11ReceivedSession|no11_received_session|no11_received_pipeline_service|Observe-No11AccountReadOnly|Probe-No11Chart50ContinuousReadOnly)'
})
if($running.Count){throw 'NO11_RSS_INSTALL_CLOSE_ARK_FIRST'}
if([string]::IsNullOrWhiteSpace($PythonExecutable)){
 $PythonExecutable=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
}
if(-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)){throw 'NO11_RSS_INSTALL_PINNED_PYTHON_MISSING'}
$arguments=@('-B',(Join-Path $PSScriptRoot 'install.py'),'--root',$Root)
if($Apply){
 $arguments+=@('--apply','--backup-parent',(Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'))
}
& $PythonExecutable @arguments
if($LASTEXITCODE -ne 0){throw 'NO11_RSS_INSTALL_STOPPED_SEE_ERROR_ABOVE'}
