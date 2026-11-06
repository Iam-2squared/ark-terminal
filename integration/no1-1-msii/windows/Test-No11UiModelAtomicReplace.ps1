# PS5.1 Windows filesystem test. Synthetic READ ONLY JSON, never broker inputs.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if($PSVersionTable.PSVersion.Major -ne 5){throw 'NO11_WINDOWS_POWERSHELL_51_REQUIRED'}
$helper=Join-Path $PSScriptRoot 'Set-No11UiReadModelAtomic.ps1'
. $helper
$root=Join-Path ([IO.Path]::GetTempPath()) ('ArkNo11_UiAtomic_'+[Guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $root -ErrorAction Stop)
$dest=Join-Path $root 'ui-read-model.json'
function New-TestModel([string]$content){
    $file=Join-Path $root ('ui-model-'+[Guid]::NewGuid().ToString('N')+'.json')
    [IO.File]::WriteAllText($file,$content,[Text.Encoding]::ASCII)
    return $file
}
function Assert-Model([string]$expected){
    if(-not [IO.File]::Exists($dest)-or [IO.File]::ReadAllText($dest)-cne $expected){
        throw 'NO11_UI_ATOMIC_MODEL_VALUE_WRONG'
    }
}
function Assert-NoBackup{
    if(@(Get-ChildItem -LiteralPath $root -File -Filter 'ui-model-backup-*.json').Count -ne 0){
        throw 'NO11_UI_ATOMIC_BACKUP_NOT_CLEANED'
    }
}
try{
    $a=New-TestModel '{"version":"initial","readOnly":true}'
    Commit-No11UiReadModelAtomic -TemporaryPath $a -DestinationPath $dest -PrivateRoot $root
    Assert-Model '{"version":"initial","readOnly":true}'
    Assert-NoBackup
    if([IO.File]::Exists($a)){throw 'NO11_UI_ATOMIC_OLD_INPUT_STILL_PRESENT'}
    Write-Host 'NO11_UI_MODEL_FIRST_COMMIT_PASS=True'

    $b=New-TestModel '{"version":"updated","readOnly":true}'
    Commit-No11UiReadModelAtomic -TemporaryPath $b -DestinationPath $dest -PrivateRoot $root
    Assert-Model '{"version":"updated","readOnly":true}'
    Assert-NoBackup
    if([IO.File]::Exists($b)){throw 'NO11_UI_ATOMIC_REPLACED_INPUT_PRESENT'}
    Write-Host 'NO11_UI_MODEL_EXISTING_REPLACE_PASS=True'

    $c=New-TestModel '{"version":"third","readOnly":true}'
    Commit-No11UiReadModelAtomic -TemporaryPath $c -DestinationPath $dest -PrivateRoot $root
    Assert-Model '{"version":"third","readOnly":true}'
    Assert-NoBackup
    Write-Host 'NO11_UI_MODEL_REPEATED_REFRESH_PASS=True'

    $foreign=Join-Path $root 'ownership-baseline.json'
    $d=New-TestModel '{"version":"untrusted"}'
    $blocked=$false
    try{Commit-No11UiReadModelAtomic -TemporaryPath $d -DestinationPath $foreign -PrivateRoot $root}
    catch{if($_.Exception.Message -ceq 'NO11_UI_MODEL_DESTINATION_NOT_APPROVED'){$blocked=$true}else{throw}}
    if(-not $blocked){throw 'NO11_UI_ATOMIC_FOREIGN_NOT_BLOCKED'}
    Assert-Model '{"version":"third","readOnly":true}'
    if([IO.File]::Exists($foreign)){throw 'NO11_UI_ATOMIC_FOREIGN_WRITTEN'}
    Write-Host 'NO11_UI_MODEL_FOREIGN_FILE_PROTECTED=True'

    $missing=Join-Path $root ('ui-model-'+[Guid]::NewGuid().ToString('N')+'.json')
    $blocked=$false
    try{Commit-No11UiReadModelAtomic -TemporaryPath $missing -DestinationPath $dest -PrivateRoot $root}
    catch{if($_.Exception.Message -ceq 'NO11_UI_MODEL_SOURCE_MISSING_OR_COLLISION'){$blocked=$true}else{throw}}
    if(-not $blocked){throw 'NO11_UI_ATOMIC_MISSING_SOURCE_NOT_BLOCKED'}
    Assert-Model '{"version":"third","readOnly":true}'
    Write-Host 'NO11_UI_MODEL_FAILURE_PRESERVES_PREVIOUS=True'
    Write-Host 'NO11_UI_MODEL_WINPS51_ATOMIC_TEST_PASS=True'
} finally{
    Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}
