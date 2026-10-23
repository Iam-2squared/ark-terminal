import test from 'node:test';
import assert from 'node:assert/strict';
import {
  partialDailyUpEvidence,measureUnknownConditionalBounds
} from '../tools/no11_rss_daily_partial_numeric_bounds.mjs';
import {
  DAILY_PLAN_SCHEMA,DAILY_SOURCE_SCHEMA,requiredDailySessions
} from '../runtime/no11_rss_daily_trend_census.mjs';

const session='2026-10-23',dates=requiredDailySessions(session);
const classes=()=>dates.map((date,i)=>({
  session:date,open:String(100+i),high:String(101+i),
  low:String(99+i),close:String(100+i),volume:'1000',
}));
const plan=names=>({
  schemaId:DAILY_PLAN_SCHEMA,planId:'synthetic-plan',
  createdAtJst:'2026-10-23T18:00:00.000+09:00',
  asOfSession:session,expectedSessions:dates,
  symbols:names,baselineAdded:[],
});
function capture(symbol,rows,invalidRows=0,status='OBSERVED'){
  return {
    schemaId:DAILY_SOURCE_SCHEMA,
    planId:'synthetic-plan',symbol,asOfSession:session,
    period:'D',formula:'=RssChart($A$2:$J$2,"'+symbol+'","D",100)',
    observedStartJst:'2026-10-23T19:00:00.000+09:00',
    observedEndJst:'2026-10-23T19:01:00.000+09:00',
    priceBasis:'RSS_CHART_UNVERIFIED',
    decimalProvenance:'EXCEL_VALUE2_ROUNDTRIP',
    corporateActionsCleared:false,originalVendorDecimalCertified:false,
    productionReady:false,orderTransmission:false,
    rows,invalidRows,status,
  };
}
test('complete 76 parsed rising closes with invalid row remains UNKNOWN',()=>{
  const c=capture('1111.T',classes(),1);
  const r=measureUnknownConditionalBounds(plan(['1111.T']),[c]);
  assert.equal(r.report.counts.malformedObservedAllUpButSourceUncertified,1);
  assert.equal(r.report.conditionalObservedCannotPass,0);
  assert.equal(r.report.originalCounts.UNKNOWN,1);
  assert.equal(r.report.conditionalPossiblePassUpperBound,1);
  assert.equal(r.report.productionReady,false);
});
test('known short-period downward slope proves observed numeric nonpass despite a missing old date',()=>{
  const c=classes().map((bar,i)=>({
    ...bar,close:String(300-i),
    open:String(300-i),high:String(301-i),low:String(299-i)
  }));
  const rows=c.slice(1); // MA75 remains missing; 5/15/25 still checkable
  const r=measureUnknownConditionalBounds(plan(['1111.T']),[
    capture('1111.T',rows,2),
  ]);
  assert.equal(r.report.counts.malformedObservedCannotPass,1);
  assert.equal(r.report.conditionalPossiblePassUpperBound,0);
  assert.ok(r.privateDetails[0].knownFalsePeriods.includes(5));
  assert.ok(r.privateDetails[0].knownFalsePeriods.includes(75));
  assert.equal(r.report.passesCertifiedForLive,undefined);
});
test('missing current close cannot be inferred from old observations',()=>{
  const r=partialDailyUpEvidence(dates,classes().slice(0,-1));
  assert.equal(r.category,'UNRESOLVED');
  assert.deepEqual(r.knownFalsePeriods,[]);
  assert.equal(r.missingRequiredDates,1);
  assert.equal(r.unknownPeriods.length,4);
});
test('past bars dropped from 76-day window cause unresolved until true false is known',()=>{
  const r=partialDailyUpEvidence(dates,classes().slice(1));
  assert.equal(r.category,'UNRESOLVED');
  assert.equal(r.knownTruePeriods.length,3);
  assert.deepEqual(r.unknownPeriods,[75]);
});
test('a false price-above-average is sufficient even if the slope endpoint is missing',()=>{
  const r=classes();
  for(let i=0;i<76;i++){
    r[i].close=i===75?'100':String(170+i);
    r[i].open=r[i].close;r[i].high=r[i].close;r[i].low=r[i].close;
  }
  const source=r.filter((_,i)=>i!==70);
  const o=partialDailyUpEvidence(dates,source);
  assert.equal(o.category,'OBSERVED_NUMERIC_CANNOT_PASS');
  assert.ok(o.knownFalsePeriods.includes(5));
});
test('equal slopes are not up, micropositive decimals remain strictly up',()=>{
  let r=classes().map(x=>({...x,close:'100'}));
  assert.equal(partialDailyUpEvidence(dates,r).category,
    'OBSERVED_NUMERIC_CANNOT_PASS');
  r[r.length-1].close='100.000000000000000000000001';
  assert.equal(partialDailyUpEvidence(dates,r).category,
    'OBSERVED_NUMERIC_ALL_UP_BUT_SOURCE_UNCERTIFIED');
});
test('duplicate required date and corrupt closing never infer an exclusion',()=>{
  const r=classes();
  assert.equal(partialDailyUpEvidence(dates,[...r,{...r[0]}]).category,'UNRESOLVED');
  const altered=classes();
  altered[75].close='1e300';
  assert.equal(partialDailyUpEvidence(dates,altered).category,'UNRESOLVED');
});
test('future dates do not modify previous G1 arithmetic',()=>{
  const r=classes(),base=partialDailyUpEvidence(dates,r);
  const next={...r[0],session:'2026-10-26',close:'9999999'};
  assert.deepEqual(partialDailyUpEvidence(dates,[...r,next]),base);
});
test('non-captured symbols and unavailable symbols never become admitted',()=>{
  const names=['1111.T','2222.T','3333.T'];
  const c=capture('1111.T',[],0,'UNAVAILABLE');
  const r=measureUnknownConditionalBounds(plan(names),[c]).report;
  assert.equal(r.originalCounts.UNKNOWN,3);
  assert.equal(r.counts.unavailable,1);
  assert.equal(r.remainingUncaptured,2);
  assert.equal(r.conditionalPossiblePassUpperBound,3);
  assert.equal(r.fullUniverse500CeilingCertified,false);
  assert.equal(r.originalSelectorLiveConnected,false);
});
test('no symbol identifiers or raw values in aggregate receipt',()=>{
  const r=measureUnknownConditionalBounds(plan(['1111.T']),[
    capture('1111.T',classes(),1),
  ]);
  const json=JSON.stringify(r.report);
  assert.equal(json.includes('1111.T'),false);
  assert.equal(json.includes('"1000"'),false);
  assert.equal(r.report.newModelTraining,false);
  assert.equal(r.report.orderTransmission,false);
});
test('invalid provenance rejects without fabricating numeric bounds',()=>{
  const c=capture('1111.T',classes(),1);
  c.orderTransmission=true;
  assert.throws(()=>measureUnknownConditionalBounds(plan(['1111.T']),[c]),
    /NO11_DAILY_CAPTURE_CONTRACT_INVALID/);
});
