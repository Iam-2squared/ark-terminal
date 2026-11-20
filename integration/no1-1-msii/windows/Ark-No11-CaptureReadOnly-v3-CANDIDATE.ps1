# ARK TERMINAL No.1.1 - ISOLATED READ ONLY bulk capture candidate (not production).
# Windows PowerShell 5.1. Retains the v2 schema, exact 18-header layout and complete-row checks.
# No workbook creation, mutation, save, RSS orders, or Safety release.
# Writes only fresh, uniquely named LOCALAPPDATA/ArkTerminal/No11/capture-v3-candidate evidence.
param(
    [string]$WorkbookPath = (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ark_No11_MSII_RSS.xlsx'),
    [switch]$OfflineSelfTest
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Stage = 'PREFLIGHT'
$maxCaptureSeconds = 25 # Stricter than the unchanged 30-second downstream gate.

function Trim-Value($Value) { return ([string]$Value).Trim() }
function Empty-RssField($Value) {
    $s = Trim-Value $Value
    return ($s.Length -eq 0 -or $s -match '^[\-－—–―‐‑‒−ー]+$')
}
function Numeric-OrNull($Value) {
    if ($null -eq $Value -or $Value -isnot [ValueType]) { return $null }
    $n = [double]$Value
    if ([double]::IsNaN($n) -or [double]::IsInfinity($n)) { return $null }
    return $n
}
function Read-PositiveQuantity($Value, [string]$Label) {
    $n = Numeric-OrNull $Value
    if ($null -eq $n -or $n -le 0 -or $n -gt [int]::MaxValue -or $n -ne [math]::Floor($n)) {
        throw "INVALID_POSITIVE_QUANTITY:$Label"
    }
    return [int]$n
}
# One Excel COM call for the full rectangular range; no per-padding-cell COM calls.
function Read-BulkRange {
    param($Sheet, [string]$Address, [int]$Rows, [int]$Columns)
    $data = $Sheet.Range($Address).Value2
    if ($data -isnot [array] -or $data.Rank -ne 2 -or
        $data.GetLength(0) -ne $Rows -or $data.GetLength(1) -ne $Columns) {
        throw 'RSS_BULK_RANGE_SHAPE_INVALID'
    }
    return ,$data # Do not let PowerShell enumerate/mangle the 2-D SAFEARRAY.
}
function Bulk-Value {
    param([array]$Data, [int]$RowIndex, [int]$ColIndex)
    if ($Data.Rank -ne 2 -or $RowIndex -lt 0 -or $ColIndex -lt 0 -or
        $RowIndex -ge $Data.GetLength(0) -or $ColIndex -ge $Data.GetLength(1)) {
        throw 'RSS_BULK_INDEX_INVALID'
    }
    return $Data.GetValue($Data.GetLowerBound(0) + $RowIndex,
                          $Data.GetLowerBound(1) + $ColIndex)
}
function Test-BulkPaddingRow {
    param([array]$Data, [int]$RowIndex, [int]$Columns)
    for ($c=0; $c -lt $Columns; $c++) {
        if (-not (Empty-RssField (Bulk-Value $Data $RowIndex $c))) { return $false }
    }
    return $true
}
function Write-PositionRowShape {
    param([array]$Data, [int]$Index, [int]$ExcelRow)
    $sym = (Trim-Value (Bulk-Value $Data $Index 0)).ToUpperInvariant()
    $qty = Bulk-Value $Data $Index 3
    $qtyClass = if (Empty-RssField $qty) { 'EMPTY_OR_DASH' }
        elseif ($qty -is [ValueType]) { 'NUMERIC' } else { 'NONNUMERIC' }
    $extra = 0
    for ($c=4; $c -lt 18; $c++) {
        if (-not (Empty-RssField (Bulk-Value $Data $Index $c))) { $extra++ }
    }
    # Never print account values, security identifier, holdings, or market prices.
    Write-Host ("POSITION_ROW_SHAPE=ROW_{0};SYMBOL_VALID={1};NAME_PRESENT={2};ACCOUNT_PRESENT={3};QUANTITY_CLASS={4};OTHER_MATERIAL_COLUMNS={5}" -f
        $ExcelRow, [bool]($sym -cmatch '^[0-9A-Z]{4,5}$'),
        [bool](-not (Empty-RssField (Bulk-Value $Data $Index 1))),
        [bool](-not (Empty-RssField (Bulk-Value $Data $Index 2))), $qtyClass, $extra)
}
function Assert-BulkHeaders {
    param([array]$Data, [string[]]$Expected, [string]$Label)
    if ($Data.GetLength(0) -ne 1 -or $Data.GetLength(1) -ne $Expected.Count) {
        throw 'RSS_HEADER_RANGE_SHAPE_INVALID'
    }
    for ($i=0; $i -lt $Expected.Count; $i++) {
        if ((Trim-Value (Bulk-Value $Data 0 $i)) -cne $Expected[$i]) {
            throw "RSS_HEADER_MISMATCH:$Label"
        }
    }
}
function Normalize-Formula($Cell) {
    return ((([string]$Cell.Formula).Trim() -replace '^=@', '=') -replace '\$', '')
}
function Read-VerifiedStatus {
    param($Cell, [string]$ExpectedFormula, [string]$ExpectedState)
    if (-not [bool]$Cell.HasFormula) { return 'MISSING_FORMULA' }
    $formula = Normalize-Formula $Cell
    if ($formula -cne $ExpectedFormula) { return 'FORMULA_MISMATCH' }
    foreach ($raw in @([string]$Cell.Value2, [string]$Cell.Text)) {
        $value = $raw.Trim()
        if ($value -ceq $ExpectedState) { return $ExpectedState }
        if ($value -notmatch '^(.*) => (.*)$') { continue }
        $echo = (($Matches[1].Trim() -replace '^=@', '=') -replace '\$', '')
        if ($echo -ceq $formula -and $Matches[2] -ceq $ExpectedState) { return $ExpectedState }
    }
    return 'STATUS_UNVERIFIED'
}
function Assert-ElapsedWithinLimit {
    param([datetime]$StartedAt, [datetime]$CompletedAt, [double]$LimitSec)
    $seconds = ($CompletedAt - $StartedAt).TotalSeconds
    if ($seconds -lt 0 -or $seconds -ge $LimitSec) {
        throw 'CAPTURE_TOO_SLOW_NO_SNAPSHOT'
    }
    return $seconds
}

if ($OfflineSelfTest) {
    $Stage = 'OFFLINE_SELFTEST'
    $data = [array]::CreateInstance([object],([int[]]@(2,3)))
    $data[0,0]='foo'; $data[1,2]='----'
    if ((Bulk-Value $data 0 0) -cne 'foo' -or -not (Empty-RssField (Bulk-Value $data 1 2))) {
        throw 'SELFTEST_BULK_VALUES_FAILED'
    }
    $failed=$false
    try { Bulk-Value $data 2 1 | Out-Null } catch {
        if ($_.Exception.Message -ceq 'RSS_BULK_INDEX_INVALID') { $failed=$true } else { throw }
    }
    if (-not $failed) { throw 'SELFTEST_BULK_BOUNDS_NOT_ENFORCED' }
    # Excel COM SAFEARRAYs commonly use a 1-based lower bound.
    $oneBased = [array]::CreateInstance([object],([int[]]@(2,3)),([int[]]@(1,1)))
    $oneBased.SetValue(123,1,1)
    $oneBased.SetValue('---',2,3)
    if ((Bulk-Value $oneBased 0 0) -ne 123 -or
        (Bulk-Value $oneBased 1 2) -cne '---') { throw 'SELFTEST_SAFEARRAY_LOWER_BOUND_FAILED' }
    $statusCell=[pscustomobject]@{
        HasFormula=$true
        Formula='=@RssPositionList($AL$2:$BC$2)'
        Value2='=@RssPositionList($AL$2:$BC$2) => 配信中'
        Text='=@RssPositionList($AL$2:$BC$2) => 配信中'
    }
    if ((Read-VerifiedStatus $statusCell '=RssPositionList(AL2:BC2)' '配信中') -cne '配信中') {
        throw 'SELFTEST_POSITION_FORMULA_REJECTED'
    }
    $badStatusCell=[pscustomobject]@{
        HasFormula=$true;Formula='=RssPositionList(AL2:AU2)'
        Value2='配信中';Text='配信中'
    }
    if ((Read-VerifiedStatus $badStatusCell '=RssPositionList(AL2:BC2)' '配信中') -ceq '配信中') {
        throw 'SELFTEST_WRONG_POSITION_FORMULA_ACCEPTED'
    }
    $start = [datetime]'2026-10-11T09:00:00'
    $end = $start.AddSeconds(33.25)
    $failed=$false
    try { Assert-ElapsedWithinLimit $start $end 25 | Out-Null } catch {
        if ($_.Exception.Message -ceq 'CAPTURE_TOO_SLOW_NO_SNAPSHOT') { $failed=$true } else { throw }
    }
    if (-not $failed) { throw 'SELFTEST_SLOW_CAPTURE_ACCEPTED' }
    Write-Host 'NO11_V3_BULK_OFFLINE_SELFTEST_PASS=True'
    Write-Host 'ORDER_TRANSMISSION=False'
    return
}

try {
    $target = [IO.Path]::GetFullPath($WorkbookPath)
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw 'TARGET_WORKBOOK_NOT_FOUND' }
    if (@(Get-Process EXCEL -ErrorAction SilentlyContinue).Count -ne 1) {
        throw 'EXCEL_PROCESS_COUNT_NOT_ONE'
    }
    try { $excel = [Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application') }
    catch { throw 'EXCEL_NOT_ATTACHED' }
    if ([int]$excel.Workbooks.Count -ne 1) { throw 'EXCEL_BOOK_COUNT_NOT_ONE' }
    $book = $excel.Workbooks.Item(1)
    if (-not [string]::Equals([IO.Path]::GetFullPath([string]$book.FullName),$target,
        [StringComparison]::OrdinalIgnoreCase)) { throw 'WRONG_EXCEL_WORKBOOK' }
    if ([int]$book.Worksheets.Count -ne 1) { throw 'SHEET_COUNT_NOT_ONE' }
    $sheet = $book.Worksheets.Item(1)
    if ([string]$sheet.Name -cne 'ARK_ACCOUNT_READONLY') { throw 'SHEET_NAME_UNEXPECTED' }

    $Stage = 'VERIFY_LAYOUT'
    $formulaList = [ordered]@{
        L1='=RssCapacityList(L2:L2)'; N1='=RssOrderList(N2:W2,0,1)'
        AA1='=RssExecutionList(AA2:AI2,1)'; AL1='=RssPositionList()'
    }
    $initialAL1Formula=$null
    foreach ($key in $formulaList.Keys) {
        $cell=$sheet.Range($key)
        if (-not [bool]$cell.HasFormula) { throw "RSS_FORMULA_MISSING:$key" }
        $formula = Normalize-Formula $cell
        if ($key -eq 'AL1') {
            if ($formula -cne '=RssPositionList()' -and
                $formula -cne '=RssPositionList(AL2:BC2)') {
                throw 'RSS_POSITION_FORMULA_UNEXPECTED'
            }
            $initialAL1Formula=$formula
        } elseif ($formula -cne $formulaList[$key]) { throw "RSS_FORMULA_UNEXPECTED:$key" }
    }
    if ((Trim-Value ($sheet.Range('L2').Value2)) -cne '現物買付可能額') {
        throw 'RSS_HEADER_MISMATCH:L2'
    }
    $ordersHeaders = @('注文番号','通常注文状況','銘柄コード','銘柄名称','口座区分','売買','取引','執行条件','注文数量','約定数量')
    $executionHeaders = @('約定日','銘柄コード','銘柄名称','口座区分','市場名称','取引','売買','約定数量','約定単価')
    $positionHeaders = @('銘柄コード','銘柄名称','口座区分','保有数量','発注数量','平均取得価額','時価',
        '前日比','前日比率','時価評価額','評価損益額','評価損益率','銘柄情報等','JAX時価','JNX時価','PER','PBR','配当利回り')
    Assert-BulkHeaders (Read-BulkRange $sheet 'N2:W2' 1 10) $ordersHeaders 'ORDERS'
    Assert-BulkHeaders (Read-BulkRange $sheet 'AA2:AI2' 1 9) $executionHeaders 'EXECUTIONS'
    Assert-BulkHeaders (Read-BulkRange $sheet 'AL2:BC2' 1 18) $positionHeaders 'POSITIONS'

    $Stage = 'CHECK_RSS_STATUS_INITIAL'
    $expectedStates = [ordered]@{L1='完了'; N1='配信中'; AA1='配信中'; AL1='配信中'}
    foreach ($key in $expectedStates.Keys) {
        $valid = $formulaList[$key]
        if ($key -eq 'AL1') { $valid = $initialAL1Formula }
        $state = Read-VerifiedStatus ($sheet.Range($key)) $valid $expectedStates[$key]
        if ($state -cne $expectedStates[$key]) { throw "RSS_INITIAL_STATUS_INVALID:$key" }
    }

    $Stage = 'BULK_CAPTURE'
    # capturedAt precedes every account-value read, not the initial layout preflight.
    $start = Get-Date
    # Include limit sentinel rows as part of each *same* bulk read.
    $positionsBlock = Read-BulkRange $sheet 'AL3:BC201' 199 18
    $ordersBlock = Read-BulkRange $sheet 'N3:W301' 299 10
    $executionsBlock = Read-BulkRange $sheet 'AA3:AI301' 299 9
    $buyingPower = Numeric-OrNull ($sheet.Range('L3').Value2)
    if ($null -eq $buyingPower -or $buyingPower -lt 0) { throw 'BUYING_POWER_NOT_VERIFIED' }

    $Stage = 'READ_POSITION_ROWS'
    $positions=@();$blankSeen=$false;$positionPaddingRows=0
    for ($row=3; $row -le 200; $row++) {
        $idx = $row - 3
        if (Test-BulkPaddingRow $positionsBlock $idx 18) {
            $blankSeen=$true;$positionPaddingRows++;continue
        }
        if ($blankSeen) {
            Write-PositionRowShape $positionsBlock $idx $row
            throw "POSITION_ROW_GAP_OR_PARTIAL_AFTER_END:$row"
        }
        $symbol=(Trim-Value (Bulk-Value $positionsBlock $idx 0)).ToUpperInvariant()
        $name=Trim-Value (Bulk-Value $positionsBlock $idx 1)
        $account=Trim-Value (Bulk-Value $positionsBlock $idx 2)
        $rawQty=Bulk-Value $positionsBlock $idx 3
        if ($symbol -cnotmatch '^[0-9A-Z]{4,5}$' -or (Empty-RssField $name) -or (Empty-RssField $account)) {
            Write-PositionRowShape $positionsBlock $idx $row
            throw "POSITION_IDENTITY_INVALID:$row"
        }
        $qty=Read-PositiveQuantity $rawQty "POSITION_$row"
        $positions += [pscustomobject][ordered]@{
            symbol=$symbol;name=$name;account=$account;quantity=$qty
            orderQuantity=(Numeric-OrNull (Bulk-Value $positionsBlock $idx 4))
            averagePrice=(Numeric-OrNull (Bulk-Value $positionsBlock $idx 5))
            marketPrice=(Numeric-OrNull (Bulk-Value $positionsBlock $idx 6))
            marketValue=(Numeric-OrNull (Bulk-Value $positionsBlock $idx 9))
            unrealizedPnl=(Numeric-OrNull (Bulk-Value $positionsBlock $idx 10))
            unrealizedPnlPercent=(Numeric-OrNull (Bulk-Value $positionsBlock $idx 11))
        }
    }
    if ($positions.Count -lt 1) { throw 'NO_VERIFIED_BROKER_POSITIONS' }
    if (-not (Test-BulkPaddingRow $positionsBlock 198 18)) { throw 'POSITION_ROW_LIMIT_EXCEEDED' }

    $Stage = 'READ_ORDER_ROWS'
    $orders=@();$blankSeen=$false
    for ($row=3; $row -le 300; $row++) {
        $idx=$row-3
        if (Test-BulkPaddingRow $ordersBlock $idx 10) {$blankSeen=$true;continue}
        if ($blankSeen) {throw "ORDER_ROW_GAP_OR_PARTIAL_AFTER_END:$row"}
        $id=Trim-Value (Bulk-Value $ordersBlock $idx 0)
        if ((Empty-RssField $id) -or $id -eq '0') { throw "ORDER_ID_MISSING_BUT_ROW_HAS_DATA:$row" }
        $orders += [pscustomobject][ordered]@{
            orderNumber=$id;status=(Trim-Value (Bulk-Value $ordersBlock $idx 1))
            symbol=(Trim-Value (Bulk-Value $ordersBlock $idx 2))
            quantity=(Numeric-OrNull (Bulk-Value $ordersBlock $idx 8))
            filledQty=(Numeric-OrNull (Bulk-Value $ordersBlock $idx 9))
        }
    }
    if (-not (Test-BulkPaddingRow $ordersBlock 298 10)) { throw 'ORDER_ROW_LIMIT_EXCEEDED' }

    $Stage = 'READ_EXECUTION_ROWS'
    $executions=@();$blankSeen=$false
    for ($row=3; $row -le 300; $row++) {
        $idx=$row-3
        if (Test-BulkPaddingRow $executionsBlock $idx 9) {$blankSeen=$true;continue}
        if ($blankSeen) {throw "EXECUTION_ROW_GAP_OR_PARTIAL_AFTER_END:$row"}
        # Preserve the proven v2 date presentation, without doing per-padding-row COM.
        $date=Trim-Value ($sheet.Cells.Item($row,27).Text)
        if ((Empty-RssField $date) -or $date -match '^#+$') { throw "EXECUTION_DATE_UNREADABLE:$row" }
        $executions += [pscustomobject][ordered]@{
            executionDate=$date;symbol=(Trim-Value (Bulk-Value $executionsBlock $idx 1))
            account=(Trim-Value (Bulk-Value $executionsBlock $idx 3))
            side=(Trim-Value (Bulk-Value $executionsBlock $idx 6))
            quantity=(Numeric-OrNull (Bulk-Value $executionsBlock $idx 7))
            price=(Numeric-OrNull (Bulk-Value $executionsBlock $idx 8))
        }
    }
    if (-not (Test-BulkPaddingRow $executionsBlock 298 9)) {throw 'EXECUTION_ROW_LIMIT_EXCEEDED'}

    $Stage = 'FINAL_RSS_STATUS_OBSERVATION'
    # Re-read every original RSS status formula/value AFTER the account values.
    # observedAt is the genuine COM observation time, NEVER a made-up broker timestamp.
    $state=@{};$finalObservedAt=@{}
    foreach ($key in $expectedStates.Keys) {
        $formula=$formulaList[$key]
        if ($key -eq 'AL1') { $formula=$initialAL1Formula }
        $status=Read-VerifiedStatus ($sheet.Range($key)) $formula $expectedStates[$key]
        $observationDate=Get-Date
        if ($status -cne $expectedStates[$key]) { throw "RSS_FINAL_STATUS_INVALID:$key" }
        $state[$key]=$status
        $finalObservedAt[$key]=$observationDate.ToString('o')
    }
    $end=Get-Date
    $seconds=Assert-ElapsedWithinLimit $start $end $maxCaptureSeconds

    $Stage = 'WRITE_PRIVATE_CANDIDATE_ONLY'
    $safety=[ordered]@{
        executionAllowed=$false;brokerWriteAllowed=$false;excelOrderWriteAllowed=$false
        rssOrderFunctionAllowed=$false;liveTradingAllowed=$false;paperTradingAllowed=$false
        automaticPromotionAllowed=$false;productionUpdateAllowed=$false
        transmitted=$false;productionReady=$false
    }
    $snapshot=[ordered]@{
        schemaId='ARK_ACCOUNT_READONLY_SNAPSHOT_V2'
        capturedAt=$start.ToString('o');captureCompletedAt=$end.ToString('o')
        source='MARKETSPEED_II_RSS';mode='READ_ONLY'
        captureMethod='ISOLATED_BULK_CANDIDATE_NOT_PRODUCTION'
        rssStatus=[ordered]@{capacity=$state['L1'];orders=$state['N1'];executions=$state['AA1'];positions=$state['AL1']}
        positions=@($positions);orders=@($orders);executions=@($executions)
        buyingPower=$buyingPower;safety=$safety
    }
    $health=[ordered]@{
        schemaId='ARK_MSII_RSS_SOURCE_HEALTH_V1'
        source='MARKETSPEED_II_RSS';readOnly=$true
        addinLoaded=$true;workbookPersisted=$true;rssErrors=0
        healthCapturedAt=$end.ToString('o')
        actualFeedTimestampCertified=$false
        observationBasis='FINAL_STATUS_RE_READ_NOT_MARKET_SOURCE_TIMESTAMP'
        feeds=[ordered]@{
            capacity=@{state=$state['L1'];observedAt=$finalObservedAt['L1']}
            orders=@{state=$state['N1'];observedAt=$finalObservedAt['N1']}
            executions=@{state=$state['AA1'];observedAt=$finalObservedAt['AA1']}
            positions=@{state=$state['AL1'];observedAt=$finalObservedAt['AL1']}
        }
    }
    $base=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No11\capture-v3-candidate'
    $dir=Join-Path $base ([Guid]::NewGuid().ToString('N'))
    [void](New-Item -ItemType Directory -Path $dir -ErrorAction Stop)
    $utf8=New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText((Join-Path $dir 'snapshot.json'),($snapshot|ConvertTo-Json -Depth 12),$utf8)
    [IO.File]::WriteAllText((Join-Path $dir 'source-health.json'),($health|ConvertTo-Json -Depth 12),$utf8)
    Write-Host 'NO11_V3_CANDIDATE_SNAPSHOT_READY=True'
    Write-Host ('NO11_V3_CAPTURE_DURATION_SEC={0:N2}' -f $seconds)
    Write-Host "NO11_V3_POSITION_COUNT=$($positions.Count)"
    Write-Host "NO11_V3_POSITION_PADDING_ROWS=$positionPaddingRows"
    Write-Host "NO11_V3_ORDER_COUNT=$($orders.Count)"
    Write-Host "NO11_V3_EXECUTION_COUNT=$($executions.Count)"
    Write-Host 'ACTUAL_FEED_TIMESTAMP_CERTIFIED=False'
    Write-Host 'NO11_PRODUCTION_READY=False'
    Write-Host 'EXCEL_MODIFIED=False'
    Write-Host 'ORDER_TRANSMISSION=False'
} catch {
    $code=[string]$_.Exception.Message
    if ($code -cnotmatch '^[A-Z][A-Z0-9_]*(?::[A-Z0-9_]+)?$') { $code='REDACTED_UNEXPECTED_ERROR' }
    Write-Host "FAILED_AT=$Stage"
    Write-Host "ERROR_CODE=$code"
    Write-Host 'NO11_V3_CANDIDATE_SNAPSHOT_READY=False'
    Write-Host 'EXCEL_MODIFIED=False'
    Write-Host 'ORDER_TRANSMISSION=False'
    throw "NO11_V3_CANDIDATE_BLOCKED:$code"
}
