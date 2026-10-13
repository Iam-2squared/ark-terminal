import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const s=fs.readFileSync(new URL('../windows/Probe-No11SavedExcelChartInputsReadOnly.ps1',import.meta.url),'utf8');
test('Windows PowerShell UTF-8 BOM and 1M/5M offline formula mode',()=>{
 assert.equal(s.charCodeAt(0),0xFEFF);
 for(const phrase of ['NO11_CHART_OFFLINE_SELFTEST=PASS',
  'RssChart($A$2:$J$2','OneMinuteBars=300','FiveMinuteBars=100',
  "period='1M'","period='5M'"])
  assert(s.includes(phrase),phrase);
});
test('uses RSS-enabled Excel with exact original and saved market workbook identities',()=>{
 for(const phrase of ['Ark_No11_MSII_RSS.xlsx','ARK_ACCOUNT_READONLY',
 'Ark_No11_MARKET_RSS.xlsx','ARK_MARKET_READONLY',
 'AccessibleObjectFromWindow','NO11_ACCOUNT_UI_MUST_BE_STOPPED_FIRST',
 'NO11_CHART_PROBE=PASS','NO11_CHART_PROBE=BLOCKED'])
  assert(s.includes(phrase),phrase);
});
test('only creates and closes an unsaved temporary workbook; never orders',()=>{
 assert.match(s,/\$book=\$excel\.Workbooks\.Add\(\)/);
 assert.match(s,/\$book\.Close\(\$false\)/);
 for(const p of [/RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,
  /Workbooks\.Open\(/i,/SaveAs\(/i,/\.Save\(/i,
  /Invoke-WebRequest|Invoke-RestMethod|Start-BitsTransfer/i])
  assert.doesNotMatch(s,p);
 assert.match(s,/ORDER_TRANSMISSION=False/);
 assert.match(s,/NO11_PRODUCTION_READY=False/);
});
