import test from 'node:test';
import assert from 'node:assert/strict';
import {
 planNo12JpxMarketwideReadOnly as plan,
 auditNo12ScanWaveCoverage as audit,
 NO12_MARKETWIDE_MAX_RSS_SYMBOLS as QUOTES,
 NO12_MARKETWIDE_MAX_RSS_CHARTS as CHARTS,
 NO12_MARKETWIDE_SOURCE_SCHEMA as ROSTER
} from '../runtime/no12_marketwide_rss_capacity.mjs';
const all=()=>Array.from({length:3500},(_,i)=>String(1000+i)+'.T');
const decisionAt='2026-10-13T09:40:00+09:00';
function args(overrides={}){
 const u=all();
 return {mode:'SYNTHETIC_OFFLINE_ONLY',
  roster:{schemaId:ROSTER,source:'JPX_DATED_MASTER_SYMBOLS_ONLY',
    asOf:'2026-10-12T16:00:00+09:00',symbols:u},
  decisionAt,pinnedSymbols:u.slice(0,3),
  chartSymbols:u.slice(0,40),chartPeriods:['1M'],
  otherQuoteSymbols:[],otherChartFunctions:0,...overrides};
}
test('JPX market-wide 3500 symbols are scheduled across capped quote waves, not as 3500 simultaneous RSS subscriptions',()=>{
 const x=plan(args());
 assert.equal(QUOTES,500);assert.equal(CHARTS,50);
 assert.equal(x.expectedUniverseSymbols,3500);
 assert.equal(x.waves.length,8);
 assert(x.waves.every(w=>w.quoteCount<=QUOTES));
 assert(x.waves.every(w=>x.pinnedSymbols.every(s=>w.quoteSymbols.includes(s))));
 assert.equal(x.chartFunctionsUsed,40);
 assert.equal(x.status,'SYNTHETIC_SCAN_PLAN_NOT_MARKET_OBSERVATION');
 assert.equal(x.allWavesPhysicallyObserved,false);
 assert.equal(x.productionReady,false);
 assert.equal(x.orderTransmission,false);
});
test('using 1M and 5M separately costs TWO chart functions per symbol',()=>{
 const x=all();
 const p=plan(args({chartSymbols:x.slice(0,25),chartPeriods:['1M','5M']}));
 assert.equal(p.chartFunctionsUsed,50);
 assert.throws(()=>plan(args({chartSymbols:x.slice(0,26),chartPeriods:['1M','5M']})),
  /NO12_RSS_CHART_FUNCTION_CAPACITY_EXCEEDED/);
});
test('existing RSS functions reduce chart budget and cannot be silently evicted',()=>{
 const x=all();
 const p=plan(args({chartSymbols:x.slice(0,48),otherChartFunctions:2}));
 assert.equal(p.chartFunctionsUsed,50);
 assert.throws(()=>plan(args({chartSymbols:x.slice(0,48),otherChartFunctions:3})),
  /NO12_RSS_CHART_FUNCTION_CAPACITY_EXCEEDED/);
});
test('pinned positions require market chart coverage, not just an unused slot',()=>{
 const x=all();
 assert.throws(()=>plan(args({chartSymbols:x.slice(3,20)})),
  /NO12_PINNED_EXIT_SYMBOL_NOT_MONITORED/);
 assert.throws(()=>plan(args({pinnedSymbols:['9999.T']})),
  /NO12_PRIORITY_SYMBOL_NOT_IN_DATED_ROSTER/);
});
test('quotes already subscribed lower each per-wave capacity without breaking roster coverage',()=>{
 const x=all();
 const p=plan(args({otherQuoteSymbols:['8501.T','8502.T']}));
 assert.equal(p.quotedSymbolsAlreadyReserved,2);
 assert(p.waves.every(w=>w.quoteCount<=500));
 assert.equal(new Set(p.waves.flatMap(w=>w.quoteSymbols).filter(s=>x.includes(s))).size,3500);
});
test('dated master roster must be large, causal, unique, explicit and not TradingView quote data',()=>{
 const x=all();
 assert.throws(()=>plan(args({roster:{...args().roster,source:'TRADINGVIEW_JAPAN_SCANNER'}})),
  /NO12_UNIVERSE_ROSTER_SOURCE_INVALID/);
 assert.throws(()=>plan(args({roster:{...args().roster,symbols:x.slice(0,2500)}})),
  /NO12_UNIVERSE_COVERAGE_NOT_PROVEN/);
 assert.throws(()=>plan(args({roster:{...args().roster,symbols:[...x,x[0]]}})),
  /NO12_UNIVERSE_DUPLICATE/);
 assert.throws(()=>plan(args({roster:{...args().roster,asOf:'2026-10-13T10:00:00+09:00'}})),
  /NO12_UNIVERSE_ROSTER_FUTURE_OR_STALE/);
 assert.throws(()=>plan(args({roster:{...args().roster,asOf:'2026-09-25T15:00:00+09:00'}})),
  /NO12_UNIVERSE_ROSTER_FUTURE_OR_STALE/);
 assert.throws(()=>plan(args({roster:{...args().roster,symbols:[...x.slice(1),'72030']}})),
  /NO12_UNIVERSE_EXPLICIT_TSE_SYMBOL_REQUIRED/);
});
test('real execution mode fails even for a perfectly formatted universe and chart budget',()=>{
 assert.throws(()=>plan(args({mode:'LIVE_TRADING'})),/NO12_MARKETWIDE_LIVE_PROMOTION_FORBIDDEN/);
});
function waveReceipts(p,intervalSec=35){
 return p.waves.map((w,i)=>{
  const start=Date.parse('2026-10-13T09:32:00+09:00')+i*intervalSec*1000;
  return {waveIndex:w.index,symbols:[...w.quoteSymbols],
   startedAt:new Date(start).toISOString(),
   finishedAt:new Date(start+5000).toISOString()};
 });
}
test('finite synthetic wave observation window can be measured but is NOT authenticated feed delivery',()=>{
 const p=plan(args());
 const a=audit({plan:p,receipts:waveReceipts(p),decisionAt});
 assert.equal(a.status,'LOCAL_WAVE_COVERAGE_RECORDED_NOT_BROKER_CERTIFIED');
 assert.equal(a.expectedWaves,8);
 assert.equal(a.observedWaves,8);
 assert.equal(a.observedRosterMembers,3500);
 assert.equal(a.withinFiveMinuteObservationWindow,true);
 assert.equal(a.brokerActualArrivalCertified,false);
 assert.equal(a.nativeFrozenSelectorCertified,false);
 assert.equal(a.productionReady,false);
});
test('a missing quote wave or >5 minute capture span stays INCOMPLETE',()=>{
 const p=plan(args());
 const missing=audit({plan:p,receipts:waveReceipts(p).slice(1),decisionAt});
 assert.equal(missing.status,'INCOMPLETE_OR_DELAYED_WAVE_COVERAGE');
 assert.equal(missing.observedRosterMembers<3500,true);
 const slow=audit({plan:p,receipts:waveReceipts(p,55),decisionAt});
 assert.equal(slow.status,'INCOMPLETE_OR_DELAYED_WAVE_COVERAGE');
 assert.equal(slow.withinFiveMinuteObservationWindow,false);
});
test('unexpected symbols, duplicated wave IDs and future observations fail closed',()=>{
 const p=plan(args()),receipts=waveReceipts(p);
 const wrong=structuredClone(receipts);
 wrong[0].symbols[1]='9999.T';
 assert.throws(()=>audit({plan:p,receipts:wrong,decisionAt}),/NO12_SCAN_WAVE_IDENTITY_MISMATCH/);
 assert.throws(()=>audit({plan:p,receipts:[receipts[0],receipts[0]],decisionAt}),
  /NO12_SCAN_WAVE_ID_INVALID_OR_DUPLICATE/);
 const future=structuredClone(receipts);
 future[0].finishedAt='2026-10-13T10:00:00+09:00';
 assert.throws(()=>audit({plan:p,receipts:future,decisionAt}),/NO12_WAVE_CAUSAL_TIME_INVALID/);
});
test('plan tampering fails even when underlying timestamp and output shape look valid',()=>{
 const p=plan(args()),altered={...p,maxSimultaneousQuoteSymbols:3500};
 assert.throws(()=>audit({plan:altered,receipts:waveReceipts(p),decisionAt}),
  /NO12_SCAN_PLAN_TAMPERED/);
});
