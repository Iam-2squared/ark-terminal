import { writeFile } from 'node:fs/promises';
import { trainModel } from '../models/phase47-real-training.js';
import { searchPrecisionConditions } from '../chart/phase56-precision-search.js';

const symbols=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const sectors={'7203.T':'AUTOMOTIVE','6758.T':'ELECTRONICS','9984.T':'COMMUNICATIONS','8306.T':'BANKS','8035.T':'SEMICONDUCTOR_DISTRIBUTION'};
const contextSymbols={nikkei:'^N225',nasdaq:'^IXIC',sox:'^SOX',vix:'^VIX',usdJpy:'JPY=X'};
const range='5y',interval='1d',lookback=120,horizon=1;
const minTrainDates=360,innerValidationDates=60,outerTestDates=60,stepDates=60;
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

function baseFeatures(bars){
  const c=bars.map(b=>b.close),v=bars.map(b=>b.volume),last=c.at(-1);
  const ma5=mean(c.slice(-5)),ma25=mean(c.slice(-25)),ma75=mean(c.slice(-75));
  const ret=n=>c.length>n?last/c.at(-1-n)-1:0;
  const tr=bars.slice(-20).map((b,i,arr)=>i?Math.max(b.high-b.low,Math.abs(b.high-arr[i-1].close),Math.abs(b.low-arr[i-1].close)):b.high-b.low);
  const hi=Math.max(...bars.slice(-20).map(b=>b.high)),lo=Math.min(...bars.slice(-20).map(b=>b.low));
  const vol20=mean(v.slice(-20))||1;
  return {ret1:ret(1),ret3:ret(3),ret5:ret(5),ret20:ret(20),ma5Distance:last/ma5-1,ma25Distance:last/ma25-1,ma75Distance:last/ma75-1,trend20:ma25/ma75-1,atr20:mean(tr)/last,rangePosition:hi===lo?.5:(last-lo)/(hi-lo),relativeVolume:mean(v.slice(-5))/vol20,breakout20:last/hi-1,drawdown20:last/hi-1};
}
function rowsFor(symbol,candles){const rows=[];for(let i=lookback-1;i+horizon<candles.length;i++){const future=candles[i+horizon],actualReturn=future.close/candles[i].close-1;rows.push({id:`${symbol}:${candles[i].date}`,symbol,sector:sectors[symbol],sessionDate:candles[i].date,outcomeAt:future.date,actualReturn,featureVector:baseFeatures(candles.slice(i-lookback+1,i+1))});}return rows;}
function contextMap(bars){const m=new Map();for(let i=1;i<bars.length;i++)m.set(bars[i].date,{ret1:bars[i].close/bars[i-1].close-1,level:bars[i].close});return m;}
function latestBefore(map,date,strict=false){let best=null;for(const [d,v] of map){if(strict?d<date:d<=date){if(!best||d>best.date)best={date:d,...v};}}return best;}
function attachContext(rows,maps){for(const r of rows){const n=latestBefore(maps.nikkei,r.sessionDate,false),na=latestBefore(maps.nasdaq,r.sessionDate,true),so=latestBefore(maps.sox,r.sessionDate,true),vi=latestBefore(maps.vix,r.sessionDate,true),fx=latestBefore(maps.usdJpy,r.sessionDate,true);Object.assign(r.featureVector,{ctxNikkeiRet1:n?.ret1??0,ctxNasdaqPrevRet1:na?.ret1??0,ctxSoxPrevRet1:so?.ret1??0,ctxVixPrevRet1:vi?.ret1??0,ctxVixPrevLevel:vi?.level??0,ctxUsdJpyPrevRet1:fx?.ret1??0});r.contextCutoffs={nikkei:n?.date??null,nasdaq:na?.date??null,sox:so?.date??null,vix:vi?.date??null,usdJpy:fx?.date??null};}}
const analogKeys=['ret1','ret5','ma25Distance','trend20','atr20','rangePosition','relativeVolume'];
const scales={ret1:.03,ret5:.08,ma25Distance:.12,trend20:.15,atr20:.04,rangePosition:.35,relativeVolume:.8};
function dist(a,b){return Math.sqrt(mean(analogKeys.map(k=>((Number(a[k]??0)-Number(b[k]??0))/(scales[k]||1))**2)));}
function attachAnalogs(rows){const bySymbol=new Map();for(const r of rows){const history=bySymbol.get(r.symbol)??[];const eligible=history.filter(x=>x.outcomeAt<=r.sessionDate);const nearest=eligible.map(x=>({x,d:dist(r.featureVector,x.featureVector)})).sort((a,b)=>a.d-b.d).slice(0,25);r.featureVector.analogCount=nearest.length;r.featureVector.analogUpRate=nearest.length?nearest.filter(z=>z.x.actualReturn>0).length/nearest.length:.5;r.featureVector.analogMeanReturn=nearest.length?mean(nearest.map(z=>z.x.actualReturn)):0;r.featureVector.analogMeanDistance=nearest.length?mean(nearest.map(z=>z.d)):9;history.push(r);bySymbol.set(r.symbol,history);}}
function enrichInteractions(r){const f=r.featureVector;Object.assign(f,{trendXAnalog:f.trend20*(f.analogUpRate-.5),rvolXAnalog:(f.relativeVolume-1)*(f.analogUpRate-.5),marketXMomentum:f.ctxNikkeiRet1*f.ret5,soxXSemi:f.ctxSoxPrevRet1*(r.symbol==='8035.T'?1:0),riskXTrend:f.ctxVixPrevRet1*f.trend20});for(const s of symbols)f[`symbol_${s}`]=r.symbol===s?1:0;}
const uniqueDates=rows=>[...new Set(rows.map(r=>r.sessionDate))].sort();
const filterDates=(rows,dates)=>{const s=new Set(dates);return rows.filter(r=>s.has(r.sessionDate));};
function trainRows(rows){return rows.map(r=>({id:r.id,symbol:r.symbol,sessionDate:r.sessionDate,label:r.actualReturn>0?1:0,actualReturn:r.actualReturn,features:r.featureVector}));}
function scoreModel(model,r){return Math.min(.999,Math.max(.001,model.predict({features:r.featureVector})));}
function candidateConfigs(train,val){const defs=[['LOGIT','LOGISTIC_REGRESSION',{iterations:180,learningRate:.06,l2:.001}],['RF16','RANDOM_FOREST',{treeCount:16}],['GB16','GRADIENT_BOOSTING',{rounds:16,learningRate:.08}]];const out=[];for(const [id,type,options] of defs){const model=trainModel({rows:trainRows(train),modelType:type,options});for(const threshold of [.5,.55,.6]){const signals=val.map(r=>{const p=scoreModel(model,r),conf=Math.max(p,1-p);if(conf<threshold)return null;const dir=p>=.5?1:-1;return dir*r.actualReturn;}).filter(x=>x!==null);if(signals.length<20)continue;out.push({id,type,options,threshold,score:mean(signals),signals:signals.length});}}return out.sort((a,b)=>b.score-a.score||b.signals-a.signals);}

const errors=[],all=[],context={};
for(const s of symbols){try{all.push(...rowsFor(s,await fetchCandles(s)));}catch(e){errors.push(String(e?.message??e));}}
for(const [k,s] of Object.entries(contextSymbols)){try{context[k]=contextMap(await fetchCandles(s));}catch(e){errors.push(String(e?.message??e));context[k]=new Map();}}
all.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.symbol.localeCompare(b.symbol));attachContext(all,context);attachAnalogs(all);all.forEach(enrichInteractions);
const dates=uniqueDates(all),outerPredictions=[],folds=[];
for(let outerStart=minTrainDates;outerStart+outerTestDates<=dates.length;outerStart+=stepDates){const devDates=dates.slice(0,outerStart),outerDates=dates.slice(outerStart,outerStart+outerTestDates),innerValDates=devDates.slice(-innerValidationDates),innerTrainDates=devDates.slice(0,-innerValidationDates);const innerTrain=filterDates(all,innerTrainDates),innerVal=filterDates(all,innerValDates),dev=filterDates(all,devDates),test=filterDates(all,outerDates);const best=candidateConfigs(innerTrain,innerVal)[0];if(!best)continue;const model=trainModel({rows:trainRows(dev),modelType:best.type,options:best.options});let signals=0;for(const r of test){const p=scoreModel(model,r),confidence=Math.max(p,1-p);if(confidence<best.threshold)continue;const dir=p>=.5?1:-1,alignedReturn=dir*r.actualReturn;outerPredictions.push({id:r.id,symbol:r.symbol,sector:r.sector,regime:r.featureVector.ctxVixPrevLevel>=25?'HIGH_VOL':r.featureVector.trend20>=0?'TREND_UP':'TREND_DOWN',sessionDate:r.sessionDate,probability:p,label:r.actualReturn>0?1:0,hit:alignedReturn>0,alignedReturn,selectedConfigId:`${best.id}_C${best.threshold}`});signals++;}folds.push({fold:folds.length,innerTrainEnd:innerTrainDates.at(-1),innerValidationEnd:innerValDates.at(-1),outerTestStart:outerDates[0],outerTestEnd:outerDates.at(-1),selectedModel:best.id,selectedThreshold:best.threshold,innerValidationSignals:best.signals,outerSignals:signals});}
const hitRate=outerPredictions.length?outerPredictions.filter(r=>r.hit).length/outerPredictions.length:null;
const nestedOos={selectionLeakBlocked:true,outerTestUntouchedBySelection:true,outerPredictions};
const precision=searchPrecisionConditions({nestedOos,candidates:[{id:'CONF_GE_55',description:'context+analog confidence >=55%',predicate:r=>Math.max(r.probability,1-r.probability)>=.55},{id:'CONF_GE_60',description:'context+analog confidence >=60%',predicate:r=>Math.max(r.probability,1-r.probability)>=.60},{id:'ANALOG_STRONG',description:'reserved for model-selected context+analog signals',predicate:()=>true}]});
const report={generatedAt:new Date().toISOString(),source:'Yahoo Finance public chart endpoint',symbols,contextSymbols,range,interval,horizon,lookback,dataRows:all.length,errors,folds,nestedSummary:{status:folds.length?'NESTED_CONTEXT_ANALOG_OOS_READY':'INSUFFICIENT_DATA',folds:folds.length,outerSignals:outerPredictions.length,hitRate,meanAlignedReturn:outerPredictions.length?mean(outerPredictions.map(r=>r.alignedReturn)):null,selectionLeakBlocked:true,outerTestUntouchedBySelection:true},pointInTime:{historicalAnalogsUseOnlyResolvedPriorOutcomes:true,usMarketContextUsesPriorSessionOnly:true,japanContextUsesSameOrPriorSessionClose:true},precision,limitations:['Daily Yahoo OHLCV/context only; no historical order-book/tick microstructure or crowd sentiment backfill.','US index/VIX/FX context is lagged to a prior session to avoid using information unavailable at the Japan close.'],safety};
await writeFile('phase56-p11-context-analog-fusion.json',JSON.stringify(report,null,2));console.log('PHASE56_P11_CONTEXT_ANALOG_START');console.log(JSON.stringify(report));console.log('PHASE56_P11_CONTEXT_ANALOG_END');
