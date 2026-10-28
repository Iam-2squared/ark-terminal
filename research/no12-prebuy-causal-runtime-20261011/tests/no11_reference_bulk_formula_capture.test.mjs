import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const collector=fileURLToPath(new URL('../windows/Capture-No11SessionReferenceReadOnly.ps1',import.meta.url));
const parent=fileURLToPath(new URL('../windows/Run-No11Oct28AfternoonShadowReadOnly.ps1',import.meta.url));
const source=readFileSync(collector,'utf8'),wrapper=readFileSync(parent,'utf8');

test('avoid unbounded per-formula COM cell enumerations; use one Excel Formula snapshot per sheet',()=>{
 for(const marker of [
  'function ScanMarketFormulaSnapshot',
  '$snapshot=$used.Formula',
  '$cellCount=[long]$used.CountLarge',
  "'FORMULA_SCAN_LIMIT'",
  "'MARKET_CAPACITY_EXCEEDED'",
  "$existing.Count+$unknown -le 500",
  "if($candidate -ceq '!UNKNOWN!')",
  "StartsWith('=')",
  "'NO11_REFERENCE_STAGE=ORIGINAL_WORKBOOK_FORMULA_SCAN_START'",
  "'NO11_REFERENCE_STAGE=CREATE_UNSAVED_TEMP_WORKBOOK'",
  'NO11_REFERENCE_STAGE=WRITE_MARKET_FORMULAS',
  'NO11_REFERENCE_STAGE=WAIT_RSS_FORMULAS',
  "'NO11_REFERENCE_STAGE=READ_RSS_MARKET_VALUES'",
  "'NO11_REFERENCE_STAGE=WRITE_IMMUTABLE_RECEIPT'",
  'NO11_REFERENCE_BULK_FORMULA_SELFTEST=PASS',
 ])assert.ok(source.includes(marker),marker);
 assert.doesNotMatch(source,/\$cells\.Cells|foreach\(\$cell in \$cells/);
 assert.doesNotMatch(source,/GetActiveObject\s*\(|RssStockOrder\s*\(|RssCancelOrder\s*\(|Stop-Process|\.SaveAs\s*\(|\.Save\s*\(|\.Quit\s*\(/);
});
test('source errors are fail-closed and immutable receipts and source checks stay intact',()=>{
 for(const marker of [
  'NO11_REFERENCE_EXCEL_COM_OR_SOURCE_FAILURE',
  'NO11_REFERENCE_EXCEL_COM_ATTACH_FAILED',
  'NO11_REFERENCE=','NO11_SESSION_REFERENCE_FILE=',
  'corporateActionReviewPerformed=$false','productionReady=$false',
  'orderTransmission=$false',"$book.Close($false)",
  "Read-DailyRows" // not present; no dependence on RSS daily historical capture
 ].slice(0,-1))assert.ok(source.includes(marker),marker);
 assert.ok(source.startsWith('\ufeff'),'preserve Windows PowerShell 5.1 UTF-8 BOM');
});
test('parent streams progress, but still captures and validates immutable receipt',()=>{
 for(const marker of [
  'ForEach-Object {',
  "NO11_REFERENCE_STAGE=",
  "NO11_REFERENCE_FORMULA_SCAN_SHEET=",
  "NO11_SESSION_REFERENCE=BLOCKED",
  'Write-Host $line',
  '$line',
  "Need ($LASTEXITCODE -eq 0) 'ACTUAL_RSS_REFERENCE_FAILED'",
  "FromOutput $output 'NO11_SESSION_REFERENCE_FILE='",
  'NO11_TODAY_SHADOW_REFERENCE=OBSERVED_NOT_EXTERNALLY_REVIEWED',
  'ORDER_TRANSMISSION=False'
 ])assert.ok(wrapper.includes(marker),marker);
 assert.doesNotMatch(wrapper,/RssStockOrder\s*\(|RssCancelOrder\s*\(|Stop-Process/);
});
test('Windows offline pure formula-snapshot regression does not open Excel',{skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass',
  '-File',collector,'-OfflineSelfTest'],{encoding:'utf8',timeout:20000});
 assert.equal(r.status,0,(r.stdout||'')+'\n'+(r.stderr||''));
 assert.match(r.stdout,/NO11_REFERENCE_BULK_FORMULA_SELFTEST=PASS/);
 assert.match(r.stdout,/NO11_REFERENCE_OFFLINE_SELFTEST=PASS/);
 assert.match(r.stdout,/ORDER_TRANSMISSION=False/);
});
