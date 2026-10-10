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
        if($one -cne $state -or $two -cne $state){throw "RSS_VALID_STATUS_REJECTED:$address"}
        $checks++
    }
    foreach($value in @("#NAME?","$formula => #NAME?","$formula => 配信停止","$formula => $state MALFORMED","文字列 $state")){
        $sheet=Fake-Sheet -Formula $formula -Value $value
        $one=Get-No11ObservedStatus -Sheet $sheet -Address $address -ExpectedStatus $state
        $two=Get-No11RssCellStatus -Worksheet $sheet -Address $address
        if($one -ceq $state -or $two -ceq $state){throw "RSS_BAD_STATUS_ACCEPTED:$address"}
        $checks++
    }
    $bad=Fake-Sheet -Formula "=SUM(1,1)" -Value $state
    if((Get-No11ObservedStatus -Sheet $bad -Address $address -ExpectedStatus $state) -ceq $state){throw "RSS_WRONG_FORMULA_ACCEPTED"}
    if((Get-No11RssCellStatus -Worksheet $bad -Address $address) -ceq $state){throw "RSS_WRONG_FORMULA_ACCEPTED"}
    $checks++
    $literal=Fake-Sheet -Formula $formula -Value $state -HasFormula $false
    if((Get-No11ObservedStatus -Sheet $literal -Address $address -ExpectedStatus $state) -ceq $state){throw "RSS_LITERAL_ACCEPTED"}
    if((Get-No11RssCellStatus -Worksheet $literal -Address $address) -ceq $state){throw "RSS_LITERAL_ACCEPTED"}
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
