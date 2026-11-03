# Additive private helper only. No existing engine files, models, Excel books,
# account data, launcher settings, order permissions or ledgers are changed.
param(
 [string]$SpecFile='',
 [string]$PythonExecutable='',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$ref='21811d459ca3b2e075a955411346e22bf2bf7676'
$raw="https://raw.githubusercontent.com/Iam-2squared/ark-terminal/$ref"
$files=@(
 @{Name='morning_master.py';Path='research/no11-morning-master-20261103/morning_master.py';Blob='4887918a01751f5107b6d6f56c4d838d75107ed2'},
 @{Name='test_morning_master.py';Path='research/no11-morning-master-20261103/test_morning_master.py';Blob='cdbe4e5ad29058d1bd0cc126240bb0ac9fc2161b'},
 @{Name='no11_auto_master_sources.py';Path='research/no12-prebuy-causal-runtime-20261011/tools/no11_auto_master_sources.py';Blob='18fa90ab91b0a75fae90184ddc5a1d470d623bdf'}
)
function GitBlob([string]$Path){
 [byte[]]$bytes=[IO.File]::ReadAllBytes($Path)
 [byte[]]$head=[Text.Encoding]::ASCII.GetBytes("blob $($bytes.Length)`0")
 $stream=[IO.MemoryStream]::new()
 $hash=[Security.Cryptography.SHA1]::Create()
 try{
  $stream.Write($head,0,$head.Length)
  $stream.Write($bytes,0,$bytes.Length)
  $stream.Position=0
  return [BitConverter]::ToString($hash.ComputeHash($stream)).Replace('-','').ToLowerInvariant()
 }finally{$hash.Dispose();$stream.Dispose()}
}
if($OfflineSelfTest){
 if($files.Count -ne 3 -or @($files|Where-Object {$_.Blob -cnotmatch '^[a-f0-9]{40}$'}).Count -ne 0){throw 'MANIFEST_INVALID'}
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$errors)
 if($errors.Count -ne 0){throw 'INSTALLER_PARSE_FAILED'}
 Write-Host 'MORNING_INSTALLER_SELFTEST=PASS_NO_NETWORK_NO_ORDERS'
 exit 0
}
$base=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
if(-not $PythonExecutable){
 $PythonExecutable=Join-Path $base 'frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
}
foreach($file in @($SpecFile,$PythonExecutable)){
 if(-not [IO.Path]::IsPathRooted($file) -or -not (Test-Path -LiteralPath $file -PathType Leaf)){
  throw 'MORNING_SPEC_OR_PINNED_PYTHON_MISSING'
 }
}
[void](Get-Command node -ErrorAction Stop)
$config=Get-Content -LiteralPath $SpecFile -Raw -Encoding UTF8|ConvertFrom-Json
if(-not [IO.Path]::IsPathRooted([string]$config.outputRoot)){
 throw 'MORNING_OUTPUT_NOT_ABSOLUTE'
}
[void][IO.Directory]::CreateDirectory([string]$config.outputRoot)
$work=Join-Path $base ('morning-master-tools-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($work)
$oldPythonPath=[Environment]::GetEnvironmentVariable('PYTHONPATH','Process')
try{
 foreach($item in $files){
  $target=Join-Path $work $item.Name
  Invoke-WebRequest -Uri ($raw+'/'+$item.Path) -OutFile $target -UseBasicParsing -ErrorAction Stop
  if((GitBlob $target) -cne $item.Blob){throw ('MORNING_SOURCE_HASH_MISMATCH_'+$item.Name)}
 }
 Write-Host 'MORNING_SOURCE_HASHES=PASS'
 & $PythonExecutable -B -X utf8 (Join-Path $work 'test_morning_master.py')
 if($LASTEXITCODE -ne 0){throw 'MORNING_CHAIN_UNIT_TESTS_FAILED'}
 Write-Host 'MORNING_CHAIN_UNIT_TESTS=PASS'
 # xlrd is installed into this NEW private folder, never the frozen Python environment.
 $deps=Join-Path $work 'xls-reader'
 $requirements=Join-Path $work 'requirements-xls.txt'
 [IO.File]::WriteAllText($requirements,
  "xlrd==2.0.2 --hash=sha256:ea762c3d29f4cca48d82df517b6d89fbce4db3107f9d78713e48cd321d5c9aa9`n",
  [Text.UTF8Encoding]::new($false))
 & $PythonExecutable -m pip --isolated --disable-pip-version-check install `
  --no-input --no-deps --no-compile --only-binary=:all: --require-hashes `
  --index-url 'https://pypi.org/simple' --target $deps --requirement $requirements
 if($LASTEXITCODE -ne 0){throw 'PRIVATE_XLS_READER_INSTALL_FAILED'}
 [Environment]::SetEnvironmentVariable('PYTHONPATH',$deps,'Process')
 Write-Host 'PINNED_MODEL_ENVIRONMENT_MODIFIED=False'
 $runner=Join-Path $work 'morning_master.py'
 Write-Host ('MORNING_RUNNER='+$runner)
 & $PythonExecutable -B -X utf8 $runner prepare --spec $SpecFile
 if($LASTEXITCODE -ne 0){throw 'MORNING_SOURCE_PREPARATION_BLOCKED'}
 Write-Host 'EXISTING_ENGINE_FILES_MODIFIED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}finally{
 [Environment]::SetEnvironmentVariable('PYTHONPATH',$oldPythonPath,'Process')
}
