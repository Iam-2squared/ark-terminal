# One-shot verified after-close Daily/Weekly installation for locally patched weekly runner.
# Does NOT touch the white OneClick UI, Excel, session ledger, broker orders or stop markers.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$reason){if(-not $ok){throw ('NO11_NIGHTLY_BOOTSTRAP_'+$reason)}}
if($OfflineSelfTest){
 Need (-not $Apply) 'OFFLINE_ONLY'
 Write-Host 'NO11_NIGHTLY_BOOTSTRAP_OFFLINE_SELFTEST=PASS'
 Write-Host 'UI_TOUCHED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'EXPLICIT_APPLY_REQUIRED'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$bindingFile=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $bindingFile -PathType Leaf) 'BINDING_MISSING'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and $binding.orderTransmission -eq $false) 'BINDING_UNSAFE'
$python=[string]$binding.python
Need ([IO.Path]::IsPathRooted($python) -and (Test-Path -LiteralPath $python -PathType Leaf)) 'PYTHON_MISSING'
$active=@(Get-CimInstance Win32_Process | Where-Object {
 $_.ProcessId -ne $PID -and
 $_.Name -match '^(powershell|pwsh|python|pythonw)(\.exe)?$' -and
 [string]$_.CommandLine -match 'Start-No11OneClick\.ps1|Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder'
})
Need ($active.Count -eq 0) 'CLOSE_ARK_PROCESSES_FIRST'
$repo='Iam-2squared/ark-terminal'
$commit='83cc1c7b194ad4a6dab13183db83fbdaa88fb8af'
$path='research/no11-morning-master-20261103'
$pins=[ordered]@{
 'install_daily_cycle.py'='3117d4707f1356c82f00203988f9a45a9adba2f2'
 'daily_cycle.py'='0720dc62ce9625c8e19b43d17c500c6b2c1e4f04'
 'scope_morning_master.py'='7006f673850401d0f3a076f2bf01ba1b25040c48'
 'launcher_automatic_bridge_v4.py'='224766266bfe953bc6dfa1abda28230fae6ff69f'
 'Run-No11NightlyCycle.ps1'='9ca459c9f58238975fe4fe4d1e03664484458a6a'
 'nightly_workbook_compat.py'='2a91aafdfd41bae90ae553d7ce4e4c17dd76ecea'
}
function Blob([byte[]]$bytes) {
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length)+[char]0)
 $all=New-Object byte[] ($header.Length+$bytes.Length)
 [Array]::Copy($header,0,$all,0,$header.Length)
 [Array]::Copy($bytes,0,$all,$header.Length,$bytes.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$dir=Join-Path $env:TEMP ('ark-nightly-fix-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($dir)
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
foreach($name in $pins.Keys) {
 $url='https://raw.githubusercontent.com/'+$repo+'/'+$commit+'/'+$path+'/'+$name
 $file=Join-Path $dir $name
 Invoke-WebRequest -Uri $url -OutFile $file -UseBasicParsing -ErrorAction Stop
 $actual=Blob ([IO.File]::ReadAllBytes($file))
 Need ($actual -ceq $pins[$name]) ('PIN_MISMATCH_'+$name.Replace('.','_'))
}
$installer=Join-Path $dir 'install_daily_cycle.py'
Write-Host 'NO11_NIGHTLY_BOOTSTRAP_SOURCES=VERIFIED'
Write-Host 'NO11_NIGHTLY_BOOTSTRAP_BEGIN=TRANSACTIONAL_INSTALL'
& $python -B -X utf8 $installer --source-dir $dir
$exitCode=$LASTEXITCODE
Need ($exitCode -eq 0) 'INSTALLER_FAILED_SEE_SAFE_REASON_ABOVE'
Write-Host 'NO11_NIGHTLY_BOOTSTRAP=PASS'
Write-Host 'ONECLICK_WHITE_UI_MODIFIED=False'
Write-Host 'ORIGINAL_TRADING_STRATEGY_MODIFIED=False'
Write-Host 'NIGHTLY_SCHEDULE_REGISTERED=False'
Write-Host 'TRADE_LAUNCHED=False'
Write-Host 'EXCEL_TOUCHED=False'
Write-Host 'ORDER_TRANSMISSION=False'
