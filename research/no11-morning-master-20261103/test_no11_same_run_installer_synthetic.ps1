# Windows CI: actually APPLY the same-run recovery installer to a private,
# synthetic *white customized* OneClick. Never touches user Excel or broker.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_INSTALL_ACCEPTANCE_'+$reason)}
}
$original=$env:LOCALAPPDATA
$sandbox=Join-Path $env:TEMP ('ark-recovery-ci-'+[guid]::NewGuid().ToString('N'))
$env:LOCALAPPDATA=Join-Path $sandbox 'fake-appdata'
try{
 [void][IO.Directory]::CreateDirectory($env:LOCALAPPDATA)
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $oneclick=Join-Path $store 'oneclick'
 $engine=Join-Path $sandbox 'fake-installed-engine'
 $tools=Join-Path $engine 'tools'
 [void][IO.Directory]::CreateDirectory($oneclick)
 [void][IO.Directory]::CreateDirectory($tools)
 $python=(Get-Command python -ErrorAction Stop).Source
 Need ([IO.Path]::IsPathRooted($python) -and
       (Test-Path -LiteralPath $python -PathType Leaf)) 'PYTHON_REQUIRED'
 $base='fb41945877229393b944ac3ce171c9571eaf4134'
 $source='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$base
 $paths=[ordered]@{
   'ui'='research/no11-morning-master-20261103/Start-No11OneClick.ps1'
   'recovery'='research/no12-prebuy-causal-runtime-20261011/tools/no11_received_run_recovery.py'
   'controller'='research/no12-prebuy-causal-runtime-20261011/tools/no11_received_session_controller.py'
 }
 $data=@{}
 foreach($key in $paths.Keys){
  $dest=Join-Path $sandbox ('base-'+$key+'.txt')
  Invoke-WebRequest -UseBasicParsing -Uri ($source+'/'+$paths[$key]) -OutFile $dest
  $data[$key]=[IO.File]::ReadAllText($dest)
 }
 # Distinct from GitHub graphite source: original local WHITE theme is
 # deliberately customized. The installer must preserve this sentinel.
 $white=$data['ui'].Replace('FromArgb(29,32,38)','FromArgb(248,249,250)')
 $white=$white.Replace('$form.ForeColor=',('# APPROVED_LOCAL_WHITE_THEME_DO_NOT_OVERWRITE' + [char]10 + '$form.ForeColor='))
 Need ($white -cne $data['ui'] -and
       $white.Contains('APPROVED_LOCAL_WHITE_THEME_DO_NOT_OVERWRITE')) 'WHITE_FIXTURE_INVALID'
 $encoding=New-Object System.Text.UTF8Encoding($true)
 $uiPath=Join-Path $oneclick 'Start-No11OneClick.ps1'
 [IO.File]::WriteAllText($uiPath,$white,$encoding)
 [IO.File]::WriteAllText((Join-Path $tools 'no11_received_run_recovery.py'),$data['recovery'])
 [IO.File]::WriteAllText((Join-Path $tools 'no11_received_session_controller.py'),$data['controller'])
 $binding=[ordered]@{
  schemaId='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
  engine=$engine
  python=$python
  orderTransmission=$false
 }
 [IO.File]::WriteAllText((Join-Path $store 'automatic-inputs.json'),
                         (ConvertTo-Json -InputObject $binding -Compress -Depth 5))
 $installer=Join-Path $PSScriptRoot 'Apply-No11SameRunRecovery.ps1'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $installer -Apply
 Need ($LASTEXITCODE -eq 0) 'REAL_INSTALLER_FAILED'
 $after=[IO.File]::ReadAllText($uiPath)
 Need ($after.Contains('APPROVED_LOCAL_WHITE_THEME_DO_NOT_OVERWRITE') -and
       $after.Contains('FromArgb(248,249,250)') -and
       $after.Contains('ARK_NO11_ONECLICK_SAME_RUN_RESUME_BUTTON_V1') -and
       $after.Contains('ARK_NO11_ONECLICK_PREOPEN_STANDBY_0830_V1') -and
       $after.Contains('ARK_NO11_ONECLICK_TRADE_UI2_AUTOOPEN_WATCH_V1') -and
       -not $after.Contains('# ARK_NO11_ONECLICK_GRAPHITE_INSTALL_APPLIED')) 'WHITE_OR_PREOPEN_OR_UI2_CHANGED'
 $controller=[IO.File]::ReadAllText((Join-Path $tools 'no11_received_session_controller.py'))
 $recovery=[IO.File]::ReadAllText((Join-Path $tools 'no11_received_run_recovery.py'))
 Need ($controller.Contains('marked_cleanup_proven(') -and
       $recovery.Contains('POSTMORTEM_CLOSURE_REPORT_CHANGED') -and
       $recovery.Contains('collector-postmortem-cleanup.json')) 'ENGINE_PATCH_MISSING'
 foreach($name in @('Resume-No11SameSession.ps1',
                     'Close-No11OwnedC50Temporary.ps1',
                     'no11_same_session_rearm.py',
                     'no11_manual_reconnect_review.py',
                     'no11_finalize_owned_collector_cleanup.py')){
  Need (Test-Path -LiteralPath (Join-Path $oneclick $name) -PathType Leaf) 'HELPER_MISSING'
 }
 $backup=@(Get-ChildItem -LiteralPath $store -Directory -Filter 'same-run-recovery-backup-*')
 Need ($backup.Count -eq 1) 'BACKUP_COUNT'
 $saved=[IO.File]::ReadAllText((Join-Path $backup[0].FullName 'WhiteOneClick.before.ps1'))
 Need ($saved -ceq $white) 'WHITE_SOURCE_BACKUP_CHANGED'
 $savedEngine=[IO.File]::ReadAllText((Join-Path $backup[0].FullName 'no11_received_run_recovery.before.py'))
 Need ($savedEngine -ceq $data['recovery']) 'ENGINE_BACKUP_CHANGED'
 Write-Host 'NO11_SAME_RUN_SYNTHETIC_WINDOWS_APPLY=PASS'
 Write-Host 'WHITE_LOCAL_THEME_PRESERVED=True'
 Write-Host 'PREOPEN_0830_PRESERVED=True'
 Write-Host 'UI2_AUTOOPEN_PRESERVED=True'
 Write-Host 'ORIGINAL_BROKER_ORDERS_ACCESSED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}finally{
 $env:LOCALAPPDATA=$original
 if(Test-Path -LiteralPath $sandbox -PathType Container){
  Remove-Item -LiteralPath $sandbox -Recurse -Force -ErrorAction SilentlyContinue
 }
}
