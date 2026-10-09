# Windows PowerShell 5.1 offline regression tests for observed RSS formula echo.
# No Excel, broker, COM, account information or order transmission.
$ErrorActionPreference = 'Stop'
$base = $PSScriptRoot
$expectedFormulas = [ordered]@{
    L1 = "=RssCapacityList(L2:L2)"
    N1 = "=RssOrderList(N2:W2,0,1)"
    AA1 = "=RssExecutionList(AA2:AI2,1)"
    AL1 = "=RssPositionList(AL2:AU2)"
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
    Invoke-Expression $funcs[0].Extent.Text
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
