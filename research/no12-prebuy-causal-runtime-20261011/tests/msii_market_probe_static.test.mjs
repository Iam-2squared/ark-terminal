import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const script=fs.readFileSync(new URL('../windows/Probe-No12MarketRssChartReadOnly.ps1',import.meta.url),'utf8');
test('No12 Windows market-only probe uses exact 2026/3/30 RSS chart columns and 5M formula',()=>{
 for(const name of ['銘柄名称','市場名称','足種','日付','時刻','始値','高値','安値','終値','出来高']){
   assert.ok(script.includes(name),name);
 }
 assert.match(script,/=RssChart\(\$A\$2:\$J\$2,"7203.T","5M",\{0\}\)/);
 assert.match(script,/\$HistoryBars=500/);
 assert.match(script,/NO12_RSS_CHART_FORMULA_SELFTEST_PASS=True/);
});
test('probe cannot silently replace or modify existing Ark Account workbook',()=>{
 assert.match(script,/NO11_ACCOUNT_UI_MUST_BE_STOPPED_FIRST/);
 assert.match(script,/EXCEL_HAS_EXISTING_WORKBOOK_CLOSE_FIRST/);
 assert.match(script,/\$excel\.Workbooks\.Add\(\)/);
 assert.match(script,/\$book\.Close\(\$false\)/);
 assert.doesNotMatch(script,/Workbooks\.Open\(/i);
 assert.doesNotMatch(script,/SaveAs\(/i);
 assert.doesNotMatch(script,/\.Save\(/i);
});
test('probe uses only chart, never RSS order function / PowerShell kill-switch reset',()=>{
 for(const expr of [/RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,/\.Formula\s*=\s*['"]?=RssStockOrder/i,
   /explicitSafetyReset\s*\(/i,/killSwitchLatched\s*=\s*false/i]){
   assert.doesNotMatch(script,expr);
 }
 assert.match(script,/ORDER_TRANSMISSION=False/);
 assert.match(script,/ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False/);
});

test('market probe converts Excel Value2 date/time and sends data only to private local receipt',()=>{
 for(const token of [
  'Convert-No12VendorDate','Convert-No12VendorTime','FromOADate',
  'chart-candidate-','no12_private_chart_publish.mjs',
  'NO12_RSS_CHART_PRIVATE_READ_ONLY_RECEIPT=True',
  'ArkTerminal\\No12','NO12_RSS_EXCEL_OADATE_SELFTEST_FAILED'
 ]){
   assert.ok(script.includes(token),token);
 }
 assert.doesNotMatch(script,/https?:\/\//i);
 assert.doesNotMatch(script,/Invoke-WebRequest|Invoke-RestMethod|Start-BitsTransfer/i);
});

test('500-row historical bootstrap defaults to exact dynamic range and never reads a fixed 20 rows',()=>{
 assert.match(script,/\$lastRow=2\+\$HistoryBars/);
 assert.match(script,/A3:J\{0\}/);
 assert.match(script,/\$r0\+\$HistoryBars/);
 assert.match(script,/NO12_RSS_HISTORY_BAR_REQUEST_OUT_OF_RANGE/);
 assert.doesNotMatch(script,/Range\('A3:J22'\)/);
 assert.match(script,/NO12_RSS_HISTORY_BARS_REQUESTED/);
});

test('market probe includes one private first-seen record, never backfill-as-live or order writes',()=>{
 for(const token of ['no12_market_first_seen.mjs','NO12_FIRST_SEEN_LOCAL_JOURNAL_BLOCKED',
  'NO12_5DAY_HISTORY_STATUS=','NO12_5DAY_HISTORY_PREVIOUS_SESSIONS=',
  'NO12_FIRST_SEEN_STATUS=','NO12_FIRST_SEEN_CONTINUITY=',
  'NO12_MARKET_NATIVE_DECISION_READY=False']){
  assert.ok(script.includes(token),token);
 }
 assert.match(script,/GAP_OR_CLOCK_MISMATCH/);
 assert.match(script,/NO12_HISTORY_RECEIPT_RESULT_UNVERIFIED/);
});
