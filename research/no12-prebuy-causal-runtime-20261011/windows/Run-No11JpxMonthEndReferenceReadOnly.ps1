# Fetch the official JPX MONTH-END listed-issues workbook and classify
# private No.1.1 78 G1 candidates. Reference only, no same-day certification.
# Never uses Excel COM, MSII RSS, live broker, trading orders or original files.
param([switch]$OfflineSelfTest,[string]$JpxWorkbook='')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$rev='8f4569fcdb283764a990dc2fc6f536fafd116b26'
$expected='ad8b946a360dc87efa214859de9b928c4e54e4fd'
$sourceRel='research/no12-prebuy-causal-runtime-20261011/tools/no11_jpx_monthly_equity_reference.py'
$root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
$private=Join-Path $root 'jpx-month-end-reference\2026-10-30'
$audit=Join-Path $root 'external-security-review\2026-10-30\equity-type-provisional-304f08b2eed20c63.json'
$python=Join-Path $root 'frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
$original='https://www.jpx.co.jp/markets/statistics-equities/misc/01.html'
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_JPX_REFERENCE_STAGE_'+$reason)}
}
function Blob([string]$file){
 $h=@(& git hash-object --no-filters $file)
 Need ($LASTEXITCODE -eq 0 -and $h.Count -eq 1 -and
       [string]$h[0] -cmatch '^[0-9a-f]{40}$') 'GIT_HASH'
 return [string]$h[0]
}
function Sha([string]$file){
 return (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
}
function LinkFromOfficialPage {
 $page=Invoke-WebRequest -Uri $original -UseBasicParsing
 Need ($null -ne $page -and -not [string]::IsNullOrEmpty([string]$page.Content)) 'JPX_PAGE_UNAVAILABLE'
 $rx='(?i)href\s*=\s*["''](?<href>[^"'']+\.xlsx(?:\?[^"'']*)?)["'']'
 $links=@([regex]::Matches([string]$page.Content,$rx) |
    ForEach-Object {$_.Groups['href'].Value} |
    Where-Object {$_ -match '(?i)data_j\.xlsx(?:\?|$)'} | Select-Object -Unique)
 Need ($links.Count -eq 1) 'JPX_LATEST_XLSX_LINK_NOT_UNIQUE'
 $uri=[Uri]::new([Uri]$original,[string]$links[0])
 Need ($uri.Scheme -ceq 'https' -and $uri.Host -ceq 'www.jpx.co.jp' -and
       $uri.AbsolutePath -match '(?i)/data_j\.xlsx$') 'JPX_XLSX_ORIGIN_INVALID'
 return $uri.AbsoluteUri
}
if($OfflineSelfTest){
 Need (-not $JpxWorkbook -and $rev -cmatch '^[a-f0-9]{40}$' -and
       $expected -cmatch '^[a-f0-9]{40}$') 'OFFLINE_PINS_INVALID'
 Write-Host 'NO11_JPX_REFERENCE_STAGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_JPX_OFFICIAL_SITE_ACCESSED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$phase='CHECK_INPUTS'
try{
 [void](Get-Command git -ErrorAction Stop)
 Need (Test-Path -LiteralPath $audit -PathType Leaf) 'ORIGINAL_G1_AUDIT_MISSING'
 Need (Test-Path -LiteralPath $python -PathType Leaf) 'PINNED_PYTHON_MISSING'
 [void][IO.Directory]::CreateDirectory($private)
 Need (((Get-Item -LiteralPath $private -Force).Attributes -band
        [IO.FileAttributes]::ReparsePoint) -eq 0) 'PRIVATE_ROOT_REPARSE'
 $phase='PINNED_PYTHON'
 $reader=Join-Path $private 'no11_jpx_monthly_equity_reference.py'
 if(-not (Test-Path -LiteralPath $reader -PathType Leaf)){
  $tmp=Join-Path $env:TEMP ('ark-jpx-'+[guid]::NewGuid().ToString('N')+'.py')
  try{
   $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$rev+'/'+$sourceRel
   Invoke-WebRequest -Uri $url -UseBasicParsing -OutFile $tmp
   Need ((Blob $tmp) -ceq $expected) 'PYTHON_SOURCE_PIN_MISMATCH'
   & $python -B -m py_compile $tmp
   Need ($LASTEXITCODE -eq 0) 'PYTHON_SYNTAX_INVALID'
   [IO.File]::Copy($tmp,$reader,$false)
  }finally{
   if(Test-Path -LiteralPath $tmp -PathType Leaf){[IO.File]::Delete($tmp)}
  }
 }
 Need ((Blob $reader) -ceq $expected) 'PREVIOUS_READER_CHANGED'
 $phase='JPX_MONTH_END_WORKBOOK'
 if($JpxWorkbook){
  Need ([IO.Path]::IsPathRooted($JpxWorkbook) -and
        (Test-Path -LiteralPath $JpxWorkbook -PathType Leaf)) 'USER_XLSX_MISSING'
  $jpx=[IO.Path]::GetFullPath($JpxWorkbook)
 }else{
  $download=LinkFromOfficialPage
  $tmp=Join-Path $private ('jpx-download-'+[guid]::NewGuid().ToString('N')+'.xlsx')
  try{
   Invoke-WebRequest -Uri $download -UseBasicParsing -OutFile $tmp
   Need ((Get-Item -LiteralPath $tmp).Length -gt 10000 -and
         (Get-Item -LiteralPath $tmp).Length -le 15000000) 'JPX_XLSX_SIZE'
   $digest=Sha $tmp
   $jpx=Join-Path $private ('jpx-2026-09-month-end-'+$digest+'.xlsx')
   if(Test-Path -LiteralPath $jpx -PathType Leaf){
    Need ((Sha $jpx) -ceq $digest) 'PREVIOUS_JPX_SOURCE_CHANGED'
   }else{
    [IO.File]::Copy($tmp,$jpx,$false)
   }
  }finally{
   if(Test-Path -LiteralPath $tmp -PathType Leaf){[IO.File]::Delete($tmp)}
  }
 }
 $phase='VALIDATE_MONTH_END_BASELINE'
 & $python -B $reader --audit $audit --jpx-xlsx $jpx --output $private
 Need ($LASTEXITCODE -eq 0) 'JPX_MONTH_END_SOURCE_NOT_VERIFIED'
 Write-Host 'NO11_JPX_REFERENCE_STAGE=PASS_MONTH_END_ONLY'
 Write-Host 'NO11_JPX_DAY_OF_SESSION_COMMON_EQUITY_CERTIFIED=False'
 Write-Host 'NO11_JPX_CORPORATE_ACTIONS_CLEARED=False'
 Write-Host 'NO11_JPX_CHART50_EXECUTABLE=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_JPX_REFERENCE_STAGE_[A-Z0-9_]+$'){
  $reason='NO11_JPX_REFERENCE_STAGE_EXTERNAL_SOURCE_OR_INPUT_FAILURE'
 }
 Write-Host ('NO11_JPX_REFERENCE_FAILURE_STAGE='+$phase)
 Write-Host ('NO11_JPX_REFERENCE_STAGE=BLOCKED|'+$reason)
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
