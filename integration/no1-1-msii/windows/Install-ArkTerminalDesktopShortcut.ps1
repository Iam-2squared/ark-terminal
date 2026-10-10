# One-time Windows desktop shortcut creator. No Excel or broker operations.
param(
    [string]$ShortcutName = 'Ark Terminal No.1.1 READ ONLY.lnk'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($ShortcutName -notmatch '^[a-zA-Z0-9 ._-]+\.lnk$') {
    throw 'ARK_SHORTCUT_NAME_INVALID'
}
$cmd = Join-Path $PSScriptRoot 'Ark-Terminal-No11.cmd'
if (-not (Test-Path -LiteralPath $cmd -PathType Leaf)) {
    throw 'ARK_ONE_CLICK_COMMAND_MISSING'
}
$desktop = [Environment]::GetFolderPath('Desktop')
if (-not (Test-Path -LiteralPath $desktop -PathType Container)) {
    throw 'ARK_DESKTOP_NOT_AVAILABLE'
}
$shortcutPath = Join-Path $desktop $ShortcutName
if (Test-Path -LiteralPath $shortcutPath) {
    throw 'ARK_DESKTOP_SHORTCUT_ALREADY_EXISTS_DO_NOT_OVERWRITE'
}
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($shortcutPath)
$link.TargetPath = $cmd
$link.WorkingDirectory = $PSScriptRoot
$link.WindowStyle = 1
$link.Description = 'Ark Terminal No.1.1 RSS/Excel/UI READ ONLY startup (no trading)'
$link.Save()
Write-Host 'ARK_DESKTOP_SHORTCUT_CREATED=True'
Write-Host 'LIVE_ORDER_ENABLED=False'
