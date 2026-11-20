# Windows PowerShell 5.1 READ ONLY UI model atomic commit. No Excel/order/Safety writes.
function Commit-No11UiReadModelAtomic {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$TemporaryPath,
        [Parameter(Mandatory=$true)][string]$DestinationPath,
        [Parameter(Mandatory=$true)][string]$PrivateRoot
    )
    $root = [IO.Path]::GetFullPath($PrivateRoot).TrimEnd('\')
    $src = [IO.Path]::GetFullPath($TemporaryPath)
    $dest = [IO.Path]::GetFullPath($DestinationPath)
    $expected = Join-Path $root 'ui-read-model.json'
    $rootAttrs = [IO.File]::GetAttributes($root)
    if (($rootAttrs -band [IO.FileAttributes]::Directory) -eq 0 -or
        ($rootAttrs -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'NO11_UI_MODEL_PRIVATE_DIRECTORY_UNSAFE'
    }
    if (-not [string]::Equals($dest,$expected,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'NO11_UI_MODEL_DESTINATION_NOT_APPROVED'
    }
    if (-not [string]::Equals([IO.Path]::GetDirectoryName($src),$root,[StringComparison]::OrdinalIgnoreCase) -or
        [IO.Path]::GetFileName($src) -cnotmatch '^ui-model-[a-f0-9]{32}\.json$') {
        throw 'NO11_UI_MODEL_TEMPORARY_PATH_UNSAFE'
    }
    if ([string]::Equals($src,$dest,[StringComparison]::OrdinalIgnoreCase) -or
        -not [IO.File]::Exists($src)) {
        throw 'NO11_UI_MODEL_SOURCE_MISSING_OR_COLLISION'
    }
    $srcAttrs = [IO.File]::GetAttributes($src)
    if (($srcAttrs -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
        ($srcAttrs -band [IO.FileAttributes]::Directory) -ne 0) {
        throw 'NO11_UI_MODEL_TEMPORARY_FILE_UNSAFE'
    }
    if ([IO.File]::Exists($dest)) {
        $destAttrs = [IO.File]::GetAttributes($dest)
        if (($destAttrs -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
            ($destAttrs -band [IO.FileAttributes]::Directory) -ne 0) {
            throw 'NO11_UI_MODEL_DESTINATION_FILE_UNSAFE'
        }
        # Windows PS5.1: use a non-null, unique, same-directory backup for File.Replace.
        # No non-atomic copy/delete fallback is permitted.
        $backup = Join-Path $root ('ui-model-backup-' + [Guid]::NewGuid().ToString('N') + '.json')
        if ([IO.File]::Exists($backup) -or [IO.Directory]::Exists($backup)) {
            throw 'NO11_UI_MODEL_BACKUP_PATH_COLLISION'
        }
        $replaced = $false
        try {
            [IO.File]::Replace($src,$dest,$backup)
            $replaced = $true
        } finally {
            # A failed replacement preserves any private forensic backup.
            if ($replaced -and [IO.File]::Exists($backup)) {
                [IO.File]::Delete($backup)
            }
        }
    } else {
        if ([IO.Directory]::Exists($dest)) {
            throw 'NO11_UI_MODEL_DESTINATION_DIRECTORY_COLLISION'
        }
        [IO.File]::Move($src,$dest)
    }
}
