# Ark Terminal 2.0 LIVE ONLY: open a read-only browser UI for an
# already operator-requested No.1.1 cash-LONG session.
# Never starts or authorizes trading, Shadow, Excel or MarketSpeed II.
param(
 [string]$ConfigFile='',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$engine=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$backend=Join-Path $engine 'tools\no11_live_ui2_readonly.py'
$page=Join-Path $engine 'ui\no11_live_operations.html'
$root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
$store=Join-Path $root 'ui2-live-only'
$python=Join-Path $root 'frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_UI2_LIVE_'+$reason)}
}
function SafeArg([string]$v){
 Need (-not [string]::IsNullOrWhiteSpace($v) -and
  -not $v.Contains('"') -and -not $v.Contains([char]10) -and
  -not $v.Contains([char]13)) 'UNSAFE_ARG'
 return '"'+$v+'"'
}
try {
 Need ((Test-Path -LiteralPath $backend -PathType Leaf) -and
       (Test-Path -LiteralPath $page -PathType Leaf)) 'SOURCE_MISSING'
 $source=Get-Content -LiteralPath $backend -Raw -Encoding UTF8
 $html=Get-Content -LiteralPath $page -Raw -Encoding UTF8
 Need ($source.Contains('ARK_NO11_BROKER_EXECUTION_REPORT_V1') -and
  $source.Contains('BROKER_OBSERVATION') -and
  $source.Contains('127.0.0.1') -and
  $html.Contains('ARK TERMINAL 2.0') -and
  $html.Contains('LIVE OPERATIONS') -and
  $html.Contains('/api/live') -and
  -not $html.Contains('SHADOW PORTFOLIO')) 'LIVE_ONLY_CONTRACT_MISSING'
 if($OfflineSelfTest){
  Write-Host 'NO11_UI2_LIVE_ONLY_WINDOWS_OFFLINE_SELFTEST=PASS'
  Write-Host 'NO11_UI2_SHADOW_DATA_INCLUDED=False'
  Write-Host 'NO11_UI2_ORDER_TRANSMISSION=False'
  exit 0
 }
 Need ([IO.Path]::IsPathRooted($ConfigFile) -and
       (Test-Path -LiteralPath $ConfigFile -PathType Leaf) -and
       (Test-Path -LiteralPath $python -PathType Leaf)) 'CONFIG_OR_PYTHON_MISSING'
 $cfg=Get-Content -LiteralPath $ConfigFile -Raw -Encoding UTF8 | ConvertFrom-Json
 $now=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9))
 $session=$now.ToString('yyyy-MM-dd')
 Need ($cfg.schemaId -ceq 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1' -and
       $cfg.sessionDate -ceq $session -and
       $cfg.orderTransmission -eq $false -and
       $cfg.productionReady -eq $false) 'SAME_DAY_CONFIG_REQUIRED'
 $private=[string]$cfg.privateRoot
 Need ([IO.Path]::IsPathRooted($private) -and
       (Test-Path -LiteralPath $private -PathType Container) -and
       [string]$cfg.brokerExecutionConfig -ne '' -and
       (Test-Path -LiteralPath $cfg.brokerExecutionConfig -PathType Leaf)) 'BROKER_CONFIG_REQUIRED'
 $broker=Get-Content -LiteralPath $cfg.brokerExecutionConfig -Raw -Encoding UTF8 | ConvertFrom-Json
 Need ($broker.schemaId -ceq 'ARK_NO11_BROKER_EXECUTION_CONFIG_V1' -and
       $broker.sessionDate -ceq $session -and
       $broker.evidenceMode -ceq 'BROKER_OBSERVATION' -and
       $broker.transport.mode -ceq 'LIVE') 'REAL_ONLY_BROKER_MODE_REQUIRED'
 [void][IO.Directory]::CreateDirectory($store)
 $id=[guid]::NewGuid().ToString('N')
 $ready=Join-Path $store ('ui-'+$session+'-'+$id+'.ready.json')
 $stdout=Join-Path $store ('ui-'+$session+'-'+$id+'.log')
 $stderr=Join-Path $store ('ui-'+$session+'-'+$id+'.err')
 $arguments=@('-B',(SafeArg $backend),'--session',(SafeArg $session),
  '--private-root',(SafeArg $private),'--document',(SafeArg $page),
  '--ready-file',(SafeArg $ready),'--token',(SafeArg $id))
 $p=Start-Process -FilePath $python -ArgumentList ($arguments -join ' ') -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
 $readyFound=$false
 for($i=0;$i -lt 100;$i++){
  if(Test-Path -LiteralPath $ready -PathType Leaf){$readyFound=$true;break}
  if($p.HasExited){break}
  Start-Sleep -Milliseconds 100
 }
 Need $readyFound 'SERVER_NOT_READY'
 $receipt=Get-Content -LiteralPath $ready -Raw -Encoding UTF8 | ConvertFrom-Json
 Need ($receipt.schemaId -ceq 'ARK_NO11_UI2_LIVE_ONLY_READY_V1' -and
       $receipt.sessionDate -ceq $session -and
       $receipt.token -ceq $id -and
       [int]$receipt.pid -eq [int]$p.Id -and
       $receipt.readOnly -eq $true -and
       $receipt.realOrderPermissionNotGrantedByUI -eq $true -and
       [string]$receipt.url -cmatch '^http://127[.]0[.]0[.]1:[0-9]{1,5}/$') 'SERVER_RECEIPT_IDENTITY'
 Need (-not $p.HasExited) 'SERVER_STOPPED'
 Start-Process -FilePath ([string]$receipt.url)
 Write-Host 'NO11_UI2_LIVE_ONLY=LOCAL_BROWSER_OPEN_REQUESTED'
 Write-Host ('NO11_UI2_LIVE_ONLY_URL='+[string]$receipt.url)
 Write-Host 'NO11_UI2_LIVE_STATUS=NOT_AN_ORDER_OR_FILL_CONFIRMATION'
 Write-Host 'NO11_UI2_SHADOW_DATA_INCLUDED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
} catch {
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_UI2_LIVE_[A-Z0-9_]+$'){$reason='NO11_UI2_LIVE_STARTUP_FAILURE'}
 Write-Host ('NO11_UI2_LIVE_ONLY=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
