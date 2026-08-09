import fs from 'node:fs';
import { buildHistoricalIntradayRows, evaluateHistoricalIntradayBaseline } from './phase57-historical-intraday-baseline.js';

const symbols = (process.env.PHASE57_SYMBOLS || '7203.T,6758.T,9984.T,8306.T,8035.T').split(',').map(s=>s.trim()).filter(Boolean);
const interval = process.env.PHASE57_INTERVAL || '5m';
const range = process.env.PHASE57_RANGE || '60d';
const horizonBars = Number(process.env.PHASE57_HORIZON_BARS || 5);
const barrierBps = Number(process.env.PHASE57_BARRIER_BPS || 20);

function jstParts(tsMs){
  const d = new Date(tsMs);
  const parts = new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(d);
  const o=Object.fromEntries(parts.map(p=>[p.type,p.value]));
  return {date:`${o.year}-${o.month}-${o.day}`, hm:`${o.hour}:${o.minute}`};
}

async function fetchBars(symbol){
  const url=`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=${encodeURIComponent(range)}&interval=${encodeURIComponent(interval)}&includePrePost=false&events=div%2Csplits`;
  const res=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0'}});
  if(!res.ok) throw new Error(`${symbol} Yahoo chart HTTP ${res.status}`);
  const json=await res.json();
  const result=json?.chart?.result?.[0];
  if(!result) throw new Error(`${symbol} Yahoo chart returned no result: ${JSON.stringify(json?.chart?.error||null)}`);
  const q=result.indicators?.quote?.[0]||{};
  const out=[];
  for(let i=0;i<(result.timestamp||[]).length;i++){
    const t=Number(result.timestamp[i])*1000;
    const {date,hm}=jstParts(t);
    if(hm<'09:00' || hm>'15:30') continue;
    const vals=[q.open?.[i],q.high?.[i],q.low?.[i],q.close?.[i]];
    if(vals.some(v=>v==null || !Number.isFinite(Number(v)))) continue;
    out.push({timestamp:new Date(t).toISOString(),open:Number(q.open[i]),high:Number(q.high[i]),low:Number(q.low[i]),close:Number(q.close[i]),volume:Number(q.volume?.[i]||0),sessionDate:date});
  }
  return out;
}

const allRows=[];
const bySymbol=[];
for(const symbol of symbols){
  const bars=await fetchBars(symbol);
  const sessions=new Map();
  for(const b of bars){if(!sessions.has(b.sessionDate)) sessions.set(b.sessionDate,[]); sessions.get(b.sessionDate).push(b);}
  let rows=[];
  for(const [sessionDate,sessionBars] of sessions){
    rows.push(...buildHistoricalIntradayRows({symbol,sessionDate,bars:sessionBars,horizonBars,barrierBps}));
  }
  rows.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));
  allRows.push(...rows);
  const ev=evaluateHistoricalIntradayBaseline(rows,{trainFraction:0.6,testFraction:0.1,minTrainRows:200,innerTrainFraction:0.6,innerTestFraction:0.15,innerMinTrainRows:100,thresholds:[0.55,0.60,0.65],minInnerSignals:20,feePercent:0,slippagePercent:0.05,delayCostPercent:0});
  bySymbol.push({symbol,barCount:bars.length,sessionCount:sessions.size,rowCount:rows.length,signalCount:ev.result.signalCount,hitRate:ev.result.hitRate,netAverageReturn:ev.result.netAverageReturn,outerFoldCount:ev.result.outerResults?.length||0});
}
allRows.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));
const combined=evaluateHistoricalIntradayBaseline(allRows,{trainFraction:0.6,testFraction:0.1,minTrainRows:500,innerTrainFraction:0.6,innerTestFraction:0.15,innerMinTrainRows:200,thresholds:[0.55,0.60,0.65],minInnerSignals:50,feePercent:0,slippagePercent:0.05,delayCostPercent:0});
const summary={phase:'57.p19.2',status:'HISTORICAL_5M_BASELINE_MEASURED',source:'Yahoo Finance chart API historical intraday OHLCV',interval,range,horizonBars,barrierBps,symbols,bySymbol,combined:{rowCount:allRows.length,signalCount:combined.result.signalCount,hitRate:combined.result.hitRate,netAverageReturn:combined.result.netAverageReturn,outerFoldCount:combined.result.outerResults?.length||0,selectionIntegrity:combined.result.selectionIntegrity},limitations:['Historical order-book/tick-flow not reconstructed','Yahoo intraday history availability is provider-limited','Slippage assumption fixed at 0.05% for this baseline'],executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false};
fs.mkdirSync('artifacts',{recursive:true});
fs.writeFileSync('artifacts/phase57-historical-5m-baseline.json',JSON.stringify(summary,null,2));
console.log('PHASE57_HISTORICAL_BASELINE_JSON_START');
console.log(JSON.stringify(summary,null,2));
console.log('PHASE57_HISTORICAL_BASELINE_JSON_END');
