# Compatible with Windows PowerShell 5.1 and PowerShell 7. No Excel access.
function Invoke-ArkCashLockedPipeline {
    param(
        [Parameter(Mandatory=$true)][System.Collections.IDictionary]$Request,
        [string]$PythonExecutable = "python",
        [string]$PipelineScript = (Join-Path $PSScriptRoot "phase57_cash_locked_cli.py")
    )
    $ErrorActionPreference = "Stop"
    $pythonCommand = Get-Command -Name $PythonExecutable -CommandType Application -ErrorAction Stop | Select-Object -First 1
    if (-not (Test-Path -LiteralPath $PipelineScript -PathType Leaf)) {
        throw "LOCKED_PIPELINE_SCRIPT_MISSING"
    }
    $tempDirectory = Join-Path ([IO.Path]::GetTempPath()) ("ark-cash-locked-" + [Guid]::NewGuid().ToString("N"))
    [void](New-Item -ItemType Directory -Path $tempDirectory -ErrorAction Stop)
    $requestPath = Join-Path $tempDirectory "request.json"
    $outputPath = Join-Path $tempDirectory "result.json"
    try {
        $utf8 = New-Object System.Text.UTF8Encoding($false)
        [IO.File]::WriteAllText($requestPath, ($Request | ConvertTo-Json -Depth 16), $utf8)
        # Only nonempty file paths/options are passed here. Quantities, symbols
        # and decimals stay typed JSON values, independent of locale/argv rules.
        $nativeArgs = @("-X", "utf8", $PipelineScript, "--request", $requestPath, "--output", $outputPath)
        & $pythonCommand.Source @nativeArgs | Out-Null
        $processExitCode = $LASTEXITCODE
        if ($processExitCode -ne 0) {
            throw "LOCKED_PIPELINE_PROCESS_FAILED:$processExitCode"
        }
        if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
            throw "LOCKED_PIPELINE_OUTPUT_MISSING"
        }
        $result = [IO.File]::ReadAllText($outputPath, $utf8) | ConvertFrom-Json -ErrorAction Stop
        if ($null -eq $result -or @("BLOCKED", "LOCKED_READY") -notcontains $result.status -or
            [string]::IsNullOrWhiteSpace([string]$result.stage) -or $result.inspectionOnly -ne $true) {
            throw "LOCKED_PIPELINE_OUTPUT_INVALID"
        }
        return $result
    }
    finally {
        Remove-Item -LiteralPath $tempDirectory -Recurse -Force -ErrorAction SilentlyContinue
    }
}
