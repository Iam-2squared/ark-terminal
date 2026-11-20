# Install the unified launcher in a separate clean Git worktree.
# Never reset, checkout, clean, pull or overwrite the user's modified repo.
# No broker, Excel, RSS, order, account transfer or authorizations.
param(
 [string]$ExistingRepo='',
 [string]$Destination='C:\ArkTerminal\no11-unified-2026-10-30',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$pinned='24b906e19a2623e45701311ca3fbb20dafe11c80'
$branch='research/no12-prebuy-causal-runtime-20261011'
$relative='research/no12-prebuy-causal-runtime-20261011/windows'
$stage='BEGIN'
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_UNIFIED_GIT_INSTALL_'+$reason)}
}
if($OfflineSelfTest){
 Need ($pinned -cmatch '^[0-9a-f]{40}$' -and
       $branch -ceq 'research/no12-prebuy-causal-runtime-20261011') 'STATIC'
 Write-Host 'NO11_UNIFIED_GIT_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_UNIFIED_GIT_INSTALL_EXISTING_SOURCE_CHANGED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 $stage='FIND_GIT_REPOSITORY'
 [void](Get-Command git.exe -ErrorAction Stop)
 if([string]::IsNullOrWhiteSpace($ExistingRepo)){
  $ExistingRepo=(Get-Location).Path
 }
 Need ([IO.Path]::IsPathRooted($ExistingRepo)) 'REPO_PATH_ABSOLUTE'
 $actual=@(& git -C $ExistingRepo rev-parse --show-toplevel)
 Need ($LASTEXITCODE -eq 0 -and $actual.Count -eq 1) 'REPO_NOT_FOUND'
 $repo=[IO.Path]::GetFullPath([string]$actual[0])
 $remote=@(& git -C $repo remote get-url origin)
 Need ($LASTEXITCODE -eq 0 -and $remote.Count -eq 1 -and
       [string]$remote[0] -match 'github\.com[:/]Iam-2squared/ark-terminal(?:\.git)?$') 'REPO_REMOTE_UNEXPECTED'
 $stage='VALIDATE_DESTINATION'
 Need ([IO.Path]::IsPathRooted($Destination)) 'DESTINATION_ABSOLUTE'
 $target=[IO.Path]::GetFullPath($Destination)
 Need (-not $target.Equals($repo,[StringComparison]::OrdinalIgnoreCase) -and
       -not $target.StartsWith(($repo+[IO.Path]::DirectorySeparatorChar),
          [StringComparison]::OrdinalIgnoreCase)) 'WOULD_OVERWRITE_SOURCE_WORKTREE'
 $parent=Split-Path -Parent $target
 [void][IO.Directory]::CreateDirectory($parent)
 $stage='PINNED_FETCH_NO_SOURCE_RESET'
 if(-not (Test-Path -LiteralPath $target)){
  & git -C $repo fetch --no-tags origin $branch | Out-Null
  Need ($LASTEXITCODE -eq 0) 'FETCH_FAILED'
  & git -C $repo cat-file -e ($pinned+'^{commit}')
  Need ($LASTEXITCODE -eq 0) 'PINNED_COMMIT_MISSING'
  $stage='CREATE_SEPARATE_WORKTREE'
  & git -C $repo worktree add --detach $target $pinned | Out-Null
  Need ($LASTEXITCODE -eq 0) 'WORKTREE_CREATE_FAILED'
 }
 $stage='VERIFY_PINNED_FILES'
 Need (Test-Path -LiteralPath $target -PathType Container) 'TARGET_NOT_FOLDER'
 $head=@(& git -C $target rev-parse HEAD)
 Need ($LASTEXITCODE -eq 0 -and $head.Count -eq 1 -and
       [string]$head[0] -ceq $pinned) 'INSTALLED_COMMIT_CHANGED'
 $dirty=@(& git -C $target status --porcelain)
 Need ($LASTEXITCODE -eq 0 -and $dirty.Count -eq 0) 'INSTALLED_WORKTREE_LOCALLY_MODIFIED'
 $windows=Join-Path $target ($relative.Replace('/','\'))
 $start=Join-Path $windows 'Start-No11UnifiedLauncher.ps1'
 $install=Join-Path $windows 'Install-No11UnifiedDesktopShortcut.ps1'
 Need ((Test-Path -LiteralPath $start -PathType Leaf) -and
       (Test-Path -LiteralPath $install -PathType Leaf)) 'LAUNCHER_FILES_NOT_PRESENT'
 $stage='OFFLINE_SELFTESTS'
 & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $start -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'UNIFIED_SELFTEST_FAILED'
 & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $install -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'SHORTCUT_SELFTEST_FAILED'
 $stage='INSTALL_SEPARATE_DESKTOP_SHORTCUT'
 & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $install
 Need ($LASTEXITCODE -eq 0) 'DESKTOP_SHORTCUT_FAILED'
 Write-Host 'NO11_UNIFIED_GIT_INSTALL=PASS'
 Write-Host ('NO11_UNIFIED_GIT_INSTALL_ROOT='+$target)
 Write-Host 'NO11_UNIFIED_GIT_INSTALL_EXISTING_SOURCE_CHANGED=False'
 Write-Host 'NO11_UNIFIED_GIT_INSTALL_LIVE_PERMISSION_NOT_GRANTED=True'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_UNIFIED_GIT_INSTALL_[A-Z0-9_]+$'){
  $reason='NO11_UNIFIED_GIT_INSTALL_UNEXPECTED_RUNTIME_FAILURE'
 }
 Write-Host ('NO11_UNIFIED_GIT_INSTALL_FAILURE_STAGE='+$stage)
 Write-Host ('NO11_UNIFIED_GIT_INSTALL=BLOCKED|'+$reason)
 Write-Host 'NO11_UNIFIED_GIT_INSTALL_NO_SOURCE_RESET=True'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}