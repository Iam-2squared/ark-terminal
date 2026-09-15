param(
    [string]$WorkbookName = "Ark_MSII_LiveSource.xlsx",
    [string]$AccountSheet = "ARK_ACCOUNT_READONLY",
    [string]$OrderSheet = "ARK_CASH_ORDER_LOCKED",
    [string]$SnapshotPath = "C:\Ark\account-readonly-20260915\account-snapshot-live.json",
    [string]$Symbol = "7203.T",
    [int]$Quantity = 100,
    [double]$EstimatedNotional = 300000,
    [string]$ExternalSymbol = "408A",
    [double]$ExternalQuantity = 180
)
$ErrorActionPreference = "Stop"
$excel = [Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
$wb = $excel.Workbooks | Where-Object { $_.Name -eq $WorkbookName }
if ($null -eq $wb) { throw "$WorkbookName is not open" }
$acct = $wb.Worksheets.Item($AccountSheet)
$excel.CalculateFull(); Start-Sleep -Milliseconds 500

$positions=@()
for($r=3;$r -le 200;$r++){
 $symbol=$acct.Cells.Item($r,38).Text; $name=$acct.Cells.Item($r,39).Text; $account=$acct.Cells.Item($r,40).Text; $qty=$acct.Cells.Item($r,41).Value2
 if($symbol -and $symbol -ne "--------" -and $name -and $name -ne "--------" -and $null -ne $qty){
  $positions += [PSCustomObject]@{symbol=$symbol;name=$name;account=$account;quantity=$qty}
 }
}
$orders=@()
for($r=3;$r -le 300;$r++){
 $n=$acct.Cells.Item($r,14).Text
 if($n -and $n -ne "--------"){$orders += [PSCustomObject]@{orderNumber=$n;status=$acct.Cells.Item($r,15).Text;symbol=$acct.Cells.Item($r,16).Text;quantity=$acct.Cells.Item($r,22).Value2;filledQty=$acct.Cells.Item($r,23).Value2}}
}
$buyingPower=$acct.Cells.Item(3,12).Value2; if($null -eq $buyingPower){$buyingPower=0}
$snapshot=[PSCustomObject]@{schemaId="ARK_ACCOUNT_READONLY_SNAPSHOT_V2";capturedAt=(Get-Date).ToString("o");source="MARKETSPEED_II_RSS";mode="READ_ONLY";positions=$positions;orders=$orders;executions=@();buyingPower=$buyingPower;safety=@{executionAllowed=$false;brokerWriteAllowed=$false;excelOrderWriteAllowed=$false;rssOrderFunctionAllowed=$false;liveTradingAllowed=$false;paperTradingAllowed=$false;automaticPromotionAllowed=$false;productionUpdateAllowed=$false;transmitted=$false}}
$dir=Split-Path -Parent $SnapshotPath; New-Item -ItemType Directory -Force $dir | Out-Null
$snapshot | ConvertTo-Json -Depth 10 | Set-Content $SnapshotPath -Encoding UTF8

$env:PYTHONPATH=(Resolve-Path ".\tools").Path
$py = @'
import json, sys
from pathlib import Path
from phase57_cash_locked_pipeline import run_locked_pipeline
snapshot_path=Path(sys.argv[1])
symbol=sys.argv[2]
quantity=int(sys.argv[3])
external_symbol=sys.argv[4]
external_quantity=float(sys.argv[5])
estimated_notional=float(sys.argv[6])
with snapshot_path.open("r",encoding="utf-8-sig") as f:
    snapshot=json.load(f)
intent={"symbol":symbol,"direction":"LONG","side":"BUY","positionEffect":"OPEN","quantity":quantity,"orderType":"MARKET","limitPrice":None,"timeInForce":"DAY"}
out=run_locked_pipeline(snapshot,external_positions=[{"symbol":external_symbol,"quantity":external_quantity}],intent=intent,estimated_notional=estimated_notional)
print(json.dumps(out,ensure_ascii=False))
'@
$tmpPy = Join-Path $env:TEMP "ark_cash_locked_pipeline_tmp.py"
Set-Content -Path $tmpPy -Value $py -Encoding UTF8
try {
  $pipelineOut = python $tmpPy $SnapshotPath $Symbol ([string]$Quantity) $ExternalSymbol ([string]$ExternalQuantity) ([string]$EstimatedNotional)
  if ($LASTEXITCODE -ne 0) { throw "Locked cash Python pipeline failed with exit code $LASTEXITCODE" }
} finally {
  Remove-Item $tmpPy -Force -ErrorAction SilentlyContinue
}
$pipeline = $pipelineOut | ConvertFrom-Json
if ($null -eq $pipeline -or -not $pipeline.status) { throw "Locked cash pipeline returned no status" }

$sheet=$null; foreach($s in $wb.Worksheets){if($s.Name -eq $OrderSheet){$sheet=$s;break}}
if($null -eq $sheet){$sheet=$wb.Worksheets.Add();$sheet.Name=$OrderSheet}
$sheet.Range("A1").Value2="ARK CASH-ONLY ORDER INTERFACE"
$sheet.Range("A3").Value2="MODE";$sheet.Range("B3").Value2="LOCKED / NO TRANSMISSION"
$sheet.Range("A4").Value2="PRODUCT";$sheet.Range("B4").Value2="CASH ONLY"
$sheet.Range("A5").Value2="MARGIN";$sheet.Range("B5").Value2="DISABLED"
$sheet.Range("A6").Value2="SHORT SELLING";$sheet.Range("B6").Value2="DISABLED"
$sheet.Range("A8").Value2="SYMBOL";$sheet.Range("B8").Value2=$Symbol
$sheet.Range("A9").Value2="SIDE";$sheet.Range("B9").Value2="BUY"
$sheet.Range("A10").Value2="QUANTITY";$sheet.Range("B10").Value2=[string]$Quantity
$sheet.Range("A11").Value2="TRIGGER";$sheet.Range("B11").Value2=0
$sheet.Range("A12").Value2="BUYING POWER";$sheet.Range("B12").Value2=[string]$buyingPower
$sheet.Range("A13").Value2="RSS FUNCTION DRAFT";$sheet.Range("B13").NumberFormat="@"
$sheet.Range("A15").Value2="EXECUTION ALLOWED";$sheet.Range("B15").Value2="FALSE"
$sheet.Range("A16").Value2="TRANSMITTED";$sheet.Range("B16").Value2="FALSE"
$sheet.Range("A17").Value2="EXCEL ORDER WRITE";$sheet.Range("B17").Value2="FALSE"
$sheet.Range("A18").Value2="STATUS"
if($pipeline.status -eq "LOCKED_READY"){
 $sheet.Range("B13").Value2=[string]$pipeline.interface.cells.B13
 $sheet.Range("B18").Value2="LOCKED READY - PHYSICAL UNLOCK REQUIRED"
}else{
 $sheet.Range("B13").Value2=""
 $blockers=""
 if($pipeline.candidate -and $pipeline.candidate.blockers){$blockers=($pipeline.candidate.blockers -join ",")}
 elseif($pipeline.reconciliation -and $pipeline.reconciliation.blockers){$blockers=($pipeline.reconciliation.blockers -join ",")}
 elseif($pipeline.preflight -and $pipeline.preflight.blockers){$blockers=($pipeline.preflight.blockers -join ",")}
 $sheet.Range("B18").Value2="BLOCKED @ $($pipeline.stage): $blockers"
}
$sheet.Columns("A:B").AutoFit();$wb.Save()
Write-Host "ARK_CASH_LOCKED_READY"
Write-Host "Snapshot    :" $SnapshotPath
Write-Host "Positions   :" $positions.Count
Write-Host "Orders      :" $orders.Count
Write-Host "BuyingPower :" $buyingPower
Write-Host "Pipeline    :" $pipeline.status
Write-Host "Stage       :" $pipeline.stage
Write-Host "Trigger     :" $sheet.Range("B11").Value2
Write-Host "Formula?    :" $sheet.Range("B13").HasFormula
Write-Host "Execution   :" $sheet.Range("B15").Text
Write-Host "Transmitted :" $sheet.Range("B16").Text
Write-Host "Status      :" $sheet.Range("B18").Text
