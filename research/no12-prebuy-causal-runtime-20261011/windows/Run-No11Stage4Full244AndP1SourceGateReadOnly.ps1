# Offline Ark No.1.1: verified 40-symbol report -> full 244 original
# RC2 State9 technical replay -> First Entry P1_Q70 SOURCE-only gate.
# No model fit, Excel automation, orders or live broker interactions.
param(
    [switch]$OfflineSelfTest,
    [string]$Repo="C:\ArkTerminal\no12-launcher",
    [string]$CaptureRoot="",
    [string]$OriginalSymbols=""
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$stage3Rel="research/no12-prebuy-causal-runtime-20261011/tools/no11_2026_rc2_sparse_missing_research.py"
$stage4Rel="research/no12-prebuy-causal-runtime-20261011/tools/no11_2026_first_entry_p1_source_gate.mjs"
$stage3Blob="50a3a659127ce5f4d82c6dc56a99931664a36907"
$stage4Blob="afaf67050a971bd1cf920c001bf6fa8cf8e54e1c"
$oldName="no11-2026-rc2-sparse-research-d30f81c94b3f5313.json"
$oldSha="d30f81c94b3f5313dcd1c2543cc393bca4c095c3e73e22336994c9b686b405ca"

if ($OfflineSelfTest) {
    if ($stage3Blob.Length -ne 40 -or $stage4Blob.Length -ne 40 -or $oldSha.Length -ne 64) {
        throw "NO11_STAGE4_STATIC_PIN_INVALID"
    }
    Write-Host "NO11_STAGE4_WINDOWS_RUNNER_OFFLINE_SELFTEST=PASS"
    Write-Host "NO11_PRODUCTION_READY=False"
    Write-Host "ORDER_TRANSMISSION=False"
    exit 0
}
if ([string]::IsNullOrWhiteSpace($CaptureRoot)) {
    $CaptureRoot=Join-Path $env:LOCALAPPDATA "ArkTerminal\No12\training-capture"
}
if ([string]::IsNullOrWhiteSpace($OriginalSymbols)) {
    $OriginalSymbols=Join-Path $env:USERPROFILE "Downloads\rss_symbols_to_acquire.txt"
}
if (-not (Test-Path -LiteralPath $Repo -PathType Container) -or
    -not (Test-Path -LiteralPath $CaptureRoot -PathType Container)) {
    throw "NO11_STAGE4_PRIVATE_DIRECTORY_MISSING"
}
if ((Get-Item -LiteralPath $CaptureRoot).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw "NO11_STAGE4_PRIVATE_ROOT_SYMLINK_BLOCKED"
}

function Assert-TrackedScript([string]$rel,[string]$expected) {
    $file=Join-Path $Repo $rel
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "NO11_STAGE4_RESEARCH_SCRIPT_MISSING"
    }
    $actual=@(git -C $Repo hash-object "--path=$rel" $file)
    if ($LASTEXITCODE -ne 0 -or $actual.Count -ne 1 -or $actual[0] -cne $expected) {
        throw "NO11_STAGE4_SCRIPT_PIN_MISMATCH"
    }
    return $file
}
function Private-ReportFromStdout([object[]]$lines,[string]$label) {
    $matched=@($lines | Where-Object { $_ -like "$label=*" })
    if ($matched.Count -ne 1) { throw "NO11_STAGE4_REPORT_OUTPUT_MISSING" }
    $name=$matched[0].Substring($label.Length+1)
    $absolute=[IO.Path]::GetFullPath($name)
    $root=[IO.Path]::GetFullPath($CaptureRoot).TrimEnd('\')+'\'
    if (-not $absolute.StartsWith($root,[StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $absolute -PathType Leaf)) {
        throw "NO11_STAGE4_REPORT_OUTSIDE_PRIVATE_ROOT"
    }
    return $absolute
}
$stage3=Assert-TrackedScript $stage3Rel $stage3Blob
$stage4=Assert-TrackedScript $stage4Rel $stage4Blob

$prior=Join-Path $CaptureRoot $oldName
if (-not (Test-Path -LiteralPath $prior -PathType Leaf) -or
    (Get-FileHash -LiteralPath $prior -Algorithm SHA256).Hash.ToLowerInvariant() -cne $oldSha) {
    throw "NO11_STAGE4_40_SYMBOL_BASELINE_HASH_MISMATCH"
}
$old=Get-Content -LiteralPath $prior -Raw -Encoding UTF8 | ConvertFrom-Json
if ($old.schemaId -cne "ARK_NO11_2026_RSS_ORIGINAL_RC2_SPARSE_MISSING_REPLAY_V1" -or
    $old.actualReplayedOriginalFirstEligibleCount -ne 40 -or
    $old.sourceCoverageCounters.meetsSourceAnchorAndCurrentFloor -ne 244 -or
    $old.researchTechnicalTickCounts.totalOriginalDualEngineTickAgreements -ne 13080 -or
    $old.productionReady -ne $false -or $old.orderTransmission -ne $false) {
    throw "NO11_STAGE4_40_SYMBOL_BASELINE_CONTRACT_MISMATCH"
}
if (-not (Test-Path -LiteralPath $OriginalSymbols -PathType Leaf)) {
    Add-Type -AssemblyName System.Windows.Forms
    $picker=New-Object System.Windows.Forms.OpenFileDialog
    $picker.FileName="rss_symbols_to_acquire.txt"
    $picker.Filter="Text files (*.txt)|*.txt"
    try {
        if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
            throw "NO11_STAGE4_ORIGINAL_MASTER_SELECTION_CANCELLED"
        }
        $OriginalSymbols=$picker.FileName
    } finally { $picker.Dispose() }
}

$pyArgs=@(
    '--repo',$Repo,
    '--capture-root',$CaptureRoot,
    '--original-symbols',$OriginalSymbols,
    '--source-index',(Join-Path $CaptureRoot 'no11-2026-source-index-4828a387aca426b9.jsonl'),
    '--audit-report',(Join-Path $CaptureRoot 'rss-all-source-audit-04294e96395361e6.json'),
    '--baseline-report',(Join-Path $CaptureRoot 'no11-2026-original-rc2-technical-2e79d4f530ed492b.json'),
    '--output-dir',$CaptureRoot,
    '--previous','2026-10-09',
    '--day','2026-10-13',
    '--max-symbols','950',
    '--max-replayed','244',
    '--export-asof'
)
Write-Host "NO11_STAGE4_TECHNICAL_RC2_SCOPE=244_OF_950"
$stage3Output=@()
& py -3.12 -B $stage3 @pyArgs | Tee-Object -Variable stage3Output
if ($LASTEXITCODE -ne 0) { throw "NO11_STAGE4_FULL_RC2_FAILED" }

$stage3Report=Private-ReportFromStdout @($stage3Output) 'NO11_RC2_SPARSE_REPORT'
$full=Get-Content -LiteralPath $stage3Report -Raw -Encoding UTF8 | ConvertFrom-Json
if ($full.status -cne "TECHNICAL_SPARSE_DUAL_ENGINE_PASS_RESEARCH_ONLY" -or
    $full.actualReplayedOriginalFirstEligibleCount -ne 244 -or
    $full.eligibleNotReplayed -ne 0 -or
    $full.fullEligibleSetTechnicalReplayed -ne $true -or
    $full.privateState9AsOfEventRows -ne 79788 -or
    @($full.technicalErrorCounts.PSObject.Properties).Count -ne 0 -or
    $full.productionReady -ne $false -or $full.orderTransmission -ne $false) {
    throw "NO11_STAGE4_FULL_244_RESEARCH_RESULT_INVALID"
}
Write-Host "NO11_STAGE4_ORIGINAL_RC2_FULL_244=PASS_RESEARCH_ONLY"

$nodeArgs=@(
    '--repo',$Repo,
    '--state9-report',$stage3Report,
    '--original-symbols',$OriginalSymbols,
    '--output-dir',$CaptureRoot
)
$stage4Output=@()
& node $stage4 @nodeArgs | Tee-Object -Variable stage4Output
if ($LASTEXITCODE -ne 0) { throw "NO11_STAGE4_P1_SOURCE_AUDIT_FAILED" }

$finalPath=Private-ReportFromStdout @($stage4Output) 'NO11_FIRST_ENTRY_STAGE4_REPORT'
$final=Get-Content -LiteralPath $finalPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($final.status -cne "STATE9_ASOF_SOURCE_VERIFIED_FIRST_ENTRY_P1_Q70_NATIVE_BLOCKED" -or
    $final.researchState9AsOfCoverage.state9ResearchSymbols -ne 244 -or
    $final.originalP1FeatureRowsReproduced -ne 0 -or
    $final.originalP1ScoresComputed -ne 0 -or
    $final.originalBuyIntentsProduced -ne 0 -or
    $final.productionReady -ne $false -or $final.orderTransmission -ne $false) {
    throw "NO11_STAGE4_P1_REPORT_NOT_SOURCE_ONLY"
}
Write-Host "NO11_STAGE4_STATE9_TO_FIRST_ENTRY_P1_SOURCE=PASS_RESEARCH_ONLY"
Write-Host "NO11_STAGE4_SMALL_PRIVATE_RECEIPT=$finalPath"
Write-Host "NO11_ORIGINAL_FIRST_ENTRY_SCORE_ROWS=0"
Write-Host "NO11_PRODUCTION_READY=False"
Write-Host "ORDER_TRANSMISSION=False"
Start-Process explorer.exe -ArgumentList ('/select,"'+$finalPath+'"')
