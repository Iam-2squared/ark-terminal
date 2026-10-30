# Prepare a clean, isolated code worktree for the full MAX3 Monday LIVE mode.
# NEVER alters the existing locally modified C:\ArkTerminal\no12-launcher.
# Does not open Excel, read broker values, transfer funds or transmit orders.
param(
 [string]$ExistingRepo='C:\ArkTerminal\no12-launcher',
 [string]$Destination='C:\ArkTerminal\no11-live-2026-11-02',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$pinned='762d0214a4aa92b2d7e1ffdd5ab47a3a2f34bc91'
$branch='research/no12-prebuy-causal-runtime-20261011'
$engine='research/no12-prebuy-causal-runtime-20261011'
$checks=@('tools/no11_received_session_bootstrap.py',
          'tools/no11_received_session_controller.py',
          'windows/Run-No11ReceivedSessionOperatorLive.ps1')
function Need([bool]$condition,[string]$code){
 if(-not $condition){throw ('NO11_MONDAY_STAGE_'+$code)}
}
if($OfflineSelfTest){
 Need ($pinned -cmatch '^[a-f0-9]{40}$' -and $checks.Count -eq 3) 'STATIC_CONTRACT'
 Write-Host 'NO11_MONDAY_STAGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_MONDAY_STAGE_EXISTING_REPO_CHANGED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 [void](Get-Command git -ErrorAction Stop)
 Need ([IO.Path]::IsPathRooted($ExistingRepo) -and
       [IO.Path]::IsPathRooted($Destination)) 'ABSOLUTE_PATHS_REQUIRED'
 $ExistingRepo=[IO.Path]::GetFullPath($ExistingRepo)
 $Destination=[IO.Path]::GetFullPath($Destination)
 Need (-not $ExistingRepo.Equals($Destination,[StringComparison]::OrdinalIgnoreCase) -and
       -not $Destination.StartsWith(($ExistingRepo+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)) 'WORKTREE_OVERLAPS_ORIGINAL'
 Need (Test-Path -LiteralPath $ExistingRepo -PathType Container) 'ORIGINAL_REPO_NOT_FOUND'
 Need (Test-Path -LiteralPath (Split-Path -Parent $Destination) -PathType Container) 'DESTINATION_PARENT_MISSING'
 $root=@(& git -C $ExistingRepo rev-parse --show-toplevel)
 Need ($LASTEXITCODE -eq 0 -and $root.Count -eq 1 -and
       [IO.Path]::GetFullPath([string]$root[0]).Equals($ExistingRepo,[StringComparison]::OrdinalIgnoreCase)) 'ORIGINAL_GIT_WORKTREE_NOT_FOUND'
 $remote=@(& git -C $ExistingRepo remote get-url origin)
 Need ($LASTEXITCODE -eq 0 -and $remote.Count -eq 1 -and
       [string]$remote[0] -match 'github\.com[:/]Iam-2squared/ark-terminal(?:\.git)?$') 'REMOTE_REPOSITORY_IDENTITY'
 $already=Test-Path -LiteralPath $Destination
 if(-not $already){
  # Fetch only the target branch into the object database; DO NOT checkout,
  # pull, reset, stage or clean the existing local worktree.
  & git -C $ExistingRepo fetch --no-tags origin $branch | Out-Null
  Need ($LASTEXITCODE -eq 0) 'PINNED_BRANCH_FETCH_FAILED'
  & git -C $ExistingRepo cat-file -e ($pinned+'^{commit}')
  Need ($LASTEXITCODE -eq 0) 'PINNED_COMMIT_NOT_AVAILABLE'
  & git -C $ExistingRepo worktree add --detach $Destination $pinned | Out-Null
  Need ($LASTEXITCODE -eq 0) 'NEW_WORKTREE_CREATE_FAILED'
 }else{
  Need (Test-Path -LiteralPath $Destination -PathType Container) 'DESTINATION_IS_NOT_DIRECTORY'
 }
 $actual=@(& git -C $Destination rev-parse HEAD)
 Need ($LASTEXITCODE -eq 0 -and $actual.Count -eq 1 -and
       [string]$actual[0] -ceq $pinned) 'NEW_WORKTREE_HEAD_PIN_MISMATCH'
 $status=@(& git -C $Destination status --porcelain)
 Need ($LASTEXITCODE -eq 0 -and $status.Count -eq 0) 'NEW_WORKTREE_NOT_CLEAN'
 foreach($item in $checks){
  $file=Join-Path $Destination (($engine+'/'+$item).Replace('/','\'))
  Need (Test-Path -LiteralPath $file -PathType Leaf) 'PINNED_RUNTIME_FILE_MISSING'
 }
 $offline=Join-Path $Destination (($engine+'/windows/Run-No11ReceivedSessionOperatorLive.ps1').Replace('/','\'))
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $offline -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'NEW_LIVE_WRAPPER_OFFLINE_TEST_FAILED'
 Write-Host 'NO11_MONDAY_STAGE=PASS_CLEAN_ISOLATED_RUNTIME_ONLY'
 Write-Host ('NO11_MONDAY_STAGE_HEAD='+$pinned)
 Write-Host ('NO11_MONDAY_STAGE_PATH='+$Destination)
 Write-Host 'NO11_MONDAY_STAGE_LOCAL_MODIFICATIONS_PRESERVED=True'
 Write-Host 'NO11_MONDAY_STAGE_CASH_AND_BROKER_CONFIG=NOT_CREATED_OR_AUTHORIZED'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_MONDAY_STAGE_[A-Z0-9_]+$'){$reason='NO11_MONDAY_STAGE_LOCAL_GIT_OR_RUNTIME_BLOCKED'}
 Write-Host ('NO11_MONDAY_STAGE=BLOCKED|'+$reason)
 Write-Host 'NO11_MONDAY_STAGE_EXISTING_REPO_RESET=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
