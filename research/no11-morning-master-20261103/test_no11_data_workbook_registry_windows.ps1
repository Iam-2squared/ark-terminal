# No Excel process or workbook opened. Real PS 5.1 resolver runs on mock COM objects.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'No11DataWorkbookRegistry.ps1')
function Check([bool]$Ok,[string]$Why){if(-not $Ok){throw ('REGISTRY_TEST_'+$Why)}}
class No11BookCollectionFixture {
 [object[]]$Rows
 [int]$Count
 No11BookCollectionFixture([object[]]$rows){$this.Rows=$rows;$this.Count=$rows.Count}
 [object] Item([object]$index){
  if($index -is [int]){return $this.Rows[[int]$index-1]}
  foreach($row in $this.Rows){if($row.Name -ceq [string]$index){return $row}}
  throw 'UNEXPECTED_NAME_LOOKUP'
 }
}
function Make-Book([string]$File,[string]$Sheet){
 [IO.File]::WriteAllText($File,'NOT A SPREADSHEET; OFFLINE TEST FIXTURE')
 return [pscustomobject]@{Name=[IO.Path]::GetFileName($File);Path=[IO.Path]::GetDirectoryName($File);FullName=$File;Date1904=$false;
  Worksheets=[No11BookCollectionFixture]::new(@([pscustomobject]@{Name=$Sheet}))}
}
function Expect-Error([scriptblock]$Action,[string]$Reason){
 $ok=$false
 try{& $Action|Out-Null}catch{$ok=$_.Exception.Message -match [regex]::Escape($Reason)}
 Check $ok ('EXPECTED_'+$Reason)
}
$dir=Join-Path $env:TEMP ('ark-registry-test-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($dir)
try{
 $books=@(
  (Make-Book (Join-Path $dir 'Ark_No11_MSII_RSS (version 1).xlsb') 'ARK_ACCOUNT_READONLY'),
  (Make-Book (Join-Path $dir 'Ark_No11_MARKET_RSS (version 1).xlsb') 'ARK_MARKET_READONLY'),
  (Make-Book (Join-Path $dir 'Ark_No11_BROKER_READONLY (version 1).xlsb') 'ARK_ORDER_IDS_READONLY')
 )
 $excel=[pscustomobject]@{Workbooks=[No11BookCollectionFixture]::new($books)}
 $rows=@(Get-No11DataBookInventory $excel)
 Check ($rows.Count -eq 3) 'INVENTORY_COUNT'
 $registration=[pscustomobject]@{schemaId='ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1';orderTransmission=$false;
  books=@($rows|ForEach-Object {[pscustomobject]@{role=$_.role;sheet=$_.sheet;path=$_.path;name=$_.name;date1904=$false}})}
 $resolved=Resolve-No11DataBooks $excel $registration
 Check ($resolved.Account.Name -ceq $books[0].Name -and $resolved.Market.Name -ceq $books[1].Name -and $resolved.OrderIds.Name -ceq $books[2].Name) 'EXACT_USER_XLSB_ROLES'
 Check ($resolved.Originals.Count -eq 3 -and $resolved.OriginalCount -eq 3) 'ALL_ORIGINALS_FOR_CAPACITY'
 # Reordering tabs/books does not change identities.
 $excel.Workbooks=[No11BookCollectionFixture]::new(@($books[2],$books[0],$books[1]))
 $reordered=Resolve-No11DataBooks $excel $registration
 Check ($reordered.Account.Name -ceq $books[0].Name) 'REORDERED_BOOKS'
 $excel.Workbooks=[No11BookCollectionFixture]::new($books)
 # Old .xlsx configuration must fail, not silently bind a similarly named book.
 $expected=$registration.books[2].path
 $registration.books[2].path=Join-Path $dir 'Ark_No11_BROKER_READONLY.xlsx'
 Expect-Error {Resolve-No11DataBooks $excel $registration} 'REGISTERED_PATH_MISMATCH_ORDERIDS'
 $registration.books[2].path=$expected
 # A fourth original or duplicate/foreign role is not admitted.
 $excel.Workbooks=[No11BookCollectionFixture]::new(@($books[0],$books[1],$books[2],$books[2]))
 Expect-Error {Get-No11DataBookInventory $excel} 'EXPECTED_THREE_REGISTERED_BOOKS'
 $excel.Workbooks=[No11BookCollectionFixture]::new($books)
 $books[2].Worksheets=[No11BookCollectionFixture]::new(@([pscustomobject]@{Name='ARK_ACCOUNT_READONLY'}))
 Expect-Error {Get-No11DataBookInventory $excel} 'ROLE_NOT_UNIQUE'
 $books[2].Worksheets=[No11BookCollectionFixture]::new(@([pscustomobject]@{Name='ARK_ORDER_IDS_READONLY'}))
 $books[2].Date1904=$true
 Expect-Error {Get-No11DataBookInventory $excel} 'DATE1904'
 $books[2].Date1904=$false
 $path=$books[1].Path;$books[1].Path=''
 Expect-Error {Get-No11DataBookInventory $excel} 'UNSAVED_BOOK'
 $books[1].Path=$path
 $books[0].Worksheets=[No11BookCollectionFixture]::new(@([pscustomobject]@{Name='ARK_ACCOUNT_READONLY'},[pscustomobject]@{Name='EXTRA'}))
 Expect-Error {Get-No11DataBookInventory $excel} 'SHEET_COUNT'
 $books[0].Worksheets=[No11BookCollectionFixture]::new(@([pscustomobject]@{Name='ARK_ACCOUNT_READONLY'}))
 $final=Resolve-No11DataBooks $excel $registration
 Check ($final.OriginalCount -eq 3) 'RESTORED_FIXTURE'
 foreach($book in $books){Check ([IO.File]::ReadAllText($book.FullName) -ceq 'NOT A SPREADSHEET; OFFLINE TEST FIXTURE') 'FILES_UNCHANGED'}
 Write-Host 'NO11_XLSB_ACTUAL_NAME_REGISTRY_TESTS=PASS'
 Write-Host 'NO11_DATA_BOOK_MISMATCH_TESTS=PASS'
 Write-Host 'EXCEL_STARTED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}finally{Remove-Item -LiteralPath $dir -Recurse -Force}
