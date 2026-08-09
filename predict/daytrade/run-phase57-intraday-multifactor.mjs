import fs from 'node:fs';
import { buildHistoricalIntradayRows, evaluateHistoricalIntradayBaseline } from './phase57-historical-intraday-baseline.js';
import { enrichHistoricalIntradayBars, attachMultiFactorFeatures } from './phase57-intraday-multifactor.js';

const symbols=(process.env.PHASE57_SYMBOLS||'7203.T,6758.T,9984.T,8306.T,8035.T').split(',').map(s=>s.trim()).filter(Boolean);
const interval=process.env.PHASE57_INTERVAL||'5m';
const range=process.env.PHASE57_RANGE||'60d';
const actualWindowDays=58;
const horizonBars=Number(process.env.PHASE57_HORIZON_BARS||5);
const barrierBps=Number(process.env.PHASE57_BARRIER_BPS||20);
const evalOptions={trainFraction:0.6,testFraction:0.1,minTrainRows:200,innerTrainFraction:0.6,innerTestFraction:0.15,innerMinTrainRows:100,thresholds:[0.55,0.60,0.65],minInnerSignals:20,feePercent:0,slippagePercent:0.05,delayCostPercent:0};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));

function jstParts(tsMs){
  const d=new Date(tsMs);
  const p=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(d);
  const o=Object.fromEntries(p.map(x=>[x.type,x.value]));
  return {date:`${o.year}-${o.month}-${o.day}`,hm:`${o.hour}:${o.minute}`};
}

async function fetchJson(urls,symbol){
  let last;
  for(const url of urls){
    for(let attempt=1;attempt<=4;attempt++){
      try{
        const controller=new AbortController();
        const timer=setTimeout(()=>controller.abort(),30000);
        const res=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0','Accept':'application/json','Connection':'close'},signal:controller.signal});
        clearTimeout(timer);
        if(!res.ok) throw new Error(`${symbol} Yahoo HTTP ${res.status}`);
        return await res.json();
      }catch(err){
        last=err;
        if(attempt<4) await sleep(1000*attempt);
      }
    }
  }
  throw last;
}

function parseChart(json,symbol){
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

async function fetchBars(symbol){
  const end=Math.floor(Date.now()/1000)-300;
  const day=86400;
  const split=end-29*day;
  const windows=[[end-actualWindowDays*day,split],[split,end]];
  const merged=[];
  for(const [period1,period2] of windows){
    const qs=`period1=${period1}&period2=${period2}&interval=${encodeURIComponent(interval)}&includePrePost=false&events=div%2Csplits`;
    const urls=[1,2].map(host=>`https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${qs}`);
    merged.push(...parseChart(await fetchJson(urls,symbol),symbol));
    await sleep(500);
  }
  const byTs=new Map(merged.map(b=>[b.timestamp,b]));
  return [...byTs.values()].sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
}

function metrics(ev){return {signalCount:ev.result.signalCount,hitRate:ev.result.hitRate,netAverageReturn:ev.result.netAverageReturn,outerFoldCount:ev.result.outerResults?.length||0};}

const baselineAll=[]; const multiAll=[]; const bySymbol=[];
for(const symbol of symbols){
  const bars=await fetchBars(symbol); const sessions=new Map();
  for(const b of bars){if(!sessions.has(b.sessionDate))sessions.set(b.sessionDate,[]);sessions.get(b.sessionDate).push(b);}
  let baseRows=[],multiRows=[];
  for(const [sessionDate,sessionBars] of sessions){
    const enriched=enrichHistoricalIntradayBars(sessionBars);
    const base=buildHistoricalIntradayRows({symbol,sessionDate,bars:sessionBars,horizonBars,barrierBps});
    baseRows.push(...base); multiRows.push(...attachMultiFactorFeatures(base,enriched));
  }
  baseRows.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff)); multiRows.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));
  baselineAll.push(...baseRows); multiAll.push(...multiRows);
  const b=metrics(evaluateHistoricalIntradayBaseline(baseRows,evalOptions));
  const m=metrics(evaluateHistoricalIntradayBaseline(multiRows,evalOptions));
  bySymbol.push({symbol,barCount:bars.length,sessionCount:sessions.size,rowCount:multiRows.length,baseline:b,multiFactor:m,deltaHitRate:(m.hitRate??0)-(b.hitRate??0),deltaNetAverageReturn:(m.netAverageReturn??0)-(b.netAverageReturn??0)});
}

baselineAll.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff)); multiAll.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));
const combinedOptions={...evalOptions,minTrainRows:500,innerMinTrainRows:200,minInnerSignals:50};
const baseCombined=evaluateHistoricalIntradayBaseline(baselineAll,combinedOptions);
const multiCombined=evaluateHistoricalIntradayBaseline(multiAll,combinedOptions);
const b=metrics(baseCombined),m=metrics(multiCombined);
const summary={phase:'57.p20',status:'INTRADAY_MULTIFACTOR_5M_OOS_MEASURED',source:'Yahoo Finance historical 5m OHLCV (two 29d period chunks)',requestedRange:range,actualWindowDays,interval,horizonBars,barrierBps,symbols,features:['MA5/10/20 distance','MA5 slope','RSI14','MACD','MACD signal gap','ATR%','VWAP distance','Bollinger position','relative volume20','20-bar range position','JST time-of-day buckets'],bySymbol,combined:{rowCount:multiAll.length,baseline:b,multiFactor:m,deltaHitRate:(m.hitRate??0)-(b.hitRate??0),deltaNetAverageReturn:(m.netAverageReturn??0)-(b.netAverageReturn??0),selectionIntegrity:multiCombined.result.selectionIntegrity},limitations:['Historical order-book/tick-flow not reconstructed','Yahoo 5m provider window kept to 58 days to avoid boundary rejection','Slippage fixed at 0.05%','P20 evaluates predeclared feature expansion; outer results are not used to choose a new threshold/model'],executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false};
fs.mkdirSync('artifacts',{recursive:true});
fs.writeFileSync('artifacts/phase57-intraday-multifactor.json',JSON.stringify(summary,null,2));
console.log('PHASE57_P20_JSON_START'); console.log(JSON.stringify(summary,null,2)); console.log('PHASE57_P20_JSON_END');
