import fs from 'node:fs';
import {CHART_QUALITY_HOLDOUT_UNIVERSE} from './phase57-chart-quality-holdout-universe.js';
import {buildSessionAwareMultiTimeframePerception} from './phase57-chart-perception-session-aware.js';
import {classifyHumanStyleSetup} from './phase57-chart-perception-measurement.js';
import {scoreHumanStyleSetupQuality} from './phase57-chart-setup-quality.js';
import {simulateFrozenRatchetExit,PHASE57_P23_8D_SAFETY} from './phase57-frozen-ratchet-exit.js';
import {summarizeEconomicTrades} from './phase57-chart-economic-validation.js';
import {buildExitState} from './phase57-probabilistic-exit-reasoner.js';
import {P23_19_POLICY,estimateRawExitDistribution,calibrateContinuationProbability,decideCalibratedEvExit,summarizeCalibration} from './phase57-calibrated-ev-exit.js';
import {P23_20_PROTECT_POLICY,estimateProtectionEvidence,deriveProtectionStop,stopFill} from './phase57-probabilistic-profit-protection.js';

const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const symbols=process.env.PHASE57_SYMBOLS?.split(',').map(x=>x.trim()).filter(Boolean)??CHART_QUALITY_HOLDOUT_UNIVERSE.slice(0,3);
const minHistoryBars=Number(process.env.PHASE57_MIN_HISTORY_BARS??1600),stepBars=Number(process.env.PHASE57_STEP_BARS??3),maxContextBars=Number(process.env.PHASE57_MAX_CONTEXT_BARS??2600);
const JST=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
function parts(ts){const p=Object.fromEntries(JST.formatToParts(new Date(ts)).map(x=>[x.type,x.value]));return{date:`${p.year}-${p.month}-${p.day}`,hm:`${p.hour}:${p.minute}`};}
function norm(rows=[]){return rows.map(r=>({timestamp:new Date(r.timestamp).toISOString(),open:+r.open,high:+r.high,low:+r.low,close:+r.close,volume:+(r.volume??0)})).filter(r=>[r.open,r.high,r.low,r.close].every(Number.isFinite)&&r.high>=r.low).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));}
async function fetchJson(urls,s){let last;for(const u of urls)for(let a=1;a<=4;a++)try{const c=new AbortController(),t=setTimeout(()=>c.abort(),30000),res=await fetch(u,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0',Accept:'application/json'},signal:c.signal});clearTimeout(t);if(!res.ok)throw new Error(`${s} Yahoo HTTP ${res.status}`);return await res.json();}catch(e){last=e;if(a<4)await sleep(a*1000);}throw last;}
function parseYahoo(j,s){const r=j?.chart?.result?.[0];if(!r)throw new Error(`${s} missing Yahoo result`);const q=r.indicators?.quote?.[0]??{},out=[];for(let i=0;i<(r.timestamp??[]).length;i++){const ts=+r.timestamp[i]*1000,p=parts(ts);if(!((p.hm>='09:00'&&p.hm<'11:30')||(p.hm>='12:30'&&p.hm<'15:30')))continue;const v=[q.open?.[i],q.high?.[i],q.low?.[i],q.close?.[i]];if(v.some(x=>x==null||!Number.isFinite(+x)))continue;out.push({timestamp:new Date(ts).toISOString(),open:+q.open[i],high:+q.high[i],low:+q.low[i],close:+q.close[i],volume:+(q.volume?.[i]??0)});}return norm(out);}
async function fetchBars(s){const end=Math.floor(Date.now()/1000),start=end-58*86400,q=`period1=${start}&period2=${end}&interval=5m&includePrePost=false`;return parseYahoo(await fetchJson([1,2].map(h=>`https://query${h}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(s)}?${q}`),s),s);}
function dirRet(a,b,sign){return (b/a-1)*100*sign;}
function trueRange(b,p){return Math.max(b.high-b.low,Math.abs(b.high-p),Math.abs(b.low-p));}
function entryAtr(context){if(!context.length)return null;const x=context.map((b,i)=>trueRange(b,i?context[i-1].close:b.open));const a=x.slice(-8);return a.reduce((s,v)=>s+v,0)/a.length;}

function reasonedExit({entryPrice,direction,setup,sessionDate,path,context,pool,calibrationRows}){
  const sign=direction==='UP'?1:-1,a=entryAtr(context)??entryPrice*0.005,hard=sign===1?entryPrice-1.5*a:entryPrice+1.5*a,obs=[],decisions=[],scored=[];
  let protectionStop=null,protectActivations=0;
  for(let i=0;i<path.length;i++){
    const b=path[i];
    const activeStop=protectionStop==null?hard:(sign===1?Math.max(hard,protectionStop):Math.min(hard,protectionStop));
    const fill=stopFill(b,activeStop,direction);
    if(fill!=null){obs.push(b);return finish(fill,protectionStop==null?'ENTRY_ATR_HARD_STOP':'PROBABILISTIC_PROTECT_STOP',b.timestamp);}
    obs.push(b);
    const state=buildExitState({entryPrice,direction,bars:obs}),query={setup,direction,sessionDate,timestamp:b.timestamp,state};
    const raw=estimateRawExitDistribution(query,pool);
    const cal=raw.ready?calibrateContinuationProbability(raw.rawPContinuation,query,calibrationRows):{ready:false,reason:'RAW_NOT_READY'};
    const ev=decideCalibratedEvExit({raw,calibration:cal});
    const j=i+P23_19_POLICY.horizonBars;
    if(raw.ready&&path[j]){
      const actualRet=dirRet(b.close,path[j].close,sign),actualContinuation=actualRet>0?1:0;
      calibrationRows.push({setup,direction,sessionDate,timestamp:b.timestamp,fullyRealizedAt:path[j].timestamp,rawPContinuation:raw.rawPContinuation,actualContinuation,actualReturnPct:actualRet});
      if(cal.ready)scored.push({pContinuation:cal.pContinuation,actualContinuation,expectedReturnPct:ev.expectedReturnPct,actualReturnPct:actualRet});
    }
    if(ev.ready&&ev.decision==='EXIT'){decisions.push({timestamp:b.timestamp,state:'EXIT',raw,calibration:cal,...ev});return finish(b.close,'CALIBRATED_EV_EXIT',b.timestamp);}
    const pe=estimateProtectionEvidence(query,pool),gross=dirRet(entryPrice,b.close,sign);
    const protect=deriveProtectionStop({entryPrice,currentPrice:b.close,direction,currentGrossReturnPct:gross,priorStop:protectionStop,evidence:pe});
    if(protect.state==='PROTECT'){if(protectionStop==null||protect.stop!==protectionStop)protectActivations++;protectionStop=protect.stop;}
    decisions.push({timestamp:b.timestamp,state:protect.state,raw,calibration:cal,ev,protection:protect});
  }
  return finish(path.at(-1).close,'SESSION_END',path.at(-1).timestamp);
  function finish(px,reason,ts){const gross=dirRet(entryPrice,px,sign),mfe=Math.max(0,...obs.map(b=>dirRet(entryPrice,sign===1?b.high:b.low,sign))),mae=Math.min(0,...obs.map(b=>dirRet(entryPrice,sign===1?b.low:b.high,sign)));return{exitPrice:px,exitReason:reason,exitTimestamp:ts,barsHeld:obs.length,grossReturnPct:gross,netReturnPct:gross-0.05,mfePct:mfe,maePct:mae,profitGivebackPctPoints:Math.max(0,mfe-gross),captureRatio:mfe>0?gross/mfe:null,decisions,calibrationRows:scored,protectActivations,finalProtectionStop:protectionStop};}
}

const barsBySymbol={};for(const s of symbols){barsBySymbol[s]=await fetchBars(s);await sleep(250);}const candidates=[];
for(const s of symbols){const bars=barsBySymbol[s];for(let i=Math.max(24,minHistoryBars);i<bars.length-4;i+=Math.max(1,stepBars)){const context=bars.slice(Math.max(0,i+1-maxContextBars),i+1),per=buildSessionAwareMultiTimeframePerception({bars5m:context}),setup=classifyHumanStyleSetup(per);if(![1,-1].includes(+setup.directionSign))continue;const q=scoreHumanStyleSetupQuality(per,setup);if(+q.score<0.70)continue;const signal=bars[i],entry=bars[i+1],sessionDate=parts(signal.timestamp).date;if(!entry||parts(entry.timestamp).date!==sessionDate)continue;const path=[];for(let j=i+1;j<bars.length;j++){if(parts(bars[j].timestamp).date!==sessionDate)break;path.push(bars[j]);}if(path.length<4)continue;candidates.push({symbol:s,setup:setup.setup,direction:setup.directionSign===1?'UP':'DOWN',sessionDate,signalTimestamp:signal.timestamp,entryTimestamp:entry.timestamp,entryPrice:entry.open,context,path});}}
const pool=[];for(const c of candidates){const sign=c.direction==='UP'?1:-1;for(let i=0;i<c.path.length-P23_19_POLICY.horizonBars;i++){const b=c.path[i],f=c.path[i+P23_19_POLICY.horizonBars],state=buildExitState({entryPrice:c.entryPrice,direction:c.direction,bars:c.path.slice(0,i+1)});pool.push({setup:c.setup,direction:c.direction,sessionDate:c.sessionDate,timestamp:b.timestamp,fullyRealizedAt:f.timestamp,state,nextDirectionalReturnPct:dirRet(b.close,f.close,sign)});}}
const pairs=[],onlineCalibrationRows=[];for(const s of symbols){let activeUntil=null;for(const c of candidates.filter(x=>x.symbol===s).sort((a,b)=>a.entryTimestamp.localeCompare(b.entryTimestamp))){if(activeUntil&&c.entryTimestamp<=activeUntil)continue;const base=simulateFrozenRatchetExit({entryPrice:c.entryPrice,signalDirection:c.direction==='UP'?'LONG':'SHORT',contextBars:c.context,futureBars:c.path,frozenEntry:true,sessionDate:c.sessionDate});if(!base)continue;activeUntil=base.outcomeAt;const treatment=reasonedExit({...c,pool,calibrationRows:onlineCalibrationRows});const meta={symbol:s,setup:c.setup,direction:c.direction,sessionDate:c.sessionDate,entryTimestamp:c.entryTimestamp,entryPrice:c.entryPrice};const baseline={...meta,exitTimestamp:base.outcomeAt,exitPrice:base.exitPrice,exitReason:base.exitReason,barsHeld:base.barsHeld,grossReturnPct:base.grossReturnPct,netReturnPct:base.netReturnPct,mfePct:base.mfePct,maePct:base.maePct,profitGivebackPctPoints:base.profitGivebackPctPoints,captureRatio:base.captureRatio};pairs.push({baseline,reasoned:{...meta,...treatment}});}}
if(!pairs.length)throw new Error('no paired P23.20 trades');
const baselineRows=pairs.map(x=>x.baseline),reasonedRows=pairs.map(x=>x.reasoned),b=summarizeEconomicTrades(baselineRows),r=summarizeEconomicTrades(reasonedRows),calRows=reasonedRows.flatMap(x=>x.calibrationRows??[]);
const exitReasons=Object.fromEntries([...new Set(reasonedRows.map(x=>x.exitReason))].map(k=>[k,reasonedRows.filter(x=>x.exitReason===k).length]));
const states={HOLD:0,PROTECT:0,EXIT:0};for(const row of reasonedRows)for(const d of row.decisions??[])if(states[d.state]!=null)states[d.state]++;
const result={phase:'57.p23.20-probabilistic-profit-protection',status:'PROBABILISTIC_PROFIT_PROTECTION_REMEASUREMENT_COMPLETE',symbols,symbolCount:symbols.length,policy:{ev:P23_19_POLICY,protection:P23_20_PROTECT_POLICY},baseline:b,reasoned:r,delta:{net:r.averageNetReturnPct-b.averageNetReturnPct,pf:r.profitFactor-b.profitFactor,giveback:r.averageGivebackPctPoints-b.averageGivebackPctPoints,barsHeld:r.averageBarsHeld-b.averageBarsHeld,maxDD:r.maxSequentialDrawdownPctPoints-b.maxSequentialDrawdownPctPoints},calibration:summarizeCalibration(calRows),exitReasons,decisionStates:states,protectActivationCount:reasonedRows.reduce((s,x)=>s+Number(x.protectActivations||0),0),pairs,methodology:{strongEntryFrozenQ4:true,exactSameEntriesPaired:true,baselineOccupancyFreezesEntrySet:true,priorFullyRealizedAnalogOnly:true,priorSessionCalibrationOnly:true,empiricalDownsideQuantileProtection:true,monotonicProtection:true,entryAtrHardStopUsesCompletedContext:true,noThresholdSweep:true,noEntryRetuning:true,noSymbolFiltering:true,sameSessionOnly:true,developmentRemeasurement:true,freshHoldoutConsumed:false},edgeClaimAllowed:false,recommendationAllowed:false,transmitted:false,...PHASE57_P23_8D_SAFETY};
for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed'])if(result[k]!==false)throw new Error(`${k} must remain false`);
fs.mkdirSync('artifacts',{recursive:true});fs.writeFileSync('artifacts/phase57-p23-20-probabilistic-profit-protection.json',JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,baseline:result.baseline,reasoned:result.reasoned,delta:result.delta,calibration:result.calibration,exitReasons:result.exitReasons,decisionStates:result.decisionStates,protectActivationCount:result.protectActivationCount},null,2));
