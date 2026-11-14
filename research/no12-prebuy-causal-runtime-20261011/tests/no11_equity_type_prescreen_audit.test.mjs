import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {
  AUDIT_SCHEMA,JPX_CONFIRMED_EXCLUDED,computeEquityTypePreview
} from '../tools/no11_equity_type_prescreen_audit.mjs';
import {makeNo11G1Chart50Plan} from '../runtime/no11_rss_chart_50_prescreen.mjs';

const session='2026-10-30',previous='2026-10-29';
const mask={
 schemaId:'ARK_NO11_DAILY_OBSERVED_PASS_ONLY_SHADOW_V1',
 asOfSession:previous,planId:'synthetic-g1-pass-mask',
 observedPassSymbols:['2038.T','1671.T','7203.T','6758.T','2014.T','9501.T'],
 observedPassCount:6,strictNoUnknownFallback:true,shadowOnly:true,
 productionReady:false,orderTransmission:false
};
const ranked=['2038.T','1671.T','7203.T','6758.T','2014.T','9501.T']
 .map((symbol,i)=>({symbol,minMarginPct:12-i,meanMarginPct:20-i}));
function fixture(opts={}){
 const chartPlan=makeNo11G1Chart50Plan({
  mask,priorityRows:ranked,sessionDate:session,...opts});
 const selected=chartPlan.selectorInputSymbols;
 const stage={schemaId:'ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1',
   sessionDate:session,previousSession:previous,
   chartPlanSha256:chartPlan.planSha256,selectedSymbols:selected,
   symbols:Object.fromEntries(selected.map(s=>[s,{rows:[{label:'test'}]}])),
   omittedSymbols:{},productionReady:false,orderTransmission:false};
 return {chartPlan,mask,ranked,stage,sourceDigest:'a'.repeat(64)};
}
test('strict provisional re-ranking excludes publicly confirmed ETF/ETN and does not certify 73 others',()=>{
 const a=fixture({otherChartFunctions:45,emptySafetySlots:3});
 const orig=structuredClone(a.chartPlan);
 const out=computeEquityTypePreview(a);
 assert.equal(out.schemaId,AUDIT_SCHEMA);
 assert.equal(out.status,'PROVISIONAL_REVIEW_REQUIRED_NOT_A_TRADING_PLAN');
 assert.equal(out.originalSelectedCount,2);
 assert.deepEqual(out.knownExcludedFromOriginal,['2038.T','1671.T']);
 assert.deepEqual(out.provisionalSelectedAfterKnownExclusions,['7203.T','6758.T']);
 assert.deepEqual(out.provisionalReplacementCandidates,['7203.T','6758.T']);
 assert.deepEqual(out.replacementPriorArchiveMissing,['7203.T','6758.T']);
 assert.equal(out.unreviewedG1Count,3);
 assert.equal(out.executableChartPlanProduced,false);
 assert.equal(out.actualCommonEquityIndependentlyReviewed,false);
 assert.equal(out.permitsBuy,false);
 assert.equal(out.orderTransmission,false);
 assert.deepEqual(a.chartPlan,orig,'must not touch original Chart50 plan');
});
test('the 5 JPX-documented noncommon securities are always excluded from provisional BUY scans',()=>{
 const f=fixture();
 const out=computeEquityTypePreview(f);
 for(const s of JPX_CONFIRMED_EXCLUDED){
  assert.ok(!out.provisionalSelectedAfterKnownExclusions.includes(s),s);
 }
 assert.equal(out.provisionalSelectedCount,3);
 assert.equal(out.knownExcludedFromG1.length,3);
 assert.equal(out.unreviewedG1Count,3);
 assert.equal(out.replacementPriorArchiveMissing.length,0);
});
test('protected existing held ETF keeps an EXIT observation slot but never an entry slot',()=>{
 const f=fixture({heldSymbols:['2038.T'],otherChartFunctions:45,emptySafetySlots:2});
 const out=computeEquityTypePreview(f);
 assert.deepEqual(out.knownExcludedPinnedForExitOnly,['2038.T']);
 assert.ok(!out.provisionalSelectedAfterKnownExclusions.includes('2038.T'));
 assert.equal(f.chartPlan.protectedChartSymbols[0],'2038.T');
 assert.equal(out.permitsBuy,false);
});
test('tampered previous selection, source SHA, or ranking cannot silently create a provisional report',()=>{
 const f=fixture({otherChartFunctions:45,emptySafetySlots:3});
 for(const change of [
  {stage:{...f.stage,chartPlanSha256:'b'.repeat(64)}},
  {stage:{...f.stage,selectedSymbols:['7203.T']}},
  {stage:{...f.stage,productionReady:true}},
  {ranked:f.ranked.slice(1)},
  {ranked:f.ranked.map((r,i)=>({...r,minMarginPct:i+1,meanMarginPct:i+1}))},
  {sourceDigest:'not-a-digest'}
 ]){
  assert.throws(()=>computeEquityTypePreview({...f,...change}),/^Error: NO11_EQUITY_TYPE_/);
 }
});
test('audit source neither emits tradeable plans nor writes an order or changes Frozen files',()=>{
 const script=fs.readFileSync(new URL('../tools/no11_equity_type_prescreen_audit.mjs',import.meta.url),'utf8');
 assert.ok(script.includes('verifyWeeklyShadowScope({'));
 assert.ok(script.includes('rankVerifiedG1PassForChartBudget(daily,captures,mask)'));
 assert.ok(script.includes('UNKNOWN_G1')||script.includes('UNKNOWN_G1'));
 assert.ok(script.includes('executab')&&script.includes('false'));
 assert.doesNotMatch(script,/RssStockOrder\s*\(|spawnSync|execSync|child_process/);
});
