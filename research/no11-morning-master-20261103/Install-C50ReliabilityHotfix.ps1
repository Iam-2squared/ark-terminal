# 2026-11-04 Chart50 collector reliability hotfix.
# Local source-only update: no Excel access, no order calls, no ledger modification.
param([switch]$Apply)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if(-not $Apply){throw 'C50_HOTFIX_EXPLICIT_APPLY_REQUIRED'}
$day='2026-11-04'
$base=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
$bindingFile=Join-Path $base 'unified-launcher\automatic-inputs.json'
if(-not (Test-Path -LiteralPath $bindingFile -PathType Leaf)){throw 'C50_HOTFIX_BINDING_MISSING'}
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8 | ConvertFrom-Json
$target=Join-Path ([string]$binding.engine) 'windows\Probe-No11Chart50ContinuousReadOnly.ps1'
if(-not (Test-Path -LiteralPath $target -PathType Leaf)){throw 'C50_HOTFIX_COLLECTOR_MISSING'}
function Assert-ArkStopped {
 $active=@(Get-CimInstance Win32_Process | Where-Object {
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)(\.exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder'
 })
 if($active.Count -gt 0){throw ('C50_HOTFIX_ARK_PROCESS_ACTIVE_'+$active.Count)}
}
Assert-ArkStopped
if((Get-Date -Format 'yyyy-MM-dd') -ne $day){throw 'C50_HOTFIX_SESSION_DATE_MISMATCH'}
$raw=[IO.File]::ReadAllBytes($target)
$beforeHash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
$encoding=[Text.UTF8Encoding]::new($false,$true)
$bom=$raw.Length -ge 3 -and $raw[0] -eq 239 -and $raw[1] -eq 187 -and $raw[2] -eq 191
$offset=if($bom){3}else{0}
$local=$encoding.GetString($raw,$offset,$raw.Length-$offset)
$crlf=([string][char]13)+([string][char]10)
$lf=[string][char]10
$newline=if($local.Contains($crlf)){$crlf}else{$lf}
$local=$local.Replace($crlf,$lf)
if($local.Contains('ARK_NO11_C50_BOUNDED_ATTACH_RETRY_V1')){
 Write-Host 'C50_RELIABILITY_HOTFIX=ALREADY_INSTALLED'
 exit 0
}
foreach($pin in @('ARK_NO11_C50_PRESERVE_UNSAVED_ON_FAILURE_V1',
 'ARK_NO11_C50_BOUNDED_GROWING_SHAPE_RETRY_V1',
 'NO11_C50_GROWING_SHAPE_RETRY_SELFTEST=PASS',
 'temporaryWorkbookClosed=$temporaryClosed;collectorFailed=$failed')){
 if(-not $local.Contains($pin)){throw 'C50_HOTFIX_PREREQUISITE_MISSING'}
}
# Fetch immutable source from pinned GitHub commit; check its Git blob SHA.
$url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/2bcf8b537ba4c882a79ee0192f4c48452126766b/research/no12-prebuy-causal-runtime-20261011/windows/Probe-No11Chart50ContinuousReadOnly.ps1'
$expectedBlob='afc70acacabd4655a45931d6bc5edd63a36fc1ee'
$download=Join-Path $env:TEMP ('ark-c50-source-'+[guid]::NewGuid().ToString('N')+'.ps1')
$candidate=Join-Path (Split-Path -Parent $target) ('ark-c50-candidate-'+[guid]::NewGuid().ToString('N')+'.ps1')
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 Invoke-WebRequest -Uri $url -OutFile $download -UseBasicParsing -ErrorAction Stop
 $bytes=[IO.File]::ReadAllBytes($download)
 $prefix=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length)+[char]0)
 $joined=New-Object byte[] ($prefix.Length+$bytes.Length)
 [array]::Copy($prefix,0,$joined,0,$prefix.Length)
 [array]::Copy($bytes,0,$joined,$prefix.Length,$bytes.Length)
 $sha1=[Security.Cryptography.SHA1]::Create()
 try{$blob=([BitConverter]::ToString($sha1.ComputeHash($joined))).Replace('-','').ToLowerInvariant()}
 finally{$sha1.Dispose()}
 if($blob -cne $expectedBlob){throw 'C50_HOTFIX_REFERENCE_HASH_MISMATCH'}
 $ref=$encoding.GetString($bytes).Replace($crlf,$lf)

 function Slice([string]$body,[string]$start,[string]$end){
  $i=$body.IndexOf($start,[StringComparison]::Ordinal)
  if($i -lt 0){throw 'C50_HOTFIX_START_ANCHOR_MISSING'}
  if($body.IndexOf($start,$i+$start.Length,[StringComparison]::Ordinal) -ge 0){throw 'C50_HOTFIX_START_ANCHOR_DUPLICATE'}
  $j=$body.IndexOf($end,$i+$start.Length,[StringComparison]::Ordinal)
  if($j -lt 0){throw 'C50_HOTFIX_END_ANCHOR_MISSING'}
  return $body.Substring($i,$j-$i)
 }
 function Splice([string]$oldStart,[string]$referenceStart,[string]$end,[string]$tag){
  $old=Slice $script:local $oldStart $end
  $replacement=Slice $script:ref $referenceStart $end
  if(-not $old -or -not $replacement){throw ('C50_HOTFIX_EMPTY_BLOCK_'+$tag)}
  $script:local=$script:local.Replace($old,$replacement)
  if(-not $script:local.Contains($referenceStart)){throw ('C50_HOTFIX_INSERT_FAILED_'+$tag)}
 }

 Splice ' $accounts=@($Books | Where-Object {$_.Name -ceq ''Ark_No11_MSII_RSS.xlsx''})' ' # ARK_NO11_C50_BOOK_MATCH_DIAGNOSTICS_V1' ' if($extra){' 'IDENTITY'
 Splice ' $originalBooks=OriginalBooks @($excel.Workbooks) $OrderIdWorkbookPath' ' # ARK_NO11_C50_BOUNDED_ATTACH_RETRY_V1' ' $stage=''CAPACITY''' 'ATTACH'
 Splice ' $values=$null;$shapeOK=$false' ' $values=$null;$shapeOK=$false' ' # One extra fence row' 'CHART'
 Splice '  $values=$quote.Range((''A2:E{0}'' -f ($symbols.Count+1))).Value2' '  # ARK_NO11_C50_MARKET_BOUNDED_RETRY_V1' '  $mi=New-Object System.Collections.ArrayList' 'MARKET'

 $oldTest='if($persistent.Reads -ne 3){throw ''NO11_C50_GROWING_SHAPE_BOUNDED_SELFTEST_FAILED''}'
 $newTest='if($persistent.Reads -ne 12){throw ''NO11_C50_GROWING_SHAPE_BOUNDED_SELFTEST_FAILED''}'
 if($script:local.Split(@($oldTest),[StringSplitOptions]::None).Count -ne 2){throw 'C50_HOTFIX_TEST_CONTEXT_CHANGED'}
 $script:local=$script:local.Replace($oldTest,$newTest)
 foreach($pin in @('ARK_NO11_C50_PRESERVE_UNSAVED_ON_FAILURE_V1',
  'ARK_NO11_C50_BOOK_MATCH_DIAGNOSTICS_V1',
  'ARK_NO11_C50_BOUNDED_ATTACH_RETRY_V1',
  'ARK_NO11_C50_BOUNDED_GROWING_SHAPE_RETRY_V1',
  'ARK_NO11_C50_MARKET_BOUNDED_RETRY_V1',
  'temporaryWorkbookClosed=$temporaryClosed;collectorFailed=$failed')){
  if(-not $script:local.Contains($pin)){throw 'C50_HOTFIX_CONTRACT_MISSING'}
 }
 if($script:local.Split(@('try{$book.Close($false);$temporaryClosed=$true}'),[StringSplitOptions]::None).Count -ne 2){
  throw 'C50_HOTFIX_CLOSE_SCOPE_CHANGED'
 }
 $patched=$script:local.Replace($lf,$newline)
 $out=[Text.UTF8Encoding]::new($false).GetBytes($patched)
 if($bom){$out=[byte[]]@(239,187,191)+$out}
 $backupDir=Join-Path $base ('patch-backups\c50-reliability-'+[guid]::NewGuid().ToString('N'))
 New-Item -Path $backupDir -ItemType Directory -Force | Out-Null
 [IO.File]::WriteAllBytes((Join-Path $backupDir 'collector-original.ps1'),$raw)
 [IO.File]::WriteAllBytes($candidate,$out)
 $tokens=$null;$parseErrors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($candidate,[ref]$tokens,[ref]$parseErrors)
 if($parseErrors.Count -ne 0){throw 'C50_HOTFIX_PARSE_FAILED'}
 $result=& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $candidate -OfflineSelfTest
 $exitCode=$LASTEXITCODE
 if($exitCode -ne 0 -or @($result|Where-Object {$_ -eq 'NO11_C50_GROWING_SHAPE_RETRY_SELFTEST=PASS'}).Count -ne 1){
  throw 'C50_HOTFIX_OFFLINE_SELFTEST_FAILED'
 }
 Assert-ArkStopped
 if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -cne $beforeHash){throw 'C50_HOTFIX_TARGET_CHANGED'}
 [IO.File]::Replace($candidate,$target,[System.Management.Automation.Language.NullString]::Value)
 Write-Host 'C50_RELIABILITY_HOTFIX=PASS'
 Write-Host 'C50_ATTACH_RETRIES=12'
 Write-Host 'C50_CHART_RETRIES=12'
 Write-Host 'C50_MARKET_RETRIES=12'
 Write-Host 'EXCEL_PRESERVED_ON_FAILURE=True'
 Write-Host 'POWERSHELL_SYNTAX=PASS'
 Write-Host 'OFFLINE_SELFTEST=PASS'
 Write-Host 'BACKUP_CREATED=True'
 Write-Host 'LIVE_LEDGER_UNCHANGED=True'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_SENT_BY_INSTALLER=False'
}finally{
 if(Test-Path -LiteralPath $candidate){Remove-Item -LiteralPath $candidate -Force}
 if(Test-Path -LiteralPath $download){Remove-Item -LiteralPath $download -Force}
}
