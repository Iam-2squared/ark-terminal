# Ark No.1.1: optional ONE-TIME private original model installation. NOT a trading permission.
# Windows PowerShell 5.1. Read verified user-provided private ZIP only.
# No model fit, broker orders, Excel modification, Safety reset or automatic UI launch.
param(
 [string]$ArchivePath=(Join-Path $HOME 'Downloads\Ark_No11_Frozen_H2_H3_H5_Models_VERIFIED_PRIVATE.zip')
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$archiveSha='990A0AADDDDDA36DEC4C2E7D77BEC291C306E57265B2D1879AC1447B1A0BDC80'
$local=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No11'
$target=Join-Path $local 'private-native-models'
$auditor=Join-Path (Split-Path -Parent $PSScriptRoot) 'tools\no11_native_model_audit.mjs'
$stage=$null
try{
 if(-not (Test-Path -LiteralPath $auditor -PathType Leaf)){throw 'NATIVE_MODEL_AUDITOR_MISSING'}
 if(-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)){throw 'NATIVE_PRIVATE_ZIP_MISSING'}
 $archiveItem=Get-Item -LiteralPath $ArchivePath
 if(($archiveItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'NATIVE_PRIVATE_ZIP_UNSAFE'}
 if((Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash -cne $archiveSha){
  throw 'NATIVE_PRIVATE_ZIP_SHA256_MISMATCH'
 }
 [void](New-Item -ItemType Directory -Force -Path $local)
 $localItem=Get-Item -LiteralPath $local
 if(($localItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'NATIVE_PRIVATE_DIRECTORY_UNSAFE'}
 $node=(Get-Command node -CommandType Application -ErrorAction Stop).Source
 if(Test-Path -LiteralPath $target){
  & $node $auditor '--model-root' $target
  if($LASTEXITCODE -ne 0){throw 'NATIVE_EXISTING_MODEL_SOURCE_INVALID'}
  Write-Host 'NO11_PRIVATE_NATIVE_MODELS=VERIFIED_ALREADY_INSTALLED'
 }else{
  $stage=Join-Path $local ('private-native-staging-'+[Guid]::NewGuid().ToString('N'))
  [void](New-Item -ItemType Directory -Path $stage -ErrorAction Stop)
  Expand-Archive -LiteralPath $ArchivePath -DestinationPath $stage -ErrorAction Stop
  & $node $auditor '--model-root' $stage
  if($LASTEXITCODE -ne 0){throw 'NATIVE_STAGED_MODEL_SOURCE_INVALID'}
  if(Test-Path -LiteralPath $target){throw 'NATIVE_FINAL_DIRECTORY_COLLISION'}
  Move-Item -LiteralPath $stage -Destination $target -ErrorAction Stop
  $stage=$null
  & $node $auditor '--model-root' $target
  if($LASTEXITCODE -ne 0){throw 'NATIVE_INSTALLED_MODEL_SOURCE_INVALID'}
  Write-Host 'NO11_PRIVATE_NATIVE_MODELS=ORIGINAL_24_VERIFIED'
 }
 Write-Host 'NO11_NATIVE_INFERENCE_STARTED=False'
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $message=[string]$_.Exception.Message
 if($message -cnotmatch '^[A-Z][A-Z0-9_]*$'){$message='REDACTED_INSTALL_ERROR'}
 Write-Host ("NO11_NATIVE_PRIVATE_INSTALL_BLOCKED={0}" -f $message)
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 throw 'NO11_NATIVE_PRIVATE_INSTALL_NOT_VERIFIED'
}finally{
 if($null -ne $stage -and (Test-Path -LiteralPath $stage -PathType Container)){
  Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
 }
}
