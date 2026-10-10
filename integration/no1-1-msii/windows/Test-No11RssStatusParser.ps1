# Windows PowerShell 5.1 offline regression tests for observed RSS formula echo.
# No Excel, broker, COM, account information or order transmission.
$ErrorActionPreference = 'Stop'
$base = $PSScriptRoot
$expectedFormulas = [ordered]@{
    L1 = "=RssCapacityList(L2:L2)"
    N1 = "=RssOrderList(N2:W2,0,1)"
    AA1 = "=RssExecutionList(AA2:AI2,1)"
    AL1 = "=RssPositionList()"
}
$states = [ordered]@{L1="完了";N1="配信中";AA1="配信中";AL1="配信中"}

function Import-OneFunction {
    param([string]$File,[string]$Name)
    $tokens=$null;$errors=$null
    $ast=[System.Management.Automation.Language.Parser]::ParseFile($File,[ref]$tokens,[ref]$errors)
    if($errors.Count -gt 0){throw "PARSER_FAILED"}
    $funcs=@($ast.FindAll({
        param($n)
        $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $Name
    },$true))
    if($funcs.Count -ne 1){throw "FUNCTION_NOT_FOUND:$Name"}
    Invoke-Expression ("function script:" + $Name + " " + $funcs[0].Body.Extent.Text)
}
Import-OneFunction -File (Join-Path $base "New-No11RssWorkbook.ps1") -Name "Get-No11ObservedStatus"
Import-OneFunction -File (Join-Path $base "Get-No11ReadOnlySnapshot.ps1") -Name "Get-No11RssCellStatus"
Import-OneFunction -File (Join-Path $base "Start-ArkTerminalNo11.ps1") -Name "Get-ArkNo11StartupRssStatus"
Import-OneFunction -File (Join-Path $base "Start-ArkTerminalNo11.ps1") -Name "Get-ArkNo11SheetStatusReport"

function Fake-Sheet {
    param([string]$Formula,[string]$Value,[bool]$HasFormula=$true)
    $cell=[pscustomobject]@{
        Formula=$Formula;Value2=$Value;Text=$Value;HasFormula=$HasFormula
    }
    $sheet=[pscustomobject]@{Cell=$cell}
    $sheet | Add-Member -MemberType ScriptMethod -Name Range -Value {
        param($Address)
        return $this.Cell
    }
    return $sheet
}
$checks=0
foreach($address in $expectedFormulas.Keys){
    $formula=$expectedFormulas[$address]
    $state=$states[$address]
    foreach($value in @($state,("$formula => $state"),("=@" + $formula.Substring(1) + " => " + $state))){
        $sheet=Fake-Sheet -Formula $formula -Value $value
        $one=Get-No11ObservedStatus -Sheet $sheet -Address $address -ExpectedStatus $state
        $two=Get-No11RssCellStatus -Worksheet $sheet -Address $address
        $three=Get-ArkNo11StartupRssStatus -Worksheet $sheet -Address $address
        if($one -cne $state -or $two -cne $state -or $three -cne $state){throw "RSS_VALID_STATUS_REJECTED:$address"}
        $checks++
    }
    foreach($value in @("#NAME?","$formula => #NAME?","$formula => 配信停止","$formula => $state MALFORMED","文字列 $state")){
        $sheet=Fake-Sheet -Formula $formula -Value $value
        $one=Get-No11ObservedStatus -Sheet $sheet -Address $address -ExpectedStatus $state
        $two=Get-No11RssCellStatus -Worksheet $sheet -Address $address
        $three=Get-ArkNo11StartupRssStatus -Worksheet $sheet -Address $address
        if($one -ceq $state -or $two -ceq $state -or $three -ceq $state){throw "RSS_BAD_STATUS_ACCEPTED:$address"}
        $checks++
    }
    $bad=Fake-Sheet -Formula "=SUM(1,1)" -Value $state
    if((Get-No11ObservedStatus -Sheet $bad -Address $address -ExpectedStatus $state) -ceq $state){throw "RSS_WRONG_FORMULA_ACCEPTED"}
    if((Get-No11RssCellStatus -Worksheet $bad -Address $address) -ceq $state){throw "RSS_WRONG_FORMULA_ACCEPTED"}
    if((Get-ArkNo11StartupRssStatus -Worksheet $bad -Address $address) -ceq $state){throw "RSS_WRONG_FORMULA_ACCEPTED"}
    $checks++
    $literal=Fake-Sheet -Formula $formula -Value $state -HasFormula $false
    if((Get-No11ObservedStatus -Sheet $literal -Address $address -ExpectedStatus $state) -ceq $state){throw "RSS_LITERAL_ACCEPTED"}
    if((Get-No11RssCellStatus -Worksheet $literal -Address $address) -ceq $state){throw "RSS_LITERAL_ACCEPTED"}
    if((Get-ArkNo11StartupRssStatus -Worksheet $literal -Address $address) -ceq $state){throw "RSS_LITERAL_ACCEPTED"}
    $checks++
}
Write-Host "NO11_RSS_FORMULA_ECHO_OFFLINE_PASS=$checks"
# Independently exercise the formula whitelist without Excel/COM or account data.
Import-OneFunction -File (Join-Path $base "New-No11RssWorkbook.ps1") -Name "Assert-No11FormulaFootprint"

function New-No11FootprintMock {
    param([switch]$ExtraFormula,[switch]$MissingAnchor)
    $samples = @()
    foreach($address in @("L1","M1","N1","AA1","AL1")) {
        $hasFormula = ($address -in @("L1","N1","AA1","AL1"))
        if ($ExtraFormula -and $address -eq "M1") { $hasFormula = $true }
        if ($MissingAnchor -and $address -eq "AL1") { $hasFormula = $false }
        $one = [pscustomobject]@{ AddressLabel=$address; HasFormula=$hasFormula }
        $one | Add-Member -MemberType ScriptMethod -Name Address -Value {
            param($absRow,$absCol)
            return $this.AddressLabel
        }
        $samples += $one
    }
    $cells = [pscustomobject]@{ Items=$samples }
    $cells | Add-Member -MemberType ScriptMethod -Name Item -Value {
        param($row,$col)
        return $this.Items[$col-1]
    }
    $used = [pscustomobject]@{
        Rows=[pscustomobject]@{ Count=1 }
        Columns=[pscustomobject]@{ Count=5 }
        Cells=$cells
    }
    return [pscustomobject]@{ UsedRange=$used }
}

$footprintChecks=0
Assert-No11FormulaFootprint -Sheet (New-No11FootprintMock)
$footprintChecks++
foreach ($scenario in @(
    @{ Fake=(New-No11FootprintMock -ExtraFormula); Expected="NO11_EXTRA_FORMULA_FORBIDDEN:M1" },
    @{ Fake=(New-No11FootprintMock -MissingAnchor); Expected="NO11_REQUIRED_FORMULA_NOT_FOUND:AL1" }
)) {
    $failed = $false
    try {
        Assert-No11FormulaFootprint -Sheet $scenario.Fake
    } catch {
        if ($_.Exception.Message -cne $scenario.Expected) { throw }
        $failed = $true
    }
    if (-not $failed) { throw ("NO11_EXPECTED_FAIL_CLOSED_MISSING:{0}" -f $scenario.Expected) }
    $footprintChecks++
}
$oversized=New-No11FootprintMock
$oversized.UsedRange.Rows.Count = 50001
$oversizedBlocked=$false
try {
    Assert-No11FormulaFootprint -Sheet $oversized
} catch {
    if ($_.Exception.Message -cne "NO11_USED_RANGE_UNBOUNDED") { throw }
    $oversizedBlocked=$true
}
if (-not $oversizedBlocked) { throw "NO11_EXPECTED_UNBOUNDED_BLOCK_MISSING" }
$footprintChecks++
Write-Host ("NO11_FORMULA_FOOTPRINT_MOCK_PASS={0}" -f $footprintChecks)


# The producer no longer writes or opens a staging OOXML document.
# Windows test deliberately avoids loading a private or broker workbook.
Write-Host "NO11_READY_TEMPLATE_COPY_ONLY_DESIGN=TRUE"


# Offline categorical startup-diagnostic audit, with synthetic-only RSS cells.
function New-ArkStartupTestSheet {
    $cells = @{}
    foreach ($address in $expectedFormulas.Keys) {
        $cells[$address] = [pscustomobject]@{
            Formula = $expectedFormulas[$address]
            HasFormula = $true
            Value2 = ('=@' + $expectedFormulas[$address].Substring(1) + ' => ' + $states[$address])
            Text = ('=@' + $expectedFormulas[$address].Substring(1) + ' => ' + $states[$address])
        }
    }
    $sheet = [pscustomobject]@{Cells=$cells}
    $sheet | Add-Member -MemberType ScriptMethod -Name Range -Value {
        param($Address)
        return $this.Cells[$Address]
    }
    return $sheet
}
$okSheet = New-ArkStartupTestSheet
$okReport = Get-ArkNo11SheetStatusReport -Worksheet $okSheet
if ($okReport.Ready -ne $true) { throw 'NO11_STARTUP_DIAG_VALID_FORMULA_ECHO_REJECTED' }
$badSheet = New-ArkStartupTestSheet
$badSheet.Cells.AL1.Value2 = '#NAME?'
$badSheet.Cells.AL1.Text = '#NAME?'
$badReport = Get-ArkNo11SheetStatusReport -Worksheet $badSheet
if ($badReport.Ready -eq $true -or $badReport.AL1 -cne 'RSS_STATUS_UNRECOGNIZED') {
    throw 'NO11_STARTUP_DIAG_NAME_ERROR_NOT_BLOCKED'
}
$wrongSheet = New-ArkStartupTestSheet
$wrongSheet.Cells.N1.Formula = '=SUM(1,1)'
$wrongReport = Get-ArkNo11SheetStatusReport -Worksheet $wrongSheet
if ($wrongReport.Ready -eq $true -or $wrongReport.N1 -cne 'RSS_FORMULA_MISMATCH') {
    throw 'NO11_STARTUP_DIAG_WRONG_FORMULA_NOT_BLOCKED'
}
Write-Host 'NO11_STARTUP_DIAGNOSTIC_MOCK_PASS=3'


# AL1 18-header absolute/relative reference compatibility (READ ONLY synthetic).
# This must not turn a 10-column or filtered account list into a complete source.
function New-ArkRssPositionHeaderMock {
    param([string]$Formula,[string]$Value,[switch]$TamperHeader)
    $sheet = Fake-Sheet -Formula $Formula -Value $Value
    $names = @('銘柄コード', '銘柄名称', '口座区分', '保有数量', '発注数量', '平均取得価額', '時価', '前日比', '前日比率', '時価評価額', '評価損益額', '評価損益率', '銘柄情報等', 'JAX時価', 'JNX時価', 'PER', 'PBR', '配当利回り')
    $headerMap = @{}
    for ($i = 0; $i -lt $names.Count; $i++) {
        $word = $names[$i]
        if ($TamperHeader -and $i -eq 9) { $word = '不正な列' }
        $headerMap[[string](38 + $i)] = [pscustomobject]@{ Text=$word }
    }
    $cols = [pscustomobject]@{ Map=$headerMap }
    $cols | Add-Member -MemberType ScriptMethod -Name Item -Value {
        param($row,$col)
        if ($row -ne 2) { throw 'HEADER_ROW_INVALID' }
        return $this.Map[[string]$col]
    }
    $sheet | Add-Member -MemberType NoteProperty -Name Cells -Value $cols
    return $sheet
}
$absolute = '=RssPositionList($AL$2:$BC$2)'
if ($absolute.Length -ne 29) { throw 'NO11_AL1_ABSOLUTE_LENGTH_WRONG' }
$absoluteEcho = '=@RssPositionList($AL$2:$BC$2) => 配信中'
$relative = '=RssPositionList(AL2:BC2)'
foreach ($sample in @(
    @{ Formula=$absolute; Value=$absoluteEcho },
    @{ Formula=$absolute; Value='配信中' },
    @{ Formula=$relative; Value='=RssPositionList(AL2:BC2) => 配信中' }
)) {
    $mock = New-ArkRssPositionHeaderMock -Formula $sample.Formula -Value $sample.Value
    if ((Get-ArkNo11StartupRssStatus -Worksheet $mock -Address 'AL1') -cne '配信中') {
        throw 'NO11_AL1_VERIFIED_HEADER_18_REJECTED'
    }
}
foreach ($sample in @(
    @{ Formula='=RssPositionList($AL$2:$AU$2)'; Expected='RSS_FORMULA_MISMATCH' },
    @{ Formula='=RssPositionList(AL2:BD2)'; Expected='RSS_FORMULA_MISMATCH' },
    @{ Formula='=RssPositionList(AL2:BC2,1234)'; Expected='RSS_FORMULA_MISMATCH' },
    @{ Formula='=RssPositionList(AL2:BC2,1)'; Expected='RSS_FORMULA_MISMATCH' },
    @{ Formula='=RssPositionList(A2:J2)'; Expected='RSS_FORMULA_MISMATCH' }
)) {
    $mock = New-ArkRssPositionHeaderMock -Formula $sample.Formula -Value '配信中'
    if ((Get-ArkNo11StartupRssStatus -Worksheet $mock -Address 'AL1') -cne $sample.Expected) {
        throw 'NO11_AL1_INCOMPLETE_OR_FILTERED_SOURCE_NOT_BLOCKED'
    }
}
$wrongHeader = New-ArkRssPositionHeaderMock -Formula $absolute -Value $absoluteEcho -TamperHeader
if ((Get-ArkNo11StartupRssStatus -Worksheet $wrongHeader -Address 'AL1') -cne 'RSS_POSITION_HEADERS_MISMATCH') {
    throw 'NO11_AL1_HEADER_MAPPING_NOT_BLOCKED'
}
$badEcho = New-ArkRssPositionHeaderMock -Formula $absolute -Value '=@RssPositionList($AL$2:$BC$2) => #NAME?'
if ((Get-ArkNo11StartupRssStatus -Worksheet $badEcho -Address 'AL1') -cne 'RSS_STATUS_UNRECOGNIZED') {
    throw 'NO11_AL1_BAD_FEED_STATUS_NOT_BLOCKED'
}
Write-Host 'NO11_AL1_18_HEADER_REFERENCE_TESTS_PASS=10'
