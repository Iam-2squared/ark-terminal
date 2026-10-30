# Local-only, human-reviewed MarketSpeed II securities-side cash evidence.
# Source: Domestic summary -> Rakuten Securities buying power (NOT total
# cash-stock buying power which may include Rakuten Bank).
# No broker/Excel COM, transfer, margin, order, or permission modification.
param(
 [string]$ScreenshotFile='',
 [string]$SecuritiesAvailableJpy='',
 [string]$Account='',
 [switch]$IReviewedExactSecuritiesAmount,
 [switch]$IConfirmedAutoSweepDisabled,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_SECURITIES_CASH_EVIDENCE_'+$reason)}
}
$schema='ARK_NO11_SECURITIES_ONLY_OPENING_CASH_V1'
$source='MSII_DOMESTIC_SUMMARY_RAKUTEN_SECURITIES_BUYING_POWER'
$label=(-join [char[]]@(0x697d,0x5929,0x8a3c,0x5238,0x8cb7,0x4ed8,0x53ef,0x80fd,0x984d))
if($OfflineSelfTest){
 Need ($schema -ceq 'ARK_NO11_SECURITIES_ONLY_OPENING_CASH_V1' -and
  $label.Length -eq 9 -and $source -ceq 'MSII_DOMESTIC_SUMMARY_RAKUTEN_SECURITIES_BUYING_POWER') 'STATIC'
 Write-Host 'NO11_SECURITIES_CASH_EVIDENCE_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need ($IReviewedExactSecuritiesAmount.IsPresent -and $IConfirmedAutoSweepDisabled.IsPresent) 'OPERATOR_REVIEW_REQUIRED'
 Need ($SecuritiesAvailableJpy -cmatch '^(?:0|[1-9][0-9]{0,13})$') 'CASH_AMOUNT_INVALID'
 Need ($Account -in @('特定','一般','NISA（NISA成長投資枠）','旧NISA')) 'ACCOUNT_TYPE_UNVERIFIED'
 Need ([TimeZoneInfo]::Local.GetUtcOffset([datetime]::Now).TotalHours -eq 9) 'PC_NOT_JST'
 Need ([IO.Path]::IsPathRooted($ScreenshotFile) -and
   (Test-Path -LiteralPath $ScreenshotFile -PathType Leaf)) 'REVIEWED_SCREENSHOT_REQUIRED'
 $sourceFile=[IO.Path]::GetFullPath($ScreenshotFile)
 Need ([IO.Path]::GetExtension($sourceFile).ToLowerInvariant() -in @('.png','.jpg','.jpeg','.pdf')) 'SCREENSHOT_TYPE'
 $cursor=$sourceFile
 while(-not [string]::IsNullOrEmpty($cursor)){
  if(Test-Path -LiteralPath $cursor){
   $info=Get-Item -LiteralPath $cursor -Force
   Need (($info.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_SOURCE'
  }
  $next=Split-Path -Parent $cursor
  if($next -ceq $cursor){break}
  $cursor=$next
 }
 $info=Get-Item -LiteralPath $sourceFile -Force
 Need ($info.Length -ge 100 -and $info.Length -le 10000000) 'SCREENSHOT_SIZE'
 $now=[DateTimeOffset]::Now.ToOffset([TimeSpan]::FromHours(9))
 $observed=[DateTimeOffset]::new($info.CreationTime).ToOffset([TimeSpan]::FromHours(9))
 Need ($observed -le $now -and ($now-$observed).TotalMinutes -ge 0 -and
  ($now-$observed).TotalMinutes -le 15) 'SCREENSHOT_MUST_BE_TAKEN_WITHIN_15_MIN'
 $date=$now.ToString('yyyy-MM-dd')
 Need ($observed.ToString('yyyy-MM-dd') -ceq $date) 'SOURCE_SESSION_DATE'
 $digest=(Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash.ToLowerInvariant()
 Need ($digest -cmatch '^[a-f0-9]{64}$') 'SOURCE_HASH'
 $root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\securities-cash-evidence'
 [void][IO.Directory]::CreateDirectory($root)
 $dest=Join-Path $root ('reviewed-'+$date+'-'+[guid]::NewGuid().ToString('N')+'.json')
 $record=[ordered]@{
  schemaId=$schema
  sessionDate=$date
  account=$Account
  source=$source
  displayedField=$label
  securitiesAvailableJpy=$SecuritiesAvailableJpy
  sourceCapturedAtJst=$observed.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
  operatorReviewedAtJst=$now.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
  sourceDocumentPath=$sourceFile
  sourceDocumentSha256=$digest
  bankBridgeExcluded=$true
  autoSweepDisabledConfirmed=$true
  marginAndCreditExcluded=$true
  operatorReviewed=$true
 }
 $text=(ConvertTo-Json -InputObject $record -Depth 7 -Compress)+[char]10
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes($text)
 $stream=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}
 finally{$stream.Dispose()}
 Write-Host 'NO11_SECURITIES_CASH_EVIDENCE=HUMAN_REVIEWED_ONLY_NOT_AUTOMATICALLY_CERTIFIED'
 Write-Host ('NO11_SECURITIES_CASH_EVIDENCE_FILE='+$dest)
 Write-Host 'NO11_SECURITIES_CASH_EVIDENCE_PRIVATE=True'
 Write-Host 'NO11_SECURITIES_CASH_EVIDENCE_LIVE_AUTHORIZED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_SECURITIES_CASH_EVIDENCE_[A-Z0-9_]+$'){$reason='NO11_SECURITIES_CASH_EVIDENCE_INPUT_OR_RUNTIME_ERROR'}
 Write-Host ('NO11_SECURITIES_CASH_EVIDENCE=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
