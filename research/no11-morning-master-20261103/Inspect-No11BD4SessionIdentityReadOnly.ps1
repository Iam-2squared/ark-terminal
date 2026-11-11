# Read-only precision follow-up of original three XLSB BD1/BD2/BD3 and BD4.
# Never changes cells, files, orders, sessions, control state or approval.
# ASCII-only source: Windows PowerShell 5.1 may read BOM-less files as CP932.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){
 if(-not $ok){throw ('NO11_BD4_SESSION_DIAG_'+$code)}
}
function Digest([string]$data){
 $sha=[Security.Cryptography.SHA256]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($data)))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
function CellClass($cell,[string]$expected){
 $raw=$cell.Value2
 $status='UNKNOWN_VALUE_TYPE';$length=0
 if($null -eq $raw){$status='EMPTY'}
 elseif($raw -is [string]){
  $length=$raw.Length
  if([string]::IsNullOrWhiteSpace($raw)){$status='EMPTY_WHITESPACE'}
  elseif($raw -ceq $expected){$status='EXPECTED_EXACT'}
  elseif($raw -cmatch '^[a-f0-9]{64}$'){$status='DIFFERENT_SHA256'}
  else{$status='UNKNOWN_STRING'}
 }elseif($raw -is [ValueType]){$status='NONSTRING_VALUE'}
 return [pscustomobject]@{Status=$status;Length=$length;HasFormula=[bool]$cell.HasFormula}
}
function Get-No11JapaneseGeneralFormat {
 return (-join [char[]]@(0x0047,0x002F,0x6A19,0x6E96))
}
function FormatClass([string]$normal,[string]$localized){
 if($normal -ceq 'General' -and $localized -ceq 'General'){return 'ENGLISH_GENERAL'}
 $japanese=Get-No11JapaneseGeneralFormat
 if($normal -ceq $japanese -and $localized -ceq $japanese){return 'JAPANESE_GENERAL'}
 return 'OTHER_FORMAT'
}
if($OfflineSelfTest){
 $cell=[pscustomobject]@{Value2='ARK_NO11_SEND_ONCE';HasFormula=$false}
 Need ((CellClass $cell 'ARK_NO11_SEND_ONCE').Status -ceq 'EXPECTED_EXACT') 'MOCK_GUARD'
 $cell.Value2='wrong'
 Need ((CellClass $cell 'ARK_NO11_SEND_ONCE').Status -ceq 'UNKNOWN_STRING') 'MOCK_UNKNOWN'
 $japanese=Get-No11JapaneseGeneralFormat
 Need ($japanese.Length -eq 4 -and [int][char]$japanese[2] -eq 0x6A19 -and
       [int][char]$japanese[3] -eq 0x6E96) 'MOCK_UNICODE_FORMAT'
 Need ((FormatClass $japanese $japanese) -ceq 'JAPANESE_GENERAL' -and
       (FormatClass 'General' 'General') -ceq 'ENGLISH_GENERAL' -and
       (FormatClass $japanese 'General') -ceq 'OTHER_FORMAT' -and
       (FormatClass '@' '@') -ceq 'OTHER_FORMAT') 'MOCK_FORMAT'
 Write-Host 'NO11_BD4_SESSION_DIAG_SOURCE_ENCODING=ASCII'
 Write-Host 'NO11_BD4_SESSION_DIAG_SELFTEST=PASS'
 Write-Host 'EXCEL_ACCESSED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$excel=$null
try{
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $cfg=Get-Content -LiteralPath (Join-Path $store 'settings.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $binding=Get-Content -LiteralPath (Join-Path $store 'automatic-inputs.json') -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($cfg.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
    $cfg.sameDayApprovalRequired -eq $true -and $cfg.normalMaxPositions -eq 3 -and
    $cfg.automaticOrderAuthorization -eq $false -and $cfg.orderTransmission -eq $false -and
    $binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
    $binding.orderTransmission -eq $false) 'SAFETY_SETTINGS'
 $roles=@(
  @{Role='Account';Field='accountWorkbookPath';Sheet='ARK_ACCOUNT_READONLY'},
  @{Role='Market';Field='marketWorkbookPath';Sheet='ARK_MARKET_READONLY'},
  @{Role='OrderIds';Field='orderIdWorkbookPath';Sheet='ARK_ORDER_IDS_READONLY'}
 )
 $paths=@{}
 foreach($row in $roles){
  $source=[string]$cfg.($row.Field)
  Need ([IO.Path]::IsPathRooted($source) -and (Test-Path -LiteralPath $source -PathType Leaf)) 'SAVED_BOOK_REQUIRED'
  $paths[$row.Role]=[IO.Path]::GetFullPath($source)
 }
 $processes=@(Get-Process EXCEL -ErrorAction SilentlyContinue)
 Need ($processes.Count -eq 1) 'EXCEL_PID_NOT_UNIQUE'
 $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
 Need ($excel.Workbooks.Count -eq 3) 'EXACT_THREE_BOOKS'
 $found=@{}
 for($i=1;$i -le 3;$i++){
  $book=$excel.Workbooks.Item($i)
  $full=[IO.Path]::GetFullPath([string]$book.FullName)
  $matches=@($roles|Where-Object {
   $full.Equals($paths[$_.Role],[StringComparison]::OrdinalIgnoreCase)
  })
  Need ($matches.Count -eq 1) 'REGISTERED_PATH_DIFFERENT'
  $row=$matches[0]
  Need (-not $found.ContainsKey($row.Role) -and
        $book.Worksheets.Count -eq 1 -and
        [string]$book.Worksheets.Item(1).Name -ceq $row.Sheet) 'SHEET_IDENTITY'
  $found[$row.Role]=$book
 }
 Need ($found.Count -eq 3) 'BOOK_ROLES'
 if(-not ('No11BD4SessionPid' -as [type])){
  Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class No11BD4SessionPid {
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint pid);
}
'@ -ErrorAction Stop
 }
 [uint32]$winPid=0
 [void][No11BD4SessionPid]::GetWindowThreadProcessId([IntPtr]([long]$excel.Hwnd),[ref]$winPid)
 Need ($winPid -gt 0 -and $winPid -eq [uint32]$processes[0].Id) 'EXCEL_PID_DISAGREES'
 # Same deterministic session formula as frozen New-No11ExcelSession helper.
 $started=$processes[0].StartTime.ToUniversalTime().ToString('o')
 $aHash=Digest ($paths['Account'].ToLowerInvariant())
 $oHash=Digest ($paths['OrderIds'].ToLowerInvariant())
 $key=Digest ((@([string]$winPid,$started,$aHash,$oHash)) -join [string][char]10)
 $sheet=$found['OrderIds'].Worksheets.Item('ARK_ORDER_IDS_READONLY')
 $b1=CellClass ($sheet.Range('BD1')) 'ARK_NO11_SEND_ONCE'
 $b3=CellClass ($sheet.Range('BD3')) $key
 $trigger=$sheet.Range('BD2').Value2
 $tStatus='UNKNOWN_OR_NONZERO'
 if($null -eq $trigger){$tStatus='EMPTY'}
 elseif($trigger -is [ValueType] -and $trigger -isnot [bool] -and [double]$trigger -eq 0){$tStatus='ZERO'}
 $b4=$sheet.Range('BD4')
 $format=FormatClass ([string]$b4.NumberFormat) ([string]$b4.NumberFormatLocal)
 Write-Host 'NO11_BD4_SESSION_DIAG_EXACT_THREE_BOOKS=PASS'
 Write-Host ('NO11_BD4_SESSION_DIAG_EXCEL_PID='+[int]$winPid)
 Write-Host ('NO11_BD4_SESSION_DIAG_BD1='+$b1.Status)
 Write-Host ('NO11_BD4_SESSION_DIAG_BD1_LENGTH='+$b1.Length)
 Write-Host ('NO11_BD4_SESSION_DIAG_BD1_HAS_FORMULA='+$b1.HasFormula)
 Write-Host ('NO11_BD4_SESSION_DIAG_BD2='+$tStatus)
 Write-Host ('NO11_BD4_SESSION_DIAG_BD3='+$b3.Status)
 Write-Host ('NO11_BD4_SESSION_DIAG_BD3_LENGTH='+$b3.Length)
 Write-Host ('NO11_BD4_SESSION_DIAG_BD3_HAS_FORMULA='+$b3.HasFormula)
 Write-Host ('NO11_BD4_SESSION_DIAG_BD4_FORMAT='+$format)
 $proved=$b1.Status -in @('EMPTY','EMPTY_WHITESPACE','EXPECTED_EXACT') -and
         $b3.Status -in @('EMPTY','EMPTY_WHITESPACE','EXPECTED_EXACT') -and
         -not $b1.HasFormula -and -not $b3.HasFormula -and
         $tStatus -eq 'ZERO' -and $format -in @('ENGLISH_GENERAL','JAPANESE_GENERAL')
 Write-Host ('NO11_BD4_SESSION_DIAG_SCOPE_PROVEN='+[bool]$proved)
 Write-Host 'NO11_BD4_SESSION_DIAG_TRADING_AUTHORIZED=False'
 Write-Host 'NO11_BD4_SESSION_DIAG=PASS_READ_ONLY'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_BD4_SESSION_DIAG_[A-Z0-9_]+$'){$reason='NO11_BD4_SESSION_DIAG_COM_OR_RUNTIME_UNVERIFIED'}
 Write-Host ('NO11_BD4_SESSION_DIAG=BLOCKED|'+$reason)
 exit 2
}finally{
 if($null -ne $excel -and [Runtime.InteropServices.Marshal]::IsComObject($excel)){
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
 }
 Write-Host 'WORKBOOKS_MODIFIED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}
