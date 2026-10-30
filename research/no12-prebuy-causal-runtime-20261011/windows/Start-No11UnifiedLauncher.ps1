# Ark Terminal No.1.1 unified desktop menu.
# LIVE means ORIGINAL MAX3; never grants an order merely from Excel being open.
# Weekend mode uses actual previous-Friday RSS sources; no weekend market data.
param(
 [ValidateSet('Menu','Trade','Weekly','Status','Stop')][string]$Mode='Menu',
 [switch]$IApproveOrdersForToday,
 [switch]$IUnderstandStopDoesNotCancelOrders,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$trade=Join-Path $PSScriptRoot 'Run-No11ReceivedSessionOperatorLive.ps1'
$weekly=Join-Path $PSScriptRoot 'Prepare-No11WeeklyAfterCloseReadOnly.ps1'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$settingsFile=Join-Path $store 'settings.json'
$schema='ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1'
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_UNIFIED_'+$reason)}
}
function Clock {return [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9))}
function SafeArg([string]$s){
 Need (-not [string]::IsNullOrEmpty($s) -and
       -not $s.Contains('"') -and
       -not $s.Contains([char]10) -and
       -not $s.Contains([char]13)) 'ARGUMENT_INVALID'
 return '"'+$s+'"'
}
function LocalFile([string]$v,[string]$label){
 Need (-not [string]::IsNullOrWhiteSpace($v) -and [IO.Path]::IsPathRooted($v)) ($label+'_PATH_REQUIRED')
 $f=[IO.Path]::GetFullPath($v)
 Need ((Test-Path -LiteralPath $f -PathType Leaf) -and
       ((Get-Item -LiteralPath $f -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) ($label+'_MISSING')
 return $f
}
function NewSettings {
 $desktop=[Environment]::GetFolderPath('Desktop')
 return [ordered]@{
  schemaId=$schema
  accountWorkbookPath=(Join-Path $desktop 'Ark_No11_MSII_RSS.xlsx')
  marketWorkbookPath=(Join-Path $desktop 'Ark_No11_MARKET_RSS.xlsx')
  orderIdWorkbookPath=''
  bootstrapConfigFile=''
  fullSymbolsFile=(Join-Path $env:USERPROFILE 'Downloads\rss_symbols_to_acquire.txt')
  normalMaxPositions=3
  sameDayApprovalRequired=$true
  automaticOrderAuthorization=$false
  orderTransmission=$false
 }
}
function Settings {
 [void][IO.Directory]::CreateDirectory($store)
 if(-not (Test-Path -LiteralPath $settingsFile -PathType Leaf)){
  $value=(NewSettings | ConvertTo-Json -Depth 6)+[char]10
  $bytes=[Text.UTF8Encoding]::new($false).GetBytes($value)
  $file=[IO.File]::Open($settingsFile,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}
  finally{$file.Dispose()}
 }
 $cfg=Get-Content -LiteralPath $settingsFile -Raw -Encoding UTF8|ConvertFrom-Json
 $required=@('schemaId','accountWorkbookPath','marketWorkbookPath',
   'orderIdWorkbookPath','bootstrapConfigFile','fullSymbolsFile',
   'normalMaxPositions','sameDayApprovalRequired',
   'automaticOrderAuthorization','orderTransmission')
 Need ((@($cfg.PSObject.Properties.Name) -join '|') -ceq ($required -join '|') -and
       $cfg.schemaId -ceq $schema -and
       $cfg.normalMaxPositions -eq 3 -and
       $cfg.sameDayApprovalRequired -eq $true -and
       $cfg.automaticOrderAuthorization -eq $false -and
       $cfg.orderTransmission -eq $false) 'SETTINGS_UNSAFE'
 return $cfg
}
function RssStatus($cell,[string]$expected,[string]$wanted){
 if($null -eq $cell -or $cell.HasFormula -ne $true){return $false}
 $formula=(([string]$cell.Formula).Trim() -replace '^=@','=').Replace('$','')
 if($formula -cne $expected){return $false}
 $state=([string]$cell.Value2).Trim()
 return ($state -ceq $wanted -or $state -ceq ($formula+' => '+$wanted))
}
function CheckExcel($cfg,[bool]$live){
 Need (@(Get-Process EXCEL -ErrorAction SilentlyContinue).Count -eq 1) 'EXCEL_PROCESS_NOT_UNIQUE'
 $a=LocalFile $cfg.accountWorkbookPath 'ACCOUNT_XLSX'
 $b=LocalFile $cfg.marketWorkbookPath 'MARKET_XLSX'
 $files=@($a,$b)
 if($live){$files+=@(LocalFile $cfg.orderIdWorkbookPath 'ORDER_ID_XLSX')}
 $excel=$null
 try{
  $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
  Need ($excel.Workbooks.Count -eq $files.Count) 'EXCEL_BOOK_COUNT'
  $opened=@()
  foreach($book in $excel.Workbooks){$opened+=@([IO.Path]::GetFullPath([string]$book.FullName))}
  foreach($expected in $files){
   Need (@($opened|Where-Object {$_ -ieq $expected}).Count -eq 1) 'WORKBOOK_IDENTITY'
  }
  $account=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx').Worksheets.Item('ARK_ACCOUNT_READONLY')
  $market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx').Worksheets.Item('ARK_MARKET_READONLY')
  Need ($account.Name -ceq 'ARK_ACCOUNT_READONLY' -and
        $market.Name -ceq 'ARK_MARKET_READONLY') 'RSS_SHEET_IDENTITY'
  $rx=(-join [char[]]@(0x914d,0x4fe1,0x4e2d))
  $done=(-join [char[]]@(0x5b8c,0x4e86))
  Need ((RssStatus ($account.Range('L1')) '=RssCapacityList(L2:L2)' $done) -and
        (RssStatus ($account.Range('N1')) '=RssOrderList(N2:W2,0,1)' $rx) -and
        (RssStatus ($account.Range('AA1')) '=RssExecutionList(AA2:AI2,1)' $rx)) 'RSS_NOT_CONNECTED'
  if($live){
   $ids=$excel.Workbooks.Item([IO.Path]::GetFileName($cfg.orderIdWorkbookPath))
   Need ($ids.Worksheets.Count -eq 1 -and
         $ids.Worksheets.Item(1).Name -ceq 'ARK_ORDER_IDS_READONLY') 'RSS_ID_BOOK_IDENTITY'
  }
 }finally{
  if($null -ne $excel -and
     [Runtime.InteropServices.Marshal]::IsComObject($excel)){
   [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
  }
 }
}
function StartChild([string]$kind,[string]$file,[string[]]$parts,[string]$sourceDigest,[string]$date){
 $marker=Join-Path $store ($kind+'-'+$date+'.launch.json')
 Need (-not (Test-Path -LiteralPath $marker -PathType Leaf)) ($kind+'_ALREADY_STARTED_NO_DUPLICATE')
 $receipt=[ordered]@{
  schemaId='ARK_NO11_UNIFIED_START_REQUEST_V1';kind=$kind
  asOfDate=$date;operatorRequestedAtJst=(Clock).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
  sourceSha256=$sourceDigest;externalBrokerApprovalStillRequired=$true
 }
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes(
  (ConvertTo-Json -InputObject $receipt -Compress)+[char]10)
 $stream=[IO.File]::Open($marker,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}
 finally{$stream.Dispose()}
 $cmd=@('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',(SafeArg $file))
 foreach($p in $parts){$cmd+=@(SafeArg ([string]$p))}
 $logs=Join-Path $store 'logs'
 [void][IO.Directory]::CreateDirectory($logs)
 $id=[guid]::NewGuid().ToString('N')
 $stdout=Join-Path $logs ($kind+'-'+$date+'-'+$id+'.log')
 $stderr=Join-Path $logs ($kind+'-'+$date+'-'+$id+'.err')
 $process=Start-Process -FilePath 'powershell.exe' -ArgumentList ($cmd -join ' ') -WorkingDirectory $PSScriptRoot -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
 Write-Host ('NO11_UNIFIED_'+$kind+'_LAUNCHED_PID='+$process.Id)
 Write-Host ('NO11_UNIFIED_'+$kind+'_LOG='+$stdout)
 Write-Host 'NO11_UNIFIED_LAUNCH_IS_NOT_AN_EXECUTION_CONFIRMATION=True'
}
function RunTrade($cfg,[bool]$approved){
 Need $approved 'TODAYS_EXPLICIT_OPERATOR_APPROVAL_REQUIRED'
 $now=Clock
 $day=$now.ToString('yyyy-MM-dd')
 Need ($now.DayOfWeek -notin @([DayOfWeek]::Saturday,[DayOfWeek]::Sunday) -and
       $now.ToString('HH:mm:ss') -ge '09:00:00' -and
       $now.ToString('HH:mm:ss') -le '15:20:00') 'TRADING_SESSION_REQUIRED'
 $file=LocalFile $cfg.bootstrapConfigFile 'LIVE_BOOTSTRAP_CONFIG'
 $config=Get-Content -LiteralPath $file -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($config.schemaId -ceq 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1' -and
       $config.sessionDate -ceq $day -and
       $config.orderTransmission -eq $false -and
       $config.orderIdWorkbookPath -ceq $cfg.orderIdWorkbookPath -and
       [string]$config.brokerExecutionConfig -ne '' -and
       [string]$config.h235ModelRoot -ne '') 'LIVE_DATED_CONFIG_REQUIRED'
 $broker=Get-Content -LiteralPath (LocalFile $config.brokerExecutionConfig 'BROKER_CONFIG') -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($broker.transport.mode -ceq 'LIVE' -and
       $broker.transport.operatorEnabled -eq $true -and
       $broker.transport.approvedForSession -eq $true -and
       $broker.sessionDate -ceq $day -and
       $broker.transport.sessionDate -ceq $day -and
       $broker.ledger.maxSymbols -eq 3 -and
       $broker.ledger.allocatedCashJpy -ceq 'AUTO_SECURITIES_ACCOUNT_CASH_ONLY') 'BROKER_CASH_ONLY_AND_SESSION_APPROVAL'
 [void](LocalFile $broker.securitiesCashEvidenceFile 'SECURITIES_CASH_EVIDENCE')
 CheckExcel $cfg $true
 $sha=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
 $params=@('-ConfigFile',$file,'-AccountWorkbookPath',$cfg.accountWorkbookPath,
           '-OrderIdWorkbookPath',$cfg.orderIdWorkbookPath,
           '-IApproveFullArkLiveOrdersForThisSession')
 StartChild 'TRADE' $trade $params $sha $day
 Write-Host 'NO11_UNIFIED_TRADEX=FROZEN_MAX3_ENGINE_REQUESTED'
}
function RunWeekly($cfg){
 $now=Clock
 $weekday=$now.DayOfWeek
 $weekend=$weekday -in @([DayOfWeek]::Saturday,[DayOfWeek]::Sunday)
 $friday=$weekday -eq [DayOfWeek]::Friday -and $now.ToString('HH:mm') -ge '18:00'
 $otherAfterClose=$weekday -in @([DayOfWeek]::Monday,[DayOfWeek]::Tuesday,[DayOfWeek]::Wednesday,[DayOfWeek]::Thursday) -and $now.ToString('HH:mm') -ge '18:00'
 Need ($weekend -or $friday -or $otherAfterClose) 'WEEKLY_OR_DAILY_AFTERCLOSE_REQUIRED'
 $source=if($weekday -eq [DayOfWeek]::Saturday){$now.AddDays(-1)}
    elseif($weekday -eq [DayOfWeek]::Sunday){$now.AddDays(-2)}
    else{$now}
 $sourceDay=$source.ToString('yyyy-MM-dd')
 $list=LocalFile $cfg.fullSymbolsFile 'ORIGINAL_SYMBOLS'
 CheckExcel $cfg $false
 $arguments=@('-FullSymbolsFile',$list)
 if($weekend){$arguments+=@('-WeekendFriday')}
 $sha=(Get-FileHash -LiteralPath $list -Algorithm SHA256).Hash.ToLowerInvariant()
 StartChild 'WEEKLY' $weekly $arguments $sha $sourceDay
 Write-Host ('NO11_UNIFIED_WEEKLY_REAL_ASOF_FRIDAY='+$sourceDay)
 Write-Host 'ORDER_TRANSMISSION=False'
}
function StopRunningEngine($cfg,[bool]$approved){
 Need $approved 'STOP_REQUIRES_MANUAL_ORDER_CHECK_CONFIRMATION'
 $day=(Clock).ToString('yyyy-MM-dd')
 $config=Get-Content -LiteralPath (LocalFile $cfg.bootstrapConfigFile 'LIVE_BOOTSTRAP_CONFIG') -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($config.sessionDate -ceq $day) 'STOP_REQUIRES_CURRENT_DAY'
 $private=[IO.Path]::GetFullPath([string]$config.privateRoot)
 Need ([IO.Path]::IsPathRooted($private) -and
       (Test-Path -LiteralPath $private -PathType Container)) 'STOP_PRIVATE_ROOT_INVALID'
 $pointer=Join-Path $private ('received-session-'+$day+'.active.json')
 $body=Get-Content -LiteralPath (LocalFile $pointer 'RUN_POINTER') -Raw -Encoding UTF8|ConvertFrom-Json
 $run=[IO.Path]::GetFullPath([string]$body.runRoot)
 Need ($body.schemaId -ceq 'ARK_NO11_RECEIVED_ACTIVE_RUN_V1' -and
       $body.sessionDate -ceq $day -and
       $run.StartsWith(($private+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase) -and
       (Test-Path -LiteralPath $run -PathType Container)) 'STOP_RUN_IDENTITY_INVALID'
 $attempts=@(Get-ChildItem -LiteralPath $run -Directory -Filter 'attempt-*'|Sort-Object Name)
 Need ($attempts.Count -gt 0) 'STOP_ACTIVE_COLLECTOR_NOT_FOUND'
 $folder=$attempts[$attempts.Count-1].FullName
 $attempt=Get-Content -LiteralPath (LocalFile (Join-Path $folder 'attempt.json') 'ATTEMPT') -Raw -Encoding UTF8|ConvertFrom-Json
 $ready=Get-Content -LiteralPath (LocalFile (Join-Path $folder 'collector-ready.json') 'READY_MARKER') -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($attempt.status -ceq 'CONNECTED' -and $attempt.sessionDate -ceq $day -and
       $ready.schemaId -ceq 'ARK_NO11_C50_COLLECTOR_READY_V1' -and
       $ready.sessionDate -ceq $day -and
       $ready.processId -eq $attempt.pid) 'STOP_RUNNING_COLLECTOR_NOT_PROVEN'
 $stop=Join-Path $folder 'collector.stop'
 Need (-not (Test-Path -LiteralPath $stop)) 'STOP_ALREADY_REQUESTED'
 $data=[Text.UTF8Encoding]::new($false).GetBytes('STOP_NEW_ENTRIES_REQUESTED'+[char]10)
 $out=[IO.File]::Open($stop,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$out.Write($data,0,$data.Length);$out.Flush($true)}
 finally{$out.Dispose()}
 Write-Host 'NO11_UNIFIED_ENGINE_STOP=REQUESTED_NOT_ACKNOWLEDGED'
 Write-Host 'NO11_UNIFIED_BROKER_ORDER_CANCELLED=False'
 Write-Host 'NO11_UNIFIED_MANUAL_OPEN_ORDERS_AND_HOLDINGS_CHECK_REQUIRED=True'
}
function Describe($cfg){
 $now=Clock
 $day=$now.ToString('yyyy-MM-dd')
 $config='UNSET'
 if($cfg.bootstrapConfigFile -and (Test-Path -LiteralPath $cfg.bootstrapConfigFile -PathType Leaf)){
  try{
   $obj=Get-Content -LiteralPath $cfg.bootstrapConfigFile -Raw -Encoding UTF8|ConvertFrom-Json
   $config=if($obj.sessionDate -ceq $day){'CURRENT_DAY'}else{'WRONG_SESSION_DATE'}
  }catch{$config='INVALID'}
 }
 $excelCount=@(Get-Process EXCEL -ErrorAction SilentlyContinue).Count
 return ('JST='+$now.ToString('yyyy-MM-dd HH:mm')+
   ' | EXCEL='+$excelCount+' | LIVE_CONFIG='+$config+
   ' | NORMAL_MAX3 | OPENING_EXCEL_ALONE_NEVER_AUTHORIZES_ORDERS')
}
if($OfflineSelfTest){
 Need ((NewSettings).normalMaxPositions -eq 3 -and
       (NewSettings).automaticOrderAuthorization -eq $false -and
       (Test-Path -LiteralPath $trade -PathType Leaf) -and
       (Test-Path -LiteralPath $weekly -PathType Leaf)) 'OFFLINE_CONTRACT'
 Write-Host 'NO11_UNIFIED_OFFLINE_SELFTEST=PASS_NO_EXCEL_NO_RSS_NO_ORDERS'
 Write-Host 'NO11_UNIFIED_NORMAL_FULL_MAX3_SAME_DAY_CONFIRMATION_REQUIRED=True'
 Write-Host 'NO11_UNIFIED_WEEKEND_PRIOR_FRIDAY_RSS_OPTION=True'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 $cfg=Settings
 if($Mode -eq 'Status'){
  Write-Host (Describe $cfg)
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 if($Mode -eq 'Trade'){
  RunTrade $cfg ([bool]$IApproveOrdersForToday)
  exit 0
 }
 if($Mode -eq 'Weekly'){
  RunWeekly $cfg
  exit 0
 }
 if($Mode -eq 'Stop'){
  StopRunningEngine $cfg ([bool]$IUnderstandStopDoesNotCancelOrders)
  exit 0
 }
 Add-Type -AssemblyName System.Windows.Forms
 Add-Type -AssemblyName System.Drawing
 [System.Windows.Forms.Application]::EnableVisualStyles()
 $form=New-Object System.Windows.Forms.Form
 $form.Text='Ark Terminal No.1.1 - Unified Launcher'
 $form.Size=New-Object System.Drawing.Size(730,430)
 $form.StartPosition='CenterScreen'
 $form.MaximizeBox=$false
 $form.FormBorderStyle='FixedDialog'
 $header=New-Object System.Windows.Forms.Label
 $header.Text='ARK TERMINAL   |   NORMAL MAX3 CASH LONG'
 $header.Location=New-Object System.Drawing.Point(18,18)
 $header.Size=New-Object System.Drawing.Size(685,40)
 $header.Font=New-Object System.Drawing.Font('Segoe UI',15,[System.Drawing.FontStyle]::Bold)
 $form.Controls.Add($header)
 $status=New-Object System.Windows.Forms.Label
 $status.Text=Describe $cfg
 $status.Location=New-Object System.Drawing.Point(18,68)
 $status.Size=New-Object System.Drawing.Size(675,65)
 $form.Controls.Add($status)
 $errorDialog={
  param([string]$reason)
  $status.Text='BLOCKED: '+$reason
  [System.Windows.Forms.MessageBox]::Show($reason,'Ark Terminal',
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Warning)|Out-Null
 }
 $normal=New-Object System.Windows.Forms.Button
 $normal.Text='START NORMAL MAX3 TRADING'
 $normal.Location=New-Object System.Drawing.Point(18,145)
 $normal.Size=New-Object System.Drawing.Size(330,58)
 $normal.Add_Click({
  try{
   $yes=[System.Windows.Forms.MessageBox]::Show(
    'Authorize actual broker cash LONG orders for TODAY ONLY, subject to verified funds, frozen rules and workbook guard? This does not guarantee an entry or EXIT.',
    'ARK REAL BROKER ORDERS',
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Warning)
   if($yes -eq [System.Windows.Forms.DialogResult]::Yes){
    RunTrade $cfg $true
    $status.Text='LIVE ENGINE START REQUESTED. Check private logs; an order/fill is NOT confirmed.'
   }
  }catch{& $errorDialog $_.Exception.Message}
 })
 $form.Controls.Add($normal)
 $week=New-Object System.Windows.Forms.Button
 $week.Text='WEEKLY / AFTER-CLOSE RSS UPDATE'
 $week.Location=New-Object System.Drawing.Point(366,145)
 $week.Size=New-Object System.Drawing.Size(330,58)
 $week.Add_Click({
  try{
   RunWeekly $cfg
   $status.Text='RSS DATA UPDATE START REQUESTED. Progress is in local logs; no orders.'
  }catch{& $errorDialog $_.Exception.Message}
 })
 $form.Controls.Add($week)
 $settings=New-Object System.Windows.Forms.Button
 $settings.Text='EDIT LOCAL PATH SETTINGS'
 $settings.Location=New-Object System.Drawing.Point(18,220)
 $settings.Size=New-Object System.Drawing.Size(330,55)
 $settings.Add_Click({
  Start-Process -FilePath notepad.exe -ArgumentList (SafeArg $settingsFile)
 })
 $form.Controls.Add($settings)
 $refresh=New-Object System.Windows.Forms.Button
 $refresh.Text='REFRESH STATUS / OPEN LOGS'
 $refresh.Location=New-Object System.Drawing.Point(366,220)
 $refresh.Size=New-Object System.Drawing.Size(330,55)
 $refresh.Add_Click({
  try{
   $cfg=Settings
   $status.Text=Describe $cfg
   $logs=Join-Path $store 'logs'
   [void][IO.Directory]::CreateDirectory($logs)
   Start-Process -FilePath explorer.exe -ArgumentList (SafeArg $logs)
  }catch{& $errorDialog $_.Exception.Message}
 })
 $form.Controls.Add($refresh)
 $stopBtn=New-Object System.Windows.Forms.Button
 $stopBtn.Text='STOP ENGINE (NOT BROKER ORDERS)'
 $stopBtn.Location=New-Object System.Drawing.Point(18,287)
 $stopBtn.Size=New-Object System.Drawing.Size(678,44)
 $stopBtn.Add_Click({
  $yes=[System.Windows.Forms.MessageBox]::Show(
    'Stopping Ark does NOT cancel open broker orders or sell holdings. Manually check/cancel/sell via MarketSpeed II. Request an engine stop now?',
    'ARK: STOP IS NOT CANCEL',
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Warning)
  if($yes -eq [System.Windows.Forms.DialogResult]::Yes){
   try{StopRunningEngine $cfg $true; $status.Text='Engine stop REQUESTED. Check broker orders and holdings manually.'}
   catch{& $errorDialog $_.Exception.Message}
  }
 })
 $form.Controls.Add($stopBtn)
 $notice=New-Object System.Windows.Forms.Label
 $notice.Text='Weekend: actual Friday source only, RSS connection required. Engine STOP does not automatically cancel existing broker orders.'
 $notice.Location=New-Object System.Drawing.Point(18,348)
 $notice.Size=New-Object System.Drawing.Size(675,42)
 $form.Controls.Add($notice)
 [void]$form.ShowDialog()
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_UNIFIED_[A-Z0-9_]+$'){$reason='NO11_UNIFIED_LOCAL_RUNTIME_OR_SETTINGS_BLOCKED'}
 Write-Host ('NO11_UNIFIED=BLOCKED|'+$reason)
 Write-Host 'NO11_UNIFIED_AUTOMATIC_ORDER_APPROVAL=False'
 exit 2
}