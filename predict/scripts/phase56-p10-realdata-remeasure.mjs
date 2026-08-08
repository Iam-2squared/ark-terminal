import { writeFile } from 'node:fs/promises';
import { evaluateOosAdaptiveFusion } from '../chart/phase56-oos-adaptive-fusion.js';
import { buildNestedWalkForwardOos } from '../chart/phase56-nested-walkforward-oos.js';
import { searchPrecisionConditions } from '../chart/phase56-precision-search.js';

const symbols=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const sectors={'7203.T':'AUTOMOTIVE','6758.T':'ELECTRONICS','9984.T':'COMMUNICATIONS','8306.T':'BANKS','8035.T':'SEMICONDUCTOR_DISTRIBUTION'};
const horizons=[1,3,5,10,20], lookback=80, range='5y', interval='1d';
const configs=[
 {id:'S5_M2',minimumScore:5,minimumMargin:2},
 {id:'S6_M2',minimumScore:6,minimumMargin:2},
 {id:'S7_M3',minimumScore:7,minimumMargin:3},
 {id:'S8_M3',minimumScore:8,minimumMargin:3},
];

async function fetchCandles(symbol){
 const u=`https://query2.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=${range}&interval=${interval}&events=div%2Csplits`;
 const r=await fetch(u,{headers:{'User-Agent':'Mozilla/5.0 (compatible; ArkTerminal/3.0)',Accept:'application/json'}});
 if(!r.ok)throw new Error(`${symbol}: Yahoo HTTP ${r.status}`);
 const x=(await r.json())?.chart?.result?.[0]; if(!x)throw new Error(`${symbol}: no chart result`);
 const q=x.indicators?.quote?.[0]??{},a=x.indicators?.adjclose?.[0]?.adjclose??[];
 return (x.timestamp??[]).map((time,i)=>{const o=+q.open?.[i],h=+q.high?.[i],l=+q.low?.[i],c=+q.close?.[i],ad=+a?.[i];if(![o,h,l,c].every(Number.isFinite)||c<=0)return null;const f=Number.isFinite(ad)&&ad>0?ad/c:1;return{time:+time,sessionDate:new Date(+time*1000).toISOString().slice(0,10),open:o*f,high:h*f,low:l*f,close:c*f,volume:+q.volume?.[i]||0};}).filter(Boolean);
}

function scoreConfig({config,validationRows}){
 const xs=validationRows.map(r=>r.byConfig[config.id]).filter(x=>x?.signal===1||x?.signal===-1);
 if(xs.length<20)return -1e9;
 const hr=xs.filter(x=>x.hit).length/xs.length;
 const mean=xs.reduce((s,x)=>s+x.alignedReturn,0)/xs.length;
 return hr + Math.max(-.1,Math.min(.1,mean))*2 + Math.min(xs.length,200)/10000;
}

function evaluateConfig({config,testRows}){
 return testRows.map(r=>{const x=r.byConfig[config.id];if(!x||!(x.signal===1||x.signal===-1))return null;return {symbol:r.symbol,sector:r.sector,sessionDate:r.sessionDate,horizon:r.horizon,regime:x.regime,weightedScore:x.weightedScore,signal:x.signal,alignedReturn:x.alignedReturn,return:x.alignedReturn,hit:x.hit,label:x.hit?1:0,probability:null};}).filter(Boolean);
}

const rows=[], errors=[];
for(const symbol of symbols){
 try{
  const candles=await fetchCandles(symbol);
  for(const horizon of horizons){
   for(let i=lookback-1;i+horizon<candles.length;i++){
    const bars=candles.slice(i-lookback+1,i+1), forward=candles[i+horizon].close/candles[i].close-1, byConfig={};
    for(const config of configs){
     const s=evaluateOosAdaptiveFusion({bars,horizon,symbol,timeframe:'1d',minimumScore:config.minimumScore,minimumMargin:config.minimumMargin,requirePatternEvidence:false});
     if(s.signal===1||s.signal===-1){const aligned=forward*s.signal;byConfig[config.id]={signal:s.signal,regime:s.regime,weightedScore:s.weightedScore,alignedReturn:aligned,hit:aligned>0};}
     else byConfig[config.id]={signal:0,regime:s.regime?.regime??'ABSTAIN',weightedScore:0,alignedReturn:0,hit:false};
    }
    rows.push({symbol,sector:sectors[symbol]??'UNKNOWN',sessionDate:candles[i].sessionDate,horizon,byConfig});
   }
  }
 }catch(e){errors.push({symbol,error:String(e?.message??e)});}
}

const nested=buildNestedWalkForwardOos({rows,candidateConfigs:configs,minTrainDates:252,innerValidationDates:63,outerTestDates:63,stepDates:63,scoreConfig:({config,validationRows})=>scoreConfig({config,validationRows}),evaluateConfig:({config,testRows})=>evaluateConfig({config,testRows})});
const candidates=[
 {id:'H1',description:'1-day horizon only',predicate:r=>r.horizon===1},
 {id:'H3',description:'3-day horizon only',predicate:r=>r.horizon===3},
 {id:'H5',description:'5-day horizon only',predicate:r=>r.horizon===5},
 {id:'SCORE_GE_8',description:'weighted fusion score >= 8',predicate:r=>Number(r.weightedScore)>=8},
 {id:'SCORE_GE_10',description:'weighted fusion score >= 10',predicate:r=>Number(r.weightedScore)>=10},
 {id:'TREND_1D',description:'1-day trend regimes',predicate:r=>r.horizon===1&&['TREND_UP','TREND_DOWN','VOLATILE_UP','VOLATILE_DOWN'].includes(r.regime)},
];
const precision=searchPrecisionConditions({nestedOos:nested,candidates,minSamples:100,minCoverage:.01,minProfitFactor:1.2,maxDrawdown:.25,minHitRate:.70,maxStabilitySpread:.20});
const report={generatedAt:new Date().toISOString(),source:'Yahoo Finance public chart endpoint',range,interval,lookback,symbols,horizons,configs,dataRows:rows.length,errors,nestedSummary:{status:nested.status,folds:nested.folds.length,outerSamples:nested.outerPredictions.length,metrics:nested.metrics,selectionLeakBlocked:nested.selectionLeakBlocked,outerTestUntouchedBySelection:nested.outerTestUntouchedBySelection},precision,limitations:['P8 multi-factor model has no fitted real-data coefficient artifact yet; this remeasurement validates P9/P10 outer-only selection using the existing adaptive-fusion signal family.','Microstructure and crowd-sentiment sources are not backfilled in this daily Yahoo dataset.','P10 maxDrawdown is a research diagnostic over prediction returns, not executable portfolio PnL.'],safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false}};
await writeFile('phase56-p10-realdata-remeasure.json',JSON.stringify(report,null,2));
console.log('PHASE56_P10_REALDATA_REMEASURE_START');console.log(JSON.stringify(report));console.log('PHASE56_P10_REALDATA_REMEASURE_END');
