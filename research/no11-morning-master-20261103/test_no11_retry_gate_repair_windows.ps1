# End-to-end isolated Windows test for today's stale seed-date repair.
# Uses a synthetic LOCALAPPDATA and fake WHITE OneClick, never Excel or Trade.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_RETRY_GATE_SYNTHETIC_'+$reason)}
}
$oldEnv=$env:LOCALAPPDATA
$sandbox=Join-Path $env:TEMP ('no11-retry-gate-ci-'+[guid]::NewGuid().ToString('N'))
$env:LOCALAPPDATA=Join-Path $sandbox 'localappdata'
try{
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $ui=Join-Path $store 'oneclick'
 [void][IO.Directory]::CreateDirectory($ui)
 $white=Join-Path $ui 'Start-No11OneClick.ps1'
 [IO.File]::WriteAllText($white,'# APPROVED WHITE ONECLICK THEME',([Text.UTF8Encoding]::new($false)))
 $orig=(Get-FileHash -LiteralPath $white -Algorithm SHA256).Hash
 $old='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/c592a318ca913fe82f835253dbfc9f1c89ab6f75/research/no11-morning-master-20261103/Recover-No11FilteredMorning.ps1'
 $helper=Join-Path $ui 'Recover-No11FilteredMorning.ps1'
 Invoke-WebRequest -UseBasicParsing -Uri $old -OutFile $helper
 $oldHash=(& git hash-object --no-filters -- $helper).Trim()
 Need ($oldHash -ceq 'd844d7a45cb9bbcd247258ca16dc7797cbd4a6b4') 'ORIGINAL_HELPER_PIN'
 $installer=Join-Path $PSScriptRoot 'Repair-No11MorningRetrySeedDate.ps1'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $installer -Apply
 Need ($LASTEXITCODE -eq 0) 'ACTUAL_INSTALLER_FAILED'
 $newHash=(& git hash-object --no-filters -- $helper).Trim()
 Need ($newHash -ceq 'a05315c6840fce75c70f96e36d1c7d6a073cc6e6') 'NEW_HELPER_PIN'
 Need ((Get-FileHash -LiteralPath $white -Algorithm SHA256).Hash -ceq $orig) 'WHITE_ONECLICK_CHANGED'
 $backups=@(Get-ChildItem -LiteralPath $store -Directory -Filter 'morning-retry-gate-backup-*')
 Need ($backups.Count -eq 1) 'BACKUP_MISSING'
 $prior=Join-Path $backups[0].FullName 'Recover-No11FilteredMorning.before.ps1'
 Need ((& git hash-object --no-filters -- $prior).Trim() -ceq $oldHash) 'BACKUP_NOT_EXACT'
 $newText=[IO.File]::ReadAllText($helper)
 Need ($newText.Contains('TODAY_HANDOFF_CHANGED_SINCE_0830_APPROVAL') -and
       -not $newText.Contains('$binding.sessionDate -ceq $day')) 'CURRENT_DAY_PROOF_NOT_PRESENT'
 Write-Host 'NO11_RETRY_GATE_MOCK_INSTALL=PASS'
 Write-Host 'WHITE_ONECLICK_MODIFIED=False'
 Write-Host 'BROKER_ORDER_TRANSMISSION=False'
}finally{
 $env:LOCALAPPDATA=$oldEnv
 if(Test-Path -LiteralPath $sandbox -PathType Container){
  Remove-Item -LiteralPath $sandbox -Recurse -Force -ErrorAction SilentlyContinue
 }
}
