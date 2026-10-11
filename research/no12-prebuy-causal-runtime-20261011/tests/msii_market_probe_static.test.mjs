import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const script=fs.readFileSync(new URL('../windows/Probe-No12MarketRssChartReadOnly.ps1',import.meta.url),'utf8');
test('No12 Windows market-only probe uses exact 2026/3/30 RSS chart columns and 5M formula',()=>{
 for(const name of ['銘柄名称','市場名称','足種','日付','時刻','始値','高値','安値','終値','出来高']){
   assert.ok(script.includes(name),name);
 }
 assert.match(script,/=RssChart\(\$A\$2:\$J\$2,"7203.T","5M",20\)/);
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
