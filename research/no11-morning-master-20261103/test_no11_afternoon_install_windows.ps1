# True Windows 5.1 installer test against isolated fake LOCALAPPDATA.
# No Excel, broker orders, trading, or real user files are accessed.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){
 if(-not $ok){throw ('NO11_AFTERNOON_INSTALL_TEST_'+$why)}
}
$prior=$env:LOCALAPPDATA
$test=Join-Path $env:TEMP ('ark-afternoon-test-'+[guid]::NewGuid().ToString('N'))
$env:LOCALAPPDATA=Join-Path $test 'isolated-localappdata'
try{
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $oneclick=Join-Path $store 'oneclick'
 [void][IO.Directory]::CreateDirectory($oneclick)
 $white=Join-Path $oneclick 'Start-No11OneClick.ps1'
 [IO.File]::WriteAllText($white,'# ARK USER APPROVED WHITE THEME NOT REPLACED',
                         [Text.UTF8Encoding]::new($false))
 $before=(Get-FileHash -LiteralPath $white -Algorithm SHA256).Hash
 $helper=Join-Path $oneclick 'Recover-No11FilteredMorning.ps1'
 $oldUrl='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/c592a318ca913fe82f835253dbfc9f1c89ab6f75/research/no11-morning-master-20261103/Recover-No11FilteredMorning.ps1'
 Invoke-WebRequest -UseBasicParsing -Uri $oldUrl -OutFile $helper
 Need ((& git hash-object --no-filters -- $helper).Trim() -ceq
       'd844d7a45cb9bbcd247258ca16dc7797cbd4a6b4') 'ORIGINAL_HELPER_PIN'
 $installer=Join-Path $PSScriptRoot 'Install-No11AfternoonFilteredRecovery.ps1'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $installer -Apply
 Need ($LASTEXITCODE -eq 0) 'INSTALLER_APPLY_FAILED'
 $newSha=(& git hash-object --no-filters -- $helper).Trim()
 Need ($newSha -ceq 'a05315c6840fce75c70f96e36d1c7d6a073cc6e6') 'NEW_SEED_GATE_HELPER_PIN'
 $worker=Join-Path $oneclick 'Start-No11AfternoonFilteredRecovery.ps1'
 Need ((Test-Path -LiteralPath $worker -PathType Leaf) -and
       (& git hash-object --no-filters -- $worker).Trim() -ceq
       '537fa896d6931852c7cfbd8be497099e8bdf9432') 'WORKER_PIN'
 Need ((Get-FileHash -LiteralPath $white -Algorithm SHA256).Hash -ceq $before) 'WHITE_THEME_CHANGED'
 $base=@(Get-ChildItem -LiteralPath $store -Directory -Filter 'afternoon-installer-backup-*')
 Need ($base.Count -eq 1) 'AFTERNOON_BACKUP_MISSING'
 $gate=@(Get-ChildItem -LiteralPath $store -Directory -Filter 'morning-retry-gate-backup-*')
 Need ($gate.Count -eq 1) 'SEED_GATE_BACKUP_MISSING'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $installer -Apply
 Need ($LASTEXITCODE -eq 0) 'SECOND_NO_CHANGE_INSTALL_FAILED'
 Need ((Get-FileHash -LiteralPath $white -Algorithm SHA256).Hash -ceq $before) 'WHITE_SECOND_INSTALL_CHANGED'
 Write-Host 'NO11_AFTERNOON_SYNTHETIC_WINDOWS_APPLY=PASS'
 Write-Host 'WHITE_THEME_MODIFIED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}finally{
 $env:LOCALAPPDATA=$prior
 if(Test-Path -LiteralPath $test -PathType Container){
  Remove-Item -LiteralPath $test -Recurse -Force -ErrorAction SilentlyContinue
 }
}
