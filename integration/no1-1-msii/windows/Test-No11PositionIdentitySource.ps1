# Ark No.1.1 MSII RSS position-symbol read-only probe.
# Uses an unsaved temporary Excel workbook with only =RssPositionList().
# Never alters existing Ark workbooks, registers XLL, or invokes RSS orders.
param(
    [string]$WorkbookPath = "C:\Ark\Ark_No11_RSS_ReadOnly.xlsx",
    [ValidateRange(1,15)][int]$WaitSeconds = 4
)
$ErrorActionPreference = "Stop"

$excel = [Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
$fullPath = [IO.Path]::GetFullPath($WorkbookPath)
$books = @($excel.Workbooks | Where-Object {
    [string]::Equals([IO.Path]::GetFullPath([string]$_.FullName),
        $fullPath,[StringComparison]::OrdinalIgnoreCase)
})
if ($books.Count -ne 1) { throw "NO11_ORIGINAL_READ_ONLY_WORKBOOK_NOT_OPEN" }
$original = $books[0]
$account = $original.Worksheets.Item("ARK_ACCOUNT_READONLY")
$positionFormula = [string]$account.Range("AL1").Formula
if (($positionFormula -replace "^=@", "=") -ne "=RssPositionList(AL2:AU2)") {
    throw "NO11_ORIGINAL_POSITION_FORMULA_UNEXPECTED"
}
if ([string]$account.Range("AL2").Value2 -ne "銘柄コード") {
    throw "NO11_ORIGINAL_POSITION_HEADER_UNEXPECTED"
}
$sourceSymbol = ([string]$account.Range("AL3").Value2).Trim()
$sourceName = ([string]$account.Range("AM3").Value2).Trim()
$sourceAccount = ([string]$account.Range("AN3").Value2).Trim()
$sourceQuantity = $account.Range("AO3").Value2
if ([string]::IsNullOrWhiteSpace($sourceName) -or $null -eq $sourceQuantity) {
    throw "NO11_ORIGINAL_ROW_NOT_COMPARABLE"
}

Write-Host ("ORIGINAL_SYMBOL_PRESENT={0}" -f (-not [string]::IsNullOrWhiteSpace($sourceSymbol)))
Write-Host ("ORIGINAL_ROW_COMPLETE={0}" -f ($null -ne $sourceQuantity -and $sourceName.Length -gt 0))
Write-Host "TEMP_PROBE_MODE=UNSAVED_READ_ONLY_RSS_FUNCTION"
$tempBook = $null
try {
    # Create a new, unsaved, one-sheet workbook in the same Excel instance.
    # This never opens, edits or saves the existing source workbook.
    $tempBook = $excel.Workbooks.Add(-4167)
    $tempSheet = $tempBook.Worksheets.Item(1)
    $tempSheet.Range("A1").Formula = "=RssPositionList()"
    try { $tempSheet.Calculate() } catch { }
    Start-Sleep -Seconds $WaitSeconds

    $expected = @("銘柄コード","銘柄名称","口座区分","保有数量")
    $headerMatches = $true
    for ($col=1; $col -le 4; $col++) {
        if ([string]$tempSheet.Cells.Item(2,$col).Value2 -ne $expected[$col-1]) {
            $headerMatches = $false
        }
    }
    $tempSymbol = ([string]$tempSheet.Range("A3").Value2).Trim()
    $tempName = ([string]$tempSheet.Range("B3").Value2).Trim()
    $tempAccount = ([string]$tempSheet.Range("C3").Value2).Trim()
    $tempQty = $tempSheet.Range("D3").Value2
    $identityValid = $tempSymbol -match '^[0-9A-Z]{4,5}$'
    $metadataMatch = $tempName -ceq $sourceName -and
        $tempAccount -ceq $sourceAccount -and
        $null -ne $tempQty -and
        [string]$tempQty -ceq [string]$sourceQuantity

    Write-Host ("DEFAULT_HEADERS_MATCH={0}" -f $headerMatches)
    Write-Host ("DEFAULT_SYMBOL_VALID={0}" -f [bool]$identityValid)
    Write-Host ("SAME_HOLDING_NAME_ACCOUNT_QUANTITY={0}" -f [bool]$metadataMatch)
    if (-not $headerMatches) {
        Write-Host "PROBE_RESULT=DEFAULT_HEADER_LAYOUT_UNKNOWN"
    } elseif ($identityValid -and $metadataMatch) {
        Write-Host "PROBE_RESULT=DEFAULT_RSS_HEADER_IDENTIFIES_HOLDING"
    } else {
        Write-Host "PROBE_RESULT=BROKER_POSITION_SYMBOL_STILL_UNRESOLVED"
    }
    Write-Host "EXCEL_ORDER_WRITE=FALSE"
    Write-Host "RSS_ORDER_CALL=FALSE"
    Write-Host "TRANSMITTED=FALSE"
} finally {
    if ($null -ne $tempBook) {
        try { $tempBook.Close($false) } catch {
            Write-Host "WARNING_TEMP_PROBE_WORKBOOK_CLOSE_FAILED"
        }
    }
}
