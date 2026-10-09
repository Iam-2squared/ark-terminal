# Ark Integrated No.1.1 - create/diagnose a NEW, read-only MSII RSS Workbook.
# No RegisterXLL, no RSS order/cancel/modify functions, no old Workbook changes.
param(
    [ValidateSet("Create","Diagnose")][string]$Mode = "Create",
    [string]$WorkbookPath = "C:\Ark\Ark_No11_RSS_DefaultHeaders_v2.xlsx",
    [string]$ReportPath = (Join-Path $env:LOCALAPPDATA "ArkTerminal\No11\workbook-diagnostic.json"),
    [ValidateRange(0,30)][int]$ObserveSeconds = 3
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$expectedHeaders = [ordered]@{
    L2 = "現物買付可能額"
    N2 = "注文番号"; O2 = "通常注文状況"; P2 = "銘柄コード"
    Q2 = "銘柄名称"; R2 = "口座区分"; S2 = "売買"; T2 = "取引"
    U2 = "執行条件"; V2 = "注文数量"; W2 = "約定数量"
    AA2 = "約定日"; AB2 = "銘柄コード"; AC2 = "銘柄名称"
    AD2 = "口座区分"; AE2 = "市場名称"; AF2 = "取引"
    AG2 = "売買"; AH2 = "約定数量"; AI2 = "約定単価"
    AL2 = "銘柄コード"; AM2 = "銘柄名称"; AN2 = "口座区分"
    AO2 = "保有数量"; AP2 = "発注数量"; AQ2 = "平均取得価額"
    AR2 = "時価"; AS2 = "前日比"; AT2 = "前日比率"
    AU2 = "時価評価額"; AV2 = "評価損益額"; AW2 = "評価損益率"
    AX2 = "銘柄情報等"; AY2 = "JAX時価"; AZ2 = "JNX時価"
    BA2 = "PER"; BB2 = "PBR"; BC2 = "配当利回り"
}
$expectedFormulas = [ordered]@{
    L1  = "=RssCapacityList(L2:L2)"
    N1  = "=RssOrderList(N2:W2,0,1)"
    AA1 = "=RssExecutionList(AA2:AI2,1)"
    AL1 = "=RssPositionList()"
}
$expectedStates = [ordered]@{
    L1  = "完了"
    N1  = "配信中"
    AA1 = "配信中"
    AL1 = "配信中"
}

function Get-No11Excel {
    param([bool]$MayStart)
    try {
        return [Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
    } catch {
        if (-not $MayStart) { throw "EXCEL_NOT_RUNNING" }
        $created = New-Object -ComObject Excel.Application
        $created.Visible = $true
        return $created
    }
}
function Resolve-No11Workbook {
    param($Excel, [string]$FullPath)
    $matches = @($Excel.Workbooks | Where-Object {
        [string]::Equals([IO.Path]::GetFullPath([string]$_.FullName),
            $FullPath, [StringComparison]::OrdinalIgnoreCase)
    })
    if ($matches.Count -gt 1) { throw "NO11_DUPLICATE_WORKBOOK_OPEN" }
    if ($matches.Count -eq 1) { return $matches[0] }
    if (-not (Test-Path -LiteralPath $FullPath -PathType Leaf)) {
        throw "NO11_WORKBOOK_MISSING"
    }
    # Only open the new, isolated Workbook in READ ONLY mode.
    $opened = $Excel.Workbooks.Open($FullPath,0,$true)
    if ($null -eq $opened) { throw "NO11_WORKBOOK_READ_ONLY_OPEN_FAILED" }
    return $opened
}
function Assert-No11Layout {
    param($Sheet)
    foreach ($address in $expectedFormulas.Keys) {
        $cell = $Sheet.Range($address)
        if ($cell.HasFormula -ne $true) {
            throw ("NO11_RSS_FORMULA_STORED_AS_TEXT_OR_MISSING:{0}" -f $address)
        }
        $actual = ([string]$cell.Formula) -replace "^=@", "="
        if ($actual -ne $expectedFormulas[$address]) {
            if ($address -eq "AL1") {
                # On a real Excel installation, Formula readback may differ
                # from the requested formula. This is DIAGNOSTIC ONLY.
                # Never relax the safety gate or print any broker cell values.
                $raw = [string]$cell.Formula
                $redact = '(?i)\b(?=[0-9A-Z]{4,5}\b)(?=[0-9A-Z]*[0-9])[0-9A-Z]{4,5}\b'
                $safe = [Regex]::Replace($raw, $redact, '[REDACTED]')
                if ($safe.Length -gt 256) {
                    $safe = $safe.Substring(0,256) + '...[TRUNCATED]'
                }
                Write-Host ("NO11_AL1_FORMULA_HAS_FORMULA={0}" -f [bool]$cell.HasFormula)
                Write-Host ("NO11_AL1_FORMULA_RAW_LENGTH={0}" -f $raw.Length)
                Write-Host ("NO11_AL1_FORMULA_SAFE={0}" -f $safe)
                try {
                    $f2 = [string]$cell.Formula2
                    $safe2 = [Regex]::Replace($f2, $redact, '[REDACTED]')
                    if ($safe2.Length -gt 256) {
                        $safe2 = $safe2.Substring(0,256) + '...[TRUNCATED]'
                    }
                    Write-Host ("NO11_AL1_FORMULA2_SAFE={0}" -f $safe2)
                } catch { Write-Host 'NO11_AL1_FORMULA2_UNAVAILABLE' }
                Write-Host 'NO11_FORMULA_READBACK_DIAGNOSTIC_ONLY=TRUE'
            }
            throw ("NO11_RSS_FORMULA_ARGUMENT_MISMATCH:{0}" -f $address)
        }
    }
    foreach ($address in $expectedHeaders.Keys) {
        if ([string]$Sheet.Range($address).Value2 -ne $expectedHeaders[$address]) {
            throw ("NO11_RSS_HEADER_MISMATCH:{0}" -f $address)
        }
    }
    # Never trust an extra formula inserted into this account-only Workbook.
    foreach ($cell in $Sheet.UsedRange.SpecialCells(-4123).Cells) {
        $address = [string]$cell.Address($false,$false)
        if (-not $expectedFormulas.Contains($address)) {
            throw ("NO11_EXTRA_FORMULA_FORBIDDEN:{0}" -f $address)
        }
    }
}
function New-No11Workbook {
    param($Excel, [string]$FullPath)
    if (Test-Path -LiteralPath $FullPath -PathType Leaf) {
        throw "NO11_WORKBOOK_ALREADY_EXISTS_USE_DIAGNOSE"
    }
    if ([string]::Equals($FullPath,
        [IO.Path]::GetFullPath("C:\Ark\Ark_No11_RSS_ReadOnly.xlsx"),
        [StringComparison]::OrdinalIgnoreCase)) {
        throw "NO11_PREVIOUS_WORKBOOK_OVERWRITE_FORBIDDEN"
    }
    if ([string]::Equals($FullPath,
        [IO.Path]::GetFullPath("C:\Ark\Ark_MSII_LiveSource.xlsx"),
        [StringComparison]::OrdinalIgnoreCase)) {
        throw "NO11_LEGACY_WORKBOOK_OVERWRITE_FORBIDDEN"
    }
    $directory = Split-Path -Parent $FullPath
    if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
        [void](New-Item -ItemType Directory -Force -Path $directory)
    }
    # xlWBATWorksheet = -4167. Creates a new one-sheet Workbook.
    $book = $Excel.Workbooks.Add(-4167)
    try {
        $sheet = $book.Worksheets.Item(1)
        $sheet.Name = "ARK_ACCOUNT_READONLY"
        $Excel.Visible = $true
        $book.Activate()
        $book.Windows.Item(1).DisplayFormulas = $false
        $sheet.Range("L1:AU2").Font.Bold = $true
        $sheet.Range("L2:AU2").Interior.Color = 15790320
        $sheet.Columns("L:AU").ColumnWidth = 16
        $sheet.Columns("L").ColumnWidth = 22
        foreach ($address in $expectedHeaders.Keys) {
            $sheet.Range($address).Value2 = $expectedHeaders[$address]
        }
        foreach ($address in $expectedFormulas.Keys) {
            $cell = $sheet.Range($address)
            # Fresh Excel cells already use General by default. On some
            # Windows/Excel installations the COM NumberFormat setter fails
            # even on a new sheet; do not make formatting a setup prerequisite.
            $cell.Formula = $expectedFormulas[$address]
        }
        Assert-No11Layout -Sheet $sheet
        # .xlsx, macro-free. No other open Workbook is saved or recalculated.
        $book.SaveAs($FullPath,51)
        if ($ObserveSeconds -gt 0) {
            # Only the newly created sheet is calculated; never CalculateFull().
            $sheet.Calculate()
            Start-Sleep -Seconds $ObserveSeconds
        }
        return $book
    } catch {
        # Never overwrite the old file, and never save a failed Workbook.
        try { $book.Close($false) } catch { }
        throw
    }
}
function Get-No11ObservedStatus {
    param($Sheet,[string]$Address,[string]$ExpectedStatus)
    $cell = $Sheet.Range($Address)
    if ($cell.HasFormula -ne $true) { return "RSS_FORMULA_MISSING" }
    $formula = ([string]$cell.Formula) -replace "^=@", "="
    if ($formula -cne $expectedFormulas[$Address]) { return "RSS_FORMULA_MISMATCH" }
    # MarketSpeed II RSS may render "=RssFunction(args) => 配信中" as the
    # calculated result. Match the exact verified formula and terminal status,
    # never a loose substring that could accept "#NAME?" or an error suffix.
    $echo = $formula + " => " + $ExpectedStatus
    foreach ($raw in @([string]$cell.Value2,[string]$cell.Text)) {
        $value = $raw.Trim()
        if ($value -ceq $ExpectedStatus -or $value -ceq $echo) {
            return $ExpectedStatus
        }
        if ($value -ceq ("=@" + $formula.Substring(1) + " => " + $ExpectedStatus)) {
            return $ExpectedStatus
        }
    }
    return "RSS_STATUS_UNRECOGNIZED"
}

function Write-No11Diagnostic {
    param($Book, [string]$ReportFullPath)
    $sheets = @($Book.Worksheets | Where-Object { $_.Name -eq "ARK_ACCOUNT_READONLY" })
    if ($sheets.Count -ne 1) { throw "NO11_ACCOUNT_SHEET_MISSING_OR_DUPLICATE" }
    $sheet = $sheets[0]
    Assert-No11Layout -Sheet $sheet
    $feeds = [ordered]@{}
    $blockers = @()
    foreach ($address in $expectedStates.Keys) {
        $state = Get-No11ObservedStatus -Sheet $sheet -Address $address -ExpectedStatus $expectedStates[$address]
        $feeds[$address] = $state
        if ($state -ne $expectedStates[$address]) {
            $blockers += ("RSS_STATUS_NOT_READY:{0}" -f $address)
        }
    }
    $show = [bool]$Book.Windows.Item(1).DisplayFormulas
    if ($show) { $blockers += "EXCEL_SHOW_FORMULAS_ON" }
    $report = [ordered]@{
        schemaId = "ARK_NO11_RSS_WORKBOOK_DIAGNOSTIC_V1"
        observedAt = (Get-Date).ToString("o")
        workbook = [IO.Path]::GetFullPath([string]$Book.FullName)
        source = "MARKETSPEED_II_RSS_EXCEL"
        layoutVerified = $true
        showFormulas = $show
        feedStates = $feeds
        status = $(if ($blockers.Count -eq 0) { "RSS_STATUS_OBSERVED" } else { "BLOCKED" })
        blockers = $blockers
        actualBrokerArrivalTimeCertified = $false
        executionAllowed = $false
        brokerWriteAllowed = $false
        excelOrderWriteAllowed = $false
        rssOrderFunctionAllowed = $false
        transmitted = $false
        productionReady = $false
    }
    $dir = Split-Path -Parent $ReportFullPath
    [void](New-Item -ItemType Directory -Force -Path $dir)
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($ReportFullPath,($report | ConvertTo-Json -Depth 8),$utf8)
    Write-Host ("NO11_RSS_WORKBOOK_STATUS={0}" -f $report.status)
    Write-Host ("FORMULA_VIEW={0}" -f $show)
    foreach ($key in $feeds.Keys) { Write-Host ("{0}={1}" -f $key,$feeds[$key]) }
    if ($blockers.Count -gt 0) { Write-Host ("BLOCKERS={0}" -f ($blockers -join ",")) }
    Write-Host "ORDER_TRANSMISSION=FALSE"
    Write-Host ("DIAGNOSTIC={0}" -f $ReportFullPath)
}

$target = [IO.Path]::GetFullPath($WorkbookPath)
$reportTarget = [IO.Path]::GetFullPath($ReportPath)
if ($Mode -eq "Create") {
    if (Test-Path -LiteralPath $target -PathType Leaf) {
        throw "NO11_WORKBOOK_ALREADY_EXISTS_USE_DIAGNOSE"
    }
    $excel = Get-No11Excel -MayStart $true
    $book = New-No11Workbook -Excel $excel -FullPath $target
} else {
    $excel = Get-No11Excel -MayStart $true
    $book = Resolve-No11Workbook -Excel $excel -FullPath $target
}
Write-No11Diagnostic -Book $book -ReportFullPath $reportTarget
