param([Parameter(Mandatory=$true)][string]$CandidateRoot)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Check([bool]$ok,[string]$why){if(-not $ok){throw ('COMPLETED_SESSION_TEST_'+$why)}}
foreach($file in @(Get-ChildItem -LiteralPath $CandidateRoot -Filter '*.ps1' -File)){
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
 if($errors.Count){$errors|ForEach-Object{Write-Host ($file.Name+':'+$_.Message)};throw 'CANDIDATE_PARSE_FAILED'}
}
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $CandidateRoot 'native.ps1'),[ref]$tokens,[ref]$errors)
$fn=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'RunWeekly'},$true))
Check ($fn.Count -eq 1) 'RUN_WEEKLY_UNIQUE'
# Invoke-Expression has no source file and gives functions an empty
# PSScriptRoot. Dot-source only the extracted function from a real file,
# matching the installed native launcher's source-directory semantics.
$functionFile=Join-Path $CandidateRoot 'runweekly-fixture.ps1'
[IO.File]::WriteAllText($functionFile,$fn[0].Extent.Text,[Text.UTF8Encoding]::new($false))
. $functionFile
function Need([bool]$ok,[string]$reason){Check $ok $reason}
function LocalFile([string]$path,[string]$name){return $path}
$script:ClockValue=[datetimeoffset]::Parse('2026-11-09T10:05:00+09:00')
function Clock{return $script:ClockValue}
$script:ExcelCalls=0
function CheckExcel($cfg,[bool]$live){Check (-not $live) 'NO_TRADE_CHECK';$script:ExcelCalls++}
function Get-FileHash {param([string]$LiteralPath,[string]$Algorithm) return [pscustomobject]@{Hash=('a'*64)}}
$script:AsOf='2026-11-06';$script:Target='2026-11-09';$script:Scope='FULL_MARKET_FRIDAY'
function node {
 param([string]$Tool,[string]$Action)
 Check ($Action -ceq 'schedule') 'CALENDAR_ACTION'
 $global:LASTEXITCODE=0
 return (ConvertTo-Json -Compress -InputObject @{
  schemaId='ARK_NO11_WEEKLY_REFRESH_SCHEDULE_V1';asOfSession=$script:AsOf;
  sessionDate=$script:Target;mode=$script:Scope;orderTransmission=$false})
}
$script:Calls=@()
function StartChild([string]$kind,[string]$file,[string[]]$parts,[string]$digest,[string]$date){
 $script:Calls+=@([pscustomobject]@{Kind=$kind;File=$file;Parts=$parts;Date=$date})
}
$weekly='C:\fixture\Run-No11NightlyCycle.ps1'
$cfg=[pscustomobject]@{fullSymbolsFile='C:\fixture\symbols.txt'}
RunWeekly $cfg
Check ($script:Calls.Count -eq 1 -and $script:Calls[0].Kind -ceq 'WEEKLY') 'MONDAY_DATA_LAUNCH'
Check ($script:Calls[0].Date -ceq '2026-11-06') 'REAL_FRIDAY_MARKER_DATE'
Check ($script:Calls[0].Parts -notcontains '-WeekendFriday') 'NO_FAKE_WEEKEND'
Check ($script:Calls[0].Parts -notcontains '-IApproveOrdersForToday') 'NO_ORDER_APPROVAL'
$script:ClockValue=[datetimeoffset]::Parse('2026-11-08T20:00:00+09:00')
RunWeekly $cfg
Check ($script:Calls[1].Parts -contains '-WeekendFriday') 'ACTUAL_WEEKEND_STILL_WORKS'
$script:ClockValue=[datetimeoffset]::Parse('2026-11-09T19:00:00+09:00')
$script:AsOf='2026-11-09';$script:Target='2026-11-10';$script:Scope='WEEKLY_POOL_CANDIDATES_ONLY'
RunWeekly $cfg
Check ($script:Calls[2].Date -ceq '2026-11-09') 'MONDAY_CLOSE_SWITCHES_DATE'
Check ($script:ExcelCalls -eq 3) 'ORIGINAL_EXCEL_CHECK_RETAINED'
Write-Host 'NO11_COMPLETED_SESSION_WINDOWS=PASS'
Write-Host 'REAL_EXCEL_ACCESSED=False'
Write-Host 'ORDER_TRANSMISSION=False'
