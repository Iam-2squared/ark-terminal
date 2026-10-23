import test from 'node:test';
import assert from 'node:assert/strict';
import {
 CHART50_PLAN_SCHEMA,dailyG1CapacityPriority,
 rankVerifiedG1PassForChartBudget,makeNo11G1Chart50Plan,
 validateNo11Chart50Plan
} from '../runtime/no11_rss_chart_50_prescreen.mjs';
import {makeObservedPassWatchMask}
  from '../runtime/no11_observed_pass_watch_gate.mjs';
import {requiredDailySessions,DAILY_PLAN_SCHEMA,DAILY_SOURCE_SCHEMA}
  from '../runtime/no11_rss_daily_trend_census.mjs';

const prior='2026-10-23',day='2026-10-26';
const dates=requiredDailySessions(prior);
const plan={
 schemaId:DAILY_PLAN_SCHEMA,planId:'synthetic-chart-50-source',
 asOfSession:prior,createdAtJst:prior+'T18:00:00+09:00',
 expectedSessions:dates,
 symbols:['1111.T','2222.T','3333.T','4444.T'],
 baselineAdded:[]
};
function makeCapture(symbol,kind){
 const rows=dates.map((session,i)=>{
  const price=kind==='DOWN'?250-i:
    kind==='WEAK_UP'?100+0.05*i:100+0.3*i;
  return {session,open:String(price),high:String(price+2),
   low:String(price-2),close:String(price),volume:'200'};
 });
 return {
  schemaId:DAILY_SOURCE_SCHEMA,planId:plan.planId,symbol,
  formula:'=RssChart($A$2:$J$2,"'+symbol+'","D",100)',
  asOfSession:prior,period:'D',status:'OBSERVED',
  priceBasis:'RSS_CHART_UNVERIFIED',
  decimalProvenance:'EXCEL_VALUE2_ROUNDTRIP',
  corporateActionsCleared:false,originalVendorDecimalCertified:false,
  productionReady:false,orderTransmission:false,
  observedStartJst:prior+'T18:01:00+09:00',
  observedEndJst:prior+'T18:02:00+09:00',
  invalidRows:kind==='UNKNOWN'?1:0,rows
 };
}
const captures=[
 makeCapture('1111.T','WEAK_UP'),makeCapture('2222.T','STRONG_UP'),
 makeCapture('3333.T','DOWN'),makeCapture('4444.T','UNKNOWN')
];
test('G1 daily rank uses exact stored 76 closes, no proxy prices',()=>{
 const mask=makeObservedPassWatchMask(plan,captures);
 assert.deepEqual(mask.observedPassSymbols,['1111.T','2222.T']);
 const ranks=rankVerifiedG1PassForChartBudget(plan,captures,mask);
 assert.deepEqual(ranks.map(x=>x.symbol),['2222.T','1111.T']);
 assert.ok(ranks.every(x=>x.minMarginPct>0&&x.meanMarginPct>0));
 assert.ok(ranks[0].minMarginPct>ranks[1].minMarginPct);
 assert.equal(mask.dataStillUnknown,1);
 assert.equal(mask.productionReady,false);
 assert.throws(()=>dailyG1CapacityPriority(dates,captures[0].rows.slice(1)),
   /DAILY_HISTORY_INCOMPLETE/);
});
function synthetic348(){
 const symbols=Array.from({length:348},(_,i)=>String(i+1).padStart(4,'0')+'.T');
 const mask={
  schemaId:'ARK_NO11_DAILY_OBSERVED_PASS_ONLY_SHADOW_V1',
  asOfSession:prior,planId:'local-test-plan',observedPassSymbols:symbols,
  observedPassCount:symbols.length,
  strictNoUnknownFallback:true,shadowOnly:true,
  productionReady:false,orderTransmission:false
 };
 const priorityRows=symbols.map((symbol,i)=>({
  symbol,minMarginPct:(348-i)/1000,
  meanMarginPct:(348-i)/100+1
 }));
 return {mask,priorityRows,sessionDate:day};
}
test('Capacity allocator picks at most 50 charts even with 348 bullish stocks',()=>{
 const p=makeNo11G1Chart50Plan({
  ...synthetic348(),emptySafetySlots:0
 });
 assert.equal(p.schemaId,CHART50_PLAN_SCHEMA);
 assert.equal(p.observedG1PassCount,348);
 assert.equal(p.scanChartSymbols.length,50);
 assert.equal(p.totalChartFunctionsBudgeted,50);
 assert.equal(p.g1UnscannedCount,298);
 assert.equal(p.selectorInputSymbols.length,50);
 assert.equal(p.totalQuoteSlotsBudgeted,348);
 assert.equal(p.scanChartSymbols[0],'0001.T');
 assert.equal(p.scanChartSymbols[49],'0050.T');
 assert.deepEqual(validateNo11Chart50Plan({
  chartPlan:p,mask:synthetic348().mask,sessionDate:day
 }),p.selectorInputSymbols);
 assert.equal(p.productionReady,false);
 assert.equal(p.orderTransmission,false);
 assert.equal(p.originalSelectorPopulationPreserved,false);
 assert.equal(p.originalFrozenDecisionTimesModified,false);
});
test('EXIT, held, pending and persistent Watch always keep chart slots',()=>{
 const p=makeNo11G1Chart50Plan({
  ...synthetic348(),
  heldSymbols:['9001.T','9002.T'],
  activeWatchSymbols:['9002.T','0001.T'],
  pendingOrderSymbols:['9003.T'],
  otherChartFunctions:4,emptySafetySlots:3
 });
 assert.deepEqual(p.protectedChartSymbols,
  ['9001.T','9002.T','0001.T','9003.T']);
 assert.equal(p.arkChartsUsed,43);
 assert.equal(p.totalChartFunctionsBudgeted,47);
 assert.equal(p.reserveEmptyChartSlots,3);
 assert.equal(p.scanChartSymbols.length,39);
 assert.equal(p.selectorInputSymbols.length,40);
 for(const code of ['9001.T','9002.T','9003.T']){
  assert.ok(p.allRequestedChartSymbols.includes(code));
  assert.ok(!p.selectorInputSymbols.includes(code));
 }
 assert.ok(p.selectorInputSymbols.includes('0001.T'));
 assert.equal(p.totalQuoteSlotsBudgeted,351);
});
test('No silent removal of more than 50 existing protected Watch/EXIT slots',()=>{
 const many=Array.from({length:51},(_,i)=>
  String(8000+i).padStart(4,'0')+'.T');
 assert.throws(()=>makeNo11G1Chart50Plan({
  ...synthetic348(),activeWatchSymbols:many
 }),/PROTECTED_WATCH_OR_EXIT_OVER_CHART_CAP/);
});
test('Wrong day, invalid known daily or cap overflow must stop',()=>{
 assert.throws(()=>makeNo11G1Chart50Plan({
  ...synthetic348(),sessionDate:'2026-10-27'
 }),/LATEST_PREVIOUS_DAY_MASK_REQUIRED/);
 assert.throws(()=>makeNo11G1Chart50Plan({
  ...synthetic348(),otherQuoteCapacity:153
 }),/MARKET_500_CAPACITY_EXCEEDED/);
 assert.throws(()=>makeNo11G1Chart50Plan({
  ...synthetic348(),otherChartFunctions:49,emptySafetySlots:0,
  activeWatchSymbols:['8001.T','8002.T']
 }),/PROTECTED_WATCH_OR_EXIT_OVER_CHART_CAP/);
});
test('Tampering with output allocation or candidate set is rejected',()=>{
 const args=synthetic348();
 const p=makeNo11G1Chart50Plan({...args,emptySafetySlots:0});
 assert.throws(()=>validateNo11Chart50Plan({
  chartPlan:{...p,selectorInputSymbols:[...p.selectorInputSymbols,'9999.T']},
  mask:args.mask,sessionDate:day
 }),/PLAN_HASH_MISMATCH/);
 assert.throws(()=>validateNo11Chart50Plan({
  chartPlan:p,mask:args.mask,sessionDate:'2026-10-27'
 }),/PLAN_MASK_OR_DAY_MISMATCH/);
});
