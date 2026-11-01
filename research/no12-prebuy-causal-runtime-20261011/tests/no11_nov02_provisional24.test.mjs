import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {approvedMonthlyBaseline} from '../tools/no11_stage_nov02_provisional_24_readonly.mjs';
const source=fs.readFileSync(new URL('../tools/no11_stage_nov02_provisional_24_readonly.mjs',import.meta.url),'utf8');
test('Nov2 provisional shortlist is exactly 24 unique sources, not 17 unknown or 6 held',()=>{
 const selected=new Set(approvedMonthlyBaseline);
 assert.equal(selected.size,24);
 for(const code of ['1690.T','2014.T','2038.T','4347.T','5029.T','2612.T',
  '7867.T','4661.T','7947.T','4911.T','9861.T','9658.T','3397.T','3197.T',
  '2702.T','6678.T','7552.T','9069.T','4922.T','4526.T','9987.T','8153.T','9024.T']){
   assert.equal(selected.has(code),false,code);
 }
 assert.ok(approvedMonthlyBaseline.every(s=>/^[0-9A-Z]{4}\.T$/.test(s)));
});
test('reuses exact saved 47 and JPX month-end but no dishonest same-day review',()=>{
 for(const marker of [
  'previous.selectedSymbols.length===47',
  'Object.keys(previous.symbols).length===47',
  'originalScope.selectedCount===47',
  'ref.jpxMonthEndDate===',
  "baseline.get(s)?.baselineStatus==='DOMESTIC_EQUITY_MONTH_END_REFERENCE'",
  'selected.length===24',
  'independentSessionReviewStillRequired:true',
  'provisionalScopeIsNotTradingApproval:true',
  'orderTransmission:false',
  "verified.verifyWeeklyShadowScope",
  'mod.validateNo11Chart50Plan',
  'previousChartPlanSha256',
  'NO11_NOV02_24_LIVE_CONFIG=NOT_CREATED'
 ])assert.ok(source.includes(marker),marker);
 for(const forbidden of [
  /RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,/Stop-Process/,
  /approvedForSession\s*:\s*true/,
  /corporateActionsCleared\s*:\s*true/,
  /priceBasisVerified\s*:\s*true/,
  /commonEquity\s*:\s*true/,
  /orderTransmission\s*:\s*true/
 ])assert.doesNotMatch(source,forbidden);
});
test('refuses missing private evidence and never creates trading or broker files',()=>{
 const proc=spawnSync(process.execPath,[
  fileURLToPath(new URL('../tools/no11_stage_nov02_provisional_24_readonly.mjs',import.meta.url)),
  '--engine','/abs/nonexistent','--run','/abs/nonexistent',
  '--seed','/abs/nonexistent','--stage','/abs/nonexistent',
  '--jpx','/abs/nonexistent'
 ],{encoding:'utf8',timeout:20000});
 assert.notEqual(proc.status,0);
 assert.match(proc.stderr,/NO11_NOV02_24_/);
 assert.match(proc.stdout,/ORDER_TRANSMISSION=False/);
});
