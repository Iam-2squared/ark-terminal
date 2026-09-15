param([switch]$RequireWindowsPowerShell)
$ErrorActionPreference = "Stop"
if ($RequireWindowsPowerShell -and ($PSVersionTable.PSEdition -ne "Desktop" -or $PSVersionTable.PSVersion.Major -ne 5)) {
    throw "WINDOWS_POWERSHELL_5_REQUIRED"
}
. (Join-Path $PSScriptRoot "phase57_cash_locked_bridge.ps1")
function Assert-True { param([bool]$Condition, [string]$Message); if (-not $Condition) { throw $Message } }
function Assert-Throws {
    param([scriptblock]$Action)
    $caught = $false
    try { & $Action | Out-Null } catch { $caught = $true }
    Assert-True $caught "EXPECTED_FAILURE_WAS_NOT_RAISED"
}

$unicodePart = [string][char]0x65e5 + [string][char]0x672c
$root = Join-Path ([IO.Path]::GetTempPath()) ("ark bridge spaces " + $unicodePart + " " + [Guid]::NewGuid().ToString("N"))
[void](New-Item -ItemType Directory -Path $root)
$utf8 = New-Object System.Text.UTF8Encoding($true)
$accountPath = Join-Path $root "synthetic account.json"
$oldCulture = [Threading.Thread]::CurrentThread.CurrentCulture
$oldLocation = Get-Location
$oldEnvironmentSymbol = $env:ARK_SYMBOL
$passed = 0
function Write-SyntheticAccount {
    param([double]$Cash)
    # Synthetic transport fixture only. No Excel, real account or live feed.
    $data = @{
        schemaId="ARK_ACCOUNT_READONLY_SNAPSHOT_V2"; capturedAt=[DateTimeOffset]::UtcNow.ToString("o")
        source="MARKETSPEED_II_RSS"; mode="READ_ONLY"
        positions=@(@{symbol="123A";quantity=40}); orders=@(); executions=@(); buyingPower=$Cash
        safety=@{executionAllowed=$false;brokerWriteAllowed=$false;excelOrderWriteAllowed=$false;
            rssOrderFunctionAllowed=$false;liveTradingAllowed=$false;paperTradingAllowed=$false;
            automaticPromotionAllowed=$false;productionUpdateAllowed=$false;transmitted=$false}
    }
    [IO.File]::WriteAllText($accountPath, ($data | ConvertTo-Json -Depth 12), $utf8)
}
function New-TestRequest {
    return @{
        schemaId="ARK_CASH_LOCKED_REQUEST_V1"; snapshotPath=$accountPath
        intent=@{symbol="7203.T";direction="LONG";side="BUY";positionEffect="OPEN";
            quantity=100;orderType="MARKET";limitPrice=$null;timeInForce="DAY"}
        externalPositions=@(@{symbol="123A";quantity=40}); estimatedNotional=300000.25
    }
}
try {
    # Parse the actual launcher using the same PowerShell edition as the user.
    $tokens = $null; $parseErrors = $null
    $ast = [Management.Automation.Language.Parser]::ParseFile(
        (Join-Path $PSScriptRoot "Start-ArkCashLocked.ps1"), [ref]$tokens, [ref]$parseErrors)
    Assert-True (@($parseErrors).Count -eq 0) "LAUNCHER_PARSE_FAILED"
    $clobbers = @($ast.FindAll({param($node)
        $node -is [Management.Automation.Language.AssignmentStatementAst] -and
        $node.Left -is [Management.Automation.Language.VariableExpressionAst] -and
        $node.Left.VariablePath.UserPath -ieq "Symbol"
    }, $true))
    Assert-True ($clobbers.Count -eq 0) "ORDER_SYMBOL_PARAMETER_CLOBBERED"
    $unsupported = @($ast.FindAll({param($node)
        $node -is [Management.Automation.Language.MemberExpressionAst] -and
        $node.Member.Extent.Text -ieq "ArgumentList"
    }, $true))
    Assert-True ($unsupported.Count -eq 0) "UNSUPPORTED_PROCESS_ARGUMENT_API"
    $passed++

    # Reproduce the original case-insensitive collision and show the request is
    # independent. The real launcher's AST above must not contain that assignment.
    $Symbol = "7203.T"
    $request = New-TestRequest
    foreach ($cell in @("123A", "")) { $symbol = $cell }
    Assert-True ([string]::IsNullOrEmpty($Symbol)) "CASE_INSENSITIVE_REPRO_NOT_TRIGGERED"
    Assert-True ($request.intent.symbol -ceq "7203.T") "REQUEST_SYMBOL_MUTATED"
    Write-SyntheticAccount 17
    $result = Invoke-ArkCashLockedPipeline -Request $request
    Assert-True ($result.status -eq "BLOCKED" -and $result.stage -eq "G9") "EXPECTED_CASH_BLOCK"
    Assert-True ($result.candidate.blockers -contains "INSUFFICIENT_CASH") "CASH_REASON_MISSING"
    Assert-True ($result.draft.intent.symbol -ceq "7203.T" -and $result.draft.intent.quantity -eq 100) "ORDER_FIELDS_SHIFTED"
    $passed++

    # Old ARK_* environment variables are not transport inputs anymore.
    $env:ARK_SYMBOL = "WRONG_ENVIRONMENT_VALUE"
    Write-SyntheticAccount 17
    $result = Invoke-ArkCashLockedPipeline -Request (New-TestRequest)
    Assert-True ($result.draft.intent.symbol -ceq "7203.T") "ENVIRONMENT_LEAKED_INTO_ORDER"
    $passed++

    # Non-ASCII/spaced paths, non-repository working directory, decimal-comma
    # locale, and the real Python pipeline are exercised together.
    Set-Location -LiteralPath $root
    [Threading.Thread]::CurrentThread.CurrentCulture = [Globalization.CultureInfo]::GetCultureInfo("fr-FR")
    Write-SyntheticAccount 1000000
    $result = Invoke-ArkCashLockedPipeline -Request (New-TestRequest)
    Assert-True ($result.status -eq "LOCKED_READY" -and $result.inspectionOnly -eq $true) "LOCKED_FIXTURE_FAILED"
    Assert-True ($result.draft.intent.quantity -eq 100) "QUANTITY_CHANGED_BY_LOCALE"
    Assert-True ($result.interface.formulaEvaluationAllowed -eq $false -and $result.interface.transmitted -eq $false) "UNSAFE_FIXTURE_RESULT"
    $passed++

    # A malformed quantity must fail the child process and the PS caller, never
    # become an empty pipeline or a success message.
    $bad = New-TestRequest; $bad.intent.quantity = "123A"
    Assert-Throws { Invoke-ArkCashLockedPipeline -Request $bad }
    $passed++

    $bad = New-TestRequest; $bad.intent.symbol = ""
    Assert-Throws { Invoke-ArkCashLockedPipeline -Request $bad }
    $passed++

    # Exit 0 with no output is not success.
    $silent = Join-Path $root "silent child.py"
    [IO.File]::WriteAllText($silent, "raise SystemExit(0)", $utf8)
    Assert-Throws { Invoke-ArkCashLockedPipeline -Request (New-TestRequest) -PipelineScript $silent }
    $passed++

    # Exit 0 with malformed JSON is not success either.
    $malformed = Join-Path $root "malformed child.py"
    $childText = "import pathlib, sys`npathlib.Path(sys.argv[sys.argv.index('--output') + 1]).write_text('{broken', encoding='utf-8')"
    [IO.File]::WriteAllText($malformed, $childText, $utf8)
    Assert-Throws { Invoke-ArkCashLockedPipeline -Request (New-TestRequest) -PipelineScript $malformed }
    $passed++

    Assert-Throws { Invoke-ArkCashLockedPipeline -Request (New-TestRequest) -PythonExecutable "ark-nonexistent-python-executable" }
    $passed++

    Write-Host "ARK_CASH_LOCKED_BRIDGE_TEST_PASS cases=$passed PowerShell=$($PSVersionTable.PSVersion)"
    Write-Host "SYNTHETIC_ACCOUNT_ONLY / NO_EXCEL / NO_RSS_CALL / NO_TRANSMISSION"
}
finally {
    [Threading.Thread]::CurrentThread.CurrentCulture = $oldCulture
    Set-Location -LiteralPath $oldLocation.Path
    $env:ARK_SYMBOL = $oldEnvironmentSymbol
    Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}
