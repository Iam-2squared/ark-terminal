import test from 'node:test';
import assert from 'node:assert/strict';
import {makeObservedPassWatchMask,checkObservedPassBeforeBuy,OBSERVED_PASS_GATE_ID}
  from '../runtime/no11_observed_pass_watch_gate.mjs';
import {requiredDailySessions,DAILY_SOURCE_SCHEMA,DAILY_PLAN_SCHEMA}
  from '../runtime/no11_rss_daily_trend_census.mjs';
const asOf='2026-10-23',days=requiredDailySessions(asOf);
const plan={
 schemaId:DAILY_PLAN_SCHEMA,planId:'synthetic-plan',asOfSession:asOf,
 expectedSessions:days,symbols:['1111.T','2222.T','3333.T'],
};
const capture=(symbol,trend,invalidRows=0)=>({
 schemaId:DAILY_SOURCE_SCHEMA,planId:plan.planId,symbol,asOfSession:asOf,
 period:'D',formula:'=RssChart($A$2:$J$2,"'+symbol+'","D",100)',
 status:'OBSERVED',invalidRows,priceBasis:'RSS_CHART_UNVERIFIED',
 decimalProvenance:'EXCEL_VALUE2_ROUNDTRIP',corporateActionsCleared:false,
 originalVendorDecimalCertified:false,productionReady:false,orderTransmission:false,
 observedStartJst:asOf+'T19:00:00.000+09:00',
 observedEndJst:asOf+'T19:00:01.000+09:00',
 rows:days.map((session,i)=>{
   const p=trend==='UP'?100+i:200-i;
   return {session,open:String(p),high:String(p+1),
     low:String(p-1),close:String(p),volume:'1000'};
 })
});
test('Only actual PASS enters observed watch pool; UNKNOWN never fallback',()=>{
 const valid=capture('1111.T','UP');
 const rejected=capture('2222.T','DOWN');
 const malformed=capture('3333.T','UP',1);
 const mask=makeObservedPassWatchMask(plan,[valid,rejected,malformed]);
 assert.equal(mask.schemaId,OBSERVED_PASS_GATE_ID);
 assert.deepEqual(mask.observedPassSymbols,['1111.T']);
 assert.equal(mask.observedPassCount,1);
 assert.equal(mask.dataStillUnknown,1);
 assert.equal(mask.originalSelectorMarketBreadthResolved,false);
 assert.equal(mask.productionReady,false);
 assert.equal(mask.orderTransmission,false);
 for(const code of ['2222.T','3333.T']){
  assert.deepEqual(checkObservedPassBeforeBuy({mask,symbol:code,priorSession:asOf}),
    {dailyGatePassed:false,reason:'NOT_CONFIRMED_UPTREND',orderAuthorized:false});
 }
 assert.deepEqual(checkObservedPassBeforeBuy({mask,symbol:'1111.T',priorSession:asOf}),
   {dailyGatePassed:true,reason:'OBSERVED_DAILY_PASS_ONLY_FURTHER_CHECKS_REQUIRED',
    orderAuthorized:false});
});
test('Wrong day and malformed allowlist fail closed at final candidate',()=>{
 const mask=makeObservedPassWatchMask(plan,[
  capture('1111.T','UP'),capture('2222.T','DOWN'),capture('3333.T','UP',1)]);
 assert.equal(checkObservedPassBeforeBuy({mask,symbol:'1111.T',
    priorSession:'2026-10-22'}).dailyGatePassed,false);
 assert.equal(checkObservedPassBeforeBuy({mask:{...mask,shadowOnly:false},
    symbol:'1111.T',priorSession:asOf}).dailyGatePassed,false);
 assert.equal(checkObservedPassBeforeBuy({mask:{...mask,observedPassSymbols:['BAD']},
    symbol:'1111.T',priorSession:asOf}).dailyGatePassed,false);
});
test('Incomplete source blocks manifest instead of inventing an all-PASS pool',()=>{
 assert.throws(()=>makeObservedPassWatchMask(plan,[capture('1111.T','UP')]),
  /NO11_DAYPASS_FULL_CAPTURE_REQUIRED/);
});
