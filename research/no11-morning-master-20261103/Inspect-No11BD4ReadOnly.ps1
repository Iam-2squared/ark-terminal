# ARK No.1.1 — 2026-11-10 Excel BD4 error 1004, read-only root-cause probe.
# Verifies original three saved workbooks and reads control cells WITHOUT writes.
# Never changes Excel, sessions, settings, order/EXIT, or stored evidence.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Assert-No11Bd4([bool]$ok,[string]$code){
 if(-not $ok){throw ('NO11_BD4_DIAG_'+$code)}
}
function Get-No11Bd4State($Cell,[string]$Kind){
 $value=$Cell.Value2
 if($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)){return 'EMPTY'}
 if($Kind -eq 'GUARD'){
  if([string]$value -ceq 'ARK_NO11_SEND_ONCE'){return 'ORIGINAL_GUARD'}
  return 'UNKNOWN_GUARD'
 }
 if($Kind -eq 'TRIGGER'){
  if($value -is [ValueType] -and $value -isnot [bool] -and [double]$value -eq 0){return 'ZERO'}
  return 'NONZERO_OR_UNKNOWN'
 }
 if($Kind -eq 'SESSION'){
  if([string]$value -cmatch '^[a-f0-9]{64}$'){return 'SHA256_KEY_PRESENT'}
  return 'UNKNOWN_SESSION'
 }
 return 'OTHER'
}
function SafeFormat($value){
 if($null -eq $value){return 'NULL'}
 $s=[string]$value
 if($s.Length -gt 80){return 'LONG_FORMAT_CODE'}
 if($s -match '[\r\n|=]'){return 'COMPLEX_FORMAT_CODE'}
 if([string]::IsNullOrEmpty($s)){return 'EMPTY'}
 return $s
}
if($OfflineSelfTest){
 $a=[pscustomobject]@{Value2='ARK_NO11_SEND_ONCE'}
 $b=[pscustomobject]@{Value2=[double]0}
 $c=[pscustomobject]@{Value2=('a'*64)}
 Assert-No11Bd4 ((Get-No11Bd4State $a 'GUARD') -ceq 'ORIGINAL_GUARD' -and
     (Get-No11Bd4State $b 'TRIGGER') -ceq 'ZERO' -and
     (Get-No11Bd4State $c 'SESSION') -ceq 'SHA256_KEY_PRESENT') 'OFFLINE_STATE_CLASSIFIER'
 $b.Value2=[double]1
 Assert-No11Bd4 ((Get-No11Bd4State $b 'TRIGGER') -ceq 'NONZERO_OR_UNKNOWN') 'OFFLINE_NONZERO'
 Write-Host 'NO11_BD4_DIAG_SELFTEST=PASS_READ_ONLY'
 Write-Host 'EXCEL_ACCESSED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$excel=$null
try{
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $settingsFile=Join-Path $store 'settings.json'
 Assert-No11Bd4 (Test-Path -LiteralPath $settingsFile -PathType Leaf) 'SETTINGS_MISSING'
 $cfg=Get-Content -LiteralPath $settingsFile -Raw -Encoding UTF8|ConvertFrom-Json
 Assert-No11Bd4 ($cfg.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
     $cfg.normalMaxPositions -eq 3 -and
     $cfg.sameDayApprovalRequired -eq $true -and
     $cfg.automaticOrderAuthorization -eq $false -and
     $cfg.orderTransmission -eq $false) 'SETTINGS_UNSAFE'
 $roles=@(
     @{Name='Account';Key='accountWorkbookPath';Sheet='ARK_ACCOUNT_READONLY'},
     @{Name='Market';Key='marketWorkbookPath';Sheet='ARK_MARKET_READONLY'},
     @{Name='OrderIds';Key='orderIdWorkbookPath';Sheet='ARK_ORDER_IDS_READONLY'}
 )
 $expected=@{}
 foreach($role in $roles){
  $inputPath=[string]$cfg.($role.Key)
  Assert-No11Bd4 ([IO.Path]::IsPathRooted($inputPath) -and
      (Test-Path -LiteralPath $inputPath -PathType Leaf)) 'CONFIGURED_BOOK_MISSING'
  $expected[$role.Name]=[IO.Path]::GetFullPath($inputPath)
 }
 Assert-No11Bd4 (@(Get-Process EXCEL -ErrorAction SilentlyContinue).Count -eq 1) 'EXCEL_PROCESS_NOT_UNIQUE'
 $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
 Assert-No11Bd4 ([int]$excel.Workbooks.Count -eq 3) 'EXPECTED_THREE_OPEN_BOOKS'
 $books=@{}
 for($i=1;$i -le 3;$i++){
  $book=$excel.Workbooks.Item($i)
  $full=[IO.Path]::GetFullPath([string]$book.FullName)
  $matches=@($roles|Where-Object {
    $full.Equals($expected[$_.Name],[StringComparison]::OrdinalIgnoreCase)
  })
  Assert-No11Bd4 ($matches.Count -eq 1) 'EXCEL_PATH_DIFFERENT'
  $role=$matches[0]
  Assert-No11Bd4 (-not $books.ContainsKey($role.Name) -and
      [int]$book.Worksheets.Count -eq 1 -and
      [string]$book.Worksheets.Item(1).Name -ceq $role.Sheet) 'ROLE_OR_SHEET_MISMATCH'
  $books[$role.Name]=$book
 }
 Assert-No11Bd4 ($books.Count -eq 3) 'THREE_ROLES_NOT_UNIQUE'
 $order=$books['OrderIds']
 $sheet=$order.Worksheets.Item('ARK_ORDER_IDS_READONLY')
 $guard=$sheet.Range('BD1')
 $trigger=$sheet.Range('BD2')
 $session=$sheet.Range('BD3')
 $formula=$sheet.Range('BD4')
 Write-Host 'NO11_BD4_DIAG_EXACT_THREE_ORIGINAL_BOOKS=PASS'
 Write-Host ('NO11_BD4_DIAG_BOOK_READONLY='+[bool]$order.ReadOnly)
 Write-Host ('NO11_BD4_DIAG_SHEET_PROTECTED='+[bool]$sheet.ProtectContents)
 Write-Host ('NO11_BD4_DIAG_WORKBOOK_PROTECTED_STRUCTURE='+[bool]$order.ProtectStructure)
 Write-Host ('NO11_BD4_DIAG_BD4_MERGED='+[bool]$formula.MergeCells)
 Write-Host ('NO11_BD4_DIAG_BD4_HAS_ARRAY='+[bool]$formula.HasArray)
 Write-Host ('NO11_BD4_DIAG_BD4_LOCKED='+[bool]$formula.Locked)
 Write-Host ('NO11_BD4_DIAG_BD4_HAS_FORMULA='+[bool]$formula.HasFormula)
 Write-Host ('NO11_BD4_DIAG_BD4_NUMBER_FORMAT='+ (SafeFormat $formula.NumberFormat))
 Write-Host ('NO11_BD4_DIAG_BD4_FORMAT_LOCAL='+ (SafeFormat $formula.NumberFormatLocal))
 Write-Host ('NO11_BD4_DIAG_BD1_STATE='+(Get-No11Bd4State $guard 'GUARD'))
 Write-Host ('NO11_BD4_DIAG_BD2_STATE='+(Get-No11Bd4State $trigger 'TRIGGER'))
 Write-Host ('NO11_BD4_DIAG_BD3_STATE='+(Get-No11Bd4State $session 'SESSION'))
 Write-Host ('NO11_BD4_DIAG_BD4_STYLE='+(SafeFormat ([string]$formula.Style)))
 Write-Host 'NO11_BD4_DIAG_FINISHED=PASS_READ_ONLY'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_BD4_DIAG_[A-Z0-9_]+$'){$reason='NO11_BD4_DIAG_EXCEL_COM_READ_FAILED'}
 Write-Host ('NO11_BD4_DIAG=BLOCKED|'+$reason)
 $err=$_.Exception
 while($null -ne $err.InnerException){$err=$err.InnerException}
 Write-Host ('NO11_BD4_DIAG_EXCEPTION_KIND='+$err.GetType().Name)
 Write-Host ('NO11_BD4_DIAG_HRESULT='+[int]$err.HResult)
 exit 2
}finally{
 if($null -ne $excel -and [Runtime.InteropServices.Marshal]::IsComObject($excel)){
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
 }
 Write-Host 'EXCEL_WORKBOOKS_CHANGED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}
