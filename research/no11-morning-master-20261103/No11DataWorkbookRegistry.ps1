# DATA-only workbook registration and resolver. No Excel workbook writes.
# No order, live transport, Trade configuration or worksheet cell value access.
param([switch]$Discover,[string]$OutputFile)
Set-StrictMode -Version Latest

function Assert-No11DataBook([bool]$Ok,[string]$Reason){
 if(-not $Ok){throw ('NO11_DATA_BOOK_'+$Reason)}
}
function Get-No11DataBookRoles {
 return [ordered]@{Account='ARK_ACCOUNT_READONLY';Market='ARK_MARKET_READONLY';OrderIds='ARK_ORDER_IDS_READONLY'}
}
function Get-No11DataBookInventory($Excel){
 $count=[int]$Excel.Workbooks.Count
 Assert-No11DataBook ($count -eq 3) 'EXPECTED_THREE_REGISTERED_BOOKS'
 $roles=Get-No11DataBookRoles
 $rows=@()
 # Index explicitly; COM enumeration must not depend on an array unroller.
 for($i=1;$i -le $count;$i++){
  $book=$Excel.Workbooks.Item($i)
  Assert-No11DataBook (-not [string]::IsNullOrWhiteSpace([string]$book.Path)) 'UNSAVED_BOOK'
  Assert-No11DataBook ([int]$book.Worksheets.Count -eq 1) 'SHEET_COUNT'
  Assert-No11DataBook (-not [bool]$book.Date1904) 'DATE1904'
  $sheet=[string]$book.Worksheets.Item(1).Name
  $role=@($roles.Keys|Where-Object {$roles[$_] -ceq $sheet})
  Assert-No11DataBook ($role.Count -eq 1) 'UNKNOWN_SHEET_ROLE'
  $full=[string]$book.FullName
  Assert-No11DataBook ([IO.Path]::IsPathRooted($full)) 'PATH_NOT_LOCAL_ABSOLUTE'
  $full=[IO.Path]::GetFullPath($full)
  Assert-No11DataBook ([IO.Path]::GetFileName($full).Equals([string]$book.Name,[StringComparison]::OrdinalIgnoreCase)) 'NAME_PATH_DISAGREE'
  Assert-No11DataBook ([IO.Path]::GetExtension($full).ToLowerInvariant() -in @('.xlsx','.xlsb','.xlsm')) 'UNSUPPORTED_WORKBOOK_FORMAT'
  Assert-No11DataBook (Test-Path -LiteralPath $full -PathType Leaf) 'SAVED_FILE_NOT_FOUND'
  $rows+=@([pscustomobject]@{role=[string]$role[0];sheet=$sheet;path=$full;name=[string]$book.Name;date1904=$false;Book=$book})
 }
 foreach($role in $roles.Keys){Assert-No11DataBook (@($rows|Where-Object {$_.role -ceq $role}).Count -eq 1) 'ROLE_NOT_UNIQUE'}
 Assert-No11DataBook (@($rows|ForEach-Object {$_.path.ToLowerInvariant()}|Select-Object -Unique).Count -eq 3) 'PATH_NOT_UNIQUE'
 return $rows
}
function Resolve-No11DataBooks($Excel,$Registration){
 Assert-No11DataBook ($Registration.schemaId -ceq 'ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1' -and
   $Registration.orderTransmission -eq $false -and @($Registration.books).Count -eq 3) 'REGISTRATION_CONTRACT'
 $rows=@(Get-No11DataBookInventory $Excel)
 $roles=Get-No11DataBookRoles
 $found=@{}
 foreach($role in $roles.Keys){
  $expected=@($Registration.books|Where-Object {$_.role -ceq $role})
  Assert-No11DataBook ($expected.Count -eq 1) 'REGISTERED_ROLE_NOT_UNIQUE'
  Assert-No11DataBook ($expected[0].sheet -ceq $roles[$role] -and $expected[0].date1904 -eq $false) 'REGISTERED_SHEET'
  $actual=@($rows|Where-Object {$_.role -ceq $role})[0]
  $path=[IO.Path]::GetFullPath([string]$expected[0].path)
  Assert-No11DataBook ($actual.path.Equals($path,[StringComparison]::OrdinalIgnoreCase)) ('REGISTERED_PATH_MISMATCH_'+$role.ToUpperInvariant())
  $found[$role]=$actual.Book
 }
 return [pscustomobject]@{Account=$found['Account'];Market=$found['Market'];OrderIds=$found['OrderIds'];Originals=@($found['Account'],$found['Market'],$found['OrderIds']);OriginalCount=3}
}
function Get-No11RegisteredDataBooks($Excel){
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $binding=Get-Content -LiteralPath (Join-Path $store 'automatic-inputs.json') -Raw -Encoding UTF8|ConvertFrom-Json
 Assert-No11DataBook ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and $binding.orderTransmission -eq $false) 'DATA_BINDING'
 $path=[string]$binding.dataWorkbookRegistration
 Assert-No11DataBook ([IO.Path]::IsPathRooted($path) -and (Test-Path -LiteralPath $path -PathType Leaf)) 'REGISTRATION_MISSING'
 $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
 Assert-No11DataBook ($hash -ceq [string]$binding.dataWorkbookRegistrationSha256) 'REGISTRATION_HASH'
 $record=Get-Content -LiteralPath $path -Raw -Encoding UTF8|ConvertFrom-Json
 return (Resolve-No11DataBooks $Excel $record)
}
function Export-No11OpenDataBooks([string]$Destination){
 Assert-No11DataBook ([IO.Path]::IsPathRooted($Destination) -and -not (Test-Path -LiteralPath $Destination)) 'PROBE_OUTPUT_MUST_BE_NEW'
 $visible=@(Get-Process EXCEL -ErrorAction SilentlyContinue|Where-Object {$_.MainWindowHandle -ne [IntPtr]::Zero})
 $named=@($visible|Where-Object {$_.MainWindowTitle -like 'Ark_No11_*'})
 $chosen=@()
 if($named.Count -eq 1){$chosen=@($named)}elseif($named.Count -eq 0 -and $visible.Count -eq 1){$chosen=@($visible)}
 Assert-No11DataBook ($chosen.Count -eq 1) 'EXCEL_NOT_UNIQUE'
 if(-not ('No11DataBookWindowV1' -as [type])){
  Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class No11DataBookWindowV1 {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,Callback cb,IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h,StringBuilder b,int n);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);
 [DllImport("oleacc.dll")] public static extern int AccessibleObjectFromWindow(IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object o);
}
'@ -ErrorAction Stop
 }
 $script:no11DataBookWindows=@()
 $callback=[No11DataBookWindowV1+Callback]{param($h,$p)
  $name=New-Object Text.StringBuilder 128
  [void][No11DataBookWindowV1]::GetClassName($h,$name,128)
  if($name.ToString() -ceq 'EXCEL7'){$script:no11DataBookWindows+=@($h)}
  return $true
 }
 [void][No11DataBookWindowV1]::EnumChildWindows($chosen[0].MainWindowHandle,$callback,[IntPtr]::Zero)
 Assert-No11DataBook ($script:no11DataBookWindows.Count -eq 1) 'EXCEL7_NOT_UNIQUE'
 $obj=$null;$excel=$null
 try{
  $iid=[guid]'00020400-0000-0000-C000-000000000046'
  $hr=[No11DataBookWindowV1]::AccessibleObjectFromWindow($script:no11DataBookWindows[0],[uint32]4294967280,[ref]$iid,[ref]$obj)
  Assert-No11DataBook ($hr -eq 0 -and $null -ne $obj) 'COM_ATTACH'
  $excel=$obj.Application
  $processId=[uint32]0
  [void][No11DataBookWindowV1]::GetWindowThreadProcessId([IntPtr]$excel.Hwnd,[ref]$processId)
  Assert-No11DataBook ($processId -eq [uint32]$chosen[0].Id) 'EXCEL_PID_DISAGREES'
  $rows=@(Get-No11DataBookInventory $excel)
  $books=@($rows|ForEach-Object {[ordered]@{role=$_.role;path=$_.path;name=$_.name;sheet=$_.sheet;date1904=$false}})
  $record=[ordered]@{schemaId='ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1';books=$books;orderTransmission=$false}
  $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $record -Depth 6 -Compress)+[char]10)
  $stream=[IO.File]::Open($Destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
  foreach($row in $rows){Write-Host ('NO11_DATA_BOOK_DISCOVERED='+$row.role+'|'+$row.name)}
  Write-Host 'WORKBOOKS_MODIFIED=False'
 }finally{
  if($null -ne $excel -and [Runtime.InteropServices.Marshal]::IsComObject($excel)){[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}
  if($null -ne $obj -and [Runtime.InteropServices.Marshal]::IsComObject($obj)){[void][Runtime.InteropServices.Marshal]::ReleaseComObject($obj)}
 }
}
if($Discover){
 $ErrorActionPreference='Stop'
 Export-No11OpenDataBooks $OutputFile
}
