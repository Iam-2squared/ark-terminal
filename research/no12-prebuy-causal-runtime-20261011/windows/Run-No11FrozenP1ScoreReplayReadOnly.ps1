# Replay the frozen P1 scores against the verified private originals.
# No model fit, Excel automation, broker calls, orders or repository changes.
param(
    [string]$BaseArtifact = '',
    [string]$CorrectedArtifact = '',
    [switch]$RuntimeOnly,
    [string]$RuntimeBundleArtifact = '',
    [string]$PrivateRoot = '',
    [switch]$NoDialog,
    [switch]$OfflineSelfTest
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$baseZip = 'Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip'
$correctedZip = 'Ark_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZE_20261003_PRIVATE.zip'
$runtimeZip = 'Ark_No11_FrozenP1_Inference_20261023_PRIVATE.zip'
$sourceRel = 'research/persistent-watchlist-uptrend-first-entry-20261003-v2'
$correctedRel = $sourceRel + '/CORRECTED_LINEAGE_FAST_FREEZE_20261003'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$fullReplayScorer = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\tools\no11_frozen_p1_score_replay.py'))
$runtimeInstaller = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\tools\no11_frozen_p1_runtime_install.py'))
$scorer = $fullReplayScorer
if ($RuntimeOnly) { $scorer = $runtimeInstaller }

function New-ReplayArguments([string]$Root, [string]$Base, [string]$Corrected) {
    $arguments = @('--private-root', $Root, '--sample-per-fold', '0')
    if (-not [string]::IsNullOrWhiteSpace($Base)) { $arguments += @('--base', $Base) }
    if (-not [string]::IsNullOrWhiteSpace($Corrected)) { $arguments += @('--corrected', $Corrected) }
    return $arguments
}

function New-RuntimeArguments([string]$Root, [string]$Bundle) {
    $arguments = @('--private-root', $Root)
    if (-not [string]::IsNullOrWhiteSpace($Bundle)) { $arguments += @('--bundle', $Bundle) }
    return $arguments
}

function Get-ZipNamePattern([string]$Name) {
    return '^' + [regex]::Escape([IO.Path]::GetFileNameWithoutExtension($Name)) + '(?: ?\([0-9]+\))?\.zip$'
}

if ($OfflineSelfTest) {
    # Pure argument/path checks: no artifact reads, UI, Python imports or network.
    foreach ($scriptPath in @($fullReplayScorer, $runtimeInstaller)) {
        if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
            throw 'NO11_P1_REPLAY_SCORER_MISSING'
        }
    }
    $fixtureRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'fixture root'))
    $fixtureBase = Join-Path $fixtureRoot 'base artifact.zip'
    $fixtureCorrected = Join-Path $fixtureRoot 'corrected artifact.zip'
    $allArguments = @(New-ReplayArguments $fixtureRoot $fixtureBase $fixtureCorrected)
    $missingArguments = @(New-ReplayArguments $fixtureRoot '' '')
    $fixtureBundle = Join-Path $fixtureRoot $runtimeZip
    $runtimeArguments = @(New-RuntimeArguments $fixtureRoot $fixtureBundle)
    $missingRuntimeArguments = @(New-RuntimeArguments $fixtureRoot '')
    if ($allArguments.Count -ne 8 -or $allArguments[1] -cne $fixtureRoot -or
        $allArguments[2] -cne '--sample-per-fold' -or $allArguments[3] -cne '0' -or
        $allArguments[5] -cne $fixtureBase -or $allArguments[7] -cne $fixtureCorrected -or
        $missingArguments.Count -ne 4 -or
        $runtimeArguments.Count -ne 4 -or $runtimeArguments[1] -cne $fixtureRoot -or
        $runtimeArguments[2] -cne '--bundle' -or $runtimeArguments[3] -cne $fixtureBundle -or
        $missingRuntimeArguments.Count -ne 2 -or
        $baseZip -notmatch (Get-ZipNamePattern $baseZip) -or
        ($correctedZip -replace '\.zip$', ' (1).zip') -notmatch (Get-ZipNamePattern $correctedZip) -or
        ($runtimeZip -replace '\.zip$', ' (2).zip') -notmatch (Get-ZipNamePattern $runtimeZip) -or
        'unrelated.zip' -match (Get-ZipNamePattern $runtimeZip) -or
        'unrelated.zip' -match (Get-ZipNamePattern $baseZip)) {
        throw 'NO11_P1_REPLAY_ARGUMENT_SELFTEST_FAILED'
    }
    Write-Host 'NO11_FROZEN_P1_WINDOWS_OFFLINE_SELFTEST=PASS'
    Write-Host 'NO11_LIVE_DATA_ACCESSED=False'
    Write-Host 'NO11_NEW_MODEL_FIT=0'
    Write-Host 'ORDER_TRANSMISSION=False'
    exit 0
}

function Find-KnownZip([string[]]$Roots, [string]$Name) {
    $pattern = Get-ZipNamePattern $Name
    foreach ($directory in $Roots) {
        if (-not (Test-Path -LiteralPath $directory -PathType Container)) { continue }
        # Direct children only; never search the disk or accept a different ZIP name.
        $zipCandidates = @(Get-ChildItem -LiteralPath $directory -Filter '*.zip' -File |
            Where-Object { $_.Name -match $pattern } |
            Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1)
        if ($zipCandidates.Count -eq 1) { return $zipCandidates[0].FullName }
    }
    return ''
}

function Find-KnownDirectory([string[]]$Roots, [string]$Relative, [string]$ZipName, [string[]]$Required) {
    $candidates = @((Join-Path $repo $Relative))
    foreach ($directory in $Roots) {
        $candidates += @(
            $directory,
            (Join-Path $directory ('ark-terminal/' + $Relative)),
            (Join-Path $directory ([IO.Path]::GetFileNameWithoutExtension($ZipName) + '/ark-terminal/' + $Relative))
        )
    }
    foreach ($candidate in @($candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Container)) { continue }
        $present = $true
        foreach ($relativeFile in $Required) {
            if (-not (Test-Path -LiteralPath (Join-Path $candidate $relativeFile) -PathType Leaf)) {
                $present = $false
                break
            }
        }
        if ($present) { return [IO.Path]::GetFullPath($candidate) }
    }
    return ''
}

function Select-Artifact([string]$Name) {
    if ($NoDialog) { return '' }
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.OpenFileDialog
    $picker.Title = 'Select ' + $Name + ' (Cancel records the missing artifact)'
    $picker.Filter = 'ZIP archives (*.zip)|*.zip'
    $picker.FileName = $Name
    $picker.CheckFileExists = $true
    try {
        if ($picker.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            return $picker.FileName
        }
        return ''
    } finally { $picker.Dispose() }
}

function Invoke-Replay([string]$Executable, [string[]]$Prefix, [string[]]$Arguments) {
    $replayLines = @()
    & $Executable @Prefix -B $scorer @Arguments | Tee-Object -Variable replayLines | Out-Host
    $replayExitCode = $LASTEXITCODE
    return [pscustomobject]@{ ExitCode = $replayExitCode; Lines = @($replayLines) }
}

function Show-ReplayReport($Result) {
    $reportLines = @($Result.Lines | Where-Object { [string]$_ -match '^REPORT_JSON=' })
    if ($reportLines.Count -ne 1) { throw 'NO11_P1_REPLAY_REPORT_OUTPUT_MISSING' }
    $report = [IO.Path]::GetFullPath(([string]$reportLines[0]).Substring('REPORT_JSON='.Length))
    $rootPrefix = [IO.Path]::GetFullPath($PrivateRoot).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    if (-not $report.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase) -or
        [IO.Path]::GetFileName($report) -notmatch '^no11-frozen-p1-score-replay-[0-9a-f]{16}\.json$' -or
        -not (Test-Path -LiteralPath $report -PathType Leaf)) {
        throw 'NO11_P1_REPLAY_REPORT_PATH_INVALID'
    }
    Write-Host ('NO11_P1_REPLAY_PRIVATE_REPORT=' + $report)
    Write-Host 'NO11_NEW_MODEL_FIT=0'
    Write-Host 'NO11_PRODUCTION_READY=False'
    Write-Host 'ORDER_TRANSMISSION=False'
    if (-not $NoDialog) {
        Start-Process -FilePath (Join-Path $env:WINDIR 'explorer.exe') -ArgumentList ('/select,"' + $report + '"')
    }
}

function Test-ReplayRuntime([string]$Executable, [string[]]$Prefix) {
    $probe = "import sys; from importlib.metadata import version; assert sys.version_info[:2] == (3,12); assert all(version(k) == v for k,v in [('numpy','2.3.5'),('scipy','1.17.0'),('scikit-learn','1.8.0')]); import numpy, scipy, sklearn"
    try {
        & $Executable @Prefix -B -c $probe 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

try {
    if (-not (Test-Path -LiteralPath $scorer -PathType Leaf)) { throw 'NO11_P1_REPLAY_SCORER_MISSING' }
    if ([string]::IsNullOrWhiteSpace($PrivateRoot)) {
        if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) { throw 'NO11_P1_REPLAY_LOCALAPPDATA_MISSING' }
        $PrivateRoot = Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay'
    }
    $PrivateRoot = [IO.Path]::GetFullPath($PrivateRoot)
    $searchRoots = @($PrivateRoot)
    if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        $searchRoots += @((Join-Path $env:USERPROFILE 'Downloads'), (Join-Path $env:USERPROFILE 'Desktop'))
    }
    $desktop = [Environment]::GetFolderPath('Desktop')
    if (-not [string]::IsNullOrWhiteSpace($desktop)) { $searchRoots += $desktop }
    $searchRoots = @($searchRoots | Select-Object -Unique)

    if ($RuntimeOnly) {
        if ([string]::IsNullOrWhiteSpace($RuntimeBundleArtifact)) {
            $RuntimeBundleArtifact = Find-KnownZip $searchRoots $runtimeZip
        }
        if ([string]::IsNullOrWhiteSpace($RuntimeBundleArtifact)) {
            $RuntimeBundleArtifact = Select-Artifact $runtimeZip
        }
        $arguments = @(New-RuntimeArguments $PrivateRoot $RuntimeBundleArtifact)
        $artifactsMissing = [string]::IsNullOrWhiteSpace($RuntimeBundleArtifact)
    } else {
        if ([string]::IsNullOrWhiteSpace($BaseArtifact)) {
            $BaseArtifact = Find-KnownZip $searchRoots $baseZip
            if ([string]::IsNullOrWhiteSpace($BaseArtifact)) {
                $baseRoots = @((Join-Path $PrivateRoot 'verified\c0024055e9afa190')) + $searchRoots
                $BaseArtifact = Find-KnownDirectory $baseRoots $sourceRel $baseZip @(
                    'PRIVATE_INPUTS/features_numeric.npy', 'PRIVATE_INPUTS/features_categories.npy',
                    'PERSISTENT_GRID.jsonl.gz', 'WATCH_RECORDS.jsonl.gz'
                )
            }
            if ([string]::IsNullOrWhiteSpace($BaseArtifact)) { $BaseArtifact = Select-Artifact $baseZip }
        }
        if ([string]::IsNullOrWhiteSpace($CorrectedArtifact)) {
            $CorrectedArtifact = Find-KnownZip $searchRoots $correctedZip
            if ([string]::IsNullOrWhiteSpace($CorrectedArtifact)) {
                $requiredModels = @()
                foreach ($fold in 1..5) {
                    foreach ($head in @('QUALITY', 'ADVERSE', 'UPSIDE', 'preprocessor')) {
                        $requiredModels += ('PRIVATE_MODELS/P1_F{0}_{1}.pkl' -f $fold, $head)
                    }
                }
                $correctedRoots = @((Join-Path $PrivateRoot 'verified\0ede654a0a730f78')) + $searchRoots
                $CorrectedArtifact = Find-KnownDirectory $correctedRoots $correctedRel $correctedZip $requiredModels
            }
            if ([string]::IsNullOrWhiteSpace($CorrectedArtifact)) { $CorrectedArtifact = Select-Artifact $correctedZip }
        }
        $arguments = @(New-ReplayArguments $PrivateRoot $BaseArtifact $CorrectedArtifact)
        $artifactsMissing = [string]::IsNullOrWhiteSpace($BaseArtifact) -or [string]::IsNullOrWhiteSpace($CorrectedArtifact)
    }

    if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'NO11_P1_REPLAY_PYTHON312_LAUNCHER_MISSING' }
    if ($artifactsMissing) {
        # The stdlib-only missing-artifact path always produces a private receipt.
        $result = Invoke-Replay -Executable 'py' -Prefix @('-3.12') -Arguments $arguments
        Show-ReplayReport $result
        exit $result.ExitCode
    }

    # Authenticate and stage the whitelisted inputs before any dependency setup.
    $precheck = Invoke-Replay -Executable 'py' -Prefix @('-3.12') -Arguments ($arguments + @('--verify-only'))
    if ($precheck.ExitCode -ne 0) {
        Show-ReplayReport $precheck
        exit $precheck.ExitCode
    }
    if (@($precheck.Lines | Where-Object { [string]$_ -ceq 'PRECHECK=PASS' }).Count -ne 1) {
        throw 'NO11_P1_REPLAY_PRECHECK_RECEIPT_INVALID'
    }

    $pythonCommand = 'py'
    $pythonPrefix = @('-3.12')
    if (-not (Test-ReplayRuntime -Executable $pythonCommand -Prefix $pythonPrefix)) {
        $venvRoot = Join-Path $PrivateRoot 'runtime-py312-sklearn180'
        $venvPython = Join-Path $venvRoot 'Scripts\python.exe'
        foreach ($directory in @($PrivateRoot, $venvRoot)) {
            if ((Test-Path -LiteralPath $directory) -and
                ((Get-Item -LiteralPath $directory).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw 'NO11_P1_REPLAY_RUNTIME_REPARSE_POINT_BLOCKED'
            }
        }
        if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
            Write-Host 'NO11_P1_RUNTIME_SETUP=PRIVATE_VENV'
            & py -3.12 -B -m venv $venvRoot
            if ($LASTEXITCODE -ne 0) { throw 'NO11_P1_REPLAY_VENV_CREATE_FAILED' }
        }
        if (-not (Test-ReplayRuntime -Executable $venvPython -Prefix @())) {
            # Confirm this interpreter belongs to the private venv before pip writes.
            $identityProbe = 'import os,sys; assert sys.prefix != sys.base_prefix; assert os.path.normcase(os.path.realpath(sys.prefix)) == os.path.normcase(os.path.realpath(sys.argv[1]))'
            & $venvPython -B -c $identityProbe $venvRoot
            if ($LASTEXITCODE -ne 0) { throw 'NO11_P1_REPLAY_VENV_IDENTITY_INVALID' }
            Write-Host 'NO11_P1_RUNTIME_SETUP=PINNED_BINARY_DEPENDENCIES'
            & $venvPython -B -m pip --isolated install --quiet --disable-pip-version-check `
                --index-url https://pypi.org/simple --only-binary=:all: `
                numpy==2.3.5 scipy==1.17.0 scikit-learn==1.8.0
            if ($LASTEXITCODE -ne 0) { throw 'NO11_P1_REPLAY_DEPENDENCY_INSTALL_FAILED' }
            if (-not (Test-ReplayRuntime -Executable $venvPython -Prefix @())) {
                throw 'NO11_P1_REPLAY_PINNED_RUNTIME_INVALID'
            }
        }
        $pythonCommand = $venvPython
        $pythonPrefix = @()
    }

    if ($RuntimeOnly) {
        Write-Host 'NO11_P1_REPLAY_SCOPE=ORIGINAL_P1_RUNTIME_SAMPLE_REPLAY'
        Write-Host 'NO11_P1_FULL_OOF_REPLAY=False'
    } else {
        Write-Host 'NO11_P1_REPLAY_SCOPE=ALL_FROZEN_ROWS'
    }
    $result = Invoke-Replay -Executable $pythonCommand -Prefix $pythonPrefix -Arguments $arguments
    Show-ReplayReport $result
    exit $result.ExitCode
} catch {
    Write-Host ('NO11_FROZEN_P1_WINDOWS_REPLAY=BLOCKED|' + $_.Exception.Message)
    Write-Host 'NO11_NEW_MODEL_FIT=0'
    Write-Host 'NO11_PRODUCTION_READY=False'
    Write-Host 'ORDER_TRANSMISSION=False'
    exit 2
}
