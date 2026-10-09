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
    # Do not let COM Application travel naked through PowerShell's output
    # pipeline. The reference is always returned as a scalar wrapper.
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
    param($Excel, [string]$FullPath)
    $matches = @($Excel.Workbooks | Where-Object {
        [string]::Equals([IO.Path]::GetFullPath([string]$_.FullName),
            $FullPath, [StringComparison]::OrdinalIgnoreCase)
    })
    if ($matches.Count -gt 1) { throw "NO11_DUPLICATE_WORKBOOK_OPEN" }
    if ($matches.Count -eq 1) {
        return [pscustomobject]@{ Workbook = $matches[0] }
    }
    if (-not (Test-Path -LiteralPath $FullPath -PathType Leaf)) {
        throw "NO11_WORKBOOK_MISSING"
    }
    # Only open the new, isolated Workbook in READ ONLY mode.
    $opened = $Excel.Workbooks.Open($FullPath,0,$true)
    if ($null -eq $opened) { throw "NO11_WORKBOOK_READ_ONLY_OPEN_FAILED" }
    if (-not [string]::Equals([IO.Path]::GetFullPath([string]$opened.FullName),
        $FullPath,[StringComparison]::OrdinalIgnoreCase)) {
        throw "NO11_DIAGNOSE_OPEN_IDENTITY_UNSAFE"
    }
    return [pscustomobject]@{ Workbook = $opened }
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
function New-No11BlankXlsx {
    param([Parameter(Mandatory=$true)][string]$Path)
    # A static single-sheet OOXML workbook. It contains no RSS expressions,
    # orders, broker values, macros, external links or active content.
    # This avoids Excel.Workbooks.Add, which returned an OLD Workbook object
    # in the real user's Windows/Excel session.
    Add-Type -AssemblyName System.IO.Compression -ErrorAction Stop
    $ct='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'
    $root='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    $wb='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="ARK_ACCOUNT_READONLY" sheetId="1" r:id="rId1"/></sheets></workbook>'
    $wbr='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
    $ws='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>'
    $parts=[ordered]@{
        '[Content_Types].xml'=$ct
        '_rels/.rels'=$root
        'xl/workbook.xml'=$wb
        'xl/_rels/workbook.xml.rels'=$wbr
        'xl/worksheets/sheet1.xml'=$ws
    }
    $fs = [System.IO.File]::Open($Path,
        [System.IO.FileMode]::CreateNew,[System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None)
    try {
        $archive = [System.IO.Compression.ZipArchive]::new(
            $fs,[System.IO.Compression.ZipArchiveMode]::Create,$true)
        try {
            $utf8 = New-Object System.Text.UTF8Encoding($false)
            foreach ($name in $parts.Keys) {
                $entry = $archive.CreateEntry([string]$name,
                    [System.IO.Compression.CompressionLevel]::Optimal)
                $stream = $entry.Open()
                $writer = [System.IO.StreamWriter]::new($stream,$utf8)
                try { $writer.Write([string]$parts[$name]) }
                finally { $writer.Dispose() }
            }
        } finally { $archive.Dispose() }
    } finally { $fs.Dispose() }
}
function New-No11Workbook {
    param($Excel, [string]$FullPath)
    if (Test-Path -LiteralPath $FullPath -PathType Leaf) {
        throw "NO11_WORKBOOK_ALREADY_EXISTS_USE_DIAGNOSE"
    }
    foreach ($protected in @(
        "C:\Ark\Ark_No11_RSS_ReadOnly.xlsx",
        "C:\Ark\Ark_MSII_LiveSource.xlsx"
    )) {
        if ([string]::Equals($FullPath,[IO.Path]::GetFullPath($protected),
            [StringComparison]::OrdinalIgnoreCase)) {
            throw "NO11_LEGACY_WORKBOOK_OVERWRITE_FORBIDDEN"
        }
    }
    $directory=Split-Path -Parent $FullPath
    if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
        [void](New-Item -ItemType Directory -Force -Path $directory)
    }
    # Isolated temporary workbook: never call Excel.Workbooks.Add.
    $stage=Join-Path $directory ("Ark_No11_V2_Stage_" +
        [guid]::NewGuid().ToString("N") + ".xlsx")
    New-No11BlankXlsx -Path $stage
    $stageBook=$null
    $stageVerified=$false
    $stageClosed=$false
    $finalBook=$null
    try {
        # Only this exact staging file is allowed to be modified.
        $stageBook=$Excel.Workbooks.Open($stage,0,$false)
        if ($null -eq $stageBook) { throw "NO11_STAGE_OPEN_FAILED" }
        if (-not [string]::Equals([IO.Path]::GetFullPath([string]$stageBook.FullName),
            $stage,[StringComparison]::OrdinalIgnoreCase)) {
            # Do NOT close this unexpected object; it might be user's old book.
            throw "NO11_STAGE_WORKBOOK_IDENTITY_UNSAFE"
        }
        if ([bool]$stageBook.ReadOnly) { throw "NO11_STAGE_OPENED_READ_ONLY" }
        $stageVerified=$true
        if ([int]$stageBook.Worksheets.Count -ne 1) {
            throw "NO11_STAGE_SHEET_COUNT_INVALID"
        }
        $sheet=$stageBook.Worksheets.Item(1)
        if ([string]$sheet.Name -cne "ARK_ACCOUNT_READONLY") {
            throw "NO11_STAGE_SHEET_IDENTITY_UNSAFE"
        }
        Write-Host "NO11_CREATION_METHOD=ISOLATED_OPENXML_STAGE"
        Write-Host "NO11_STAGE_WORKBOOK_IDENTITY_MATCH=True"
        $Excel.Visible=$true
        $stageBook.Activate()
        $stageBook.Windows.Item(1).DisplayFormulas=$false
        $sheet.Range("L1:BC2").Font.Bold=$true
        $sheet.Range("L2:BC2").Interior.Color=15790320
        $sheet.Columns("L:BC").ColumnWidth=16
        $sheet.Columns("L").ColumnWidth=22
        foreach ($address in $expectedHeaders.Keys) {
            $sheet.Range($address).Value2 = $expectedHeaders[$address]
        }
        foreach ($address in $expectedFormulas.Keys) {
            $sheet.Range($address).Formula = $expectedFormulas[$address]
        }
        Assert-No11Layout -Sheet $sheet
        if (-not [string]::Equals([IO.Path]::GetFullPath([string]$stageBook.FullName),
            $stage,[StringComparison]::OrdinalIgnoreCase)) {
            throw "NO11_STAGE_IDENTITY_CHANGED_BEFORE_SAVE"
        }
        [void]$stageBook.Save()
        [void]$stageBook.Close($false)
        $stageClosed=$true
        $stageBook=$null
        # File.Move refuses an existing destination (no overwrite).
        [IO.File]::Move($stage,$FullPath)
        Write-Host ("NO11_FINAL_FILE_PRESENT={0}" -f (
            Test-Path -LiteralPath $FullPath -PathType Leaf))
        # Reopen final Workbook READ ONLY; never call a Save method on it.
        $finalBook=$Excel.Workbooks.Open($FullPath,0,$true)
        if ($null -eq $finalBook) { throw "NO11_FINAL_OPEN_FAILED" }
        if (-not [string]::Equals([IO.Path]::GetFullPath([string]$finalBook.FullName),
            $FullPath,[StringComparison]::OrdinalIgnoreCase)) {
            # Do NOT close if Excel returned a protected foreign workbook.
            throw "NO11_FINAL_WORKBOOK_IDENTITY_UNSAFE"
        }
        if (-not [bool]$finalBook.ReadOnly) {
            throw "NO11_FINAL_NOT_READ_ONLY"
        }
        Assert-No11Layout -Sheet $finalBook.Worksheets.Item(1)
        Write-Host "NO11_FINAL_WORKBOOK_IDENTITY_MATCH=True"
        if ($ObserveSeconds -gt 0) {
            [void]$finalBook.Worksheets.Item(1).Calculate()
            Start-Sleep -Seconds $ObserveSeconds
        }
        return [pscustomobject]@{
            Workbook=$finalBook
            SavedWorkbookPath=$FullPath
        }
    } catch {
        if ($stageVerified -and -not $stageClosed -and $null -ne $stageBook) {
            try { [void]$stageBook.Close($false) } catch { }
        }
        # Any leftover staging file belongs to this run only. Never delete
        # the user-owned legacy book or an existing target Workbook.
        if (Test-Path -LiteralPath $stage -PathType Leaf) {
            try { [IO.File]::Delete($stage) } catch { }
        }
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
    $excelSession = Get-No11Excel -MayStart $true
    $excel = $excelSession.Application
    $created = New-No11Workbook -Excel $excel -FullPath $target
    if ($null -eq $created -or $null -eq $created.Workbook) {
        throw "NO11_NEW_WORKBOOK_REFERENCE_MISSING"
    }
    if (-not [string]::Equals([string]$created.SavedWorkbookPath,$target,
        [StringComparison]::OrdinalIgnoreCase)) {
        throw "NO11_NEW_WORKBOOK_WRAPPER_MISMATCH"
    }
    $book = $created.Workbook
} else {
    $excelSession = Get-No11Excel -MayStart $true
    $excel = $excelSession.Application
    $resolved = Resolve-No11Workbook -Excel $excel -FullPath $target
    if ($null -eq $resolved -or $null -eq $resolved.Workbook) {
        throw "NO11_DIAGNOSE_WORKBOOK_REFERENCE_MISSING"
    }
    $book = $resolved.Workbook
}
Write-No11Diagnostic -Book $book -ReportFullPath $reportTarget -ExpectedWorkbookPath $target
