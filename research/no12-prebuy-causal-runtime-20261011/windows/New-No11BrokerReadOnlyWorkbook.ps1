# Write a NEW macro-free xlsx, entirely offline, without starting Excel or RSS.
# The only three formulas retrieve IDs, cash orders and cash executions. Opening
# it later in the user's configured Excel is a separate read-only source step.
param([string]$OutputPath,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'Read-No11BrokerSnapshot.ps1')
function Get-No11ExcelColumn([int]$Number){
 Assert-No11Broker ($Number -ge 1 -and $Number -le 16384) 'COLUMN'
 $s='';while($Number -gt 0){$Number--;$s=[char](65+($Number%26))+$s;$Number=[int][math]::Floor($Number/26)};return $s
}
function New-No11BrokerWorkbookParts {
 $ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
 $top=New-Object Text.StringBuilder
 $headers=New-Object Text.StringBuilder
 $tables=@(
  @{kind='IDS';first=1;cell='A1';formula='RssOrderIDList(A2:F2)'},
  @{kind='ORDERS';first=8;cell='H1';formula='RssOrderList(H2:AK2,0,1)'},
  @{kind='EXECUTIONS';first=39;cell='AM1';formula='RssExecutionList(AM2:BA2,1)'}
 )
 foreach($t in $tables){
  [void]$top.Append('<c r="'+$t.cell+'" t="str"><f>'+[Security.SecurityElement]::Escape($t.formula)+'</f><v></v></c>')
  $labels=Get-No11BrokerHeaders $t.kind
  for($i=0;$i -lt $labels.Count;$i++){
   $cell=(Get-No11ExcelColumn ($t.first+$i))+'2'
   [void]$headers.Append('<c r="'+$cell+'" s="1" t="inlineStr"><is><t>'+[Security.SecurityElement]::Escape($labels[$i])+'</t></is></c>')
  }
 }
 # BD1 guard, BD2 trigger, BD3 session, BD4 vacant order/result slot.
 # Only a later explicit operator step may configure sending; defaults are inert.
 $sheet='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="'+$ns+'"><dimension ref="A1:BD4"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="2" topLeftCell="A3" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="56" width="18" customWidth="1"/></cols><sheetData><row r="1">'+$top.ToString()+'<c r="BD1" t="inlineStr"><is><t>DISABLED</t></is></c></row><row r="2">'+$headers.ToString()+'<c r="BD2"><v>0</v></c></row><row r="3"><c r="BD3" t="inlineStr"><is><t>UNCONFIGURED_RSS_SESSION</t></is></c></row><row r="4"><c r="BD4"/></row></sheetData></worksheet>'
 return [ordered]@{
  '[Content_Types].xml'='<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>'
  '_rels/.rels'='<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
  'xl/workbook.xml'='<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><workbookPr date1904="0"/><sheets><sheet name="ARK_ORDER_IDS_READONLY" sheetId="1" r:id="rId1"/></sheets><calcPr calcId="0" fullCalcOnLoad="1"/></workbook>'
  'xl/_rels/workbook.xml.rels'='<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
  'xl/styles.xml'='<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'
  'xl/worksheets/sheet1.xml'=$sheet
 }
}
function Write-No11BrokerWorkbook([string]$Destination,$Parts){
 Assert-No11Broker ([IO.Path]::IsPathRooted($Destination) -and [IO.Path]::GetExtension($Destination) -ieq '.xlsx') 'WORKBOOK_OUTPUT_PATH'
 $full=[IO.Path]::GetFullPath($Destination)
 $repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
 Assert-No11Broker (-not $full.StartsWith($repo+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) 'WORKBOOK_IN_REPO'
 Assert-No11Broker (Test-Path -LiteralPath (Split-Path -Parent $full) -PathType Container) 'WORKBOOK_PARENT'
 $cursor=$full
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  if(Test-Path -LiteralPath $cursor){Assert-No11Broker (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'WORKBOOK_REPARSE_POINT'}
  $next=Split-Path -Parent $cursor;if($next -ceq $cursor){break};$cursor=$next
 }
 Assert-No11Broker (-not (Test-Path -LiteralPath $full)) 'WORKBOOK_ALREADY_EXISTS'
 Add-Type -AssemblyName System.IO.Compression
 $stream=$null;$archive=$null;$ok=$false
 try{
  $stream=[IO.File]::Open($full,[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
  $archive=[IO.Compression.ZipArchive]::new($stream,[IO.Compression.ZipArchiveMode]::Create,$true)
  foreach($entryName in $Parts.Keys){
   $entry=$archive.CreateEntry($entryName);$target=$entry.Open()
   try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes([string]$Parts[$entryName]);$target.Write($bytes,0,$bytes.Length)}finally{$target.Dispose()}
  }
  $archive.Dispose();$archive=$null;$stream.Flush($true);$ok=$true
 }finally{
  if($null -ne $archive){$archive.Dispose()};if($null -ne $stream){$stream.Dispose()}
  if(-not $ok -and $null -ne $stream -and [IO.File]::Exists($full)){[IO.File]::Delete($full)}
 }
}
$parts=New-No11BrokerWorkbookParts
if($OfflineSelfTest){
 foreach($part in $parts.Values){[xml]$parsed=[string]$part;Assert-No11Broker ($null -ne $parsed.DocumentElement) 'TEMPLATE_XML'}
 [xml]$sheet=$parts['xl/worksheets/sheet1.xml'];$manager=New-Object Xml.XmlNamespaceManager($sheet.NameTable)
 $manager.AddNamespace('s','http://schemas.openxmlformats.org/spreadsheetml/2006/main')
 $formulas=@($sheet.SelectNodes('//s:f',$manager) | ForEach-Object {$_.InnerText})
 Assert-No11Broker ($formulas.Count -eq 3 -and $formulas[0] -ceq 'RssOrderIDList(A2:F2)' -and $formulas[1] -ceq 'RssOrderList(H2:AK2,0,1)' -and $formulas[2] -ceq 'RssExecutionList(AM2:BA2,1)') 'TEMPLATE_FORMULAS'
 Assert-No11Broker ($sheet.SelectNodes('//s:row[@r="2"]/s:c[not(@r="BD2")]',$manager).Count -eq 51) 'TEMPLATE_HEADERS'
 Assert-No11Broker ($sheet.SelectSingleNode('//s:c[@r="BD1"]/s:is/s:t',$manager).InnerText -ceq 'DISABLED' -and
  $sheet.SelectSingleNode('//s:c[@r="BD2"]/s:v',$manager).InnerText -ceq '0' -and
  $sheet.SelectSingleNode('//s:c[@r="BD3"]/s:is/s:t',$manager).InnerText -ceq 'UNCONFIGURED_RSS_SESSION' -and
  $null -eq $sheet.SelectSingleNode('//s:c[@r="BD4"]/s:f',$manager)) 'TEMPLATE_SEND_CELLS_DISABLED'
 $dir=Join-Path ([IO.Path]::GetTempPath()) ('ark-no11-broker-selftest-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($dir)
 try{
  $file=Join-Path $dir 'readonly.xlsx';Write-No11BrokerWorkbook $file $parts
  $bytes=[IO.File]::ReadAllBytes($file);Assert-No11Broker ($bytes[0] -eq 80 -and $bytes[1] -eq 75) 'TEMPLATE_ZIP'
  $blocked=$false;try{Write-No11BrokerWorkbook $file $parts}catch{if($_.Exception.Message -ceq 'NO11_BROKER_WORKBOOK_ALREADY_EXISTS'){$blocked=$true}else{throw}}
  Assert-No11Broker $blocked 'TEMPLATE_REPLACE_FORBIDDEN'
 }finally{if(Test-Path -LiteralPath $dir){[IO.Directory]::Delete($dir,$true)}}
 Write-Host 'NO11_BROKER_WORKBOOK_OFFLINE_SELFTEST=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Write-No11BrokerWorkbook $OutputPath $parts
Write-Host 'NO11_BROKER_READONLY_WORKBOOK_CREATED=True'
Write-Host 'EXCEL_STARTED=False'
Write-Host 'ORDER_TRANSMISSION=False'
