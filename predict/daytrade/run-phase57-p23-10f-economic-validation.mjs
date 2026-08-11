import fs from 'node:fs';
import { CHART_ECONOMIC_HOLDOUT_UNIVERSE } from './phase57-chart-economic-holdout-universe.js';
import { buildSessionAwareMultiTimeframePerception } from './phase57-chart-perception-session-aware.js';
import { classifyHumanStyleSetup } from './phase57-chart-perception-measurement.js';
import { scoreHumanStyleSetupQuality } from './phase57-chart-setup-quality.js';
import { simulateFrozenRatchetExit, P23_8D_FROZEN_RATCHET_CONFIG } from './phase57-frozen-ratchet-exit.js';
import {
  P23_10F_ECONOMIC_POLICY,
  PHASE57_P23_10F_SAFETY,
  frozenQualityBand,
  isFrozenQ4Candidate,
  summarizeEconomicTrades,
} from './phase57-chart-economic-validation.js';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const symbols = process.env.PHASE57_SYMBOLS
  ? process.env.PHASE57_SYMBOLS.split(',').map(v => v.trim()).filter(Boolean)
  : CHART_ECONOMIC_HOLDOUT_UNIVERSE.slice(0, 3);
const minHistoryBars = Number(process.env.PHASE57_MIN_HISTORY_BARS ?? 1600);
const stepBars = Number(process.env.PHASE57_STEP_BARS ?? 3);
const maxContextBars = Number(process.env.PHASE57_MAX_CONTEXT_BARS ?? 2600);
const JST = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Tokyo', year:'numeric', month:'2-digit', day:'2-digit',
  hour:'2-digit', minute:'2-digit', hourCycle:'h23',
});

function parts(ts) {
  const p = Object.fromEntries(JST.formatToParts(new Date(ts)).map(x => [x.type, x.value]));
  return { date:`${p.year}-${p.month}-${p.day}`, hm:`${p.hour}:${p.minute}` };
}
function normalize(rows=[]) {
  return rows.map(r => ({ timestamp:new Date(r.timestamp).toISOString(), open:Number(r.open), high:Number(r.high), low:Number(r.low), close:Number(r.close), volume:Number(r.volume??0) }))
    .filter(r => [r.open,r.high,r.low,r.close].every(Number.isFinite) && r.high>=r.low)
    .sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
}
async function fetchJson(urls, symbol) {
  let last;
  for (const url of urls) {
    for (let attempt=1; attempt<=4; attempt+=1) {
      try {
        const controller = new AbortController();
        const timer = setTimeout(()=>controller.abort(), 30000);
        const response = await fetch(url, { headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0',Accept:'application/json'}, signal:controller.signal });
        clearTimeout(timer);
        if (!response.ok) throw new Error(`${symbol} Yahoo HTTP ${response.status}`);
        return await response.json();
      } catch (error) {
        last=error;
        if (attempt<4) await sleep(attempt*1000);
      }
    }
  }
  throw last;
}
function parseYahoo(json, symbol) {
  const result=json?.chart?.result?.[0];
  if (!result) throw new Error(`${symbol} missing Yahoo chart result`);
  const q=result.indicators?.quote?.[0]??{};
  const out=[];
  for (let i=0;i<(result.timestamp??[]).length;i+=1) {
    const ts=Number(result.timestamp[i])*1000;
    const p=parts(ts);
    if (!((p.hm>='09:00'&&p.hm<'11:30')||(p.hm>='12:30'&&p.hm<'15:30'))) continue;
    const vals=[q.open?.[i],q.high?.[i],q.low?.[i],q.close?.[i]];
    if (vals.some(v=>v==null||!Number.isFinite(Number(v)))) continue;
    out.push({timestamp:new Date(ts).toISOString(),open:Number(q.open[i]),high:Number(q.high[i]),low:Number(q.low[i]),close:Number(q.close[i]),volume:Number(q.volume?.[i]??0)});
  }
  return normalize(out);
}
async function fetchBars(symbol) {
  const end=Math.floor(Date.now()/1000), start=end-58*86400;
  const query=`period1=${start}&period2=${end}&interval=5m&includePrePost=false&events=div%2Csplits`;
  const urls=[1,2].map(host=>`https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${query}`);
  return parseYahoo(await fetchJson(urls,symbol),symbol);
}
function groupSummary(rows,keyFn) {
  const groups=new Map();
  for (const row of rows) {
    const key=keyFn(row);
    if (!groups.has(key)) groups.set(key,[]);
    groups.get(key).push(row);
  }
  return Object.fromEntries([...groups].map(([key,values])=>[key,summarizeEconomicTrades(values)]));
}

const records=[];
const bySymbol={};
const counters={directionalSetups:0,q4Candidates:0,nextBarUnavailable:0,crossSessionNextBar:0,overlapSkipped:0,simulatorRejected:0,acceptedTrades:0};
for (const symbol of symbols) {
  const bars=await fetchBars(symbol);
  let activeUntil=null;
  const local={q4Candidates:0,overlapSkipped:0,acceptedTrades:0};
  for (let index=Math.max(24,minHistoryBars); index<bars.length-1; index+=Math.max(1,stepBars)) {
    const context=bars.slice(Math.max(0,index+1-maxContextBars),index+1);
    const perception=buildSessionAwareMultiTimeframePerception({bars5m:context});
    const setup=classifyHumanStyleSetup(perception);
    if (![1,-1].includes(Number(setup.directionSign))) continue;
    counters.directionalSetups+=1;
    const quality=scoreHumanStyleSetupQuality(perception,setup);
    if (!isFrozenQ4Candidate(quality.score)) continue;
    counters.q4Candidates+=1;
    local.q4Candidates+=1;

    const signalBar=bars[index];
    const entryBar=bars[index+1];
    if (!entryBar) { counters.nextBarUnavailable+=1; continue; }
    const sessionDate=parts(signalBar.timestamp).date;
    if (parts(entryBar.timestamp).date!==sessionDate) { counters.crossSessionNextBar+=1; continue; }
    if (activeUntil && entryBar.timestamp<=activeUntil) {
      counters.overlapSkipped+=1;
      local.overlapSkipped+=1;
      continue;
    }
    const path=[];
    for (let j=index+1;j<bars.length;j+=1) {
      if (parts(bars[j].timestamp).date!==sessionDate) break;
      path.push(bars[j]);
    }
    if (!path.length) { counters.nextBarUnavailable+=1; continue; }

    const exit=simulateFrozenRatchetExit({
      entryPrice:entryBar.open,
      signalDirection:setup.directionSign===1?'LONG':'SHORT',
      contextBars:context,
      futureBars:path,
      frozenEntry:true,
      sessionDate,
    });
    if (!exit) { counters.simulatorRejected+=1; continue; }
    if (exit.safety?.liveTradingAllowed!==false || exit.transmitted!==false) throw new Error('ratchet safety violation');
    activeUntil=exit.outcomeAt;
    counters.acceptedTrades+=1;
    local.acceptedTrades+=1;
    records.push({
      symbol,
      sessionDate,
      signalTimestamp:signalBar.timestamp,
      entryTimestamp:entryBar.timestamp,
      entryPrice:entryBar.open,
      setup:setup.setup,
      direction:setup.directionSign===1?'UP':'DOWN',
      qualityScore:quality.score,
      qualityBand:frozenQualityBand(quality.score),
      qualityComponents:quality.components,
      exitTimestamp:exit.outcomeAt,
      exitPrice:exit.exitPrice,
      exitReason:exit.exitReason,
      barsHeld:exit.barsHeld,
      grossReturnPct:exit.grossReturnPct,
      netReturnPct:exit.netReturnPct,
      mfePct:exit.mfePct,
      maePct:exit.maePct,
      profitGivebackPctPoints:exit.profitGivebackPctPoints,
      captureRatio:exit.captureRatio,
      ratchetActivated:exit.ratchetActivated,
      ratchetNeverLoosened:exit.ratchetNeverLoosened,
      entryAfterCompletedSignal:true,
      nextBarOpenEntry:true,
      overlappingSameSymbolTrade:false,
      futureOutcomeUsedForSetupOrQuality:false,
    });
  }
  bySymbol[symbol]={sourceBarCount:bars.length,...local};
  console.log(JSON.stringify({symbol,...bySymbol[symbol]}));
  await sleep(500);
}

const aggregate=summarizeEconomicTrades(records);
const result={
  phase:'57.p23.10f-frozen-economic-validation',
  status:'FROZEN_CHART_ECONOMIC_VALIDATION_COMPLETE',
  symbols,
  symbolCount:symbols.length,
  policy:P23_10F_ECONOMIC_POLICY,
  exitConfigId:P23_8D_FROZEN_RATCHET_CONFIG.configId,
  counters,
  aggregate,
  bySetup:groupSummary(records,row=>row.setup),
  byDirection:groupSummary(records,row=>row.direction),
  bySymbol,
  records,
  methodology:{
    newSymbolsFrozenBeforeOutcomeRetrieval:true,
    disjointFromPrior60ChartSymbols:true,
    setupRulesFrozen:true,
    qualityScoreFrozen:true,
    q4ThresholdFrozen:true,
    nextBarOpenEntry:true,
    oneActiveTradePerSymbol:true,
    p23_8dExitFrozen:true,
    aggregateRoundTripFrictionPct:P23_10F_ECONOMIC_POLICY.roundTripFrictionPct,
    sameSessionOnly:true,
    futureOutcomeUsedForSelection:false,
    confirmatoryCrossSymbolOos:true,
    untouchedTemporalOos:false,
  },
  edgeClaimAllowed:false,
  recommendationAllowed:false,
  transmitted:false,
  ...PHASE57_P23_10F_SAFETY,
};
for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed']) {
  if (result[key]!==false) throw new Error(`${key} must remain false`);
}
if (!records.length) throw new Error('no accepted P23.10F economic trades produced');
fs.mkdirSync('artifacts',{recursive:true});
fs.writeFileSync('artifacts/phase57-p23-10f-economic-validation.json',JSON.stringify(result,null,2));
console.log(JSON.stringify({status:result.status,symbolCount:result.symbolCount,counters:result.counters,aggregate:result.aggregate,bySetup:result.bySetup},null,2));
