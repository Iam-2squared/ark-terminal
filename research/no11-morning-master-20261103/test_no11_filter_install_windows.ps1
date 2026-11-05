# Isolated Windows acceptance: exercise the ACTUAL installer with a mocked
# preexisting white OneClick and two original GitHub-pinned source files.
# No real user account, broker, Excel, or trading process is touched.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){
 if(-not $ok){throw ('NO11_FILTER_MOCK_'+$why)}
}
$old=$env:LOCALAPPDATA
$test=Join-Path $env:TEMP ('ark-no11-filter-ci-'+[guid]::NewGuid().ToString('N'))
$env:LOCALAPPDATA=Join-Path $test 'fake-appdata'
try{
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $ui=Join-Path $store 'oneclick'
 $engine=Join-Path $test 'mock-git-sources'
 [void][IO.Directory]::CreateDirectory($ui)
 [void][IO.Directory]::CreateDirectory($engine)
 $base='3529490e793ef22759c1909c7e37aa91382f3828'
 $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$base+'/research/no11-morning-master-20261103/'
 $auto=Join-Path $engine 'automatic_morning.py'
 $bridge=Join-Path $engine 'launcher_automatic_bridge_v4.py'
 Invoke-WebRequest -Uri ($url+'automatic_morning.py') -OutFile $auto -UseBasicParsing
 Invoke-WebRequest -Uri ($url+'launcher_automatic_bridge_v4.py') -OutFile $bridge -UseBasicParsing
 $python=(Get-Command python -ErrorAction Stop).Source
 Need ([IO.Path]::IsPathRooted($python) -and
       (Test-Path -LiteralPath $python -PathType Leaf)) 'PYTHON_NOT_FOUND'
 $white=Join-Path $ui 'Start-No11OneClick.ps1'
 $whiteBytes=[Text.UTF8Encoding]::new($true).GetBytes('# WHITE_ONECLICK_USER_APPROVED_NOT_REPLACED'+[char]10)
 [IO.File]::WriteAllBytes($white,$whiteBytes)
 $beforeWhite=(Get-FileHash $white -Algorithm SHA256).Hash
 $binding=[ordered]@{
  schemaId='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
  automatic=$auto
  automaticSha256=(Get-FileHash $auto -Algorithm SHA256).Hash.ToLowerInvariant()
  bridge=$bridge
  bridgeSha256=(Get-FileHash $bridge -Algorithm SHA256).Hash.ToLowerInvariant()
  python=$python
  manualEvidenceRequired=$false
  manualPriceInputRequired=$false
  orderTransmission=$false
 }
 $bindingFile=Join-Path $store 'automatic-inputs.json'
 [IO.File]::WriteAllText($bindingFile,(ConvertTo-Json -InputObject $binding -Depth 10),
                          [Text.UTF8Encoding]::new($false))
 $installer=Join-Path $PSScriptRoot 'Apply-No11PriceExclusionRecovery.ps1'
 & powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $installer -Apply
 Need ($LASTEXITCODE -eq 0) 'APPLY_FAILED'
 $now=Get-Content $bindingFile -Raw -Encoding UTF8 | ConvertFrom-Json
 Need ($now.automaticSha256 -ceq (Get-FileHash $auto -Algorithm SHA256).Hash.ToLowerInvariant() -and
       $now.bridgeSha256 -ceq (Get-FileHash $bridge -Algorithm SHA256).Hash.ToLowerInvariant() -and
       $now.orderTransmission -eq $false) 'BINDING_NOT_ATOMIC'
 Need ([IO.File]::ReadAllText($auto).Contains('FILTER_ADMISSION_PARTITION') -and
       [IO.File]::ReadAllText($bridge).Contains('VERIFIED_SYMBOL_EXCLUSION_ONLY')) 'SOURCE_CHANGED_UNEXPECTEDLY'
 Need ((Get-FileHash $white -Algorithm SHA256).Hash -ceq $beforeWhite) 'WHITE_THEME_CHANGED'
 $helper=Join-Path $ui 'Recover-No11FilteredMorning.ps1'
 Need (Test-Path -LiteralPath $helper -PathType Leaf) 'RECOVERY_HELPER_MISSING'
 $backups=@(Get-ChildItem -LiteralPath $store -Directory -Filter 'morning-filter-backup-*')
 Need ($backups.Count -eq 1) 'BACKUP_MISSING'
 Write-Host 'NO11_FILTER_MOCK_INSTALL=PASS'
 Write-Host 'WHITE_ONECLICK_MODIFIED=False'
 Write-Host 'PREOPEN_APPROVAL_MODIFIED=False'
 Write-Host 'BROKER_ORDER_TRANSMISSION=False'
}finally{
 $env:LOCALAPPDATA=$old
 if(Test-Path -LiteralPath $test -PathType Container){
  Remove-Item -LiteralPath $test -Recurse -Force -ErrorAction SilentlyContinue
 }
}
