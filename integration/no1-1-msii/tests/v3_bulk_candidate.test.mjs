import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const v3=fs.readFileSync(path.join(root,'windows/Ark-No11-CaptureReadOnly-v3-CANDIDATE.ps1'));
const s=v3.toString('utf8');
test('V3 is the exact SHA-pinned 2.86-second Windows PC candidate',()=>{
  assert.equal(createHash('sha256').update(v3).digest('hex').toUpperCase(),'8B396BF22724ABBCA4BCEB7B93862AE46D40ACBDFE95B385F492E960E9F08DA3');
  assert.equal(v3[0],0xef);assert.equal(v3[1],0xbb);assert.equal(v3[2],0xbf);
});
test('V3 is isolated and cannot modify the workbook or submit orders',()=>{
  assert.match(s,/ISOLATED READ ONLY bulk capture candidate/);
  assert.match(s,/capture-v3-candidate/);
  for(const re of [/Workbooks\s*\.\s*(?:Add|Open)\s*\(/i,/\.Save(?:As)?\s*\(/i,/\.Formula\s*=/i,/\.Value2\s*=/i,/RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,/RegisterXLL\s*\(/i])assert.doesNotMatch(s,re);
  assert.match(s,/EXCEL_MODIFIED=False/);
  assert.match(s,/ORDER_TRANSMISSION=False/);
  assert.match(s,/NO11_PRODUCTION_READY=False/);
});
test('V3 handles complete position/order/execution regions and conservative freshness',()=>{
  for(const t of ["Read-BulkRange $sheet 'AL3:BC201' 199 18","Read-BulkRange $sheet 'N3:W301' 299 10","Read-BulkRange $sheet 'AA3:AI301' 299 9","Read-BulkRange $sheet 'AL2:BC2' 1 18","POSITION_ROW_LIMIT_EXCEEDED","ORDER_ROW_LIMIT_EXCEEDED","EXECUTION_ROW_LIMIT_EXCEEDED","POSITION_ROW_GAP_OR_PARTIAL_AFTER_END","ORDER_ROW_GAP_OR_PARTIAL_AFTER_END","EXECUTION_ROW_GAP_OR_PARTIAL_AFTER_END","RSS_FINAL_STATUS_INVALID:","FINAL_STATUS_RE_READ_NOT_MARKET_SOURCE_TIMESTAMP","ACTUAL_FEED_TIMESTAMP_CERTIFIED=False"])assert.ok(s.includes(t),t);
  assert.match(s,/\$maxCaptureSeconds = 25/);
  assert.match(s,/Assert-ElapsedWithinLimit \$start \$end \$maxCaptureSeconds/);
});
test('local parity tool is privacy-limited and cannot certify broker arrival times',()=>{
  const p=fs.readFileSync(path.join(root,'windows/Test-No11V3LocalParity.ps1'),'utf8');
  assert.match(p,/NO11_V3_PARITY_RESULT=/);
  assert.match(p,/PRIVATE_V3_CANDIDATE_MISSING/);
  assert.match(p,/ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False/);
  assert.doesNotMatch(p,/Write-Host\s+.*(?:\.symbol|\.buyingPower|\.quantity)/i);
});

test('single-command parity runner requires verified V2/V3, isolated output, and same mutex',()=>{
  const h=fs.readFileSync(path.join(root,'windows/Run-No11V3IsolatedParity.ps1'),'utf8');
  assert.match(h,/0EAB3CA3081B2E0CB323D8438719F2B820B69FC02F373AD843B5907315838E2C/);
  assert.match(h,/8B396BF22724ABBCA4BCEB7B93862AE46D40ACBDFE95B385F492E960E9F08DA3/);
  assert.match(h,/parity-v2/);
  assert.match(h,/Local\\ArkTerminal_No11_RSS_ReadOnly/);
  assert.match(h,/MaxComparisonGapSeconds 600/);
  assert.match(h,/NO11_PRODUCTION_READY=False/);
  assert.match(h,/ORDER_TRANSMISSION=False/);
  for(const forbidden of [/Workbooks\s*\.\s*(?:Add|Open)\s*\(/i,/\.Formula\s*=/i,/\.Value2\s*=/i,/RssStockOrder\s*\(/i])assert.doesNotMatch(h,forbidden);
});

test('Git checkout preserves byte-exact V3 source on Windows; no CRLF conversion',()=>{
  const gitattributes=fs.readFileSync(path.resolve(root,'../..','.gitattributes'),'utf8');
  assert.equal(gitattributes,
    'integration/no1-1-msii/windows/Ark-No11-CaptureReadOnly-v3-CANDIDATE.ps1 text eol=lf\n');
});
