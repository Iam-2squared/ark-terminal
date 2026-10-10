# Ark Terminal No.1.1 one-click READ ONLY startup (Windows PowerShell 5.1).
# This opens existing applications only; it never enables trading or sends orders.
param(
    [string]$WorkbookPath = (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ark_No11_MSII_RSS.xlsx'),
    [string]$MarketSpeedShortcut = '',
    [ValidateRange(30,900)][int]$StartupWaitSeconds = 240,
    [ValidateRange(1024,65535)][int]$Port = 8767,
    [switch]$SkipOpenMarketSpeed,
    [switch]$SkipOpenExcel,
    [switch]$NoBrowser,
    [switch]$DiagnosticOnly
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$freeze = '10c94c92c4bd2a59a22744667fd0210252602df4'
$frozenRepo = 'C:\ArkTerminal\repo'
$uiScript = Join-Path $PSScriptRoot 'Start-No11DesktopUi.ps1'
$privateBaseline = Join-Path $env:LOCALAPPDATA 'ArkTerminal\No11\ownership-baseline.json'
$expectedSheet = 'ARK_ACCOUNT_READONLY'
$expectedStates = [ordered]@{
    L1 = '完了'
    N1 = '配信中'
    AA1 = '配信中'
    AL1 = '配信中'
}

# Never inspect account amounts or stock rows here. Only readiness status cells.

# Same strict formula+RSS-status contract as Get-No11ReadOnlySnapshot.ps1.
# Do not accept any text merely ending in "完了" or "配信中".
# Reading here never executes the RSS formula or writes Excel.
function Get-ArkNo11StartupRssStatus {
    param(
        [Parameter(Mandatory=$true)]$Worksheet,
        [Parameter(Mandatory=$true)][string]$Address
    )
    $expected = @{
        L1  = @{ formula = '=RssCapacityList(L2:L2)'; state = '完了' }
        N1  = @{ formula = '=RssOrderList(N2:W2,0,1)'; state = '配信中' }
        AA1 = @{ formula = '=RssExecutionList(AA2:AI2,1)'; state = '配信中' }
        AL1 = @{ formula = '=RssPositionList()'; state = '配信中' }
    }
    if (-not $expected.ContainsKey($Address)) { throw 'RSS_STATUS_ADDRESS_INVALID' }
    $cell = $Worksheet.Range($Address)
    if ($cell.HasFormula -ne $true) { return 'RSS_FORMULA_MISSING' }
    # Excel implicitly inserts @ for some add-in formula versions.
    $formula = ([string]$cell.Formula) -replace '^=@', '='
    if ($formula -cne $expected[$Address].formula) { return 'RSS_FORMULA_MISMATCH' }
    $state = [string]$expected[$Address].state
    foreach ($raw in @([string]$cell.Value2, [string]$cell.Text)) {
        $value = $raw.Trim()
        if ($value -ceq $state -or $value -ceq ($formula + ' => ' + $state)) {
            return $state
        }
        if ($value -ceq ('=@' + $formula.Substring(1) + ' => ' + $state)) {
            return $state
        }
    }
    return 'RSS_STATUS_UNRECOGNIZED'
}

function Get-WorkbookOpenState {
    # Unlike feed readiness, this checks identity even while RSS is pending.
    try {
        $excel = [Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
        $count = 0
        foreach ($book in $excel.Workbooks) {
            if ([string]::Equals(
                [IO.Path]::GetFullPath([string]$book.FullName),
                [IO.Path]::GetFullPath($WorkbookPath),
                [StringComparison]::OrdinalIgnoreCase)) { $count++ }
        }
        if ($count -gt 1) { return 'AMBIGUOUS' }
        if ($count -eq 1) { return 'OPEN' }
        return 'NOT_OPEN'
    } catch {
        # Excel may be busy; never use COM failure as a reason to open a duplicate.
        return 'COM_UNAVAILABLE'
    }
}


# Only categorical diagnostics. This never prints any RSS cell value, symbol,
# cash value, workbook path, formula, HRESULT, or exception text.
function Get-ArkNo11SheetStatusReport {
    param([Parameter(Mandatory=$true)]$Worksheet)
    # Self-contained approved statuses: usable both in production and isolated tests.
    $requiredStates = [ordered]@{
        L1 = '完了'
        N1 = '配信中'
        AA1 = '配信中'
        AL1 = '配信中'
    }
    $result = [ordered]@{
        Workbook = 'MATCHED'
        Sheet = 'FOUND'
        L1 = 'NOT_CHECKED'
        N1 = 'NOT_CHECKED'
        AA1 = 'NOT_CHECKED'
        AL1 = 'NOT_CHECKED'
        Ready = $false
    }
    foreach ($address in $requiredStates.Keys) {
        try {
            $result[$address] = Get-ArkNo11StartupRssStatus -Worksheet $Worksheet -Address $address
        } catch {
            $result[$address] = 'CELL_COM_READ_FAILED'
        }
    }
    $ready = $true
    foreach ($address in $requiredStates.Keys) {
        if ($result[$address] -cne $requiredStates[$address]) { $ready = $false }
    }
    $result.Ready = $ready
    return [pscustomobject]$result
}

function Get-ArkNo11ReadinessDiagnostic {
    $result = [ordered]@{
        Workbook = 'NOT_CHECKED'
        Sheet = 'NOT_CHECKED'
        L1 = 'NOT_CHECKED'
        N1 = 'NOT_CHECKED'
        AA1 = 'NOT_CHECKED'
        AL1 = 'NOT_CHECKED'
        Ready = $false
    }
    try {
        $excel = [Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
    } catch {
        $result.Workbook = 'EXCEL_COM_UNAVAILABLE'
        return [pscustomobject]$result
    }
    try {
        $matches = @()
        foreach ($book in $excel.Workbooks) {
            if ([string]::Equals(
                [IO.Path]::GetFullPath([string]$book.FullName),
                [IO.Path]::GetFullPath($WorkbookPath),
                [StringComparison]::OrdinalIgnoreCase)) {
                $matches += $book
            }
        }
        if ($matches.Count -eq 0) {
            $result.Workbook = 'EXPECTED_WORKBOOK_NOT_IN_ACTIVE_EXCEL'
            return [pscustomobject]$result
        }
        if ($matches.Count -ne 1) {
            $result.Workbook = 'WORKBOOK_IDENTITY_AMBIGUOUS'
            return [pscustomobject]$result
        }
        $result.Workbook = 'MATCHED'
    } catch {
        $result.Workbook = 'WORKBOOK_COM_ENUMERATION_FAILED'
        return [pscustomobject]$result
    }
    try {
        $sheet = $matches[0].Worksheets.Item($expectedSheet)
    } catch {
        $result.Sheet = 'ACCOUNT_SHEET_UNAVAILABLE'
        return [pscustomobject]$result
    }
    return Get-ArkNo11SheetStatusReport -Worksheet $sheet
}

function Write-ArkNo11ReadinessDiagnostic {
    param([Parameter(Mandatory=$true)]$Report)
    Write-Host 'NO11_RSS_DIAGNOSTIC_READ_ONLY=True'
    Write-Host ('NO11_RSS_DIAG_WORKBOOK={0}' -f $Report.Workbook)
    Write-Host ('NO11_RSS_DIAG_SHEET={0}' -f $Report.Sheet)
    foreach ($address in @('L1','N1','AA1','AL1')) {
        Write-Host ('NO11_RSS_DIAG_{0}={1}' -f $address,$Report.$address)
    }
    Write-Host ('NO11_RSS_DIAG_READY={0}' -f $Report.Ready)
    Write-Host 'ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False'
    Write-Host 'LIVE_ORDER_ENABLED=False'
}

function Test-StatusCells {
    $report = Get-ArkNo11ReadinessDiagnostic
    return ($report.Ready -eq $true)
}

# Check the disk copy *before* opening it with the RSS add-in.
# A modified workbook with any order RSS formula must never be auto-opened.
function Assert-WorkbookDiskReadOnly {
    if (-not [string]::Equals(
            [IO.Path]::GetExtension($WorkbookPath), '.xlsx',
            [StringComparison]::OrdinalIgnoreCase)) {
        throw 'ARK_WORKBOOK_XLSX_ONLY'
    }
    Add-Type -AssemblyName System.IO.Compression
    $stream = [IO.File]::Open($WorkbookPath,
        [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    $zip = $null
    $seenSheet = $false
    try {
        $zip = [IO.Compression.ZipArchive]::new(
            $stream, [IO.Compression.ZipArchiveMode]::Read, $false)
        if ($zip.Entries.Count -lt 2 -or $zip.Entries.Count -gt 512) {
            throw 'ARK_WORKBOOK_ZIP_LAYOUT_UNEXPECTED'
        }
        foreach ($entry in $zip.Entries) {
            $name = $entry.FullName
            if ($name -match '(?i)(vbaProject|xl/macrosheets/|\.bin$)') {
                throw 'ARK_WORKBOOK_MACRO_BINARY_BLOCKED'
            }
            if ($entry.Length -gt 8388608) {
                throw 'ARK_WORKBOOK_ENTRY_TOO_LARGE'
            }
            if ($name -notmatch '(?i)\.(xml|rels)$') { continue }
            $reader = $null
            try {
                $reader = New-Object IO.StreamReader($entry.Open())
                $body = $reader.ReadToEnd()
                if ($name -ceq 'xl/workbook.xml' -and
                    $body.Contains($expectedSheet)) { $seenSheet = $true }
                if ($body -match '(?i)Rss(?:StockOrder|Margin(?:Open|Close)Order|FOP(?:Multi)?(?:Open|Close)Order|FOPModifyOrder|FOPCancelOrder|ModifyOrder|CancelOrder)\b') {
                    throw 'ARK_WORKBOOK_ORDER_RSS_FORMULA_FORBIDDEN'
                }
            } finally {
                if ($null -ne $reader) { $reader.Dispose() }
            }
        }
        if (-not $seenSheet) { throw 'ARK_WORKBOOK_EXPECTED_SHEET_NOT_FOUND' }
    } finally {
        if ($null -ne $zip) { $zip.Dispose() }
        $stream.Dispose()
    }
}

function Find-UniqueMarketSpeedShortcut {
    $menuRoots = @(
        [Environment]::GetFolderPath('StartMenu'),
        [Environment]::GetFolderPath('CommonStartMenu')
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) }
    $found = @()
    foreach ($menu in $menuRoots) {
        $found += @(Get-ChildItem -LiteralPath $menu -Filter '*.lnk' -Recurse -ErrorAction SilentlyContinue |
            Where-Object {
                $_.BaseName -match '(?i)(Market\s*Speed\s*(?:II|2)|マーケットスピード\s*(?:II|Ⅱ|２|2))' -and
                $_.BaseName -notmatch '(?i)(uninstall|setup|update|アンインストール|削除)'
            })
    }
    $unique = @($found | Sort-Object -Property FullName -Unique)
    if ($unique.Count -eq 1) { return [string]$unique[0].FullName }
    return ''
}

function Assert-PortAvailable {
    $listener = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, $Port)
    try {
        $listener.Start()
    } catch {
        throw 'ARK_UI_PORT_ALREADY_IN_USE'
    } finally {
        $listener.Stop()
    }
}

if ($DiagnosticOnly) {
    Write-ArkNo11ReadinessDiagnostic -Report (Get-ArkNo11ReadinessDiagnostic)
    return
}

Write-Host 'ARK_NO11_ONE_CLICK_STARTUP=READ_ONLY'
Write-Host 'LIVE_ORDER_ENABLED=False'
Write-Host 'EXCEL_RSS_ORDER_PERMISSION=KEEP_OFF'
Write-Host 'NO11_PRODUCTION_READY=False'

$mutex = [System.Threading.Mutex]::new($false, 'Local\ArkTerminal_No11_DesktopLauncher')
$held = $false
try {
    try {
        $held = $mutex.WaitOne(0)
    } catch [System.Threading.AbandonedMutexException] {
        $held = $true
        throw 'ARK_PREVIOUS_STARTUP_ABANDONED_REVIEW_REQUIRED'
    }
    if (-not $held) { throw 'ARK_ALREADY_RUNNING' }
    if (-not (Test-Path -LiteralPath $uiScript -PathType Leaf)) {
        throw 'ARK_UI_LAUNCHER_MISSING'
    }
    if (-not (Test-Path -LiteralPath $WorkbookPath -PathType Leaf)) {
        throw 'ARK_EXISTING_WORKBOOK_MISSING'
    }
    if (-not (Test-Path -LiteralPath $privateBaseline -PathType Leaf)) {
        throw 'ARK_PRIVATE_OWNERSHIP_BASELINE_MISSING'
    }
    if (-not (Test-Path -LiteralPath $frozenRepo -PathType Container)) {
        throw 'ARK_FROZEN_RESEARCH_CHECKOUT_MISSING'
    }
    $git = (Get-Command git -CommandType Application -ErrorAction Stop |
        Select-Object -First 1).Source
    $head = ((& $git -C $frozenRepo rev-parse HEAD) | Select-Object -First 1)
    if ($LASTEXITCODE -ne 0 -or [string]$head -cne $freeze) {
        throw 'ARK_FROZEN_RESEARCH_HEAD_MISMATCH'
    }
    $dirty = @(& $git -C $frozenRepo status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0) {
        throw 'ARK_FROZEN_RESEARCH_TRACKED_FILES_CHANGED'
    }
    Assert-PortAvailable
    Assert-WorkbookDiskReadOnly

    if (-not $SkipOpenMarketSpeed) {
        $running = @(Get-Process -Name 'MarketSpeed2' -ErrorAction SilentlyContinue)
        if ($running.Count -eq 0) {
            $shortcut = $MarketSpeedShortcut
            if ($shortcut -eq '') { $shortcut = Find-UniqueMarketSpeedShortcut }
            if ($shortcut -ne '') {
                if (-not $shortcut.EndsWith('.lnk',[StringComparison]::OrdinalIgnoreCase) -or
                    -not (Test-Path -LiteralPath $shortcut -PathType Leaf)) {
                    throw 'ARK_MARKETSPEED_SHORTCUT_INVALID'
                }
                Start-Process -FilePath $shortcut -ErrorAction Stop
                Write-Host 'MARKETSPEED_APP_START_REQUESTED=True'
            } else {
                Write-Host 'MARKETSPEED_APP_START=MANUAL_OPEN_REQUIRED'
            }
        } else {
            Write-Host 'MARKETSPEED_PROCESS_OBSERVED=True'
        }
    }

    if (-not $SkipOpenExcel) {
        if (Test-StatusCells) {
            Write-Host 'EXISTING_EXCEL_WORKBOOK_ALREADY_READY=True'
        } else {
            $openState = Get-WorkbookOpenState
            $excelProcesses = @(Get-Process -Name 'EXCEL' -ErrorAction SilentlyContinue)
            if ($openState -eq 'AMBIGUOUS') {
                throw 'ARK_DUPLICATE_WORKBOOK_INSTANCES_BLOCKED'
            }
            if ($openState -eq 'OPEN') {
                Write-Host 'EXISTING_EXCEL_WORKBOOK_ALREADY_OPEN=True'
            } elseif ($openState -eq 'NOT_OPEN' -or $excelProcesses.Count -eq 0) {
                Start-Process -FilePath $WorkbookPath -ErrorAction Stop
                Write-Host 'EXISTING_EXCEL_WORKBOOK_OPEN_REQUESTED=True'
            } else {
                Write-Host 'EXCEL_COM_BUSY_WAITING_WITHOUT_REOPEN=True'
            }
        }
    }

    Write-Host 'MARKETSPEED_LOGIN=COMPLETE_MANUALLY_IF_PROMPTED'
    Write-Host 'WAITING_FOR_READ_ONLY_RSS_STATUS=TRUE'
    $deadline = (Get-Date).AddSeconds($StartupWaitSeconds)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        if (Test-StatusCells) { $ready = $true; break }
        Start-Sleep -Seconds 5
    }
    if (-not $ready) {
        Write-ArkNo11ReadinessDiagnostic -Report (Get-ArkNo11ReadinessDiagnostic)
        throw 'ARK_RSS_STATUS_NOT_READY_TIMEOUT'
    }
    Write-Host 'RSS_FOUR_STATUS_CELLS_OBSERVED=True'
    Write-Host 'ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False'
    Write-Host 'STARTING_ARK_UI2_READ_ONLY=True'
    # The existing launcher performs the real account/Ownership/Capital gates.
    # No other executable trading pipeline is connected here.
    & $uiScript -WorkbookPath $WorkbookPath -Port $Port -RefreshSeconds 30 -NoBrowser:$NoBrowser
    if (-not $?) { throw 'ARK_READ_ONLY_UI_START_FAILED' }
} finally {
    if ($held) { [void]$mutex.ReleaseMutex() }
    $mutex.Dispose()
}
