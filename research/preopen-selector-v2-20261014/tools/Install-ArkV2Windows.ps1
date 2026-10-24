# Windows-native V2 setup; no Linux, no useradd, no secrets in arguments.
# Run once in ELEVATED Windows PowerShell 5.1+. The existing Windows user
# remains the worker and executes actual stages UNELEVATED.
# This script does not create market grants or open protected outcomes.
[CmdletBinding()]
param([string]$DownloadedSources, [string]$OwnerConfigFile)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'WINDOWS_REQUIRED_NO_LINUX_SETUP' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'ELEVATED_WINDOWS_POWERSHELL_REQUIRED_FOR_NTFS_ADMIN_SETUP'
}
$workerSid = $identity.User.Value
if ($workerSid -notmatch '^S-\d(-\d+)+$') { throw 'INVALID_WORKER_SID' }
$programRoot = 'C:\ProgramData\ArkTerminal'
$control = Join-Path $programRoot 'SelectorV2'
$sourceRoot = Join-Path $control 'Sources'
$local = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
if (-not $local) { throw 'LOCALAPPDATA_NOT_AVAILABLE' }
$private = Join-Path $local 'ArkTerminal\SelectorV2'
$outputRoot = Join-Path $private 'Output'
$journalRoot = Join-Path $private 'Journal'

function New-SafeDirectory([string]$PathValue) {
    if (Test-Path -LiteralPath $PathValue) {
        $item = Get-Item -LiteralPath $PathValue -Force
        if (-not $item.PSIsContainer) { throw 'DIRECTORY_TYPE_MISMATCH' }
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'JUNCTION_OR_SYMLINK_REFUSED'
        }
    } else {
        New-Item -ItemType Directory -Path $PathValue -Force | Out-Null
    }
}
function Invoke-Icacls([string[]]$Arguments) {
    & "$env:SystemRoot\System32\icacls.exe" @Arguments | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_ICACLS_FAILED' }
}
function Lock-Directory([string]$PathValue, [bool]$WorkerWritable, [bool]$AdminOwns) {
    Invoke-Icacls -Arguments @($PathValue, '/inheritance:r')
    $worker = if ($WorkerWritable) { ('*' + $workerSid + ':(OI)(CI)(F)') } else { ('*' + $workerSid + ':(OI)(CI)(RX)') }
    Invoke-Icacls -Arguments @($PathValue, '/grant:r', '*S-1-5-18:(OI)(CI)(F)',
                      '*S-1-5-32-544:(OI)(CI)(F)', $worker)
    if ($AdminOwns) {
        Invoke-Icacls -Arguments @($PathValue, '/setowner', '*S-1-5-32-544')
    }
}
function Lock-File([string]$PathValue) {
    Invoke-Icacls -Arguments @($PathValue, '/inheritance:r')
    Invoke-Icacls -Arguments @($PathValue, '/grant:r', '*S-1-5-18:(F)',
                     '*S-1-5-32-544:(F)', ('*' + $workerSid + ':(R)'))
    Invoke-Icacls -Arguments @($PathValue, '/setowner', '*S-1-5-32-544')
}

New-SafeDirectory $programRoot
New-SafeDirectory $control
New-SafeDirectory $sourceRoot
New-SafeDirectory $private
New-SafeDirectory $outputRoot
New-SafeDirectory $journalRoot

Lock-Directory $programRoot $false $true
Lock-Directory $control $false $true
Lock-Directory $sourceRoot $false $true
Lock-Directory $outputRoot $true $false
Lock-Directory $journalRoot $true $false

if ($DownloadedSources) {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    $restorer = Join-Path $repoRoot 'tools\windows_restore_mode_b_sources.py'
    if (-not (Test-Path -LiteralPath $restorer)) { throw 'WINDOWS_RESTORER_NOT_FOUND' }
    & py -3.12 $restorer verify --destination $DownloadedSources
    if ($LASTEXITCODE -ne 0) { throw 'PINNED_DOWNLOAD_VERIFICATION_FAILED' }
    $scope = Get-Content -LiteralPath (Join-Path $repoRoot 'MODE_B_SOURCE_SCOPE_DRAFT.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if (@($scope.source_objects).Count -ne 24) { throw 'PINNED_SCOPE_COUNT_DRIFT' }
    foreach ($entry in $scope.source_objects) {
        $prefix = 'Iam-2squared/J-quants-E/'
        if (-not $entry.source_id.StartsWith($prefix)) { throw 'UNEXPECTED_SOURCE_REPOSITORY' }
        $relative = 'raw/' + $entry.source_id.Substring($prefix.Length)
        if ($relative.Contains('..') -or $relative.Contains('\') -or $relative.Contains(':')) {
            throw 'UNSAFE_SOURCE_RELATIVE_PATH'
        }
        $subpath = $relative.Replace('/', [IO.Path]::DirectorySeparatorChar)
        $source = Join-Path $DownloadedSources $subpath
        $target = Join-Path $sourceRoot $subpath
        if (Test-Path -LiteralPath $target) { continue }
        $folder = Split-Path -Path $target -Parent
        New-SafeDirectory $folder
        Copy-Item -LiteralPath $source -Destination $target -ErrorAction Stop
    }
    & py -3.12 $restorer verify --destination $sourceRoot
    if ($LASTEXITCODE -ne 0) { throw 'OWNER_SOURCE_BYTES_VERIFICATION_FAILED' }
    Get-ChildItem -LiteralPath $sourceRoot -Directory -Recurse |
        ForEach-Object { Lock-Directory $_.FullName $false $true }
    Get-ChildItem -LiteralPath $sourceRoot -File -Recurse |
        ForEach-Object { Lock-File $_.FullName }
}

if ($OwnerConfigFile) {
    $target = Join-Path $control 'owner-channel.json'
    if (Test-Path -LiteralPath $target) { throw 'REFUSE_OWNER_CHANNEL_OVERWRITE' }
    $conf = Get-Content -LiteralPath $OwnerConfigFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($conf.schema -ne 'ARK_V2_OS_OWNER_CHANNEL_V1' -or
        $conf.worker_sid -ne $workerSid -or $conf.test_only -ne $false -or
        @($conf.grants.PSObject.Properties.Name).Count -lt 1 -or
        $conf.source_root -ne $sourceRoot -or
        $conf.output_root -ne $outputRoot -or
        $conf.journal_root -ne $journalRoot) {
        throw 'OWNER_CHANNEL_APPROVAL_OR_WORKER_CONTRACT_MISMATCH'
    }
    # Installing an independently reviewed approval is a separate admin act.
    Copy-Item -LiteralPath $OwnerConfigFile -Destination $target
    Lock-File $target
}
$summary = @{
    status = 'WINDOWS_DIRECTORIES_PREPARED'
    worker_sid = $workerSid
    linux_useradd_required = $false
    controller = $control
    installed_channel = (Test-Path -LiteralPath (Join-Path $control 'owner-channel.json'))
    source_bytes_verified = [bool]$DownloadedSources
    market_fits = 0
    research_approval_created = $false
    executionAllowed = $false
}
$summary | ConvertTo-Json -Compress
