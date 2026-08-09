import fs from 'node:fs';
import { buildHistoricalIntradayRows, evaluateHistoricalIntradayBaseline } from './phase57-historical-intraday-baseline.js';
import { enrichHistoricalIntradayBars, attachMultiFactorFeatures } from './phase57-intraday-multifactor.js';

const symbols=(process.env.PHASE57_SYMBOLS||'7203.T,6758.T,9984.T,8306.T,8035.T').split(',').map(s=>s.trim()).filter(Boolean);
const interval=process.env.PHASE57_INTERVAL||'5m';
const range=process.env.PHASE57_RANGE||'60d';
const horizonBars=Number(process.env.PHASE57_HORIZON_BARS||5);
const barrierBps=Number(process.env.PHASE57_BARRIER_BPS||20);
const evalOptions={trainFraction:0.6,testFraction:0.1,minTrainRows:200,innerTrainFraction:0.6,innerTestFraction:0.15,innerMinTrainRows:100,thresholds:[0.55,0.60,0.65],minInnerSignals:20,feePercent:0,slippagePercent:0.05,delayCostPercent:0};

const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));

function jstParts(tsMs){
  const d=new Date(tsMs);
  const p=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(d);
  const o=Object.fromEntries(p.map(x=>[x.type,x.value]));
  return {date:`${o.year}-${o.month}-${o.day}`,hm:`${o.hour}:${o.minute}`};
}

async function fetchJsonWithRetry(url,symbol,{attempts=5,baseDelayMs=1500}={}){
  let lastError;
  for(let attempt=1;attempt<=attempts;attempt++){
    try{
      const controller=new AbortController();
      const timeout=setTimeout(()=>controller.abort(),30000);
      const res=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0','Accept':'application/json'},signal:controller.signal});
      clearTimeout(timeout);
      if(!res.ok){
        const retriable=res.status===408||res.status===429||res.status>=500;
        if(!retriable) throw new Error(`${symbol} Yahoo chart HTTP ${res.status}`);
        throw new Error(`${symbol} Yahoo chart transient HTTP ${res.status}`);
      }
      return await res.json();
    }catch(error){
      lastError=error;
      if(attempt===attempts) break;
      await sleep(baseDelayMs*attempt);
    }
  }
  throw lastError;
}

async function fetchBars(symbol){
  const url=`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=${encodeURIComponent(range)}&interval=${encodeURIComponent(interval)}&includePrePost=false&events=div%2Csplits`;
  const json=await fetchJsonWithRetry(url,symbol);
  const r=json?.chart?.result?.[0]; if(!r) throw new Error(`${symbol} no chart result`);
  const q=r.indicators?.quote?.[0]||{}; const out=[];
  for(let i=0;i<(r.timestamp||[]).length;i++){
    const t=Number(r.timestamp[i])*1000; const {date,hm}=jstParts(t);
    if(hm<'09:00'||hm>'15:30') continue;
    const vals=[q.open?.[i],q.high?.[i],q.low?.[i],q.close?.[i]];
    if(vals.some(v=>v==null||!Number.isFinite(Number(v)))) continue;
    out.push({timestamp:new Date(t).toISOString(),open:Number(q.open[i]),high:Number(q.high[i]),low:Number(q.low[i]),close:Number(q.close[i]),volume:Number(q.volume?.[i]||0),sessionDate:date});
  }
  return out;
}

function metrics(ev){return {signalCount:ev.result.signalCount,hitRate:ev.result.hitRate,netAverageReturn:ev.result.netAverageReturn,outerFoldCount:ev.result.outerResults?.length||0};}

const baselineAll=[]; const multiAll=[]; const bySymbol=[];
for(const symbol of symbols){
  const bars=await fetchBars(symbol); const sessions=new Map();
  for(const b of bars){if(!sessions.has(b.sessionDate))sessions.set(b.sessionDate,[]);sessions.get(b.sessionDate).push(b);}
  let baseRows=[], multiRows=[];
  for(const [sessionDate,sessionBars] of sessions){
    const enriched=enrichHistoricalIntradayBars(sessionBars);
    const base=buildHistoricalIntradayRows({symbol,sessionDate,bars:sessionBars,horizonBars,barrierBps});
    baseRows.push(...base); multiRows.push(...attachMultiFactorFeatures(base,enriched));
  }
  baseRows.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff)); multiRows.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));
  baselineAll.push(...baseRows); multiAll.push(...multiRows);
  const baseEv=evaluateHistoricalIntradayBaseline(baseRows,evalOptions);
  const multiEv=evaluateHistoricalIntradayBaseline(multiRows,evalOptions);
  const b=metrics(baseEv), m=metrics(multiEv);
  bySymbol.push({symbol,barCount:bars.length,sessionCount:sessions.size,rowCount:multiRows.length,baseline:b,multiFactor:m,deltaHitRate:(m.hitRate??0)-(b.hitRate??0),deltaNetAverageReturn:(m.netAverageReturn??0)-(b.netAverageReturn??0)});
}

baselineAll.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff)); multiAll.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));
const combinedOptions={...evalOptions,minTrainRows:500,innerMinTrainRows:200,minInnerSignals:50};
const baseCombined=evaluateHistoricalIntradayBaseline(baselineAll,combinedOptions);
const multiCombined=evaluateHistoricalIntradayBaseline(multiAll,combinedOptions);
const b=metrics(baseCombined),m=metrics(multiCombined);
const summary={phase:'57.p20',status:'INTRADAY_MULTIFACTOR_5M_OOS_MEASURED',source:'Yahoo Finance historical 5m OHLCV',range,interval,horizonBars,barrierBps,symbols,features:['MA5/10/20 distance','MA5 slope','RSI14','MACD','MACD signal gap','ATR%','VWAP distance','Bollinger position','relative volume20','20-bar range position','JST time-of-day buckets'],bySymbol,combined:{rowCount:multiAll.length,baseline:b,multiFactor:m,deltaHitRate:(m.hitRate??0)-(b.hitRate??0),deltaNetAverageReturn:(m.netAverageReturn??0)-(b.netAverageReturn??0),selectionIntegrity:multiCombined.result.selectionIntegrity},limitations:['Historical order-book/tick-flow not reconstructed','Yahoo intraday availability provider-limited','Slippage fixed at 0.05%','P20 evaluates predeclared feature expansion; outer results are not used to choose a new threshold/model'],executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false};
fs.mkdirSync('artifacts',{recursive:true}); fs.writeFileSync('artifacts/phase57-intraday-multifactor.json',JSON.stringify(summary,null,2));
console.log('PHASE57_P20_JSON_START'); console.log(JSON.stringify(summary,null,2)); console.log('PHASE57_P20_JSON_END');
