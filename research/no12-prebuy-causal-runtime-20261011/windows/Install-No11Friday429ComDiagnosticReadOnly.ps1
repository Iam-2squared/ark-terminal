# Read-only deployment: safe operation-level diagnostic tags for masked Excel COM exceptions.
# Installer never accesses Excel COM, RSS, original models, broker, or captured files.
param(
 [string]$InstallRoot='C:\ArkTerminal\no11-unified-2026-10-30',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='09de495a9c411fb0ae64f8037ed5dc96856307b3'
$originalHead='24b906e19a2623e45701311ca3fbb20dafe11c80'
$prefix='research/no12-prebuy-causal-runtime-20261011/'
$relative=$prefix+'windows/Run-No11WeeklyCandidateRefreshReadOnly.ps1'
$oldHash='d19ae12c244f65c86ab2140daf5c9a0a41b2ace8'
$newHash='d305f1062a536fe35caad7f8b3ba81bfa1ffc927'
$support=@{
 ($prefix+'tools/no11_weekly_g1_refresh.mjs')='cac5a85c1e188fcc36f6954858f2ec4a2ada5ed7'
 ($prefix+'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1')='d098a958f6364ed0aebdf1e8d4fd2a0c01a53c93'
}
function Need([bool]$condition,[string]$reason){
 if(-not $condition){throw ('NO11_FRIDAY429_COM_DIAGNOSTIC_INSTALL_'+$reason)}
}
function GitBlob([string]$file){
 $output=@(& git hash-object --no-filters $file)
 Need ($LASTEXITCODE -eq 0 -and $output.Count -eq 1) 'HASH_TOOL_FAILED'
 return [string]$output[0]
}
function CanonicalBlob([string]$file){
 # Preserve BOM and content; normalize Windows CRLF to Git LF only.
 $strict=[Text.UTF8Encoding]::new($false,$true)
 $inputBytes=[IO.File]::ReadAllBytes($file)
 $normalized=$strict.GetString($inputBytes).Replace(([string][char]13+[char]10),[string][char]10)
 $body=$strict.GetBytes($normalized)
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$body.Length+[char]0))
 $hash=[Security.Cryptography.SHA1]::Create()
 try{
  $combined=New-Object byte[] ($header.Length+$body.Length)
  [Array]::Copy($header,0,$combined,0,$header.Length)
  [Array]::Copy($body,0,$combined,$header.Length,$body.Length)
  return ([BitConverter]::ToString($hash.ComputeHash($combined))).Replace('-','').ToLowerInvariant()
 }finally{$hash.Dispose()}
}
if($OfflineSelfTest){
 Need ($revision -match '^[a-f0-9]{40}$' -and $oldHash -match '^[a-f0-9]{40}$' -and
       $newHash -match '^[a-f0-9]{40}$' -and $support.Count -eq 2) 'CONTRACT'
 $sample=Join-Path $env:TEMP ('Ark-COM-hash-'+[guid]::NewGuid().ToString('N'))
 try{
  $encoding=[Text.UTF8Encoding]::new($false)
  [IO.File]::WriteAllBytes($sample,$encoding.GetBytes(('hello'+[char]10)))
  $expected=CanonicalBlob $sample
  [IO.File]::WriteAllBytes($sample,$encoding.GetBytes(('hello'+[char]13+[char]10)))
  Need ((CanonicalBlob $sample) -ceq $expected) 'CRLF_NORMALIZATION'
 }finally{if(Test-Path -LiteralPath $sample){Remove-Item -LiteralPath $sample -Force}}
 Write-Host 'NO11_FRIDAY429_COM_DIAGNOSTIC_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$stage='';$backup='';$installed=$false;$destination=''
try{
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command node -ErrorAction Stop)
 $active=@(Get-CimInstance Win32_Process | Where-Object {
   $_.Name -in @('powershell.exe','pwsh.exe') -and $_.CommandLine -match
    '(Prepare-No11WeeklyAfterCloseReadOnly|Prepare-No11NextSessionNightlyReadOnly|Run-No11RssDailyTrendCensusReadOnly|Run-No11WeeklyCandidateRefreshReadOnly)\.ps1'
 })
 Need ($active.Count -eq 0) 'ACTIVE_COLLECTOR_DO_NOT_PATCH'
 Need (Test-Path -LiteralPath $InstallRoot -PathType Container) 'INSTALL_ROOT_MISSING'
 $root=[IO.Path]::GetFullPath($InstallRoot)
 $head=([string](& git -C $root rev-parse HEAD)).Trim()
 Need ($LASTEXITCODE -eq 0 -and $head -ceq $originalHead) 'PINNED_HEAD_MISMATCH'
 foreach($entry in $support.GetEnumerator()){
  $file=Join-Path $root $entry.Key
  Need (Test-Path -LiteralPath $file -PathType Leaf) 'FRIDAY429_SUPPORT_MISSING'
  Need ((CanonicalBlob $file) -ceq [string]$entry.Value) 'FRIDAY429_SUPPORT_CHANGED'
 }
 $destination=Join-Path $root $relative
 Need (Test-Path -LiteralPath $destination -PathType Leaf) 'READER_MISSING'
 $current=CanonicalBlob $destination
 Need ($current -ceq $oldHash -or $current -ceq $newHash) 'READER_CHANGED_REVIEW_REQUIRED'
 if($current -ceq $newHash){
  Write-Host 'NO11_FRIDAY429_COM_DIAGNOSTIC_INSTALL=ALREADY_UPDATED_NO_OVERWRITE'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 $stage=Join-Path $env:TEMP ('Ark-Friday429-COM-DIAG-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($stage)
 $download=Join-Path $stage 'collector.ps1'
 $uri='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+'/'+$relative
 Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $download
 Need ((GitBlob $download) -ceq $newHash) 'REMOTE_SOURCE_HASH_MISMATCH'
 # Verify the synthetic COM-fault tests before changing installed files.
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $download -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'DOWNLOADED_SCRIPT_OFFLINE_SELFTEST_FAILED'
 $backupRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher\backups'
 [void][IO.Directory]::CreateDirectory($backupRoot)
 $backup=Join-Path $backupRoot ('Friday429-COM-DIAG-'+[guid]::NewGuid().ToString('N')+'.ps1.bak')
 [IO.File]::Copy($destination,$backup,$false)
 [IO.File]::Copy($download,$destination,$true)
 $installed=$true
 Need ((CanonicalBlob $destination) -ceq $newHash) 'INSTALLED_CONTENT_MISMATCH'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $destination -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'INSTALLED_SCRIPT_OFFLINE_SELFTEST_FAILED'
 $test=Join-Path $root ($prefix+'tests/no11_weekly_g1_refresh.test.mjs')
 & node --test $test
 Need ($LASTEXITCODE -eq 0) 'EXISTING_WEEKLY_TEST_FAILED'
 Write-Host 'NO11_FRIDAY429_COM_DIAGNOSTIC_INSTALL=PASS_SAFE_COM_OPERATION_DIAGNOSTICS'
 Write-Host 'NO11_FRIDAY429_SAVED_30_OF_429_UNTOUCHED=True'
 Write-Host 'NO11_FRIDAY_FULL_4328_UNTOUCHED=True'
 Write-Host 'NO11_FRIDAY429_READER_ONLY_UPDATED=True'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 if($installed -and $backup -and (Test-Path -LiteralPath $backup -PathType Leaf)){
  try{[IO.File]::Copy($backup,$destination,$true)}catch{}
 }
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_FRIDAY429_COM_DIAGNOSTIC_INSTALL_[A-Z0-9_]+$'){
  $reason='NO11_FRIDAY429_COM_DIAGNOSTIC_INSTALL_SOURCE_OR_RUNTIME_ERROR'
 }
 Write-Host ('NO11_FRIDAY429_COM_DIAGNOSTIC_INSTALL=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if($stage -and (Test-Path -LiteralPath $stage -PathType Container)){
  Remove-Item -LiteralPath $stage -Recurse -Force
 }
}
