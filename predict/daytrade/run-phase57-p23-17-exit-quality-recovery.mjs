import fs from 'node:fs';
import { CHART_QUALITY_HOLDOUT_UNIVERSE } from './phase57-chart-quality-holdout-universe.js';
import { buildSessionAwareMultiTimeframePerception } from './phase57-chart-perception-session-aware.js';
import { classifyHumanStyleSetup } from './phase57-chart-perception-measurement.js';
import { scoreHumanStyleSetupQuality } from './phase57-chart-setup-quality.js';
import { simulateFrozenRatchetExit, P23_8D_FROZEN_RATCHET_CONFIG, PHASE57_P23_8D_SAFETY } from './phase57-frozen-ratchet-exit.js';
import { summarizeEconomicTrades } from './phase57-chart-economic-validation.js';

export const P23_17_PATIENT_EXIT_CONFIG = Object.freeze({
  ...P23_8D_FROZEN_RATCHET_CONFIG,
  configId: 'STATE_PATIENT_RATCHET_V2',
  ratchetActivationAtr: 2.0,
  ratchetGivebackAtrStrong: 1.75,
  ratchetGivebackAtrHold: 1.5,
  ratchetGivebackAtrCaution: 1.1,
  cautionConfirmBars: 3,
  minBarsBeforeStateExit: 3,
});

const SAFETY = Object.freeze({
  ...PHASE57_P23_8D_SAFETY,
  mode:'PHASE57_P23_17_EXIT_QUALITY_RECOVERY_READ_ONLY_RESEARCH',
  executionAllowed:false, brokerWriteAllowed:false, excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false, liveTradingAllowed:false, paperTradingAllowed:false,
  automaticPromotionAllowed:false, productionUpdateAllowed:false, overnightHoldingAllowed:false,
  transmitted:false,
});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const symbols=(process.env.PHASE57_SYMBOLS?.split(',').map(x=>x.trim()).filter(Boolean) ?? CHART_QUALITY_HOLDOUT_UNIVERSE.slice(0,3));
const minHistoryBars=Number(process.env.PHASE57_MIN_HISTORY_BARS ?? 1600);
const stepBars=Number(process.env.PHASE57_STEP_BARS ?? 3);
const maxContextBars=Number(process.env.PHASE57_MAX_CONTEXT_BARS ?? 2600);
const JST=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
function parts(ts){const p=Object.fromEntries(JST.formatToParts(new Date(ts)).map(x=>[x.type,x.value]));return{date:`${p.year}-${p.month}-${p.day}`,hm:`${p.hour}:${p.minute}`};}
function normalize(rows=[]){return rows.map(r=>({timestamp:new Date(r.timestamp).toISOString(),open:Number(r.open),high:Number(r.high),low:Number(r.low),close:Number(r.close),volume:Number(r.volume??0)})).filter(r=>[r.open,r.high,r.low,r.close].every(Number.isFinite)&&r.high>=r.low).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));}
async function fetchJson(urls,symbol){let last;for(const url of urls){for(let a=1;a<=4;a++){try{const c=new AbortController();const t=setTimeout(()=>c.abort(),30000);const res=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0',Accept:'application/json'},signal:c.signal});clearTimeout(t);if(!res.ok)throw new Error(`${symbol} Yahoo HTTP ${res.status}`);return await res.json();}catch(e){last=e;if(a<4)await sleep(a*1000);}}}throw last;}
function parseYahoo(json,symbol){const r=json?.chart?.result?.[0];if(!r)throw new Error(`${symbol} missing Yahoo result`);const q=r.indicators?.quote?.[0]??{};const out=[];for(let i=0;i<(r.timestamp??[]).length;i++){const ts=Number(r.timestamp[i])*1000;const p=parts(ts);if(!((p.hm>='09:00'&&p.hm<'11:30')||(p.hm>='12:30'&&p.hm<'15:30')))continue;const v=[q.open?.[i],q.high?.[i],q.low?.[i],q.close?.[i]];if(v.some(x=>x==null||!Number.isFinite(Number(x))))continue;out.push({timestamp:new Date(ts).toISOString(),open:Number(q.open[i]),high:Number(q.high[i]),low:Number(q.low[i]),close:Number(q.close[i]),volume:Number(q.volume?.[i]??0)});}return normalize(out);}
async function fetchBars(symbol){const end=Math.floor(Date.now()/1000),start=end-58*86400;const query=`period1=${start}&period2=${end}&interval=5m&includePrePost=false&events=div%2Csplits`;return parseYahoo(await fetchJson([1,2].map(h=>`https://query${h}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${query}`),symbol),symbol);}
function group(rows,keyFn,field){const m=new Map();for(const row of rows){const k=keyFn(row);if(!m.has(k))m.set(k,[]);m.get(k).push(row[field]);}return Object.fromEntries([...m].map(([k,v])=>[k,summarizeEconomicTrades(v)]));}
function decorate(base,meta){return {...meta,exitTimestamp:base.outcomeAt,exitPrice:base.exitPrice,exitReason:base.exitReason,barsHeld:base.barsHeld,grossReturnPct:base.grossReturnPct,netReturnPct:base.netReturnPct,mfePct:base.mfePct,maePct:base.maePct,profitGivebackPctPoints:base.profitGivebackPctPoints,captureRatio:base.captureRatio,ratchetActivated:base.ratchetActivated};}

const pairs=[];const counters={directionalSetups:0,q4Candidates:0,overlapSkipped:0,acceptedPairs:0};
for(const symbol of symbols){const bars=await fetchBars(symbol);let activeUntil=null;for(let index=Math.max(24,minHistoryBars);index<bars.length-1;index+=Math.max(1,stepBars)){
  const context=bars.slice(Math.max(0,index+1-maxContextBars),index+1);const perception=buildSessionAwareMultiTimeframePerception({bars5m:context});const setup=classifyHumanStyleSetup(perception);if(![1,-1].includes(Number(setup.directionSign)))continue;counters.directionalSetups++;
  const quality=scoreHumanStyleSetupQuality(perception,setup);if(Number(quality.score)<0.70)continue;counters.q4Candidates++;
  const signalBar=bars[index],entryBar=bars[index+1];if(!entryBar)continue;const sessionDate=parts(signalBar.timestamp).date;if(parts(entryBar.timestamp).date!==sessionDate)continue;if(activeUntil&&entryBar.timestamp<=activeUntil){counters.overlapSkipped++;continue;}
  const path=[];for(let j=index+1;j<bars.length;j++){if(parts(bars[j].timestamp).date!==sessionDate)break;path.push(bars[j]);}if(!path.length)continue;
  const common={entryPrice:entryBar.open,signalDirection:setup.directionSign===1?'LONG':'SHORT',contextBars:context,futureBars:path,frozenEntry:true,sessionDate};
  const baseline=simulateFrozenRatchetExit(common);if(!baseline)continue;activeUntil=baseline.outcomeAt;
  const patient=simulateFrozenRatchetExit(common,{config:P23_17_PATIENT_EXIT_CONFIG});if(!patient)continue;
  const meta={symbol,sessionDate,signalTimestamp:signalBar.timestamp,entryTimestamp:entryBar.timestamp,entryPrice:entryBar.open,setup:setup.setup,direction:setup.directionSign===1?'UP':'DOWN',qualityScore:quality.score};
  pairs.push({key:`${symbol}|${entryBar.timestamp}|${setup.setup}`,baseline:decorate(baseline,meta),patient:decorate(patient,meta)});counters.acceptedPairs++;
}await sleep(400);}
if(!pairs.length)throw new Error('no P23.17 paired trades');
const baselineRows=pairs.map(x=>x.baseline),patientRows=pairs.map(x=>x.patient);
const delta={averageNetReturnPct:summarizeEconomicTrades(patientRows).averageNetReturnPct-summarizeEconomicTrades(baselineRows).averageNetReturnPct,profitFactor:summarizeEconomicTrades(patientRows).profitFactor-summarizeEconomicTrades(baselineRows).profitFactor,averageGivebackPctPoints:summarizeEconomicTrades(patientRows).averageGivebackPctPoints-summarizeEconomicTrades(baselineRows).averageGivebackPctPoints,averageCaptureRatio:summarizeEconomicTrades(patientRows).averageCaptureRatio-summarizeEconomicTrades(baselineRows).averageCaptureRatio,averageBarsHeld:summarizeEconomicTrades(patientRows).averageBarsHeld-summarizeEconomicTrades(baselineRows).averageBarsHeld};
const result={phase:'57.p23.17-exit-quality-recovery',status:'STRONG_ENTRY_PAIRED_EXIT_REMEASUREMENT_COMPLETE',symbols,symbolCount:symbols.length,counters,baselineConfigId:P23_8D_FROZEN_RATCHET_CONFIG.configId,patientConfig:P23_17_PATIENT_EXIT_CONFIG,baseline:summarizeEconomicTrades(baselineRows),patient:summarizeEconomicTrades(patientRows),delta,bySetup:{baseline:group(pairs,x=>x.baseline.setup,'baseline'),patient:group(pairs,x=>x.patient.setup,'patient')},byDirection:{baseline:group(pairs,x=>x.baseline.direction,'baseline'),patient:group(pairs,x=>x.patient.direction,'patient')},pairs,methodology:{strongEntryFrozenQ4:true,q4Threshold:0.70,exactSameEntriesPaired:true,baselineOccupancyFreezesEntrySet:true,patientExitSinglePreRegisteredHypothesis:true,noExitThresholdSweep:true,noEntryRetuning:true,noSymbolFiltering:true,sameSessionOnly:true,developmentRemeasurement:true,freshHoldoutConsumed:false,transactionCostPct:0.05},edgeClaimAllowed:false,recommendationAllowed:false,...SAFETY};
for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted'])if(result[k]!==false)throw new Error(`${k} must remain false`);
fs.mkdirSync('artifacts',{recursive:true});fs.writeFileSync('artifacts/phase57-p23-17-exit-quality-recovery.json',JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,symbolCount:result.symbolCount,counters,baseline:result.baseline,patient:result.patient,delta,byDirection:result.byDirection},null,2));