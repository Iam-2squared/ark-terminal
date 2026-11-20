/**
 * No.1.2 marketwide observation CAPACITY PLANNER ONLY.
 * Input is a dated JPX symbol roster, NOT TradingView market quotes/ranks.
 * This module never reads Excel, polls RSS, manufactures Selector scores or
 * authorizes an order. Physical per-wave read duration is still unknown.
 */
import {createHash} from 'node:crypto';
export const NO12_MARKETWIDE_SOURCE_SCHEMA='ARK_NO12_JPX_SYMBOL_ROSTER_V1';
export const NO12_MARKETWIDE_MAX_RSS_SYMBOLS=500;
export const NO12_MARKETWIDE_MAX_RSS_CHARTS=50;
const fail=s=>{throw Error(s)};
const norm=s=>{
 if(typeof s!=='string'||!/^[0-9A-Z]{4}\.T$/.test(s))
  fail('NO12_UNIVERSE_EXPLICIT_TSE_SYMBOL_REQUIRED');
 return s;
};
const when=(s,label)=>{
 if(typeof s!=='string'||!/(Z|[+-]\d\d:\d\d)$/.test(s)||!Number.isFinite(Date.parse(s)))
  fail(label);
 return Date.parse(s);
};
const unique=(rows,label)=>{
 if(!Array.isArray(rows))fail(label+'_ARRAY_REQUIRED');
 const out=new Set();
 for(const value of rows){
  const symbol=norm(value);
  if(out.has(symbol))fail(label+'_DUPLICATE');
  out.add(symbol);
 }
 return [...out];
};
const sha=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
export function planNo12JpxMarketwideReadOnly({
 mode,roster,decisionAt,pinnedSymbols=[],chartSymbols=[],
 chartPeriods=['1M'],otherQuoteSymbols=[],
 otherChartFunctions=0
}={}){
 if(mode!=='SYNTHETIC_OFFLINE_ONLY')fail('NO12_MARKETWIDE_LIVE_PROMOTION_FORBIDDEN');
 if(roster?.schemaId!==NO12_MARKETWIDE_SOURCE_SCHEMA||
  roster.source!=='JPX_DATED_MASTER_SYMBOLS_ONLY'||roster.licensedMarketQuotes===true)
  fail('NO12_UNIVERSE_ROSTER_SOURCE_INVALID');
 const t=when(decisionAt,'NO12_UNIVERSE_DECISION_TIME_INVALID');
 const asOf=when(roster.asOf,'NO12_UNIVERSE_ROSTER_TIME_INVALID');
 if(asOf>t||t-asOf>7*86400000)fail('NO12_UNIVERSE_ROSTER_FUTURE_OR_STALE');
 const all=unique(roster.symbols,'NO12_UNIVERSE');
 if(all.length<3000||all.length>6000)
  fail('NO12_UNIVERSE_COVERAGE_NOT_PROVEN');
 const listed=new Set(all);
 const pinned=unique(pinnedSymbols,'NO12_PINNED');
 const charts=unique(chartSymbols,'NO12_CHART_TARGET');
 const preallocated=unique(otherQuoteSymbols,'NO12_OTHER_QUOTE');
 if(!Array.isArray(chartPeriods)||chartPeriods.length<1||chartPeriods.length>2||
   new Set(chartPeriods).size!==chartPeriods.length||
   chartPeriods.some(x=>!['1M','5M'].includes(x)))
  fail('NO12_CHART_PERIODS_INVALID');
 if(!Number.isInteger(otherChartFunctions)||otherChartFunctions<0||
   otherChartFunctions>NO12_MARKETWIDE_MAX_RSS_CHARTS)
  fail('NO12_OTHER_CHART_BUDGET_INVALID');
 for(const s of [...pinned,...charts]){
  if(!listed.has(s))fail('NO12_PRIORITY_SYMBOL_NOT_IN_DATED_ROSTER');
 }
 for(const s of pinned)if(!charts.includes(s))fail('NO12_PINNED_EXIT_SYMBOL_NOT_MONITORED');
 const quoteSlots=new Set([...pinned,...preallocated]);
 if(quoteSlots.size!==pinned.length+preallocated.length)
  fail('NO12_PINNED_PREALLOCATED_QUOTE_COLLISION');
 if(quoteSlots.size>=NO12_MARKETWIDE_MAX_RSS_SYMBOLS)
  fail('NO12_RSS_QUOTE_CAPACITY_EXHAUSTED');
 const functionsUsed=charts.length*chartPeriods.length+otherChartFunctions;
 if(functionsUsed>NO12_MARKETWIDE_MAX_RSS_CHARTS)
  fail('NO12_RSS_CHART_FUNCTION_CAPACITY_EXCEEDED');
 const perWave=NO12_MARKETWIDE_MAX_RSS_SYMBOLS-quoteSlots.size;
 // Deduplicate per-wave priority from the general roster, but NEVER silently
 // delete or score any complete-universe member. Every member gets a wave.
 const remaining=all.filter(s=>!quoteSlots.has(s));
 const waves=[];
 for(let start=0;start<remaining.length;start+=perWave){
  const batch=remaining.slice(start,start+perWave);
  waves.push(Object.freeze({index:waves.length,quoteSymbols:Object.freeze([...quoteSlots,...batch]),
   uniqueRosterSymbols:Object.freeze(batch),quoteCount:quoteSlots.size+batch.length}));
 }
 if(waves.length===0)waves.push(Object.freeze({index:0,quoteSymbols:Object.freeze([...quoteSlots]),
  uniqueRosterSymbols:Object.freeze([]),quoteCount:quoteSlots.size}));
 const result={
  schemaId:'ARK_NO12_RSS_MARKETWIDE_SCAN_PLAN_V1',
  status:'SYNTHETIC_SCAN_PLAN_NOT_MARKET_OBSERVATION',
  decisionAt,rosterAsOf:roster.asOf,rosterSource:roster.source,
  expectedUniverseSymbols:all.length,expectedUniverseSha256:sha(all),
  universeSymbols:Object.freeze([...all]),
  pinnedSymbols:Object.freeze(pinned),chartSymbols:Object.freeze(charts),
  chartPeriods:Object.freeze([...chartPeriods]),
  chartFunctionsUsed:functionsUsed,maxChartFunctions:NO12_MARKETWIDE_MAX_RSS_CHARTS,
  quotedSymbolsAlreadyReserved:preallocated.length,
  preallocatedQuoteSymbols:Object.freeze(preallocated),
  maxSimultaneousQuoteSymbols:NO12_MARKETWIDE_MAX_RSS_SYMBOLS,
  waves:Object.freeze(waves),
  licensingOfLiveMarketFeedCertified:false,allWavesPhysicallyObserved:false,
  frozenNo11SelectorReproduced:false,originalNativeEntryCertified:false,
  productionReady:false,orderTransmission:false
 };
 return Object.freeze({...result,planSha256:sha(result)});
}
export function auditNo12ScanWaveCoverage({plan,receipts,decisionAt}={}){
 if(plan?.schemaId!=='ARK_NO12_RSS_MARKETWIDE_SCAN_PLAN_V1'||
   plan.productionReady!==false||plan.orderTransmission!==false||
   !Array.isArray(plan.waves)||plan.waves.length===0)
  fail('NO12_SCAN_PLAN_REQUIRED');
 const {planSha256,...core}=plan;
 if(planSha256!==sha(core))fail('NO12_SCAN_PLAN_TAMPERED');
 if(!Array.isArray(receipts))fail('NO12_SCAN_WAVE_RECEIPTS_REQUIRED');
 const decision=when(decisionAt,'NO12_SCAN_DECISION_INVALID'),seen=new Set();
 const covered=new Set(),spans=[];
 const listed=new Set(plan.universeSymbols);
 if(listed.size!==plan.expectedUniverseSymbols||sha(plan.universeSymbols)!==plan.expectedUniverseSha256)
  fail('NO12_SCAN_ROSTER_IDENTITY_TAMPERED');
 for(const receipt of receipts){
  const i=receipt?.waveIndex;
  if(!Number.isInteger(i)||i<0||i>=plan.waves.length||seen.has(i))
   fail('NO12_SCAN_WAVE_ID_INVALID_OR_DUPLICATE');
  seen.add(i);
  const expected=plan.waves[i].quoteSymbols;
  const actual=unique(receipt.symbols,'NO12_OBSERVED_WAVE');
  if(actual.length!==expected.length||
    actual.some((s,j)=>s!==expected[j]))
    fail('NO12_SCAN_WAVE_IDENTITY_MISMATCH');
  const start=when(receipt.startedAt,'NO12_WAVE_START_TIME_INVALID');
  const end=when(receipt.finishedAt,'NO12_WAVE_END_TIME_INVALID');
  if(end<start||end>decision||start<when(plan.rosterAsOf,'NO12_ROSTER_CLOCK_INVALID'))
   fail('NO12_WAVE_CAUSAL_TIME_INVALID');
  spans.push([start,end]);
  for(const symbol of actual)if(listed.has(symbol))covered.add(symbol);
 }
 const complete=seen.size===plan.waves.length&&covered.size===plan.expectedUniverseSymbols;
 const first=Math.min(...spans.map(x=>x[0])),last=Math.max(...spans.map(x=>x[1]));
 const bounded=spans.length>0&&last-first<=5*60000;
 return Object.freeze({
  schemaId:'ARK_NO12_MARKETWIDE_COVERAGE_AUDIT_V1',
  status:complete&&bounded?'LOCAL_WAVE_COVERAGE_RECORDED_NOT_BROKER_CERTIFIED':
   'INCOMPLETE_OR_DELAYED_WAVE_COVERAGE',
  expectedWaves:plan.waves.length,observedWaves:seen.size,
  observedRosterMembers:covered.size,expectedRosterMembers:plan.expectedUniverseSymbols,
  withinFiveMinuteObservationWindow:bounded,
  brokerActualArrivalCertified:false,licensedRealtimeSourceCertified:false,
  nativeFrozenSelectorCertified:false,productionReady:false,orderTransmission:false
 });
}
