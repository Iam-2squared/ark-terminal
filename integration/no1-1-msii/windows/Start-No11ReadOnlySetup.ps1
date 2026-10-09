# Single-command No.1.1 READ ONLY setup after user logs into MarketSpeed II.
# Never enables add-ins, places orders, changes old Workbook or authorizes trading.
param(
    [string]$WorkbookPath = "C:\Ark\Ark_No11_RSS_DefaultHeaders_v2.xlsx"
)
$ErrorActionPreference = "Stop"
$scriptRoot = $PSScriptRoot
$builder = Join-Path $scriptRoot "New-No11RssWorkbook.ps1"
$snapshotter = Join-Path $scriptRoot "Get-No11ReadOnlySnapshot.ps1"
$local = Join-Path $env:LOCALAPPDATA "ArkTerminal\No11"
# Each invocation writes its own receipt. The previous fixed receipt path
# is shared with legacy diagnostics and must never be accepted for v2.
$runId = [guid]::NewGuid().ToString("N")
$reportPath = Join-Path $local ("workbook-diagnostic-" + $runId + ".json")
$expectedWorkbook = [IO.Path]::GetFullPath($WorkbookPath)
$snapshotPath = Join-Path $local "snapshot.json"
$healthPath = Join-Path $local "source-health.json"

if (-not (Test-Path -LiteralPath $builder -PathType Leaf) -or
    -not (Test-Path -LiteralPath $snapshotter -PathType Leaf)) {
    throw "NO11_SETUP_FILES_MISSING"
}
$mode = if (Test-Path -LiteralPath $WorkbookPath -PathType Leaf) { "Diagnose" } else { "Create" }
Write-Host ("NO11_WORKBOOK_MODE={0}" -f $mode)
Write-Host ("NO11_DIAGNOSTIC_RUN_ID={0}" -f $runId)
$runStartedAt = Get-Date
& $builder -Mode $mode -WorkbookPath $WorkbookPath -ReportPath $reportPath
# Even if a nested PowerShell command returned after an error, no artifact from
# a different workbook or previous invocation can allow progress.
if (-not (Test-Path -LiteralPath $expectedWorkbook -PathType Leaf)) {
    throw "NO11_EXPECTED_WORKBOOK_NOT_PERSISTED"
}
if (-not (Test-Path -LiteralPath $reportPath -PathType Leaf)) {
    throw "NO11_DIAGNOSTIC_REPORT_MISSING"
}
$diagnostic = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($diagnostic.schemaId -ne "ARK_NO11_RSS_WORKBOOK_DIAGNOSTIC_V1") {
    throw "NO11_DIAGNOSTIC_SCHEMA_MISMATCH"
}
$observedWorkbook = [string]$diagnostic.workbook
if ([string]::IsNullOrWhiteSpace($observedWorkbook)) {
    throw "NO11_DIAGNOSTIC_WORKBOOK_IDENTITY_MISSING"
}
try {
    $actualWorkbook = [IO.Path]::GetFullPath($observedWorkbook)
} catch {
    throw "NO11_DIAGNOSTIC_WORKBOOK_IDENTITY_INVALID"
}
if (-not [string]::Equals($expectedWorkbook,$actualWorkbook,
    [StringComparison]::OrdinalIgnoreCase)) {
    throw "NO11_DIAGNOSTIC_WRONG_WORKBOOK"
}
$observedAt = [DateTimeOffset]::MinValue
if (-not [DateTimeOffset]::TryParse([string]$diagnostic.observedAt,[ref]$observedAt)) {
    throw "NO11_DIAGNOSTIC_TIMESTAMP_INVALID"
}
if ($observedAt -lt ([DateTimeOffset]$runStartedAt).AddSeconds(-2)) {
    throw "NO11_DIAGNOSTIC_FROM_PRIOR_RUN_FORBIDDEN"
}
Write-Host ("NO11_DIAGNOSTIC_VERIFIED_FOR_V2={0}" -f $runId)
Write-Host ("DIAGNOSTIC={0}" -f $reportPath)
if ($diagnostic.status -ne "RSS_STATUS_OBSERVED") {
    Write-Host "NO11_NEXT=CHECK_MARKETSPEED_LOGIN_AND_EXCEL_RSS_ADDIN_MANUALLY"
    Write-Host "NO11_READ_ONLY_STATUS=BLOCKED"
    Write-Host "ORDER_TRANSMISSION=FALSE"
    return
}
Write-Host "NO11_NEXT=READ_ONLY_ACCOUNT_SNAPSHOT"
$snapshotArgs = @{
    WorkbookName = (Split-Path -Leaf $WorkbookPath)
    WorkbookPath = $WorkbookPath
    SnapshotPath = $snapshotPath
    SourceHealthPath = $healthPath
    DoNotAutoOpenWorkbook = $true
}
& $snapshotter @snapshotArgs
Write-Host "NO11_SETUP_READ_ONLY_COMPLETE"
Write-Host ("SNAPSHOT_PATH={0}" -f $snapshotPath)
Write-Host ("HEALTH_PATH={0}" -f $healthPath)
Write-Host "OWNERSHIP=UNCLASSIFIED_UNTIL_HUMAN_CONFIRMATION"
Write-Host "RUNTIME_SAFETY=NOT_LIVE_CERTIFIED"
Write-Host "ORDER_TRANSMISSION=FALSE"
