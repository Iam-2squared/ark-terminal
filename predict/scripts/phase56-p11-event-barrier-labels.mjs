import { writeFile } from 'node:fs/promises';
import { trainModel } from '../models/phase47-real-training.js';
import { searchPrecisionConditions } from '../chart/phase56-precision-search.js';

const symbols=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const sectors={'7203.T':'AUTOMOTIVE','6758.T':'ELECTRONICS','9984.T':'COMMUNICATIONS','8306.T':'BANKS','8035.T':'SEMICONDUCTOR_DISTRIBUTION'};
const range='5y',interval='1d',lookback=120,maxHolding=5,barrierAtr=1.0;
const minTrainDates=420,innerValidationDates=60,outerTestDates=60,stepDates=60;
const safety={executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false};
const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:0;

async function fetchCandles(symbol){
  const u=`https://query2.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=${range}&interval=${interval}&events=div%2Csplits`;
  const r=await fetch(u,{headers:{'User-Agent':'Mozilla/5.0 (compatible; ArkTerminal/3.0)',Accept:'application/json'}});
  if(!r.ok) throw new Error(`${symbol}: Yahoo HTTP ${r.status}`);
  const x=(await r.json())?.chart?.result?.[0]; if(!x) throw new Error(`${symbol}: no chart result`);
  const q=x.indicators?.quote?.[0]??{},a=x.indicators?.adjclose?.[0]?.adjclose??[];
  return (x.timestamp??[]).map((time,i)=>{const o=+q.open?.[i],h=+q.high?.[i],l=+q.low?.[i],c=+q.close?.[i],ad=+a?.[i];if(![o,h,l,c].every(Number.isFinite)||c<=0)return null;const f=Number.isFinite(ad)&&ad>0?ad/c:1;return{date:new Date(+time*1000).toISOString().slice(0,10),open:o*f,high:h*f,low:l*f,close:c*f,volume:+q.volume?.[i]||0};}).filter(Boolean);
}
function features(bars){
  const c=bars.map(b=>b.close),v=bars.map(b=>b.volume),last=c.at(-1),ret=n=>last/c.at(-1-n)-1;
  const ma=n=>mean(c.slice(-n)),ma5=ma(5),ma25=ma(25),ma75=ma(75);
  const recent=bars.slice(-20),hi=Math.max(...recent.map(b=>b.high)),lo=Math.min(...recent.map(b=>b.low));
  const tr=recent.map((b,i)=>i?Math.max(b.high-b.low,Math.abs(b.high-recent[i-1].close),Math.abs(b.low-recent[i-1].close)):b.high-b.low);
  const atr20=mean(tr)/last,rv=mean(v.slice(-5))/(mean(v.slice(-20))||1);
  return {ret1:ret(1),ret3:ret(3),ret5:ret(5),ret20:ret(20),ma5Distance:last/ma5-1,ma25Distance:last/ma25-1,ma75Distance:last/ma75-1,trend20:ma25/ma75-1,atr20,rangePosition:hi===lo?.5:(last-lo)/(hi-lo),relativeVolume:rv,breakout20:last/hi-1,drawdown20:last/hi-1,trendXRvol:(ma25/ma75-1)*(rv-1),momentumXMa:ret(5)*(last/ma25-1)};
}
function eventLabel(candles,i,atrPct){
  const entry=candles[i].close,dist=Math.max(entry*atrPct*barrierAtr,entry*0.0025),upper=entry+dist,lower=entry-dist;
  for(let j=1;j<=maxHolding&&i+j<candles.length;j++){
    const b=candles[i+j],up=b.high>=upper,down=b.low<=lower;
    if(up&&down)return {status:'AMBIGUOUS',outcomeAt:b.date};
    if(up)return {status:'RESOLVED',label:1,outcomeAt:b.date,eventReturn:dist/entry,holdingDays:j};
    if(down)return {status:'RESOLVED',label:0,outcomeAt:b.date,eventReturn:-dist/entry,holdingDays:j};
  }
  return {status:'TIMEOUT',outcomeAt:candles[Math.min(i+maxHolding,candles.length-1)]?.date??null};
}
function rowsFor(symbol,candles){
  const rows=[];for(let i=lookback-1;i+maxHolding<candles.length;i++){
    const f=features(candles.slice(i-lookback+1,i+1)),ev=eventLabel(candles,i,f.atr20);if(ev.status!=='RESOLVED')continue;
    for(const s of symbols)f[`symbol_${s}`]=symbol===s?1:0;
    rows.push({id:`${symbol}:${candles[i].date}`,symbol,sector:sectors[symbol],sessionDate:candles[i].date,outcomeAt:ev.outcomeAt,label:ev.label,eventReturn:ev.eventReturn,holdingDays:ev.holdingDays,featureVector:f});
  }return rows;
}
const datesOf=rows=>[...new Set(rows.map(r=>r.sessionDate))].sort();
const inDates=(rows,dates)=>{const s=new Set(dates);return rows.filter(r=>s.has(r.sessionDate));};
const resolvedBy=(rows,cutoff)=>rows.filter(r=>r.outcomeAt<=cutoff);
const trainRows=rows=>rows.map(r=>({id:r.id,symbol:r.symbol,sessionDate:r.sessionDate,label:r.label,actualReturn:r.eventReturn,features:r.featureVector}));
const score=(m,r)=>Math.min(.999,Math.max(.001,m.predict({features:r.featureVector})));
function candidates(train,val){
  const defs=[['LOGIT','LOGISTIC_REGRESSION',{iterations:180,learningRate:.06,l2:.001}],['RF16','RANDOM_FOREST',{treeCount:16}],['GB16','GRADIENT_BOOSTING',{rounds:16,learningRate:.08}]],out=[];
  for(const [id,type,options] of defs){const m=trainModel({rows:trainRows(train),modelType:type,options});for(const threshold of [.5,.55,.6,.65]){const sig=[];for(const r of val){const p=score(m,r),conf=Math.max(p,1-p);if(conf<threshold)continue;const pred=p>=.5?1:0;sig.push({hit:pred===r.label,aligned:(pred===r.label?1:-1)*Math.abs(r.eventReturn)});}if(sig.length<30)continue;const hit=sig.filter(x=>x.hit).length/sig.length,avg=mean(sig.map(x=>x.aligned));out.push({id,type,options,threshold,signals:sig.length,hit,avg,rank:hit+Math.min(.05,Math.max(-.05,avg*5))});}}
  return out.sort((a,b)=>b.rank-a.rank||b.signals-a.signals);
}

const all=[],errors=[];for(const s of symbols){try{all.push(...rowsFor(s,await fetchCandles(s)));}catch(e){errors.push(String(e?.message??e));}}
all.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.symbol.localeCompare(b.symbol));
const dates=datesOf(all),outerPredictions=[],folds=[];
for(let outerStart=minTrainDates;outerStart+outerTestDates<=dates.length;outerStart+=stepDates){
  const devDates=dates.slice(0,outerStart),outerDates=dates.slice(outerStart,outerStart+outerTestDates),innerValDates=devDates.slice(-innerValidationDates),innerTrainDates=devDates.slice(0,-innerValidationDates);
  const trainCut=innerTrainDates.at(-1),valCut=innerValDates.at(-1),devCut=devDates.at(-1);
  const innerTrain=resolvedBy(inDates(all,innerTrainDates),trainCut),innerVal=resolvedBy(inDates(all,innerValDates),valCut),dev=resolvedBy(inDates(all,devDates),devCut),test=inDates(all,outerDates);
  if(innerTrain.length<100||innerVal.length<30||test.length<20)continue;const best=candidates(innerTrain,innerVal)[0];if(!best)continue;
  const model=trainModel({rows:trainRows(dev),modelType:best.type,options:best.options});let signals=0;
  for(const r of test){const p=score(model,r),confidence=Math.max(p,1-p);if(confidence<best.threshold)continue;const pred=p>=.5?1:0,hit=pred===r.label,alignedReturn=(hit?1:-1)*Math.abs(r.eventReturn);outerPredictions.push({id:r.id,symbol:r.symbol,sector:r.sector,regime:r.featureVector.trend20>=0?'TREND_UP':'TREND_DOWN',sessionDate:r.sessionDate,outcomeAt:r.outcomeAt,probability:p,label:r.label,hit,alignedReturn,holdingDays:r.holdingDays});signals++;}
  folds.push({fold:folds.length,outerTestStart:outerDates[0],outerTestEnd:outerDates.at(-1),selectedModel:best.id,selectedThreshold:best.threshold,innerValidationSignals:best.signals,innerValidationHitRate:best.hit,outerSignals:signals,trainingOutcomesResolvedBy:devCut});
}
const nestedOos={selectionLeakBlocked:true,outerTestUntouchedBySelection:true,outerPredictions};
const precision=searchPrecisionConditions({nestedOos,candidates:[{id:'CONF_GE_60',description:'event-barrier confidence >=60%',predicate:r=>Math.max(r.probability,1-r.probability)>=.60},{id:'CONF_GE_65',description:'event-barrier confidence >=65%',predicate:r=>Math.max(r.probability,1-r.probability)>=.65}]});
const report={generatedAt:new Date().toISOString(),source:'Yahoo Finance public chart endpoint',symbols,range,interval,lookback,eventDefinition:{type:'ATR_FIRST_TOUCH',barrierAtr,maxHolding,ambiguousSameBar:'EXCLUDED',timeouts:'EXCLUDED'},dataRows:all.length,errors,folds,nestedSummary:{status:folds.length?'NESTED_EVENT_BARRIER_OOS_READY':'INSUFFICIENT_DATA',folds:folds.length,outerSignals:outerPredictions.length,hitRate:outerPredictions.length?outerPredictions.filter(x=>x.hit).length/outerPredictions.length:null,meanAlignedReturn:outerPredictions.length?mean(outerPredictions.map(x=>x.alignedReturn)):null,selectionLeakBlocked:true,outerTestUntouchedBySelection:true},pointInTime:{trainingRequiresOutcomeAtOnOrBeforeFoldCutoff:true,outerDatesNeverUsedForSelection:true},precision,limitations:['Daily OHLC cannot order intraday touches when both barriers occur in the same bar; those cases are excluded.','Daily Yahoo OHLCV only; no historical order-book/tick microstructure or crowd sentiment backfill.'],safety};
await writeFile('phase56-p11-event-barrier-labels.json',JSON.stringify(report,null,2));console.log('PHASE56_P11_EVENT_BARRIER_START');console.log(JSON.stringify(report));console.log('PHASE56_P11_EVENT_BARRIER_END');
