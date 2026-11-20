import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const script=fs.readFileSync(new URL('../windows/Probe-No12MarketRss1mReadOnly.ps1',import.meta.url),'utf8');
test('Windows 1M probe is one temporary unsaved workbook and exactly one 1M RSS formula',()=>{
 assert.match(script,/HistoryBars=2000/);
 assert.match(script,/=RssChart\(\$A\$2:\$J\$2,"7203.T","1M",\{0\}\)/);
 assert.match(script,/\$excel\.Workbooks\.Add\(\)/);
 assert.match(script,/\$book\.Close\(\$false\)/);
 assert.match(script,/NO11_ACCOUNT_UI_MUST_BE_STOPPED_FIRST/);
 assert.match(script,/EXCEL_HAS_EXISTING_WORKBOOK_CLOSE_FIRST/);
 assert.doesNotMatch(script,/Workbooks\.Open\(/i);
 assert.doesNotMatch(script,/SaveAs\(/i);
 assert.doesNotMatch(script,/\.Save\(/i);
});
test('1M private evidence goes to local directory only and candidate is always deleted',()=>{
 assert.match(script,/one-minute-candidate-/);
 assert.match(script,/no12_private_1m_readonly_publish\.mjs/);
 assert.match(script,/NO12_1M_HISTORY_STATUS=/);
 assert.match(script,/NO12_1M_HISTORY_BARS=/);
 assert.match(script,/NO12_1M_PRIVATE_READ_ONLY_RECEIPT=True/);
 assert.match(script,/Remove-Item -LiteralPath \$candidateFile/);
 assert.match(script,/NO12_1M_NATIVE_STATE9_READY=False/);
 assert.match(script,/ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False/);
 assert.match(script,/NO12_PRODUCTION_READY=False/);
 assert.match(script,/ORDER_TRANSMISSION=False/);
});
test('no order, cancellation, network upload or safety latch reset in 1M probe',()=>{
 for(const forbidden of [/RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,
   /Invoke-WebRequest|Invoke-RestMethod|Start-BitsTransfer/i,/Workbooks\.Open\(/i,
   /https?:\/\//i,/explicitSafetyReset\s*\(/i,/killSwitchLatched\s*=\s*false/i])
  assert.doesNotMatch(script,forbidden);
});
test('Windows offline self-test can check formula and Excel OADate without broker',()=>{
 assert.match(script,/if\(\$OfflineSelfTest\)/);
 assert.match(script,/NO12_RSS_CHART_FORMULA_SELFTEST_PASS=True/);
 assert.match(script,/NO12_MARKET_PROBE_BROKER_ACCESS=False/);
 assert.match(script,/Convert-No12VendorDate/);
 assert.match(script,/Convert-No12VendorTime/);
 assert.match(script,/FromOADate/);
});
