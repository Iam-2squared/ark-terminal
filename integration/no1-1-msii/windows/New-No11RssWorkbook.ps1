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
    $app = $null
    try {
        $app = [Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
    } catch {
        if (-not $MayStart) { throw "EXCEL_NOT_RUNNING" }
        $app = New-Object -ComObject Excel.Application
        $app.Visible = $true
    }
    if ($null -eq $app) { throw "EXCEL_APPLICATION_REFERENCE_MISSING" }
    return [pscustomobject]@{ Application = $app }
}
function Resolve-No11Workbook {
    param($Excel,[string]$FullPath)
    $matches = @($Excel.Workbooks | Where-Object {
        [string]::Equals([IO.Path]::GetFullPath([string]$_.FullName),
            $FullPath,[StringComparison]::OrdinalIgnoreCase)
    })
    if ($matches.Count -gt 1) { throw "NO11_DUPLICATE_WORKBOOK_OPEN" }
    if ($matches.Count -eq 0) {
        if (-not (Test-Path -LiteralPath $FullPath -PathType Leaf)) {
            throw "NO11_WORKBOOK_MISSING"
        }
        # An already completed workbook is opened READ ONLY; no Excel cell
        # writes, creation or SaveAs are used in any branch.
        $opened=$Excel.Workbooks.Open($FullPath,0,$true)
        if ($null -ne $opened) {
            if (-not [string]::Equals(
                [IO.Path]::GetFullPath([string]$opened.FullName),
                $FullPath,[StringComparison]::OrdinalIgnoreCase)) {
                # Never close an unexpected COM workbook (may be user's old).
                throw "NO11_EXCEL_OPEN_RETURNED_FOREIGN_WORKBOOK"
            }
        }
        $matches = @($Excel.Workbooks | Where-Object {
            [string]::Equals([IO.Path]::GetFullPath([string]$_.FullName),
                $FullPath,[StringComparison]::OrdinalIgnoreCase)
        })
        if ($matches.Count -ne 1) {
            throw "NO11_READY_WORKBOOK_NOT_ACCESSIBLE_OPEN_MANUALLY"
        }
    }
    $workbook=$matches[0]
    if (-not [string]::Equals([IO.Path]::GetFullPath([string]$workbook.FullName),
        $FullPath,[StringComparison]::OrdinalIgnoreCase)) {
        throw "NO11_READ_WORKBOOK_IDENTITY_MISMATCH"
    }
    if (-not [bool]$workbook.ReadOnly) {
        throw "NO11_READY_WORKBOOK_NOT_READ_ONLY"
    }
    return [pscustomobject]@{ Workbook = $workbook }
}

function Assert-No11FormulaFootprint {
    param([Parameter(Mandatory=$true)]$Sheet)
    $used = $Sheet.UsedRange
    if ($null -eq $used) { throw "NO11_USED_RANGE_MISSING" }
    $rows = [int]$used.Rows.Count
    $cols = [int]$used.Columns.Count
    if ($rows -lt 1 -or $cols -lt 1 -or
        ([long]$rows * [long]$cols) -gt 50000) {
        throw "NO11_USED_RANGE_UNBOUNDED"
    }

    $observed = @{}
    for ($r = 1; $r -le $rows; $r++) {
        for ($c = 1; $c -le $cols; $c++) {
            $cell = $used.Cells.Item($r,$c)
            if ($null -eq $cell) { throw "NO11_FORMULA_CELL_UNREADABLE" }
            $hasFormula = $cell.HasFormula
            if ($null -eq $hasFormula) { throw "NO11_FORMULA_STATUS_UNKNOWN" }
            if ([bool]$hasFormula) {
                $address = [string]$cell.Address($false,$false)
                if (-not $expectedFormulas.Contains($address)) {
                    throw ("NO11_EXTRA_FORMULA_FORBIDDEN:{0}" -f $address)
                }
                $observed[$address] = $true
            }
        }
    }
    foreach ($required in $expectedFormulas.Keys) {
        if (-not $observed.ContainsKey($required)) {
            throw ("NO11_REQUIRED_FORMULA_NOT_FOUND:{0}" -f $required)
        }
    }
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
    # Enumerate the actual rectangular UsedRange, NOT the .Cells enumerator
    # returned by SpecialCells(-4123). That enumerator included an empty M1
    # in real Excel despite Formula.Length=0, HasArray=false and no spill.
    # Validate each SINGLE cell's HasFormula, and only allow the four exact
    # prevalidated RSS anchor formulas. A real fifth formula still FAILS CLOSED.
    Assert-No11FormulaFootprint -Sheet $Sheet
}
function New-No11Workbook {
    param([string]$FullPath)
    # The finished template already contains all four read-only RSS formulas.
    # Never create, edit, Save or SaveAs an Excel Workbook via COM.
    $template = "C:\Ark\Ark_No11_RSS_DefaultHeaders_v2_READY.xlsx"
    $expectedSha256 = "3db01750b742f85cc19c2f6c7a7547f075c3b2ed1b6f1a36d917d4e21f981c17"
    if (Test-Path -LiteralPath $FullPath -PathType Leaf) {
        throw "NO11_WORKBOOK_ALREADY_EXISTS_USE_DIAGNOSE"
    }
    foreach ($protected in @(
        "C:\Ark\Ark_No11_RSS_ReadOnly.xlsx",
        "C:\Ark\Ark_MSII_LiveSource.xlsx",
        $template
    )) {
        if ([string]::Equals($FullPath,[IO.Path]::GetFullPath($protected),
            [StringComparison]::OrdinalIgnoreCase)) {
            throw "NO11_LEGACY_WORKBOOK_OVERWRITE_FORBIDDEN"
        }
    }
    if (-not (Test-Path -LiteralPath $template -PathType Leaf)) {
        throw "NO11_VERIFIED_TEMPLATE_MISSING_DOWNLOAD_REQUIRED"
    }
    $hash = [string](Get-FileHash -LiteralPath $template -Algorithm SHA256).Hash
    if ($hash.ToLowerInvariant() -cne $expectedSha256) {
        throw "NO11_VERIFIED_TEMPLATE_HASH_MISMATCH"
    }
    $folder = Split-Path -Parent $FullPath
    if (-not (Test-Path -LiteralPath $folder -PathType Container)) {
        [void](New-Item -Path $folder -ItemType Directory -Force)
    }
    [IO.File]::Copy($template,$FullPath,$false)
    $resultHash = [string](Get-FileHash -LiteralPath $FullPath -Algorithm SHA256).Hash
    if ($resultHash.ToLowerInvariant() -cne $expectedSha256) {
        throw "NO11_COPIED_WORKBOOK_HASH_MISMATCH"
    }
    Write-Host "NO11_CREATION_METHOD=VERIFIED_READY_FILE_COPY"
    Write-Host "NO11_READY_FILE_PRESENT=True"
    Write-Host "NO11_EXCEL_WORKBOOK_WRITES=FALSE"
    return [pscustomobject]@{ SavedWorkbookPath = $FullPath }
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
    param($Book, [string]$ReportFullPath, [string]$ExpectedWorkbookPath)
    # Do not create a report for a different or unsaved Workbook. This is
    # checked before the diagnostic file can be written.
    $expectedPath = [IO.Path]::GetFullPath($ExpectedWorkbookPath)
    $observedPath = [IO.Path]::GetFullPath([string]$Book.FullName)
    if (-not [string]::Equals($expectedPath,$observedPath,
        [StringComparison]::OrdinalIgnoreCase)) {
        throw "NO11_DIAGNOSTIC_WORKBOOK_IDENTITY_MISMATCH"
    }
    if (-not (Test-Path -LiteralPath $expectedPath -PathType Leaf)) {
        throw "NO11_DIAGNOSTIC_WORKBOOK_NOT_PERSISTED"
    }
    $sheets = @($Book.Worksheets | Where-Object { $_.Name -eq "ARK_ACCOUNT_READONLY" })
    if ($sheets.Count -ne 1) { throw "NO11_ACCOUNT_SHEET_MISSING_OR_DUPLICATE" }
    $sheet = $sheets[0]
    # Finished template has intentionally uncomputed RSS UDF caches. Recalculate
    # only this exact READ ONLY sheet on the user's Excel/RSS instance.
    # Never calculate unrelated Workbooks, Save or write formulas.
    if ($ObserveSeconds -gt 0) {
        try { [void]$sheet.Calculate() }
        catch { throw "NO11_READ_ONLY_RSS_SHEET_CALCULATE_FAILED" }
        Start-Sleep -Seconds $ObserveSeconds
    }
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
    $created=New-No11Workbook -FullPath $target
    if ($null -eq $created -or $created.SavedWorkbookPath -cne $target) {
        throw "NO11_VERIFIED_READY_FILE_NOT_PREPARED"
    }
}
$session=Get-No11Excel -MayStart $true
$excel=$session.Application
$resolved=Resolve-No11Workbook -Excel $excel -FullPath $target
if ($null -eq $resolved -or $null -eq $resolved.Workbook) {
    throw "NO11_READ_ONLY_WORKBOOK_REFERENCE_MISSING"
}
$book=$resolved.Workbook
Write-No11Diagnostic -Book $book -ReportFullPath $reportTarget -ExpectedWorkbookPath $target
