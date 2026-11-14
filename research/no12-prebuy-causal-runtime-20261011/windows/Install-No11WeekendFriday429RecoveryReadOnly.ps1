# Deploy a narrowly-scoped Sunday 2026-11-01 Friday 429 RSS-only recovery.
# No original frozen models, broker execution paths, order-ID workbook, Excel
# files, existing weekly run data, or LIVE permissions are modified.
param(
 [string]$InstallRoot='C:\ArkTerminal\no11-unified-2026-10-30',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='24661f7d0846feb0f577c7315a9d7da2a8ef7b66'
$originalHead='24b906e19a2623e45701311ca3fbb20dafe11c80'
$prefix='research/no12-prebuy-causal-runtime-20261011/'
$original=[ordered]@{
 ($prefix+'tools/no11_weekly_g1_refresh.mjs')='9f73ad6f8ea9d32be09a993d6605ff553c11c816'
 ($prefix+'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1')='992ccf11570b02dd180309cd74da31ed5e9003bf'
 ($prefix+'tests/no11_weekly_g1_refresh.test.mjs')='50d2edecb9790ff4a4904b0982024eac70786bc9'
}
$updated=[ordered]@{
 ($prefix+'tools/no11_weekly_g1_refresh.mjs')='cac5a85c1e188fcc36f6954858f2ec4a2ada5ed7'
 ($prefix+'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1')='d098a958f6364ed0aebdf1e8d4fd2a0c01a53c93'
 ($prefix+'tests/no11_weekly_g1_refresh.test.mjs')='f4f7649a6ba6eb766c13d2c8ba54c24d16f0ee09'
}
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_FRIDAY429_INSTALL_'+$code)}}
function Blob([string]$file){
 $value=@(& git hash-object --no-filters $file)
 Need ($LASTEXITCODE -eq 0 -and $value.Count -eq 1) 'HASH_COMMAND_FAILED'
 return [string]$value[0]
}
# Compare local WORKTREE text as a canonical Git blob (LF) without altering it.
# git hash-object --no-filters sees Windows CRLF bytes, which differ from the
# GitHub blob despite identical code. Preserve BOM, do not trim whitespace.
function CanonicalBlob([string]$file){
 $strict=[Text.UTF8Encoding]::new($false,$true)
 $originalBytes=[IO.File]::ReadAllBytes($file)
 $source=$strict.GetString($originalBytes)
 $normalized=$source.Replace("`r`n","`n").Replace("`r","`n")
 $body=$strict.GetBytes($normalized)
 $header=[Text.Encoding]::ASCII.GetBytes("blob $($body.Length)`0")
 $sha=[Security.Cryptography.SHA1]::Create()
 try{
  $buffer=New-Object byte[] ($header.Length+$body.Length)
  [Array]::Copy($header,0,$buffer,0,$header.Length)
  [Array]::Copy($body,0,$buffer,$header.Length,$body.Length)
  return ([BitConverter]::ToString($sha.ComputeHash($buffer))).Replace('-','').ToLowerInvariant()
 } finally { $sha.Dispose() }
}
if($OfflineSelfTest){
 Need ($revision -match '^[a-f0-9]{40}$' -and
       $originalHead -match '^[a-f0-9]{40}$' -and
       $original.Count -eq 3 -and $updated.Count -eq 3) 'PINS'
 $testFile=Join-Path $env:TEMP ('ArkFriday429-blob-'+[guid]::NewGuid().ToString('N'))
 try{
  $utf8=[Text.UTF8Encoding]::new($false)
  [IO.File]::WriteAllBytes($testFile,$utf8.GetBytes("hello`n"))
  $lf=CanonicalBlob $testFile
  Need ($lf -ceq (Blob $testFile)) 'CANONICAL_LF_MISMATCH'
  [IO.File]::WriteAllBytes($testFile,$utf8.GetBytes("hello`r`n"))
  $crlf=CanonicalBlob $testFile
  Need ($lf -ceq $crlf) 'CANONICAL_CRLF_MISMATCH'
 }finally{if(Test-Path -LiteralPath $testFile){Remove-Item -LiteralPath $testFile -Force}}
 Write-Host 'NO11_FRIDAY429_INSTALL_CANONICAL_LF_CRLF=PASS'
 Write-Host 'NO11_FRIDAY429_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$stageDir=''
$backups=@{}
$written=@()
try{
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command node -ErrorAction Stop)
 $active=@(Get-CimInstance Win32_Process | Where-Object {
   $_.Name -in @('powershell.exe','pwsh.exe') -and $_.CommandLine -match
    '(Prepare-No11WeeklyAfterCloseReadOnly|Prepare-No11NextSessionNightlyReadOnly|Run-No11RssDailyTrendCensusReadOnly|Run-No11WeeklyCandidateRefreshReadOnly)\.ps1'
 })
 Need ($active.Count -eq 0) 'SCAN_PROCESS_STILL_ACTIVE_DO_NOT_OVERWRITE'
 Need (Test-Path -LiteralPath $InstallRoot -PathType Container) 'INSTALL_ROOT_MISSING'
 $root=[IO.Path]::GetFullPath($InstallRoot)
 $head=([string](& git -C $root rev-parse HEAD)).Trim()
 Need ($LASTEXITCODE -eq 0 -and $head -ceq $originalHead) 'INSTALLED_BASE_CHANGED'
 foreach($item in $original.GetEnumerator()){
  $target=Join-Path $root $item.Key
  Need (Test-Path -LiteralPath $target -PathType Leaf) 'ORIGINAL_FILE_MISSING'
  $localHash=CanonicalBlob $target
  if($localHash -cne [string]$item.Value){
   Write-Host ('NO11_FRIDAY429_LOCAL_CONTENT_DIFF='+$item.Key)
   Write-Host ('NO11_FRIDAY429_LOCAL_NORMALIZED_BLOB='+$localHash)
   throw 'NO11_FRIDAY429_INSTALL_LOCAL_SOURCE_CHANGED_REVIEW_REQUIRED'
  }
 }
 $stageDir=Join-Path $env:TEMP ('ArkFriday429-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($stageDir)
 $downloads=@{}
 $index=0
 foreach($item in $updated.GetEnumerator()){
  $index++
  $tmp=Join-Path $stageDir ('staged-'+$index)
  $uri='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+'/'+$item.Key
  Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $tmp
  Need ((Blob $tmp) -ceq [string]$item.Value) 'DOWNLOADED_HASH_MISMATCH'
  $downloads[$item.Key]=$tmp
 }
 $backupRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher\backups'
 [void][IO.Directory]::CreateDirectory($backupRoot)
 $tag=[guid]::NewGuid().ToString('N')
 foreach($item in $updated.GetEnumerator()){
  $destination=Join-Path $root $item.Key
  $backup=Join-Path $backupRoot ('friday429-'+$tag+'-'+[IO.Path]::GetFileName($destination)+'.bak')
  [IO.File]::Copy($destination,$backup,$false)
  $backups[$destination]=$backup
 }
 foreach($item in $updated.GetEnumerator()){
  $destination=Join-Path $root $item.Key
  [IO.File]::Copy([string]$downloads[$item.Key],$destination,$true)
  $written+=@($destination)
  Need ((Blob $destination) -ceq [string]$item.Value) 'STAGED_HASH_MISMATCH'
 }
 $engine=Join-Path $root $prefix
 & node --test (Join-Path $engine 'tests/no11_weekly_g1_refresh.test.mjs')
 Need ($LASTEXITCODE -eq 0) 'WEEKEND_429_TEST_FAILED'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $engine 'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1') -OfflineSelfTest -WeekendFridayLimited
 Need ($LASTEXITCODE -eq 0) 'WEEKEND_429_WINDOWS_SELFTEST_FAILED'
 Write-Host 'NO11_FRIDAY429_INSTALL=PASS_VERIFIED_READONLY_WEEKEND_429_READY'
 Write-Host 'NO11_FRIDAY429_PREVIOUS_SAVED_FILES_TOUCHED=False'
 Write-Host 'NO11_FRIDAY429_FULL_MARKET_CLAIM=False'
 Write-Host 'NO11_FRIDAY429_BROKER_MODE_CHANGED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 foreach($destination in $written){
  if($backups.ContainsKey($destination) -and (Test-Path -LiteralPath $backups[$destination] -PathType Leaf)){
   [IO.File]::Copy([string]$backups[$destination],$destination,$true)
  }
 }
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_FRIDAY429_INSTALL_[A-Z0-9_]+$'){
  $reason='NO11_FRIDAY429_INSTALL_SOURCE_OR_RUNTIME_ERROR'
 }
 Write-Host ('NO11_FRIDAY429_INSTALL=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if($stageDir -and (Test-Path -LiteralPath $stageDir -PathType Container)){
  Remove-Item -LiteralPath $stageDir -Recurse -Force
 }
}
