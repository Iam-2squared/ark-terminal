# Same-day physical Excel session -> immutable LIVE transport pins.
# Invoked only after the existing Trade approval gate. It may open the configured
# order workbook, but never saves it and never writes the order trigger to 1.
param(
 [string]$SettingsFile='',
 [string]$OutputRoot='',
 [string]$SessionDate='',
 [switch]$SameDayOperatorApproved,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)

function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_AUTO_TRANSPORT_'+$code)}}
function NowJst {return [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9))}
function Full([string]$p){
 Need (-not [string]::IsNullOrWhiteSpace($p) -and [IO.Path]::IsPathRooted($p)) 'ABSOLUTE_PATH'
 return [IO.Path]::GetFullPath($p)
}
function ReparseFree([string]$p,[bool]$directory=$false){
 $full=Full $p
 Need (Test-Path -LiteralPath $full -PathType $(if($directory){'Container'}else{'Leaf'})) 'PATH_MISSING'
 $cursor=$full
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  $i=Get-Item -LiteralPath $cursor -Force
  Need (($i.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  $next=Split-Path -Parent $cursor
  if($next -ceq $cursor){break}
  $cursor=$next
 }
 return $full
}
function WriteImmutableJson([string]$root,$value,[string]$prefix){
 $json=(ConvertTo-Json -InputObject $value -Depth 12 -Compress)+[char]10
 [byte[]]$bytes=[Text.UTF8Encoding]::new($false).GetBytes($json)
 $hash=[Security.Cryptography.SHA256]::Create()
 try{$sha=([BitConverter]::ToString($hash.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}
 finally{$hash.Dispose()}
 $file=Join-Path $root ($prefix+'-'+$sha+'.json')
 if(Test-Path -LiteralPath $file){
  Need (([IO.File]::ReadAllBytes($file) -join ',') -ceq ($bytes -join ',')) 'IMMUTABLE_CONFLICT'
 }else{
  $stream=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 }
 return $file
}

if($OfflineSelfTest){
 Need (-not $SameDayOperatorApproved) 'SELFTEST_MUST_NOT_APPROVE'
 Need ($PSCommandPath -ne '') 'SELFTEST_SOURCE'
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$errors)
 Need ($errors.Count -eq 0) 'SELFTEST_PARSE'
 Write-Host 'NO11_AUTO_TRANSPORT_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}

$excel=$null;$orderBook=$null;$sheet=$null
try{
 Need $SameDayOperatorApproved.IsPresent 'SAME_DAY_OPERATOR_APPROVAL_REQUIRED'
 $now=NowJst
 Need ($SessionDate -ceq $now.ToString('yyyy-MM-dd')) 'ACTUAL_SESSION_DAY_REQUIRED'
 Need ($now.ToString('HH:mm:ss') -ge '09:00:00' -and $now.ToString('HH:mm:ss') -le '15:20:00') 'MARKET_SESSION_REQUIRED'
 $settingsFile=ReparseFree $SettingsFile
 $root=ReparseFree $OutputRoot $true
 $settings=Get-Content -LiteralPath $settingsFile -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($settings.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
       $settings.sameDayApprovalRequired -eq $true -and
       $settings.automaticOrderAuthorization -eq $false -and
       $settings.orderTransmission -eq $false -and
       $settings.normalMaxPositions -eq 3) 'SETTINGS_CONTRACT'
 $account=ReparseFree ([string]$settings.accountWorkbookPath)
 $market=ReparseFree ([string]$settings.marketWorkbookPath)
 $order=ReparseFree ([string]$settings.orderIdWorkbookPath)
 Need ($account.EndsWith('.xlsx',[StringComparison]::OrdinalIgnoreCase) -and
       $market.EndsWith('.xlsx',[StringComparison]::OrdinalIgnoreCase) -and
       $order.EndsWith('.xlsx',[StringComparison]::OrdinalIgnoreCase)) 'WORKBOOK_EXTENSIONS'

 if(-not ('No11AutoTransportNative' -as [type])){
  Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class No11AutoTransportNative {
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
}
'@ -ErrorAction Stop
 }
 $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
 Need ($excel.Visible -eq $true -and $excel.Ready -eq $true -and [int]$excel.CalculationState -eq 0) 'EXCEL_NOT_READY'
 [long]$hwnd=[long]$excel.Hwnd
 Need ($hwnd -gt 0) 'EXCEL_HWND'
 [uint32]$excelPid=0
 [void][No11AutoTransportNative]::GetWindowThreadProcessId([IntPtr]$hwnd,[ref]$excelPid)
 Need ($excelPid -gt 0) 'EXCEL_PID'
 $process=Get-Process -Id $excelPid
 Need ($process.ProcessName -ieq 'EXCEL') 'EXCEL_PROCESS'

 $opened=@{}
 foreach($wb in @($excel.Workbooks)){
  if([string]$wb.Path -ne ''){
   $opened[[IO.Path]::GetFullPath([string]$wb.FullName).ToLowerInvariant()]=$wb
  }
 }
 foreach($required in @($account,$market)){
  Need ($opened.ContainsKey($required.ToLowerInvariant())) 'ORIGINAL_WORKBOOK_NOT_OPEN'
 }
 $orderKey=$order.ToLowerInvariant()
 $openedByAuto=$false
 if(-not $opened.ContainsKey($orderKey)){
  # Only the configured order workbook may be opened here.
  Need ($excel.Workbooks.Count -eq 2) 'UNEXPECTED_WORKBOOK_SET_BEFORE_ORDER_OPEN'
  $orderBook=$excel.Workbooks.Open($order)
  $openedByAuto=$true
 }else{$orderBook=$opened[$orderKey]}

 Need ($null -ne $orderBook -and -not $orderBook.ReadOnly -and
       [IO.Path]::GetFullPath([string]$orderBook.FullName).Equals($order,[StringComparison]::OrdinalIgnoreCase)) 'ORDER_WORKBOOK_IDENTITY'
 Need ($orderBook.Worksheets.Count -eq 1 -and
       [string]$orderBook.Worksheets.Item(1).Name -ceq 'ARK_ORDER_IDS_READONLY') 'ORDER_WORKBOOK_LAYOUT'
 $sheet=$orderBook.Worksheets.Item('ARK_ORDER_IDS_READONLY')
 Need (-not $sheet.ProtectContents) 'ORDER_SHEET_PROTECTED'
 $guard=$sheet.Range('BD1');$trigger=$sheet.Range('BD2');$session=$sheet.Range('BD3');$formula=$sheet.Range('BD4')
 Need (-not $guard.HasFormula -and -not $trigger.HasFormula -and -not $session.HasFormula -and
       -not $trigger.MergeCells -and -not $formula.MergeCells -and -not $formula.HasArray) 'ORDER_CONTROL_CELLS'
 $t=$trigger.Value2
 Need ($null -eq $t -or $t -eq '' -or (($t -is [ValueType]) -and [double]$t -eq 0)) 'TRIGGER_ALREADY_NONZERO'
 if($formula.HasFormula){
  Need ([string]$formula.Formula -match '^=Rss(?:StockOrder|CancelOrder)\(') 'FORMULA_CELL_NOT_OWNED'
  $formula.ClearContents()
 }else{
  Need ([string]::IsNullOrWhiteSpace([string]$formula.Value2)) 'FORMULA_CELL_NOT_EMPTY'
 }
 $sessionKey='ARKNO11:'+($SessionDate.Replace('-',''))+':'+[guid]::NewGuid().ToString('N')
 # Session initialization only. The sending write is BD2=1 and is NOT performed here.
 $guard.Value2='ARK_NO11_SEND_ONCE'
 $trigger.Value2=0
 $session.Value2=$sessionKey
 $formula.NumberFormat='General'
 Need ([string]$guard.Value2 -ceq 'ARK_NO11_SEND_ONCE' -and [double]$trigger.Value2 -eq 0 -and
       [string]$session.Value2 -ceq $sessionKey -and -not $formula.HasFormula -and
       [string]::IsNullOrWhiteSpace([string]$formula.Value2)) 'SESSION_INITIALIZATION_READBACK'

 $saved=@($excel.Workbooks|Where-Object{[string]$_.Path -ne ''})
 $temporary=@($excel.Workbooks|Where-Object{[string]$_.Path -eq ''})
 Need ($temporary.Count -eq 0 -and $saved.Count -eq 3) 'WORKBOOK_SET_AFTER_INITIALIZATION'
 $actual=@($saved|ForEach-Object{[IO.Path]::GetFullPath([string]$_.FullName)})
 foreach($expected in @($account,$market,$order)){
  Need (@($actual|Where-Object{$_ -ieq $expected}).Count -eq 1) 'WORKBOOK_SET_IDENTITY'
 }

 $addinPaths=@()
 foreach($addin in @($excel.AddIns)){
  try{
   if($addin.Installed -eq $true -and -not [string]::IsNullOrWhiteSpace([string]$addin.FullName)){
    $name=[IO.Path]::GetFileName([string]$addin.FullName)
    if($name -match '^MarketSpeed2_RSS_(?:32|64)bit\.xll$' -or $name -match '^MarketSpeed2_RSS_VBA\.xlam$'){
     $addinPaths+=@([IO.Path]::GetFullPath([string]$addin.FullName))
    }
   }
  }catch{}
 }
 $addinPaths=@($addinPaths|Sort-Object -Unique)
 Need ($addinPaths.Count -eq 2 -and
       @($addinPaths|Where-Object{[IO.Path]::GetFileName($_) -match '^MarketSpeed2_RSS_(?:32|64)bit\.xll$'}).Count -eq 1 -and
       @($addinPaths|Where-Object{[IO.Path]::GetFileName($_) -match '^MarketSpeed2_RSS_VBA\.xlam$'}).Count -eq 1) 'RSS_ADDINS_NOT_UNIQUE'

 $dispatch=Join-Path $root 'transport-dispatch'
 [void][IO.Directory]::CreateDirectory($dispatch)
 $dispatch=ReparseFree $dispatch $true
 $expires=[DateTimeOffset]::ParseExact(($SessionDate+'T15:25:00+09:00'),'yyyy-MM-ddTHH:mm:sszzz',[Globalization.CultureInfo]::InvariantCulture)
 $transport=[ordered]@{
  schemaId='ARK_NO11_MSII_TRANSPORT_CONFIG_V1'
  sessionDate=$SessionDate
  mode='LIVE'
  orderTransmission=$true
  operatorEnabled=$true
  approvedForSession=$true
  rssSessionKey=$sessionKey
  expiresAtJst=$expires.ToString('yyyy-MM-ddTHH:mm:sszzz')
  workbookPath=$order
  dispatchDirectory=$dispatch
  worksheetName='ARK_ORDER_IDS_READONLY'
  formulaCell='BD4'
  triggerCell='BD2'
  guardCell='BD1'
  sessionCell='BD3'
  guardValue='ARK_NO11_SEND_ONCE'
  expectedExcelPid=[int]$excelPid
  expectedExcelHwnd=[long]$hwnd
  expectedExcelStartedAt=$process.StartTime.ToUniversalTime().ToString('o')
  expectedAddInPaths=@($addinPaths)
  expectedOpenWorkbooks=@($actual)
  expectedTemporaryWorkbooks=@()
  permitMaximumAgeMs=10000
  responseTimeoutMs=5000
 }
 $file=WriteImmutableJson $root $transport 'automatic-live-transport'
 Write-Host ('AUTOMATIC_TRANSPORT='+$file)
 Write-Host ('AUTOMATIC_TRANSPORT_EXCEL_PID='+$excelPid)
 Write-Host ('AUTOMATIC_TRANSPORT_ORDER_BOOK_OPENED='+$openedByAuto)
 Write-Host 'AUTOMATIC_TRANSPORT_SESSION_INITIALIZED=True'
 Write-Host 'ORDER_TRIGGER_WRITTEN_TO_ONE=False'
 Write-Host 'ORDER_SENT=False'
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_AUTO_TRANSPORT_[A-Z0-9_]+$'){$reason='NO11_AUTO_TRANSPORT_EXCEL_OR_SESSION_BLOCKED'}
 Write-Host ('AUTOMATIC_TRANSPORT=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRIGGER_WRITTEN_TO_ONE=False'
 Write-Host 'ORDER_SENT=False'
 exit 2
}finally{
 foreach($o in @($sheet,$orderBook,$excel)){
  if($null -ne $o -and [Runtime.InteropServices.Marshal]::IsComObject($o)){
   try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($o)}catch{}
  }
 }
}
exit 0
