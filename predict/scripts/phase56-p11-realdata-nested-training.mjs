import { writeFile } from 'node:fs/promises';
import { trainPhase56MultifactorArtifact } from '../chart/phase56-multifactor-training.js';
import { scoreInteractionAwareLogistic } from '../chart/phase56-multifactor-model.js';
import { searchPrecisionConditions } from '../chart/phase56-precision-search.js';

const symbols=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const sectors={'7203.T':'AUTOMOTIVE','6758.T':'ELECTRONICS','9984.T':'COMMUNICATIONS','8306.T':'BANKS','8035.T':'SEMICONDUCTOR_DISTRIBUTION'};
const horizon=1, lookback=80, range='5y', interval='1d';
const minTrainDates=300, innerValidationDates=60, outerTestDates=60, stepDates=60;
const interactions=[
  {id:'trend_x_rvol',features:['trend20','relativeVolume']},
  {id:'ma_x_momentum',features:['ma25Distance','ret5']},
  {id:'vol_x_range',features:['atr20','rangePosition']},
];

async function fetchCandles(symbol){
  const u=`https://query2.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=${range}&interval=${interval}&events=div%2Csplits`;
  const r=await fetch(u,{headers:{'User-Agent':'Mozilla/5.0 (compatible; ArkTerminal/3.0)',Accept:'application/json'}});
  if(!r.ok) throw new Error(`${symbol}: Yahoo HTTP ${r.status}`);
  const x=(await r.json())?.chart?.result?.[0]; if(!x) throw new Error(`${symbol}: no chart result`);
  const q=x.indicators?.quote?.[0]??{},a=x.indicators?.adjclose?.[0]?.adjclose??[];
  return (x.timestamp??[]).map((time,i)=>{const o=+q.open?.[i],h=+q.high?.[i],l=+q.low?.[i],c=+q.close?.[i],ad=+a?.[i];if(![o,h,l,c].every(Number.isFinite)||c<=0)return null;const f=Number.isFinite(ad)&&ad>0?ad/c:1;return{time:+time,date:new Date(+time*1000).toISOString().slice(0,10),open:o*f,high:h*f,low:l*f,close:c*f,volume:+q.volume?.[i]||0};}).filter(Boolean);
}
const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:0;
function features(bars){
  const c=bars.map(b=>b.close), v=bars.map(b=>b.volume), last=c.at(-1), ma25=mean(c.slice(-25)), ma60=mean(c.slice(-60));
  const ret1=c.length>1?last/c.at(-2)-1:0, ret5=c.length>5?last/c.at(-6)-1:0;
  const tr=bars.slice(-20).map((b,i,arr)=>i?Math.max(b.high-b.low,Math.abs(b.high-arr[i-1].close),Math.abs(b.low-arr[i-1].close)):b.high-b.low);
  const hi=Math.max(...bars.slice(-20).map(b=>b.high)), lo=Math.min(...bars.slice(-20).map(b=>b.low));
  return {ret1,ret5,trend20:ma25/ma60-1,ma25Distance:last/ma25-1,atr20:mean(tr)/last,rangePosition:hi===lo?.5:(last-lo)/(hi-lo),relativeVolume:mean(v.slice(-5))/(mean(v.slice(-20))||1)};
}
function rowsFor(symbol,candles){const rows=[];for(let i=lookback-1;i+horizon<candles.length;i++){const bars=candles.slice(i-lookback+1,i+1), future=candles[i+horizon];const actualReturn=future.close/candles[i].close-1;rows.push({id:`${symbol}:${candles[i].date}`,symbol,sector:sectors[symbol],sessionDate:candles[i].date,featureCutoff:candles[i].date,outcomeAt:future.date,actualReturn,featureVector:features(bars)});}return rows;}
const uniqueDates=rows=>[...new Set(rows.map(r=>r.sessionDate))].sort();
const filterDates=(rows,dates)=>{const s=new Set(dates);return rows.filter(r=>s.has(r.sessionDate));};
function metrics(rows){const hits=rows.filter(r=>r.hit).length;return{sampleCount:rows.length,hitRate:rows.length?hits/rows.length:null,meanAlignedReturn:rows.length?mean(rows.map(r=>r.alignedReturn)):null};}

const all=[];const errors=[];
for(const symbol of symbols){try{all.push(...rowsFor(symbol,await fetchCandles(symbol)));}catch(e){errors.push(String(e?.message??e));}}
all.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.symbol.localeCompare(b.symbol));
const dates=uniqueDates(all), outerPredictions=[], folds=[];
for(let outerStart=minTrainDates;outerStart+outerTestDates<=dates.length;outerStart+=stepDates){
  const developmentDates=dates.slice(0,outerStart), outerDates=dates.slice(outerStart,outerStart+outerTestDates), innerVal=developmentDates.slice(-innerValidationDates), innerTrain=developmentDates.slice(0,-innerValidationDates);
  const trainRows=filterDates(all,innerTrain), valRows=filterDates(all,innerVal), fullDevRows=filterDates(all,developmentDates), testRows=filterDates(all,outerDates);
  const candidates=[{l2:.0005},{l2:.001},{l2:.005},{l2:.01}]; let best=null;
  for(const cfg of candidates){const trained=trainPhase56MultifactorArtifact({rows:trainRows,trainingAsOf:innerTrain.at(-1),interactions,options:{iterations:180,learningRate:.06,l2:cfg.l2}});if(!trained.model)continue;const scored=valRows.map(r=>{const p=scoreInteractionAwareLogistic({featureVector:r.featureVector,model:trained.model}).probability;const dir=p>=.5?1:-1;return dir*r.actualReturn;});const score=mean(scored);if(!best||score>best.score)best={cfg,score};}
  if(!best)continue;
  const trained=trainPhase56MultifactorArtifact({rows:fullDevRows,trainingAsOf:developmentDates.at(-1),interactions,options:{iterations:180,learningRate:.06,l2:best.cfg.l2}}); if(!trained.model)continue;
  for(const r of testRows){const p=scoreInteractionAwareLogistic({featureVector:r.featureVector,model:trained.model}).probability;const dir=p>=.5?1:-1, aligned=dir*r.actualReturn;outerPredictions.push({id:r.id,symbol:r.symbol,sector:r.sector,regime:'UNKNOWN',sessionDate:r.sessionDate,probability:p,label:r.actualReturn>0?1:0,hit:aligned>0,alignedReturn:aligned,selectedConfigId:`L2_${best.cfg.l2}`});}
  folds.push({fold:folds.length,innerTrainEnd:innerTrain.at(-1),innerValidationEnd:innerVal.at(-1),outerTestStart:outerDates[0],outerTestEnd:outerDates.at(-1),selectedL2:best.cfg.l2,outerSamples:testRows.length});
}
const nestedOos={selectionLeakBlocked:true,outerTestUntouchedBySelection:true,outerPredictions,metrics:metrics(outerPredictions)};
const precision=searchPrecisionConditions({nestedOos,candidates:[{id:'CONF_GE_60',description:'model confidence >= 60%',predicate:r=>Math.max(r.probability,1-r.probability)>=.60},{id:'CONF_GE_65',description:'model confidence >= 65%',predicate:r=>Math.max(r.probability,1-r.probability)>=.65},{id:'CONF_GE_70',description:'model confidence >= 70%',predicate:r=>Math.max(r.probability,1-r.probability)>=.70}]});
const report={generatedAt:new Date().toISOString(),source:'Yahoo Finance public chart endpoint',symbols,range,interval,horizon,lookback,dataRows:all.length,errors,folds,nestedSummary:{status:folds.length?'NESTED_MULTIFACTOR_OOS_READY':'INSUFFICIENT_DATA',folds:folds.length,outerSamples:outerPredictions.length,metrics:metrics(outerPredictions),selectionLeakBlocked:true,outerTestUntouchedBySelection:true},precision,limitations:['Daily Yahoo OHLCV only: no historical order-book/tick microstructure or crowd sentiment backfill in this run.','This is research-only OOS evaluation; no execution or promotion permission is changed.'],safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false}};
await writeFile('phase56-p11-realdata-nested-training.json',JSON.stringify(report,null,2));
console.log('PHASE56_P11_REALDATA_NESTED_TRAINING_START');console.log(JSON.stringify(report));console.log('PHASE56_P11_REALDATA_NESTED_TRAINING_END');
