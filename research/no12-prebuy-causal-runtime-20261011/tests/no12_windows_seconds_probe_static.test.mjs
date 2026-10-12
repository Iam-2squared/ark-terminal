import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const script=fs.readFileSync(new URL('../windows/Probe-No12RssMarketSecondsReadOnly.ps1',import.meta.url),'utf8');
test('RssMarket seconds probe uses official exact field names and one public ticker',()=>{
 for(const item of ['現在日付','現在値','現在値詳細時刻','最良売気配値','最良買気配値'])
  assert(script.includes(item));
 assert.match(script,/=RssMarket\("\{0\}","\{1\}"\)/);
 assert.match(script,/=RssMarket\("7203.T","現在値詳細時刻"\)/);
 assert.match(script,/NO12_SECONDS_RSS_FORMULA_SELFTEST_PASS=True/);
});
test('seconds probe is one temporary unsaved workbook and protects existing account UI',()=>{
 assert.match(script,/NO11_ACCOUNT_UI_MUST_BE_STOPPED_FIRST/);
 assert.match(script,/EXCEL_HAS_EXISTING_WORKBOOK_CLOSE_FIRST/);
 assert.match(script,/\$excel\.Workbooks\.Add\(\)/);
 assert.match(script,/\$book\.Close\(\$false\)/);
 assert.doesNotMatch(script,/Workbooks\.Open\(/);
 assert.doesNotMatch(script,/SaveAs\(/);
 assert.doesNotMatch(script,/\.Save\(/);
});
test('seconds probe outputs anonymized time statistics only and never transmits orders',()=>{
 assert.match(script,/no12_private_rss_seconds_publish\.mjs/);
 assert.match(script,/seconds-candidate-/);
 assert.match(script,/NO12_SECONDS_PRIVATE_READ_ONLY_RECEIPT=True/);
 assert.match(script,/ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False/);
 assert.match(script,/ORDER_TRANSMISSION=False/);
 assert.match(script,/Remove-Item -LiteralPath \$candidateFile/);
 for(const re of [/RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,
   /Invoke-WebRequest|Invoke-RestMethod|Start-BitsTransfer/i,
   /explicitSafetyReset\s*\(/i,/killSwitchLatched\s*=\s*false/i])
  assert.doesNotMatch(script,re);
});
