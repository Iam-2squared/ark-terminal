# Patch ONLY the title-dependent Excel process filter in two original
# read-only collectors. All exact workbook/sheet COM checks remain unchanged.
# No Excel COM calls, model fitting, orders, Git commands or source reset.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest

$oldDaily=@'
  $processes=@(Get-Process EXCEL -ErrorAction Stop | Where-Object {$_.MainWindowTitle -like 'Ark_No11_*' -and $_.MainWindowHandle -ne [IntPtr]::Zero})
  if($processes.Count -ne 1){throw 'NO11_DAILY_EXCEL_IDENTITY_NOT_UNIQUE'}
'@
$newDaily=@'
  # Excel changes MainWindowTitle when the active workbook switches.
  # Prefer one uniquely Ark-labelled visible process, or fall back to the
  # single visible Excel process. Original workbook/sheet COM checks remain
  # mandatory before creating a temporary book.
  $visible=@(Get-Process EXCEL -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne [IntPtr]::Zero})
  $arkNamed=@($visible | Where-Object {$_.MainWindowTitle -like 'Ark_No11_*'})
  $processes=@()
  if($arkNamed.Count -eq 1){$processes=@($arkNamed)}
  elseif($arkNamed.Count -eq 0 -and $visible.Count -eq 1){$processes=@($visible)}
  Write-Host ('NO11_DAILY_EXCEL_DISCOVERY=VISIBLE_{0}|ARK_NAMED_{1}|SELECTED_{2}' -f $visible.Count,$arkNamed.Count,$processes.Count)
  if($processes.Count -ne 1){throw 'NO11_DAILY_EXCEL_IDENTITY_NOT_UNIQUE'}
'@
$oldBatch=@'
 $processes=@(Get-Process EXCEL -ErrorAction Stop | Where-Object {
  $_.MainWindowTitle -like 'Ark_No11_*' -and $_.MainWindowHandle -ne [IntPtr]::Zero
 })
 if($processes.Count -ne 1){throw 'NO11_BATCH_EXCEL_IDENTITY_NOT_UNIQUE'}
'@
$newBatch=@'
 # Excel changes MainWindowTitle when the active workbook switches.
 # Prefer one uniquely Ark-labelled visible process, or fall back to the
 # single visible Excel process. Original workbook/sheet COM checks remain
 # mandatory before creating a temporary book.
 $visible=@(Get-Process EXCEL -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne [IntPtr]::Zero})
 $arkNamed=@($visible | Where-Object {$_.MainWindowTitle -like 'Ark_No11_*'})
 $processes=@()
 if($arkNamed.Count -eq 1){$processes=@($arkNamed)}
 elseif($arkNamed.Count -eq 0 -and $visible.Count -eq 1){$processes=@($visible)}
 Write-Host ('NO11_BATCH_EXCEL_DISCOVERY=VISIBLE_{0}|ARK_NAMED_{1}|SELECTED_{2}' -f $visible.Count,$arkNamed.Count,$processes.Count)
 if($processes.Count -ne 1){throw 'NO11_BATCH_EXCEL_IDENTITY_NOT_UNIQUE'}
'@

function Need([bool]$condition,[string]$code) {
 if(-not $condition){throw ('NO11_EXCEL_REPAIR_'+$code)}
}
function NormalizeLf([string]$s) {
 $crlf=([string][char]13)+([string][char]10)
 $lf=[string][char]10
 return $s.Replace($crlf,$lf).TrimEnd([char[]]@([char]13,[char]10))
}
function Prepare([string]$name,[string]$old,[string]$replacement,[string]$marker) {
 $file=Join-Path $PSScriptRoot $name
 Need (Test-Path -LiteralPath $file -PathType Leaf) 'LOCAL_SOURCE_MISSING'
 $file=[IO.Path]::GetFullPath($file)
 $binary=[IO.File]::ReadAllBytes($file)
 $bom=($binary.Length -ge 3 -and $binary[0] -eq 239 -and $binary[1] -eq 187 -and $binary[2] -eq 191)
 $enc=[Text.UTF8Encoding]::new($false,$true)
 $text=[IO.File]::ReadAllText($file,$enc)
 $crlf=([string][char]13)+([string][char]10)
 $lf=[string][char]10
 $normalized=$text.Replace($crlf,$lf)
 if($normalized.Contains($marker)){
  return [pscustomobject]@{path=$file;mode='ALREADY_PATCHED';content=$text;bom=$bom}
 }
 $before=NormalizeLf $old
 $after=NormalizeLf $replacement
 Need (-not [string]::IsNullOrEmpty($before)) 'OLD_ANCHOR_EMPTY'
 $parts=$normalized.Split([string[]]@($before),[StringSplitOptions]::None)
 Need ($parts.Length -eq 2) 'LOCAL_SOURCE_ANCHOR_CHANGED'
 $candidate=$normalized.Replace($before,$after)
 Need ($candidate.Contains($marker) -and
  $candidate.Contains('Ark_No11_MSII_RSS.xlsx') -and
  $candidate.Contains('Ark_No11_MARKET_RSS.xlsx') -and
  $candidate.Contains('ARK_ACCOUNT_READONLY') -and
  $candidate.Contains('ARK_MARKET_READONLY') -and
  $candidate.Contains('$excel.Workbooks.Count -ne 2')) 'ORIGINAL_WORKBOOK_GUARDS_MISSING'
 if($text.Contains($crlf)){$candidate=$candidate.Replace($lf,$crlf)}
 $tokens=$null;$parseErrors=$null
 [void][System.Management.Automation.Language.Parser]::ParseInput($candidate,[ref]$tokens,[ref]$parseErrors)
 Need ($parseErrors.Count -eq 0) 'REVISED_POWERSHELL_SYNTAX_INVALID'
 return [pscustomobject]@{path=$file;mode='PATCH_REQUIRED';content=$candidate;bom=$bom}
}

try {
 Need ($Apply -xor $OfflineSelfTest) 'SELECT_APPLY_OR_SELFTEST'
 $plans=@(
  (Prepare 'Run-No11RssDailyTrendCensusReadOnly.ps1' $oldDaily $newDaily 'NO11_DAILY_EXCEL_DISCOVERY=VISIBLE_'),
  (Prepare 'Capture-No11RssTrainingBatchReadOnly.ps1' $oldBatch $newBatch 'NO11_BATCH_EXCEL_DISCOVERY=VISIBLE_')
 )
 Need ($plans.Count -eq 2) 'PATCH_PLAN_INCOMPLETE'
 if($OfflineSelfTest) {
  foreach($p in $plans){Write-Host ('NO11_EXCEL_REPAIR_PLAN='+[IO.Path]::GetFileName($p.path)+'|'+$p.mode)}
  Write-Host 'NO11_EXCEL_REPAIR_SELFTEST=PASS'
  Write-Host 'LOCAL_FILES_MODIFIED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 $changed=0
 foreach($p in $plans){
  if($p.mode -eq 'ALREADY_PATCHED'){
   Write-Host ('NO11_EXCEL_REPAIR_FILE='+[IO.Path]::GetFileName($p.path)+'|ALREADY_PATCHED')
   continue
  }
  $temp=Join-Path (Split-Path -Parent $p.path) ('.no11-excel-fix-'+[guid]::NewGuid().ToString('N')+'.tmp')
  $backup=$p.path+'.ark-backup-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[guid]::NewGuid().ToString('N')
  try {
   $encoding=[Text.UTF8Encoding]::new([bool]$p.bom)
   [IO.File]::WriteAllText($temp,$p.content,$encoding)
   [IO.File]::Replace($temp,$p.path,$backup)
   Write-Host ('NO11_EXCEL_REPAIR_FILE='+[IO.Path]::GetFileName($p.path)+'|PATCHED')
   Write-Host ('NO11_EXCEL_REPAIR_BACKUP='+$backup)
   $changed++
  } finally {
   if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp -Force}
  }
 }
 Write-Host ('NO11_EXCEL_REPAIR_CHANGED_FILES='+$changed)
 Write-Host 'NO11_EXCEL_REPAIR=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
} catch {
 $reason=$_.Exception.Message
 if($reason -notmatch '^NO11_EXCEL_REPAIR_[A-Z0-9_]+$'){$reason='NO11_EXCEL_REPAIR_PRIVATE_SOURCE_OR_FILE_SYSTEM_FAILURE'}
 Write-Host ('NO11_EXCEL_REPAIR=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
