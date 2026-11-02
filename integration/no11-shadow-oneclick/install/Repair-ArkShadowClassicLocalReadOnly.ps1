# Recover the original rich Ark Terminal read-only UI from the already installed
# six byte-pinned Classic assets. No downloading, remote code execution, broker
# writes, Excel process changes, source checkout, or shortcut replacement.
# Creates a SEPARATE desktop shortcut after complete local verification only.
param([switch]$OfflineSelfTest, [switch]$VerifyOnly)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$original = [ordered]@{
 'windows\Ark-Shadow-READ-ONLY.cmd'          = 'ab861a5c31a975b0673081226b449cac75c2891d'
 'windows\Start-ArkShadowReadOnly.ps1'       = '4bcb50f2d56038a475052fec04d7791515605caa'
 'ui\ark_shadow_ui.py'                      = '4a2d5f66f8ad32c47c16957904ffc86121d1d83a'
}
$classic = [ordered]@{
 'windows\Ark-Shadow-CLASSIC-READ-ONLY.cmd'       = '3e955c07d114df7459a5e18ea7d3a48bd61fe829'
 'windows\Start-ArkShadowClassicReadOnly.ps1'    = '47fc03c7e1c9bd1ccfb1976cbbfdfdb03357e611'
 'ui\ark_shadow_classic.py'                      = 'b726c04e769bd9b094d3a7af06b10e66dbb98115'
 'ui\classic\index.html'                        = 'ec79214fcc8ad9f200d7899ee562ed11b917b686'
 'ui\classic\ark-readonly-overlay.js'           = 'b0f27e1ad0e62b24052ce839c9eac29f934a677f'
 'ui\classic\ark-shadow-classic-bridge.js'      = 'aa487cf742079174e058a6c3e803e24a35494277'
}
$stage = 'START'
$probe = ''
$dest = Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\shadow-oneclick-app'
$target = Join-Path $dest 'windows\Ark-Shadow-CLASSIC-READ-ONLY.cmd'
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcut = Join-Path $desktop 'Ark Terminal Classic Shadow READ ONLY.lnk'

function Need([bool]$ok, [string]$reason) {
 if (-not $ok) { throw ('ARK_CLASSIC_REPAIR_'+$reason) }
}
function Mark([string]$name) {
 $script:stage = $name
 Write-Host ('ARK_CLASSIC_REPAIR_STAGE='+$name)
}

if ($OfflineSelfTest) {
 Need ($original.Count -eq 3 -and $classic.Count -eq 6) 'PIN_COUNT_INVALID'
 Need ($classic.Keys -contains 'ui\classic\index.html') 'CLASSIC_UI_ENTRY_REQUIRED'
 Need ($classic.Keys -contains 'ui\ark_shadow_classic.py') 'CLASSIC_BACKEND_REQUIRED'
 Write-Host 'ARK_CLASSIC_REPAIR_OFFLINE_SELFTEST=PASS'
 Write-Host 'ARK_CLASSIC_REPAIR_EXISTING_FILES_MODIFIED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}

try {
 Mark 'VERIFY_EXISTING_INSTALL'
 Need (Test-Path -LiteralPath $dest -PathType Container) 'SHADOW_INSTALL_MISSING'
 Need (Test-Path -LiteralPath $desktop -PathType Container) 'DESKTOP_MISSING'
 Need (-not [string]::IsNullOrWhiteSpace($env:TEMP)) 'TEMP_MISSING'
 $git = (Get-Command git.exe -CommandType Application -ErrorAction Stop).Source

 Mark 'VERIFY_ORIGINAL_AND_CLASSIC_BLOBS'
 foreach ($map in @($original,$classic)) {
  foreach ($relative in $map.Keys) {
   $file = Join-Path $dest $relative
   Need (Test-Path -LiteralPath $file -PathType Leaf) 'LOCAL_FILE_MISSING'
   $got = & $git hash-object --no-filters -- $file
   Need ($LASTEXITCODE -eq 0) 'GIT_HASH_FAILED'
   Need (([string]$got).Trim() -ceq [string]$map[$relative]) 'LOCAL_FILE_HASH_MISMATCH'
  }
 }
 Write-Host 'ARK_CLASSIC_REPAIR_BLOBS=9_OF_9_VERIFIED'

 Mark 'WINDOWS_LAUNCHER_OFFLINE_TEST'
 $entry = Join-Path $dest 'windows\Start-ArkShadowClassicReadOnly.ps1'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $entry -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'WINDOWS_LAUNCHER_TEST_FAILED'
 Write-Host 'ARK_CLASSIC_REPAIR_WINDOWS_TEST=PASS'

 Mark 'PYTHON_IMPORT_AND_CLASSIC_HTML_TEST'
 $py = Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
 Need (Test-Path -LiteralPath $py -PathType Leaf) 'PINNED_PYTHON_MISSING'

 # Do not use Python -c through Windows PowerShell 5.1. Its native argument
 # quoting can strip characters, which caused the preceding installer failure.
 $probe = Join-Path $env:TEMP ('ark-classic-probe-'+[guid]::NewGuid().ToString('N')+'.py')
 $pythonSource = @'
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import ark_shadow_classic as classic
from pathlib import Path
page, csp = classic.classic_document()
assert len(page) > 100000
assert b"ark-readonly-overlay.js" in page
assert b"ark-shadow-classic-bridge.js" in page
assert "script-src" in csp
assert "connect-src 'self'" in csp
print("ARK_CLASSIC_REPAIR_PYTHON_TEST=PASS")
'@
 [IO.File]::WriteAllText($probe, $pythonSource, [Text.UTF8Encoding]::new($false))
 $uiDir = Join-Path $dest 'ui'
 & $py -B $probe $uiDir
 Need ($LASTEXITCODE -eq 0) 'PYTHON_IMPORT_OR_ASSET_TEST_FAILED'

 Mark 'BROWSER_JAVASCRIPT_SYNTAX_TEST'
 $node = Get-Command node.exe -CommandType Application -ErrorAction SilentlyContinue
 Need ($null -ne $node) 'NODE_NOT_INSTALLED'
 foreach($js in @('ark-readonly-overlay.js','ark-shadow-classic-bridge.js')) {
  $file = Join-Path $dest ('ui\classic\'+$js)
  & $node.Source --check $file
  Need ($LASTEXITCODE -eq 0) 'JAVASCRIPT_SYNTAX_TEST_FAILED'
 }
 Write-Host 'ARK_CLASSIC_REPAIR_JAVASCRIPT_TEST=PASS'

 if ($VerifyOnly) {
  Write-Host 'ARK_CLASSIC_REPAIR_STATUS=VERIFIED_NO_SHORTCUT_CHANGE'
  Write-Host 'ARK_CLASSIC_REPAIR_ORIGINAL_SHORTCUTS_UNCHANGED=True'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }

 Mark 'CREATE_SEPARATE_DESKTOP_SHORTCUT'
 # The former desktop icons are NOT changed. Even if the old new-style
 # Shadow launcher currently fails, this link can be tested independently.
 $shell = New-Object -ComObject WScript.Shell
 if (Test-Path -LiteralPath $shortcut -PathType Leaf) {
  $existing = $shell.CreateShortcut($shortcut)
  $existingTarget = [string]$existing.TargetPath
  Need (-not [string]::IsNullOrWhiteSpace($existingTarget)) 'SHORTCUT_TARGET_EMPTY'
  Need ([IO.Path]::GetFullPath($existingTarget).Equals(
   [IO.Path]::GetFullPath($target),
   [StringComparison]::OrdinalIgnoreCase)) 'SHORTCUT_CONFLICT_NO_OVERWRITE'
  Write-Host 'ARK_CLASSIC_REPAIR_SHORTCUT=ALREADY_PRESENT_VERIFIED'
 } else {
  $new = $shell.CreateShortcut($shortcut)
  $new.TargetPath = $target
  $new.WorkingDirectory = (Split-Path -Parent $target)
  $new.Description = 'Ark Terminal original rich UI + Frozen No.1.1 Shadow, orders OFF'
  $new.Save()
  Need (Test-Path -LiteralPath $shortcut -PathType Leaf) 'SHORTCUT_SAVE_FAILED'
  $verify = $shell.CreateShortcut($shortcut)
  Need ([IO.Path]::GetFullPath([string]$verify.TargetPath).Equals(
   [IO.Path]::GetFullPath($target),
   [StringComparison]::OrdinalIgnoreCase)) 'SHORTCUT_POSTVERIFY_FAILED'
  Write-Host 'ARK_CLASSIC_REPAIR_SHORTCUT=CREATED'
 }
 Write-Host 'ARK_CLASSIC_REPAIR_STATUS=COMPLETE'
 Write-Host 'ARK_CLASSIC_REPAIR_OLD_NO11_UNCHANGED=True'
 Write-Host 'ARK_CLASSIC_REPAIR_EXISTING_NEW_SHADOW_UNCHANGED=True'
 Write-Host 'ARK_CLASSIC_REPAIR_LOCAL_URL=http://127.0.0.1:8769/'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
} catch {
 $message = [string]$_.Exception.Message
 if ($message -notmatch '^ARK_CLASSIC_REPAIR_[A-Z0-9_]+$') {
  $message = 'ARK_CLASSIC_REPAIR_UNEXPECTED_'+$stage
 }
 Write-Host ('ARK_CLASSIC_REPAIR_STATUS=BLOCKED|'+$message)
 Write-Host ('ARK_CLASSIC_REPAIR_FAILED_STAGE='+$stage)
 Write-Host ('ARK_CLASSIC_REPAIR_EXCEPTION_TYPE='+$_.Exception.GetType().Name)
 Write-Host 'ARK_CLASSIC_REPAIR_OLD_NO11_UNCHANGED=True'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
} finally {
 if ($probe -and (Test-Path -LiteralPath $probe -PathType Leaf)) {
  Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
 }
}
