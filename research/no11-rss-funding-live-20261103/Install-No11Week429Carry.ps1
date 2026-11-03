# No.1.1 one-week 429 continuation installer; only source preparation, orders OFF.
# Fetches exact Git blobs, preflights parser, backs up, validates and stages
# genuine Nov 2 D100 plan for Nov 4. Does NOT start Excel, broker, or trading.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$engine='C:\ArkTerminal\no11-unified-2026-10-30\research\no12-prebuy-causal-runtime-20261011'
$private=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
$seed=Join-Path $private 'daily-trend-capture\daily-2026-10-26-e84a2ec53b0fdf41'
$friday=Join-Path $private 'weekly-pool-refresh\weekly-refresh-2026-10-30-862f03a3cdfa7d8f'
$refresh=Join-Path $private 'weekly-pool-refresh'
$commit='844ad2b5c550a1f71abe306be7d0c1ebdc9f3dcd'
$source="https://raw.githubusercontent.com/Iam-2squared/ark-terminal/$commit/research/no12-prebuy-causal-runtime-20261011"
$files=[ordered]@{
 'tools/no11_weekly_g1_refresh.mjs'=@{before='cac5a85c1e188fcc36f6954858f2ec4a2ada5ed7';after='19f04b5efa5e12db18cdc95c3c6d62e872d08f32'}
 'tools/no11_verified_weekly_shadow_scope.mjs'=@{before='86125c094532c959e28abb1624adbec6d23cb94f';after='b777b944379c7c6dda15eac10ddda5959ab181c8'}
 'windows/Run-No11WeeklyCandidateRefreshReadOnly.ps1'=@{before='57f22c23ce9f32202d2c16a26b86585120c2141c';after='8f92069b9abf57bac654018be8b7b08820b10394'}
 'tools/test_no11_week429_carry.mjs'=@{before='';after='1ec937ea243b9cdca5de9cc6f62597682ae4af22'}
}
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_WEEK429_SETUP_'+$reason)}
}
function BlobSha([string]$path,[switch]$Canonical){
 [byte[]]$bytes=[IO.File]::ReadAllBytes($path)
 if($Canonical){
  $decoded=[Text.UTF8Encoding]::new($false).GetString($bytes)
  $decoded=$decoded.TrimStart([char]0xfeff).Replace("`r`n","`n")
  $bytes=[Text.UTF8Encoding]::new($false).GetBytes($decoded)
 }
 $header=[Text.Encoding]::ASCII.GetBytes("blob $($bytes.Length)`0")
 $h=[Security.Cryptography.SHA1]::Create()
 $m=[IO.MemoryStream]::new()
 try{
  $m.Write($header,0,$header.Length)
  $m.Write($bytes,0,$bytes.Length)
  $m.Position=0
  return [BitConverter]::ToString($h.ComputeHash($m)).Replace('-','').ToLowerInvariant()
 }finally{$m.Dispose();$h.Dispose()}
}
if($OfflineSelfTest){
 Need ($files.Count -eq 4 -and $commit.Length -eq 40) 'STATIC'
 Write-Host 'WEEK429_INSTALLER_SELFTEST=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$stage=$null;$backup=$null;$mode=$null
try{
 Need (Test-Path -LiteralPath $engine -PathType Container) 'ENGINE_MISSING'
 Need (Test-Path -LiteralPath $seed -PathType Container) 'ORIGINAL_4328_SEED_MISSING'
 Need (Test-Path -LiteralPath $friday -PathType Container) 'FRIDAY_429_SOURCE_MISSING'
 Need (Test-Path -LiteralPath $private -PathType Container) 'PRIVATE_ROOT_MISSING'
 [void](Get-Command node -ErrorAction Stop)
 $active=@(Get-CimInstance Win32_Process -ErrorAction Stop|Where-Object{
  $_.ProcessId -ne $PID -and $_.Name -match '^(pythonw?|powershell|pwsh|node)(\.exe)?$' -and
  [string]$_.CommandLine -match '(?i)(Start-No11UnifiedLauncher|Run-No11ReceivedSession|no11_received_session_controller|no11_received_pipeline_service)'
 })
 Need ($active.Count -eq 0) 'CLOSE_ARK_LAUNCHER_FIRST'
 $status=@()
 foreach($rel in $files.Keys){
  $target=Join-Path $engine ($rel.Replace('/','\'))
  $meta=$files[$rel]
  if(-not (Test-Path -LiteralPath $target -PathType Leaf)){
   Need ($meta.before -eq '') ('MISSING_EXISTING_SOURCE_'+($rel.Replace('/','_')))
   $status+='OLD'
  }else{
   $actual=BlobSha $target -Canonical
   if($actual -ceq $meta.before){$status+='OLD'}
   elseif($actual -ceq $meta.after){$status+='NEW'}
   else{throw ('NO11_WEEK429_SETUP_LOCAL_SOURCE_MODIFIED_'+($rel.Replace('/','_')))}
  }
 }
 Need (@($status|Select-Object -Unique).Count -eq 1) 'PARTIAL_INSTALL_DETECTED'
 $mode=$status[0]
 $stage=Join-Path $private ('week429-stage-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($stage)
 foreach($rel in $files.Keys){
  $destination=Join-Path $stage ($rel.Replace('/','\'))
  [void][IO.Directory]::CreateDirectory((Split-Path -Parent $destination))
  Invoke-WebRequest -Uri ($source+'/'+$rel) -OutFile $destination -UseBasicParsing -ErrorAction Stop
  Need ((BlobSha $destination) -ceq $files[$rel].after) 'REMOTE_BLOB_MISMATCH'
  if($rel.EndsWith('.mjs')){
   & node --check $destination
   Need ($LASTEXITCODE -eq 0) 'NODE_PARSER'
  }else{
   $tokens=$null;$errors=$null
   [void][Management.Automation.Language.Parser]::ParseFile($destination,[ref]$tokens,[ref]$errors)
   Need ($errors.Count -eq 0) 'POWERSHELL_PARSER'
  }
 }
 Write-Host 'WEEK429_SOURCE_HASH_AND_SYNTAX=PASS'
 if($mode -ceq 'OLD'){
  $backup=Join-Path $private ('week429-backup-'+[guid]::NewGuid().ToString('N'))
  [void][IO.Directory]::CreateDirectory($backup)
  foreach($rel in $files.Keys){
   if($files[$rel].before -eq ''){continue}
   $original=Join-Path $engine ($rel.Replace('/','\'))
   $saved=Join-Path $backup ($rel.Replace('/','\'))
   [void][IO.Directory]::CreateDirectory((Split-Path -Parent $saved))
   [IO.File]::Copy($original,$saved,$false)
   Need ((BlobSha $saved -Canonical) -ceq $files[$rel].before) 'BACKUP_MISMATCH'
  }
  foreach($rel in $files.Keys){
   $target=Join-Path $engine ($rel.Replace('/','\'))
   if($files[$rel].before -ne ''){
    Need ((BlobSha $target -Canonical) -ceq $files[$rel].before) 'SOURCE_CHANGED'
   }else{Need (-not (Test-Path -LiteralPath $target)) 'NEW_FILE_CONFLICT'}
   [IO.File]::Copy((Join-Path $stage ($rel.Replace('/','\'))),$target,$false)
  }
 }
 foreach($rel in $files.Keys){
  Need ((BlobSha (Join-Path $engine ($rel.Replace('/','\'))) -Canonical) -ceq $files[$rel].after) 'POST_APPLY_HASH'
 }
 $test=Join-Path $engine 'tools\test_no11_week429_carry.mjs'
 & node --test $test
 Need ($LASTEXITCODE -eq 0) 'CALENDAR_TESTS_FAILED'
 $collector=Join-Path $engine 'windows\Run-No11WeeklyCandidateRefreshReadOnly.ps1'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $collector -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'COLLECTOR_SELFTEST_FAILED'
 Write-Host 'WEEK429_OFFLINE_TESTS=PASS'
 $tool=Join-Path $engine 'tools\no11_weekly_g1_refresh.mjs'
 $output=@(& node $tool plan --weekly-run $seed --root $refresh --carry-friday-run $friday --holiday-asof 2026-11-02 2>&1)
 if($LASTEXITCODE -ne 0){
  $output|ForEach-Object{Write-Host $_}
  throw 'NO11_WEEK429_SETUP_REAL_FRIDAY_429_PROOF_OR_PLAN_BLOCKED'
 }
 $plan=($output -join "`n")|ConvertFrom-Json
 Need ($plan.plan.asOfSession -ceq '2026-11-02' -and
       @($plan.plan.symbols).Count -eq 429 -and
       $plan.plan.fridayCarryForward.schemaId -ceq 'ARK_NO11_WEEK429_EXPLICIT_CARRY_V1' -and
       $plan.plan.holidayHistoricalRecovery -eq $true) 'CARRY_PLAN_SCOPE_MISMATCH'
 Write-Host ('WEEK429_PLAN_PATH='+$plan.run)
 Write-Host ('WEEK429_CARRIED_SYMBOLS='+@($plan.plan.symbols).Count)
 Write-Host ('WEEK429_FRESH_NOV02_CAPTURE_FILES='+$plan.resumed)
 Write-Host 'WEEK429_SOURCE_AND_PLAN=PASS'
 Write-Host ('WEEK429_BACKUP='+$(if($backup){$backup}else{'PREVIOUSLY_INSTALLED'}))
 Write-Host 'COLLECTOR_LAUNCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 $msg=$_.Exception.Message
 Write-Host ('WEEK429_SETUP=BLOCKED|'+$msg)
 if($mode -ceq 'OLD' -and $backup -and (Test-Path -LiteralPath $backup -PathType Container)){
  $unrestored=@()
  foreach($rel in $files.Keys){
   try{
    $target=Join-Path $engine ($rel.Replace('/','\'))
    $expected=$files[$rel].after
    if(Test-Path -LiteralPath $target){
     $current=BlobSha $target -Canonical
     if($current -ceq $files[$rel].before){continue}
     if($current -cne $expected){throw 'CONCURRENT_EDIT'}
    }else{
     if($files[$rel].before -ne ''){throw 'MISSING_DURING_ROLLBACK'}
     continue
    }
    if($files[$rel].before -eq ''){Remove-Item -LiteralPath $target -Force}
    else{[IO.File]::Copy((Join-Path $backup ($rel.Replace('/','\'))),$target,$true)}
   }catch{$unrestored+=@($rel)}
  }
  Write-Host ('WEEK429_ROLLBACK='+$(if($unrestored.Count -eq 0){'PASS'}else{'INCOMPLETE'}))
  if($unrestored.Count){Write-Host ('WEEK429_UNRESTORED='+($unrestored -join ','))}
 }
 if($backup){Write-Host ('WEEK429_BACKUP='+$backup)}
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
