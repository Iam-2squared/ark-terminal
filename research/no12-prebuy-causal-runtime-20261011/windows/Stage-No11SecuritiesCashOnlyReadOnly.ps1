# Update only three exact-pinned files in the user's PRIVATE No12 overlay.
# Never change Frozen originals, Excel, the standard read-only launcher,
# RSS order permissions, capital ledger databases, or an active process.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$ref='667d2a8fe6110fce2f994e4e7c4894353bdffc02'
$items=@(
 @{Name='no11_broker_execution_service.py';Sub='tools';Old='370b27c98a7ee776dfa8fb9b4c7f99a4c05cd090';New='defd247735eec987b53fcf9852668be760b27a40'},
 @{Name='no11_securities_cash_only.py';Sub='tools';Old='';New='fe1b1d401f7545512afe43641abceca5b4bd5ab0'},
 @{Name='New-No11SecuritiesCashEvidenceReadOnly.ps1';Sub='windows';Old='';New='16ca163370b016b2b6eb3c0e3e40cccb37ddf99e'}
)
function Need([bool]$yes,[string]$reason){if(-not $yes){throw ('NO11_SECURITIES_CASH_STAGE_'+$reason)}}
function Blob([string]$path){
 $lines=@(& git hash-object --no-filters $path)
 Need ($LASTEXITCODE -eq 0 -and $lines.Count -eq 1 -and $lines[0] -cmatch '^[a-f0-9]{40}$') 'GIT_BLOB_UNAVAILABLE'
 return [string]$lines[0]
}
function Safe([string]$path){
 $p=[IO.Path]::GetFullPath($path);$cur=$p
 while(-not [string]::IsNullOrEmpty($cur)){
  if(Test-Path -LiteralPath $cur){
   Need (((Get-Item -LiteralPath $cur -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  }
  $parent=Split-Path -Parent $cur;if($parent -ceq $cur){break};$cur=$parent
 }
 return $p
}
if($OfflineSelfTest){
 Need ($items.Count -eq 3 -and $ref -cmatch '^[a-f0-9]{40}$') 'STATIC'
 foreach($t in $items){
  Need ($t.New -cmatch '^[a-f0-9]{40}$' -and
   ($t.Old -ceq '' -or $t.Old -cmatch '^[a-f0-9]{40}$')) 'STATIC_HASH'
 }
 Write-Host 'NO11_SECURITIES_CASH_STAGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command powershell.exe -ErrorAction Stop)
 $engine=Safe (Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\physical-account-overlay\source\research\no12-prebuy-causal-runtime-20261011')
 Need (Test-Path -LiteralPath $engine -PathType Container) 'PRIVATE_OVERLAY_MISSING'
 $runner=Safe (Join-Path $engine 'windows\Run-No11PhysicalAccountOneShotReadOnly.ps1')
 Need (Test-Path -LiteralPath $runner -PathType Leaf) 'ORIGINAL_RUNNER_MISSING'
 Need ((Blob $runner) -ceq '89ea56ab1ee7c25fad8cebb36a5043e3a853ded3') 'ORIGINAL_RUNNER_CHANGED'
 $processes=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
  Where-Object {$_.ProcessId -ne $PID -and
   [string]$_.CommandLine -match '(?i)(no11_broker_execution_service|no11_received_session_controller|Run-No11ReceivedSessionReadOnly|Run-No11PhysicalAccountOneShotReadOnly|Observe-No11AccountReadOnly)'} )
 Need ($processes.Count -eq 0) 'ARK_ACCOUNT_OR_EXECUTION_WORKER_RUNNING'
 $base=Safe (Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\securities-cash-upgrade\'+[guid]::NewGuid().ToString('N')))
 $staged=Join-Path $base 'staged';$backups=Join-Path $base 'backups'
 [void][IO.Directory]::CreateDirectory($staged);[void][IO.Directory]::CreateDirectory($backups)
 $prepared=@()
 foreach($t in $items){
  $relative=([string]$t.Sub)+'\'+([string]$t.Name)
  $dest=Safe (Join-Path $engine $relative)
  Need (Test-Path -LiteralPath (Split-Path -Parent $dest) -PathType Container) 'TARGET_DIRECTORY_MISSING'
  $exists=Test-Path -LiteralPath $dest -PathType Leaf
  $old=''
  if($exists){$old=Blob $dest}
  Write-Host ('NO11_SECURITIES_CASH_STAGE_EXISTING_'+$t.Name+'='+$(if($exists){$old}else{'MISSING'}))
  Need (($exists -and ($old -ceq $t.Old -or $old -ceq $t.New)) -or
    ((-not $exists) -and $t.Old -ceq '')) 'LOCAL_SOURCE_CHANGED_NO_OVERWRITE'
  if($old -ceq $t.New){continue}
  $target=Safe (Join-Path $staged ([string]$t.Name))
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$ref+
    '/research/no12-prebuy-causal-runtime-20261011/'+$t.Sub+'/'+$t.Name
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $target
  Need ((Blob $target) -ceq $t.New) 'REMOTE_BLOB_MISMATCH'
  if($t.Name -like '*.ps1'){
   $tokens=$null;$errors=$null
   [void][Management.Automation.Language.Parser]::ParseFile($target,[ref]$tokens,[ref]$errors)
   Need ($errors.Count -eq 0) 'POWERSHELL_PARSE_FAILED'
  }else{
   $python=Get-Command py -ErrorAction SilentlyContinue
   if($null -ne $python){
    & py -3.12 -B -c 'import ast,sys;ast.parse(open(sys.argv[1],encoding="utf-8-sig").read())' $target
    Need ($LASTEXITCODE -eq 0) 'PYTHON_PARSE_FAILED'
   }
  }
  $prepared+=@([pscustomobject]@{
   name=$t.Name;from=$dest;new=$target;hash=$t.New;previous=$old;
   backup=(Join-Path $backups ($t.Name+'.backup'))
  })
 }
 foreach($t in $prepared){if($t.previous -cne ''){[IO.File]::Copy($t.from,$t.backup,$false)}}
 $written=@()
 try{
  foreach($t in $prepared){
   $written+=@($t)
   [IO.File]::Copy($t.new,$t.from,($t.previous -cne ''))
   Need ((Blob $t.from) -ceq $t.hash) 'INSTALLED_HASH_CHANGED'
  }
  foreach($t in $items){
   $file=Join-Path (Join-Path $engine $t.Sub) $t.Name
   Need ((Blob $file) -ceq $t.New) 'FINAL_FILE_HASH'
  }
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $engine 'windows\New-No11SecuritiesCashEvidenceReadOnly.ps1') -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'CASH_PROOF_HELPER_SELFTEST_FAILED'
 }catch{
  for($i=$written.Count-1;$i -ge 0;$i--){
   $t=$written[$i]
   if($t.previous -ceq ''){if(Test-Path -LiteralPath $t.from){[IO.File]::Delete($t.from)}}
   else{[IO.File]::Copy($t.backup,$t.from,$true)}
  }
  throw
 }
 Write-Host 'NO11_SECURITIES_CASH_STAGE=PASS'
 Write-Host ('NO11_SECURITIES_CASH_STAGE_BACKUP='+$backups)
 Write-Host 'NO11_SECURITIES_CASH_STAGE_FULL_LIVE_AUTHORIZED=False'
 Write-Host 'NO11_SECURITIES_CASH_STAGE_ORIGINAL_ARK_TOUCHED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_SECURITIES_CASH_STAGE_[A-Z0-9_]+$'){$reason='NO11_SECURITIES_CASH_STAGE_LOCAL_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_SECURITIES_CASH_STAGE=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
