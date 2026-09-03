import fs from 'node:fs';
import path from 'node:path';
import {
  createRealtimeSessionState,
  SAFETY,
  verifyRealtimeLedger,
} from '../predict/realtime/phase57-stateful-contract.js';
import {processRealtimeFiveMinutePoint} from '../predict/realtime/phase57-realtime-orchestrator.js';
import {scoreRealtimeFrozenEntry} from '../predict/realtime/phase57-realtime-entry-position.js';
import {scoreRealtimeSessionFromLedger,replayRealtimeSnapshotsFromLedger} from '../predict/realtime/phase57-realtime-postclose.js';
import {buildIntradayDynamicUniverseTimeline} from '../predict/daytrade/phase57-p25-intraday-dynamic-universe.js';
import {buildIntradayDynamicUniverseTimelineV2} from '../predict/daytrade/phase57-p25-intraday-dynamic-universe-v2.js';
import {buildProspectiveP21HistoricalRows} from '../predict/daytrade/phase57-p21-prospective-history.js';
import {PHASE58_P13_FROZEN_POLICY} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';
import {buildP25DataDrivenExitAnalogPool} from '../predict/daytrade/phase57-p25-data-driven-exit.js';
import {P25_EXIT_V3_INDEPENDENT_PROTOCOL} from '../predict/daytrade/phase57-p25-exit-v3-independent-protocol.js';
import {buildP252Yahoo5mUrls} from '../predict/daytrade/phase57-p25-2j-routine-nonrss-5m-source.js';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const marketwidePath=arg('--marketwide');
const historyPath=arg('--history-pack');
const statePath=arg('--state',null);
const outputState=arg('--output-state','tmp/phase57-realtime-live-state.json');
const outputSnapshot=arg('--output-snapshot','tmp/phase57-realtime-live-snapshot.json');
const outputPostClose=arg('--output-postclose',null);
if(!marketwidePath||!historyPath)throw new Error('usage: --marketwide <json> --history-pack <json> [--state prior.json] --output-state <json> --output-snapshot <json>');

const FALSE_KEYS=['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed'];
for(const key of FALSE_KEYS)if(SAFETY[key]!==false)throw new Error(`unsafe realtime live runner ${key}`);

const payload=JSON.parse(fs.readFileSync(marketwidePath,'utf8'));
const entries=Array.isArray(payload)?payload:(payload.entries??[]);
const at=String(payload?.meta?.observedAt??'');
if(!Number.isFinite(Date.parse(at)))throw new Error('marketwide observedAt required');
if(entries.length<3000)throw new Error(`marketwide input below 3000 symbols: ${entries.length}`);

const JST_DATE=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'});
const sessionDate=JST_DATE.format(new Date(at));
function jstHm(value){
  const p=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(value)).map(x=>[x.type,x.value]));
  return `${p.hour}:${p.minute}`;
}
function normalizeSymbol(value){return String(value??'').trim().toUpperCase();}
function openSymbols(state){
  const out=new Set();
  for(const strategy of Object.values(state.strategies??{}))for(const symbol of Object.keys(strategy.positions??{}))out.add(normalizeSymbol(symbol));
  return [...out].filter(Boolean).sort();
}
function expectedDecisionTimes(date){
  const out=[];
  for(const [start,end] of [['09:05','11:30'],['12:35','15:30']]){
    let t=Date.parse(`${date}T${start}:00+09:00`),last=Date.parse(`${date}T${end}:00+09:00`);
    while(t<=last){out.push(new Date(t).toISOString());t+=5*60_000;}
  }
  return out;
}
const expectedTimes=expectedDecisionTimes(sessionDate);
const atMs=Date.parse(at);
const expectedSoFar=expectedTimes.filter(x=>Date.parse(x)<=atMs).length;
const sessionEnd=jstHm(at)>='15:30';
const FIVE_MINUTES_MS=5*60_000;
const finalizedCloseMs=Math.floor(atMs/FIVE_MINUTES_MS)*FIVE_MINUTES_MS;
const targetStart=new Date(finalizedCloseMs-FIVE_MINUTES_MS).toISOString();

let state=null;
if(statePath&&fs.existsSync(statePath)){
  const candidate=JSON.parse(fs.readFileSync(statePath,'utf8'));
  if(candidate?.sessionDate===sessionDate)state=candidate;
}
if(!state)state=createRealtimeSessionState({sessionDate});
state.liveMeasurement??={startedAt:at,source:'TRADINGVIEW_MARKETWIDE_PLUS_YAHOO_5M_FINALIZED',partialLateStart:jstHm(at)>'09:05'};
state.liveMeasurement.startedAt??=at;

const held=openSymbols(state);
const heldSymbolsByCutoff={[at]:held};
const snapshots=[{asOf:at,entries}];
const previewV1=buildIntradayDynamicUniverseTimeline({snapshots,heldSymbolsByCutoff});
const previewV2=buildIntradayDynamicUniverseTimelineV2({snapshots,heldSymbolsByCutoff,priorSelections:state.selection?.priorV2??[]});
const v1=previewV1.points?.[0]?.rawUniverse??[];
const v2=previewV2.points?.[0]?.rawUniverse??[];
if(v1.length<20||v2.length<15)throw new Error(`realtime selector preview incomplete: V1=${v1.length} V2=${v2.length}`);
const symbols=[...new Set([...v1,...v2].map(x=>normalizeSymbol(x.symbol)).concat(held))].filter(Boolean).sort();

const historyPack=JSON.parse(fs.readFileSync(historyPath,'utf8'));
const cached=buildProspectiveP21HistoricalRows({sessions:historyPack.sessions??[],horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars});
if(cached.complete!==true)throw new Error(`historical materialization blocked: ${cached.status}`);
const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:historyPack.sessions??[]})
  .filter(x=>String(x.sessionDate)<=P25_EXIT_V3_INDEPENDENT_PROTOCOL.developmentCutoff);
if(!analogPool.length)throw new Error('frozen EXIT v3/v4 analog pool empty');
const priorOnlyCache=new Map();
const scoreEntry=({symbol,bars5m})=>scoreRealtimeFrozenEntry({
  symbol,sessionDate,bars5m,
  historicalHorizonRowsByBars:cached.historicalHorizonRowsByBars,
  selectionOptions:PHASE58_P13_FROZEN_POLICY.selectionOptions,
  priorOnlyCache,
});

function parseYahooPrefix(json,symbol){
  const result=json?.chart?.result?.[0];
  if(json?.chart?.error||!result)throw new Error(`Yahoo chart missing for ${symbol}`);
  const ts=Array.isArray(result.timestamp)?result.timestamp:[];
  const q=result.indicators?.quote?.[0]??{};
  const bars=[];
  for(let i=0;i<ts.length;i++){
    const epoch=Number(ts[i]);
    const values=[q.open?.[i],q.high?.[i],q.low?.[i],q.close?.[i],q.volume?.[i]].map(Number);
    if(!Number.isFinite(epoch)||values.some(v=>!Number.isFinite(v)))continue;
    const timestamp=new Date(epoch*1000).toISOString();
    const [open,high,low,close,volume]=values;
    if(open<=0||close<=0||high<low||high<Math.max(open,close)||low>Math.min(open,close)||volume<0)continue;
    const localDate=JST_DATE.format(new Date(timestamp));
    const hm=jstHm(timestamp);
    if(localDate!==sessionDate||hm<'09:00'||hm>='15:30')continue;
    if(Date.parse(timestamp)+FIVE_MINUTES_MS>atMs)continue;
    bars.push({timestamp,open,high,low,close,volume});
  }
  bars.sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  return bars;
}
async function fetchSymbolPrefix(symbol){
  let lastError='no usable finalized prefix';
  for(let attempt=0;attempt<2;attempt++){
    for(const url of buildP252Yahoo5mUrls({symbol,sessionDate})){
      try{
        const response=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0','Accept':'application/json'},cache:'no-store'});
        if(!response.ok)throw new Error(`HTTP ${response.status}`);
        const bars=parseYahooPrefix(await response.json(),symbol);
        // Realtime state must be allowed to commit the first causal 5m points.
        // Frozen Entry itself owns the >=6 closed-bar readiness gate; imposing it here
        // made 09:05-09:25 impossible and therefore made FULL_FRESH unreachable.
        if(bars.length>=1)return bars;
        lastError='no finalized same-session bars';
      }catch(error){lastError=String(error?.message??error);}
    }
    if(attempt<1)await new Promise(r=>setTimeout(r,5000));
  }
  throw new Error(`Yahoo finalized 5m prefix failed ${symbol}: ${lastError}`);
}
async function mapLimit(values,limit,fn){
  const out=new Array(values.length);let next=0;
  async function worker(){while(true){const i=next++;if(i>=values.length)return;out[i]=await fn(values[i]);}}
  await Promise.all(Array.from({length:Math.min(limit,values.length)},worker));
  return out;
}

const prefixes=await mapLimit(symbols,8,async symbol=>[symbol,await fetchSymbolPrefix(symbol)]);
const barsBySymbolHistory=Object.fromEntries(prefixes);
const marketBars=prefixes.flatMap(([symbol,bars])=>{
  const bar=bars.find(x=>x.timestamp===targetStart);
  return bar?[{symbol,bar:{...bar,at:bar.timestamp}}]:[];
});
const sparseNoTradeSymbolCount=prefixes.length-marketBars.length;

// Source-readiness guard: a delayed provider can temporarily expose a valid historical prefix
// while still not publishing the exact target bucket. Committing that point would incorrectly
// turn publication delay into a synthetic "all symbols had no trade" interval. Fail closed and
// keep the immutable raw selector snapshot queued for retry instead. A genuine sparse interval is
// still accepted once at least one selected/held symbol proves the target bucket is published.
if(symbols.length>0&&marketBars.length===0){
  throw new Error(`SOURCE_NOT_READY target=${targetStart} selectedOrHeld=${symbols.length}; retain raw snapshot for retry`);
}

const priorPointCount=state.pipeline?.history?.length??0;
const missingBucketCount=Math.max(0,expectedSoFar-(priorPointCount+1));
const sessionQuality=(state.liveMeasurement.partialLateStart===false&&missingBucketCount===0)?'FULL_FRESH':'PARTIAL_INCOMPLETE_SESSION';
const result=processRealtimeFiveMinutePoint(state,{
  at,
  marketBars,
  selectionEntries:entries,
  barsBySymbolHistory,
  scoreEntry,
  analogPool,
  sessionEnd,
  sessionQuality,
  missingBucketCount,
  expectedBucketCount:expectedTimes.length,
});

const actualV1=(result.dashboard&&state.selection?.V1?state.selection.V1:[]).map(x=>normalizeSymbol(x.symbol));
const actualV2=(result.dashboard&&state.selection?.V2?state.selection.V2:[]).map(x=>normalizeSymbol(x.symbol));
if(JSON.stringify(actualV1)!==JSON.stringify(v1.map(x=>normalizeSymbol(x.symbol))))throw new Error('R10 V1 selection differs from prefetch preview');
if(JSON.stringify(actualV2)!==JSON.stringify(v2.map(x=>normalizeSymbol(x.symbol))))throw new Error('R10 V2 selection differs from prefetch preview');
const verified=verifyRealtimeLedger(state.ledger,{sessionDate});
const snapshot={
  schemaVersion:1,
  phase:'57.realtime.r11-live',
  status:'PHASE57_REALTIME_LIVE_SNAPSHOT_COMMITTED',
  sessionDate,
  at,
  sessionQuality,
  missingBucketCount,
  expectedBucketCount:expectedTimes.length,
  processedPointCount:state.pipeline?.history?.length??0,
  source:{selection:'TRADINGVIEW_JAPAN_SCANNER_POINT_IN_TIME',bars:'YAHOO_FINANCE_5M_FINALIZED_PREFIX'},
  finalizedBarSymbolCount:marketBars.length,
  sparseNoTradeSymbolCount,
  selection:{v1:result.selection.v1,v2:result.selection.v2},
  frozenEntryCount:result.frozenEntryCount,
  dashboard:result.dashboard,
  ledgerEventCount:verified.eventCount,
  ledgerHeadHash:verified.headHash,
  methodology:{backfillUsed:false,futureOutcomeUsed:false,frozenResearchSemanticsChanged:false,postCloseDecisionRecompute:false,noTradeFiveMinuteBucketsForwardFilled:false},
  safety:SAFETY,
};
fs.mkdirSync(path.dirname(outputState),{recursive:true});
fs.mkdirSync(path.dirname(outputSnapshot),{recursive:true});
fs.writeFileSync(outputState,JSON.stringify(state,null,2)+'\n');
fs.writeFileSync(outputSnapshot,JSON.stringify(snapshot,null,2)+'\n');
if(sessionEnd&&outputPostClose){
  const postclose=scoreRealtimeSessionFromLedger(state.ledger,{sessionDate});
  const replay=replayRealtimeSnapshotsFromLedger(state.ledger,{sessionDate});
  fs.mkdirSync(path.dirname(outputPostClose),{recursive:true});
  fs.writeFileSync(outputPostClose,JSON.stringify({...postclose,replay},null,2)+'\n');
}
console.log(JSON.stringify({status:snapshot.status,sessionDate,at,sessionQuality,selection:snapshot.selection,finalizedBarSymbolCount:snapshot.finalizedBarSymbolCount,sparseNoTradeSymbolCount:snapshot.sparseNoTradeSymbolCount,frozenEntryCount:snapshot.frozenEntryCount,processedPointCount:snapshot.processedPointCount,ledgerEventCount:snapshot.ledgerEventCount,strategies:snapshot.dashboard.strategies.map(x=>({strategyId:x.strategyId,netPercent:x.netPercent,openPositions:x.openPositions,closedTrades:x.closedTrades,winRate:x.winRate,profitFactor:x.profitFactor,maxDrawdownPercent:x.maxDrawdownPercent}))},null,2));
