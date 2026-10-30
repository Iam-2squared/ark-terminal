import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const script=fileURLToPath(new URL('../windows/Run-No11Oct28DaytimeReviewPrepReadOnly.ps1',import.meta.url));
const source=fs.readFileSync(script,'utf8');
test('Oct28 daytime uses original observed 27 receipt and exact 26 G1 Chart50 pin',()=>{
 for(const token of [
  'daily-2026-10-26-e84a2ec53b0fdf41',
  'no11-chart50-private-a9d57cdb4eccb107.json',
  'no11-observed-pass-watch-ce769aac846cf1b4.json',
  'session-reference\\2026-10-27',
  'no11_review_queue_from_actual_rss.py',
  'NO11_REFERENCE_DIAG_ROWS_COMPLETE=47/47',
  'NO11_REFERENCE_DIAG_MARKET_SECTION_RECOGNIZED=47/47',
  'NO11_RSS_REFERENCE_FIELDS_MISSING=0',
  'independentlyClearedCount -eq 0',
  'NO11_DAY_REVIEW_RSS_REFERENCE=47/47',
  'NO11_DAY_REVIEW_EXTERNAL_DOCUMENTS_NEEDED=YES'
 ])assert.ok(source.includes(token),token);
});
test('no Excel, orders, live dispatch or false external review claim',()=>{
 for(const pattern of [
  /GetActiveObject\s*\(/,/Excel.Application|Workbooks\.Open/,
  /RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /orderTransmission\s*=\s*\$true/,
  /Stop-Process|\.Kill\s*\(/
 ])assert.doesNotMatch(source,pattern);
 for(const token of [
  'NO11_DAY_REVIEW_EXCEL_OPENED=False',
  'NO11_DAY_REVIEW_EVIDENCE_NOT_CERTIFIED=True',
  'NO11_DAY_REVIEW_FROZEN_OR_CAPITAL_MODIFIED=False',
  'ORDER_TRANSMISSION=False'
 ])assert.ok(source.includes(token),token);
});
test('Windows daytime wrapper offline self-test', {skip:process.platform!=='win32'},()=>{
 const a=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',script,'-OfflineSelfTest'],
  {encoding:'utf8',timeout:20000});
 assert.equal(a.status,0,(a.stdout||'')+'\n'+(a.stderr||''));
 assert.match(a.stdout,/NO11_DAY_REVIEW_OFFLINE_SELFTEST=PASS/);
 assert.match(a.stdout,/ORDER_TRANSMISSION=False/);
});
