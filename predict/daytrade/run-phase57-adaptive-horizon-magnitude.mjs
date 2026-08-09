import fs from 'node:fs';
import { buildHistoricalIntradayRows } from './phase57-historical-intraday-baseline.js';
import { enrichHistoricalIntradayBars, attachMultiFactorFeatures } from './phase57-intraday-multifactor.js';
import { buildMultiHorizonMagnitudeRows } from './phase57-adaptive-horizon-magnitude.js';
import { buildIntradayHorizonDatasets, evaluateNestedAdaptiveHorizon } from './phase57-nested-adaptive-horizon.js';
import { evaluateNestedMagnitudePrediction } from './phase57-magnitude-prediction.js';

const scope=(process.env.PHASE57_SCOPE||'COMBINED').trim();
const universe=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const symbols=scope==='COMBINED'?universe:[scope];
const horizonsBars=[1,3,6,12,24];
const horizonsMinutes=horizonsBars.map(x=>x*5);
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));

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
    out.push({
      timestamp:new Date(timestamp).toISOString(),open:Number(quote.open[i]),high:Number(quote.high[i]),
      low:Number(quote.low[i]),close:Number(quote.close[i]),volume:Number(quote.volume?.[i]||0),sessionDate:date,
    });
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

function weightedBySignals(rows,field){
  const eligible=rows.filter(row=>Number(row?.signalCount)>0&&Number.isFinite(Number(row?.[field])));
  const count=eligible.reduce((s,row)=>s+Number(row.signalCount),0);
  return count?eligible.reduce((s,row)=>s+Number(row[field])*Number(row.signalCount),0)/count:null;
}

function horizonDiagnostics(outerResults){
  const out={};
  for(const horizonBars of horizonsBars){
    const folds=outerResults.filter(row=>row?.status==='OUTER_EVALUATED'&&Number(row.selectedHorizonBars)===horizonBars);
    out[horizonBars]={
      horizonMinutes:horizonBars*5,
      selectedFoldCount:folds.length,
      signalCount:folds.reduce((s,row)=>s+Number(row.signalCount||0),0),
      hitRate:weightedBySignals(folds,'hitRate'),
      netAverageReturnPct:weightedBySignals(folds,'netAverageReturnPct'),
    };
  }
  return out;
}

const datasets=Object.fromEntries(horizonsBars.map(h=>[h,[]]));
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
    const baseFeatureRows=attachMultiFactorFeatures(
      buildHistoricalIntradayRows({symbol,sessionDate,bars:sessionBars,horizonBars:1,barrierBps:20}),
      enriched,
    );
    const magnitudeBase=buildMultiHorizonMagnitudeRows({symbol,sessionDate,bars:sessionBars,horizons:horizonsBars});
    const sessionDatasets=buildIntradayHorizonDatasets(magnitudeBase,{horizons:horizonsBars,featureRows:baseFeatureRows});
    for(const horizonBars of horizonsBars) datasets[horizonBars].push(...(sessionDatasets[horizonBars]||[]));
  }
}
for(const horizonBars of horizonsBars) datasets[horizonBars].sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));

const commonOptions={
  outerTrainFraction:0.6,outerTestFraction:0.1,outerMinTrainRows:scope==='COMBINED'?500:200,
  innerTrainFraction:0.6,innerTestFraction:0.15,innerMinTrainRows:scope==='COMBINED'?200:100,
  thresholds:[0.55,0.60,0.65],minInnerSignals:scope==='COMBINED'?50:20,minimumInnerNetReturnPct:0,
  roundTripCostPct:0.05,
};
const adaptive=evaluateNestedAdaptiveHorizon(datasets,commonOptions);
const magnitude=evaluateNestedMagnitudePrediction(datasets,{adaptiveResult:adaptive,k:25,moveThresholdsPct:[0.5,1,2,3]});
const diagnostics=horizonDiagnostics(adaptive.outerResults||[]);

const summary={
  phase:'57.p21.2-real',status:'ADAPTIVE_HORIZON_MAGNITUDE_5M_OOS_MEASURED',scope,
  source:'Yahoo Finance historical 5m OHLCV',windowDays:58,symbols,horizonsBars,horizonsMinutes,
  rawBars,sessionCount,rowCountByHorizon:Object.fromEntries(horizonsBars.map(h=>[h,datasets[h].length])),
  adaptive:{
    status:adaptive.status,commonRowCount:adaptive.commonRowCount,outerFoldCount:adaptive.outerFoldCount,
    signalCount:adaptive.signalCount,hitRate:adaptive.hitRate,netAverageReturnPct:adaptive.netAverageReturnPct,
    profitFactor:adaptive.profitFactor,horizonDiagnostics:diagnostics,outerResults:adaptive.outerResults,
    selectionIntegrity:adaptive.selectionIntegrity,
  },
  magnitude:{
    status:magnitude.status,sampleCount:magnitude.sampleCount,
    expectedReturnMaePct:magnitude.expectedReturnMaePct,expectedAbsMoveMaePct:magnitude.expectedAbsMoveMaePct,
    expectedMfeMaePct:magnitude.expectedMfeMaePct,expectedMaeMaePct:magnitude.expectedMaeMaePct,
    probabilityBrierByThreshold:magnitude.probabilityBrierByThreshold,
    actualMoveRateByThreshold:magnitude.actualMoveRateByThreshold,
    predictedMoveRateByThreshold:magnitude.predictedMoveRateByThreshold,
    foldResults:magnitude.foldResults,selectionIntegrity:magnitude.selectionIntegrity,
  },
  limitations:[
    'Historical order-book/tick-flow not reconstructed',
    'Yahoo Finance 5m window limited to recent history',
    'Only same-session fixed horizons 5/15/30/60/120 minutes are eligible',
    'Session-end exit is not yet a separate candidate',
    'Round-trip cost fixed at 0.05%',
    'Outer OOS is evaluation-only and is never used to select horizon/model/feature family/threshold',
  ],
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  overnightHoldingAllowed:false,
};

fs.mkdirSync('artifacts',{recursive:true});
const output=`artifacts/phase57-adaptive-horizon-magnitude-${scope}.json`;
fs.writeFileSync(output,JSON.stringify(summary,null,2));
console.log('PHASE57_P21_2_REAL_JSON_START');
console.log(JSON.stringify(summary,null,2));
console.log('PHASE57_P21_2_REAL_JSON_END');
