import fs from 'node:fs';
import { CHART_TRADE_MANAGEMENT_HOLDOUT_UNIVERSE } from './phase57-chart-trade-management-holdout-universe.js';
import { buildSessionAwareMultiTimeframePerception } from './phase57-chart-perception-session-aware.js';
import { classifyHumanStyleSetup } from './phase57-chart-perception-measurement.js';
import { scoreHumanStyleSetupQuality } from './phase57-chart-setup-quality.js';
import { simulateFrozenRatchetExit } from './phase57-frozen-ratchet-exit.js';
import {
  P23_10F_ECONOMIC_POLICY,
  isFrozenQ4Candidate,
  summarizeEconomicTrades,
} from './phase57-chart-economic-validation.js';
import {
  P23_10G_SETUP_MANAGEMENT_POLICY,
  PHASE57_P23_10G_SAFETY,
  simulateSetupSpecificManagedExit,
  summarizePairedExitDelta,
} from './phase57-setup-specific-trade-management.js';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const symbols = process.env.PHASE57_SYMBOLS
  ? process.env.PHASE57_SYMBOLS.split(',').map(v => v.trim()).filter(Boolean)
  : CHART_TRADE_MANAGEMENT_HOLDOUT_UNIVERSE.slice(0, 3);
const minHistoryBars = Number(process.env.PHASE57_MIN_HISTORY_BARS ?? 1600);
const stepBars = Number(process.env.PHASE57_STEP_BARS ?? 3);
const maxContextBars = Number(process.env.PHASE57_MAX_CONTEXT_BARS ?? 2600);
const JST = new Intl.DateTimeFormat('en-CA', {
  timeZone:'Asia/Tokyo', year:'numeric', month:'2-digit', day:'2-digit',
  hour:'2-digit', minute:'2-digit', hourCycle:'h23',
});

function parts(ts) {
  const p=Object.fromEntries(JST.formatToParts(new Date(ts)).map(x=>[x.type,x.value]));
  return {date:`${p.year}-${p.month}-${p.day}`,hm:`${p.hour}:${p.minute}`};
}
function normalize(rows=[]) {
  return rows.map(r=>({timestamp:new Date(r.timestamp).toISOString(),open:Number(r.open),high:Number(r.high),low:Number(r.low),close:Number(r.close),volume:Number(r.volume??0)}))
    .filter(r=>[r.open,r.high,r.low,r.close].every(Number.isFinite)&&r.high>=r.low)
    .sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
}
async function fetchJson(urls,symbol) {
  let last;
  for (const url of urls) {
    for (let attempt=1;attempt<=4;attempt+=1) {
      try {
        const controller=new AbortController();
        const timer=setTimeout(()=>controller.abort(),30000);
        const response=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0',Accept:'application/json'},signal:controller.signal});
        clearTimeout(timer);
        if(!response.ok) throw new Error(`${symbol} Yahoo HTTP ${response.status}`);
        return await response.json();
      } catch(error) { last=error; if(attempt<4) await sleep(attempt*1000); }
    }
  }
  throw last;
}
function parseYahoo(json,symbol) {
  const result=json?.chart?.result?.[0];
  if(!result) throw new Error(`${symbol} missing Yahoo chart result`);
  const q=result.indicators?.quote?.[0]??{};
  const out=[];
  for(let i=0;i<(result.timestamp??[]).length;i+=1) {
    const ts=Number(result.timestamp[i])*1000;
    const p=parts(ts);
    if(!((p.hm>='09:00'&&p.hm<'11:30')||(p.hm>='12:30'&&p.hm<'15:30'))) continue;
    const vals=[q.open?.[i],q.high?.[i],q.low?.[i],q.close?.[i]];
    if(vals.some(v=>v==null||!Number.isFinite(Number(v)))) continue;
    out.push({timestamp:new Date(ts).toISOString(),open:Number(q.open[i]),high:Number(q.high[i]),low:Number(q.low[i]),close:Number(q.close[i]),volume:Number(q.volume?.[i]??0)});
  }
  return normalize(out);
}
async function fetchBars(symbol) {
  const end=Math.floor(Date.now()/1000),start=end-58*86400;
  const query=`period1=${start}&period2=${end}&interval=5m&includePrePost=false&events=div%2Csplits`;
  const urls=[1,2].map(host=>`https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${query}`);
  return parseYahoo(await fetchJson(urls,symbol),symbol);
}
function flatten(pair,variant) {
  const exit=pair[variant];
  return {
    symbol:pair.symbol,sessionDate:pair.sessionDate,setup:pair.setup,direction:pair.direction,
    signalTimestamp:pair.signalTimestamp,entryTimestamp:pair.entryTimestamp,entryPrice:pair.entryPrice,
    exitTimestamp:exit.outcomeAt,exitPrice:exit.exitPrice,exitReason:exit.exitReason,barsHeld:exit.barsHeld,
    grossReturnPct:exit.grossReturnPct,netReturnPct:exit.netReturnPct,mfePct:exit.mfePct,maePct:exit.maePct,
    profitGivebackPctPoints:exit.profitGivebackPctPoints,captureRatio:exit.captureRatio,
  };
}
function grouped(pairs,keyFn,variant) {
  const groups=new Map();
  for(const pair of pairs) {
    const key=keyFn(pair);
    if(!groups.has(key)) groups.set(key,[]);
    groups.get(key).push(flatten(pair,variant));
  }
  return Object.fromEntries([...groups].map(([key,rows])=>[key,summarizeEconomicTrades(rows)]));
}
function groupedDelta(pairs,keyFn) {
  const groups=new Map();
  for(const pair of pairs) {
    const key=keyFn(pair);
    if(!groups.has(key)) groups.set(key,[]);
    groups.get(key).push(pair);
  }
  return Object.fromEntries([...groups].map(([key,rows])=>[key,summarizePairedExitDelta(rows)]));
}

const pairs=[];
const counters={directionalSetups:0,q4Candidates:0,nextBarUnavailable:0,crossSessionNextBar:0,baselineOverlapSkipped:0,baselineRejected:0,managedRejected:0,pairedTrades:0};
const bySymbol={};
for(const symbol of symbols) {
  const bars=await fetchBars(symbol);
  let baselineActiveUntil=null;
  const local={q4Candidates:0,baselineOverlapSkipped:0,pairedTrades:0};
  for(let index=Math.max(24,minHistoryBars);index<bars.length-1;index+=Math.max(1,stepBars)) {
    const context=bars.slice(Math.max(0,index+1-maxContextBars),index+1);
    const perception=buildSessionAwareMultiTimeframePerception({bars5m:context});
    const setup=classifyHumanStyleSetup(perception);
    if(![1,-1].includes(Number(setup.directionSign))) continue;
    counters.directionalSetups+=1;
    const quality=scoreHumanStyleSetupQuality(perception,setup);
    if(!isFrozenQ4Candidate(quality.score)) continue;
    counters.q4Candidates+=1; local.q4Candidates+=1;

    const signalBar=bars[index],entryBar=bars[index+1];
    if(!entryBar){counters.nextBarUnavailable+=1;continue;}
    const sessionDate=parts(signalBar.timestamp).date;
    if(parts(entryBar.timestamp).date!==sessionDate){counters.crossSessionNextBar+=1;continue;}
    if(baselineActiveUntil&&entryBar.timestamp<=baselineActiveUntil){counters.baselineOverlapSkipped+=1;local.baselineOverlapSkipped+=1;continue;}
    const path=[];
    for(let j=index+1;j<bars.length;j+=1){if(parts(bars[j].timestamp).date!==sessionDate)break;path.push(bars[j]);}
    if(!path.length){counters.nextBarUnavailable+=1;continue;}

    const direction=setup.directionSign===1?'UP':'DOWN';
    const baseline=simulateFrozenRatchetExit({
      entryPrice:entryBar.open,
      signalDirection:setup.directionSign===1?'LONG':'SHORT',
      contextBars:context,
      futureBars:path,
      frozenEntry:true,
      sessionDate,
    });
    if(!baseline){counters.baselineRejected+=1;continue;}
    const managed=simulateSetupSpecificManagedExit({
      setup:setup.setup,
      perception,
      entryPrice:entryBar.open,
      direction,
      contextBars:context,
      futureBars:path,
      sessionDate,
    });
    if(!managed){counters.managedRejected+=1;continue;}
    baselineActiveUntil=baseline.outcomeAt;
    counters.pairedTrades+=1; local.pairedTrades+=1;
    pairs.push({
      symbol,sessionDate,signalTimestamp:signalBar.timestamp,entryTimestamp:entryBar.timestamp,entryPrice:entryBar.open,
      setup:setup.setup,direction,qualityScore:quality.score,
      baseline:{
        outcomeAt:baseline.outcomeAt,exitPrice:baseline.exitPrice,exitReason:baseline.exitReason,barsHeld:baseline.barsHeld,
        grossReturnPct:baseline.grossReturnPct,netReturnPct:baseline.netReturnPct,mfePct:baseline.mfePct,maePct:baseline.maePct,
        profitGivebackPctPoints:baseline.profitGivebackPctPoints,captureRatio:baseline.captureRatio,
      },
      managed:{
        outcomeAt:managed.outcomeAt,exitPrice:managed.exitPrice,exitReason:managed.exitReason,barsHeld:managed.barsHeld,
        grossReturnPct:managed.grossReturnPct,netReturnPct:managed.netReturnPct,mfePct:managed.mfePct,maePct:managed.maePct,
        profitGivebackPctPoints:managed.profitGivebackPctPoints,captureRatio:managed.captureRatio,
        managerVariant:managed.managerVariant,structuralInvalidationTriggeredBeforeBaseline:managed.structuralInvalidationTriggeredBeforeBaseline,
        structuralInvalidationReference:managed.structuralInvalidationReference??null,
      },
      entrySetFrozenByBaselineOccupancy:true,
      exactSameEntryForBothVariants:true,
      futureOutcomeUsedForSelection:false,
    });
  }
  bySymbol[symbol]={sourceBarCount:bars.length,...local};
  console.log(JSON.stringify({symbol,...bySymbol[symbol]}));
  await sleep(500);
}

const baselineRows=pairs.map(pair=>flatten(pair,'baseline'));
const managedRows=pairs.map(pair=>flatten(pair,'managed'));
const result={
  phase:'57.p23.10g-setup-specific-management-holdout',
  status:'SETUP_SPECIFIC_MANAGEMENT_PAIRED_HOLDOUT_COMPLETE',
  symbols,symbolCount:symbols.length,
  policy:P23_10G_SETUP_MANAGEMENT_POLICY,
  inheritedQ4Policy:P23_10F_ECONOMIC_POLICY,
  counters,
  baseline:summarizeEconomicTrades(baselineRows),
  managed:summarizeEconomicTrades(managedRows),
  pairedDelta:summarizePairedExitDelta(pairs),
  bySetup:{
    baseline:grouped(pairs,row=>row.setup,'baseline'),
    managed:grouped(pairs,row=>row.setup,'managed'),
    delta:groupedDelta(pairs,row=>row.setup),
  },
  byDirection:{
    baseline:grouped(pairs,row=>row.direction,'baseline'),
    managed:grouped(pairs,row=>row.direction,'managed'),
    delta:groupedDelta(pairs,row=>row.direction),
  },
  bySymbol,
  pairs,
  methodology:{
    fourthDisjointSymbolBasketFrozenBeforeOutcomeRetrieval:true,
    exactPairedEntrySet:true,
    entrySetFrozenByBaselineOccupancy:true,
    setupRulesFrozen:true,
    qualityRulesFrozen:true,
    q4ThresholdFrozen:true,
    setupManagementArchitecturePreRegistered:true,
    setupSpecificNumericParameterSearch:false,
    baselineExitFrozen:true,
    nextBarOpenEntry:true,
    sameSessionOnly:true,
    futureOutcomeUsedForSelection:false,
    confirmatoryCrossSymbolOos:true,
    untouchedTemporalOos:false,
  },
  edgeClaimAllowed:false,recommendationAllowed:false,transmitted:false,
  ...PHASE57_P23_10G_SAFETY,
};
for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed']){
  if(result[key]!==false) throw new Error(`${key} must remain false`);
}
if(!pairs.length) throw new Error('no paired P23.10G trades produced');
if(pairs.some(pair=>pair.entrySetFrozenByBaselineOccupancy!==true||pair.exactSameEntryForBothVariants!==true)) throw new Error('paired entry integrity failure');
fs.mkdirSync('artifacts',{recursive:true});
fs.writeFileSync('artifacts/phase57-p23-10g-setup-management-holdout.json',JSON.stringify(result,null,2));
console.log(JSON.stringify({status:result.status,symbolCount:result.symbolCount,counters:result.counters,baseline:result.baseline,managed:result.managed,pairedDelta:result.pairedDelta,bySetup:result.bySetup},null,2));
