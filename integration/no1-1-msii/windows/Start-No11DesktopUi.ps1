# Single desktop workbook / UI2 read-only launcher. No broker order functions.
param(
 [ValidateRange(1024,65535)][int]$Port=8767,
 [ValidateRange(20,300)][int]$RefreshSeconds=30,
 [string]$WorkbookPath=(Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ark_No11_MSII_RSS.xlsx'),
 [switch]$NoBrowser,
 [switch]$NoAutoRefresh
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=Split-Path -Parent $PSScriptRoot
$server=Join-Path $root 'ui\ark_ui2_readonly_server.py'
$preview=Join-Path $PSScriptRoot 'Write-No11DesktopReadOnlyPreview.ps1'
$local=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No11'
$model=Join-Path $local 'ui-read-model.json'
$ownership=Join-Path $local 'ownership-baseline.json'
if(-not (Test-Path -LiteralPath $WorkbookPath -PathType Leaf)){throw 'DESKTOP_WORKBOOK_MISSING'}
if(-not (Test-Path -LiteralPath $ownership -PathType Leaf)){throw 'PRIVATE_OWNER_CONFIRMATION_MISSING'}
if(-not (Test-Path -LiteralPath $preview -PathType Leaf)){throw 'DESKTOP_UI_PREVIEW_SCRIPT_MISSING'}
if(-not (Test-Path -LiteralPath $server -PathType Leaf)){throw 'UI2_SERVER_CODE_MISSING'}
$py=Get-Command py -CommandType Application -ErrorAction SilentlyContinue
if($null -ne $py){
 $program=$py.Source
 $pythonArg=@('-3')
} else {
 $fallback=Get-Command python -CommandType Application -ErrorAction Stop
 $program=$fallback.Source
 $pythonArg=@()
}
& $preview -WorkbookPath $WorkbookPath -UiReadModelPath $model -OwnershipBaselinePath $ownership
if(-not $?){throw 'INITIAL_READ_ONLY_PREVIEW_BLOCKED'}
$pythonArg+=@($server,'--port',[string]$Port,
 '--workbook',$WorkbookPath,'--model',$model,
 '--ownership',$ownership,'--preview-script',$preview,
 '--refresh-seconds',[string]$RefreshSeconds,
 '--max-model-age-seconds','90')
if($NoBrowser -eq $false){$pythonArg+='--open-browser'}
if($NoAutoRefresh){$pythonArg+='--no-refresh'}
Write-Host 'NO11_UI2_DESKTOP_READ_ONLY_STARTING'
Write-Host ("URL=http://127.0.0.1:{0}/" -f $Port)
Write-Host 'MUTATIONS=FALSE'
Write-Host 'ORDER_TRANSMISSION=False'
Write-Host 'STOP=CTRL+C'
& $program @pythonArg
if($LASTEXITCODE -ne 0){throw 'UI2_DESKTOP_SERVER_EXITED_ABNORMALLY'}
