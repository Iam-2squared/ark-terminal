import fs from 'node:fs';
import { enrichHistoricalIntradayBars } from './phase57-intraday-multifactor.js';
import { buildMultiHorizonMagnitudeRows } from './phase57-adaptive-horizon-magnitude.js';
import { buildIntradayHorizonDatasets, evaluateNestedAdaptiveHorizon } from './phase57-nested-adaptive-horizon.js';
import { replayNestedAdaptiveOosSignals } from './phase57-adaptive-oos-signal-replay.js';
import { evaluateNestedRealExitOos, SAFE_REAL_EXIT_POLICIES } from './phase57-real-exit-oos.js';

const scope=(process.env.PHASE57_SCOPE||'COMBINED').trim();
const universe=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const symbols=scope==='COMBINED'?universe:[scope];
const horizonsBars=[1,3,6,12,24];
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const sessionKey=(symbol,sessionDate)=>`${symbol}|${sessionDate}`;
const rowKey=row=>`${row?.symbol??''}|${row?.sessionDate??''}|${row?.featureCutoff??''}`;

function jst(ts){
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(ts));
  const o=Object.fromEntries(parts.map(x=>[x.type,x.value]));
  return {date:`${o.year}-${o.month}-${o.day}`,hm:`${o.hour}:${o.minute}`};
}

async function fetchJson(urls,symbol){
  let last;
  for(const url of urls){
    for(let attempt=1;attempt<=4;attempt++){
      try{
        const controller=new AbortController();
        const timer=setTimeout(()=>controller.abort(),30000);
        const response=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0','Accept':'application/json','Connection':'close'},signal:controller.signal});
        clearTimeout(timer);
        if(!response.ok) throw new Error(`${symbol} Yahoo HTTP ${response.status}`);
        return await response.json();
      }catch(error){
        last=error;
        if(attempt<4) await sleep(attempt*1000);
      }
    }
  }
  throw last;
}

function parse(json,symbol){
  const result=json?.chart?.result?.[0];
  if(!result) throw new Error(`${symbol} no chart result`);
  const quote=result.indicators?.quote?.[0]||{};
  const out=[];
  for(let i=0;i<(result.timestamp||[]).length;i++){
    const timestamp=Number(result.timestamp[i])*1000;
    const {date,hm}=jst(timestamp);
    if(hm<'09:00'||hm>'15:30') continue;
    const values=[quote.open?.[i],quote.high?.[i],quote.low?.[i],quote.close?.[i]];
    if(values.some(v=>v==null||!Number.isFinite(Number(v)))) continue;
    out.push({timestamp:new Date(timestamp).toISOString(),open:Number(quote.open[i]),high:Number(quote.high[i]),low:Number(quote.low[i]),close:Number(quote.close[i]),volume:Number(quote.volume?.[i]||0),sessionDate:date});
  }
  return out;
}

async function fetchBars(symbol){
  const end=Math.floor(Date.now()/1000),day=86400;
  const windows=[[end-58*day,end-29*day],[end-29*day,end]];
  const all=[];
  for(const [period1,period2] of windows){
    const qs=`period1=${period1}&period2=${period2}&interval=5m&includePrePost=false&events=div%2Csplits`;
    const urls=[1,2].map(host=>`https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${qs}`);
    all.push(...parse(await fetchJson(urls,symbol),symbol));
    await sleep(500);
  }
  return [...new Map(all.map(bar=>[bar.timestamp,bar])).values()].sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
}

function featureRowsForMagnitude(symbol,sessionDate,sessionBars,enriched,magnitudeBase){
  const indexByTimestamp=new Map(sessionBars.map((bar,index)=>[new Date(bar.timestamp).toISOString(),index]));
  const enrichedByTimestamp=new Map(enriched.map(bar=>[new Date(bar.timestamp).toISOString(),bar]));
  const open0=Number(sessionBars[0]?.open||0);
  return magnitudeBase.flatMap(row=>{
    const timestamp=new Date(row.featureCutoff).toISOString();
    const index=indexByTimestamp.get(timestamp);
    const current=index===undefined?null:sessionBars[index];
    const enrichedBar=enrichedByTimestamp.get(timestamp);
    if(!current||!enrichedBar) return [];
    const previous=index>0?sessionBars[index-1]:current;
    const priorVolumes=sessionBars.slice(Math.max(0,index-5),index).map(bar=>Number(bar.volume||0));
    const avgPriorVolume=priorVolumes.length?priorVolumes.reduce((a,b)=>a+b,0)/priorVolumes.length:0;
    const features={
      returnFromOpen:open0?(Number(current.close)/open0-1)*100:0,
      rangePosition:Number(current.high)>Number(current.low)?(Number(current.close)-Number(current.low))/(Number(current.high)-Number(current.low)):0.5,
      shortMomentum:Number(previous.close)?(Number(current.close)/Number(previous.close)-1)*100:0,
      relativeVolume:avgPriorVolume>0?Number(current.volume||0)/avgPriorVolume:1,
      ...(enrichedBar.multiFactor||{}),
    };
    return [{symbol,sessionDate,featureCutoff:row.featureCutoff,features}];
  });
}

const datasets=Object.fromEntries(horizonsBars.map(h=>[h,[]]));
const sessionStore=new Map();
let rawBars=0,sessionCount=0;
for(const symbol of symbols){
  const bars=await fetchBars(symbol);
  rawBars+=bars.length;
  const sessions=new Map();
  for(const bar of bars){
    if(!sessions.has(bar.sessionDate)) sessions.set(bar.sessionDate,[]);
    sessions.get(bar.sessionDate).push(bar);
  }
  for(const [sessionDate,sessionBars] of sessions){
    sessionBars.sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
    if(sessionBars.length<30) continue;
    sessionCount++;
    const enriched=enrichHistoricalIntradayBars(sessionBars);
    const magnitudeBase=buildMultiHorizonMagnitudeRows({symbol,sessionDate,bars:sessionBars,horizons:horizonsBars});
    const featureRows=featureRowsForMagnitude(symbol,sessionDate,sessionBars,enriched,magnitudeBase);
    const sessionDatasets=buildIntradayHorizonDatasets(magnitudeBase,{horizons:horizonsBars,featureRows});
    for(const horizonBars of horizonsBars) datasets[horizonBars].push(...(sessionDatasets[horizonBars]||[]));
    sessionStore.set(sessionKey(symbol,sessionDate),{
      bars:sessionBars,
      indexByTimestamp:new Map(sessionBars.map((bar,index)=>[new Date(bar.timestamp).toISOString(),index])),
    });
  }
}
for(const horizonBars of horizonsBars) datasets[horizonBars].sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));

const adaptiveOptions={
  outerTrainFraction:0.6,outerTestFraction:0.1,outerMinTrainRows:scope==='COMBINED'?500:200,
  innerTrainFraction:0.6,innerTestFraction:0.15,innerMinTrainRows:scope==='COMBINED'?200:100,
  thresholds:[0.55,0.60,0.65],minInnerSignals:scope==='COMBINED'?50:20,minimumInnerNetReturnPct:0,
  roundTripCostPct:0.05,
};
const adaptive=evaluateNestedAdaptiveHorizon(datasets,adaptiveOptions);
const replay=replayNestedAdaptiveOosSignals(datasets,{...adaptiveOptions,referenceResult:adaptive});
if(replay.reconciliation&&!replay.reconciliation.matches){
  throw new Error(`P21.3 signal replay mismatch: ${JSON.stringify(replay.reconciliation)}`);
}

const datasetLookup=new Map();
for(const horizonBars of horizonsBars){
  for(const row of datasets[horizonBars]) datasetLookup.set(`${horizonBars}|${rowKey(row)}`,row);
}
const exitRows=[];
let missingSourceRows=0,missingSessionPaths=0;
for(const signal of replay.signals){
  const source=datasetLookup.get(`${signal.horizonBars}|${rowKey(signal)}`);
  if(!source){missingSourceRows++;continue;}
  const store=sessionStore.get(sessionKey(signal.symbol,signal.sessionDate));
  const index=store?.indexByTimestamp.get(new Date(signal.featureCutoff).toISOString());
  if(!store||index===undefined){missingSessionPaths++;continue;}
  const futureBars=store.bars.slice(index+1,Math.min(store.bars.length,index+25));
  if(!futureBars.length){missingSessionPaths++;continue;}
  exitRows.push(Object.freeze({
    symbol:signal.symbol,sessionDate:signal.sessionDate,outcomeSessionDate:signal.sessionDate,
    featureCutoff:signal.featureCutoff,outcomeAt:futureBars.at(-1).timestamp,label:Number(source.label),
    pointInTimeValid:true,signalPointInTimeValid:signal.signalPointInTimeValid!==false,
    entryPrice:Number(source.entryPrice),signalDirection:Number(signal.direction),baseHorizonBars:Number(signal.horizonBars),
    atrPctAtEntry:Number(source?.features?.atrPct),futureBars:Object.freeze(futureBars.map(bar=>Object.freeze({...bar}))),
    baseSignalProbability:Number(signal.probability),baseSignalConfidence:Number(signal.confidence),baseOuterFold:Number(signal.baseOuterFold),
    baseSignalOutcomeAt:signal.outcomeAt,baseSignalFeatureFamily:signal.selectedFeatureFamily,baseSignalModelType:signal.selectedModelType,
  }));
}
exitRows.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));

const exitOptions={
  policies:SAFE_REAL_EXIT_POLICIES,
  outerTrainFraction:0.6,outerTestFraction:0.1,outerMinTrainRows:20,
  innerTrainFraction:0.6,innerTestFraction:0.2,innerMinTrainRows:8,
  minSignals:8,minimumNetReturnPct:0,roundTripCostPct:0.05,
};
const exit=evaluateNestedRealExitOos(exitRows,exitOptions);

const summary={
  phase:'57.p21.3-real',status:'REAL_5M_ADAPTIVE_SIGNAL_EXIT_OOS_MEASURED',scope,
  source:'Yahoo Finance historical 5m OHLCV',windowDays:58,symbols,horizonsBars,horizonsMinutes:horizonsBars.map(x=>x*5),
  rawBars,sessionCount,rowCountByHorizon:Object.fromEntries(horizonsBars.map(h=>[h,datasets[h].length])),
  adaptiveReference:{
    status:adaptive.status,signalCount:adaptive.signalCount,hitRate:adaptive.hitRate,netAverageReturnPct:adaptive.netAverageReturnPct,
    profitFactor:adaptive.profitFactor,outerFoldCount:adaptive.outerFoldCount,
  },
  signalReplay:{
    status:replay.status,signalCount:replay.signalCount,hitRate:replay.hitRate,netAverageReturnPct:replay.netAverageReturnPct,
    profitFactor:replay.profitFactor,reconciliation:replay.reconciliation,missingSourceRows,missingSessionPaths,exitResearchRows:exitRows.length,
  },
  exit:{
    status:exit.status,researchRowCount:exit.researchRowCount,outerFoldCount:exit.outerFoldCount,
    optimized:exit.optimized,baselineAll:exit.baselineAll,baselineMatched:exit.baselineMatched,
    deltaMatchedNetAverageReturnPct:exit.deltaMatchedNetAverageReturnPct,
    selectedPolicyCounts:exit.selectedPolicyCounts,policyUniverse:exit.policyUniverse,outerResults:exit.outerResults,
    trailingPolicyQuarantined:exit.trailingPolicyQuarantined,trailingQuarantineReason:exit.trailingQuarantineReason,
    selectionIntegrity:exit.selectionIntegrity,
  },
  limitations:[
    'Historical order-book/tick-flow not reconstructed',
    'Yahoo Finance 5m window limited to recent history',
    'Base entry is modeled at the signal bar close; no separate next-bar entry-delay model yet',
    'Round-trip cost fixed at 0.05%',
    'Exit optimization is trained only on earlier realized P21.1 outer-OOS signals and evaluated on later untouched exit-OOS folds',
    'Trailing stops are quarantined because 5m OHLC does not reveal intrabar high/low ordering',
    'Small signal counts remain exploratory and cannot justify paper/live promotion',
  ],
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,overnightHoldingAllowed:false,
};

fs.mkdirSync('artifacts',{recursive:true});
const output=`artifacts/phase57-real-exit-oos-${scope}.json`;
fs.writeFileSync(output,JSON.stringify(summary,null,2));
console.log('PHASE57_P21_3_REAL_EXIT_JSON_START');
console.log(JSON.stringify(summary,null,2));
console.log('PHASE57_P21_3_REAL_EXIT_JSON_END');
