import fs from 'node:fs';
import path from 'node:path';
import {buildP252Yahoo5mUrls} from '../predict/daytrade/phase57-p25-2j-routine-nonrss-5m-source.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const partialDir=arg('--partial-dir');
const output=arg('--output');
const shardIndex=Number(arg('--shard-index','0'));
const shardCount=Number(arg('--shard-count','1'));
if(!partialDir||!output||!Number.isInteger(shardIndex)||!Number.isInteger(shardCount)||shardCount<1||shardIndex<0||shardIndex>=shardCount)throw new Error('usage: --partial-dir <dir> --output <json> --shard-index <n> --shard-count <n>');
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const sym=v=>String(v??'').trim().toUpperCase();
const uniq=xs=>[...new Set(xs.map(sym).filter(Boolean))].sort();
const JST=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
function jstParts(ms){const p=Object.fromEntries(JST.formatToParts(new Date(ms)).map(x=>[x.type,x.value]));return {date:`${p.year}-${p.month}-${p.day}`,hm:`${p.hour}:${p.minute}`};}
async function fetchSparseYahoo5m({symbol,sessionDate}){
  const errors=[];
  for(const url of buildP252Yahoo5mUrls({symbol,sessionDate})){
    try{
      const response=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0','Accept':'application/json'},cache:'no-store',signal:AbortSignal.timeout(12000)});
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const payload=await response.json(),result=payload?.chart?.result?.[0];
      if(payload?.chart?.error)throw new Error(payload.chart.error?.description??'Yahoo chart error');
      if(!result)throw new Error('Yahoo chart result missing');
      const timestamps=Array.isArray(result.timestamp)?result.timestamp:[],q=result.indicators?.quote?.[0]??{},bars=[];
      for(let i=0;i<timestamps.length;i++){
        const epoch=Number(timestamps[i]),vals=[q.open?.[i],q.high?.[i],q.low?.[i],q.close?.[i]],volume=q.volume?.[i];
        if(!Number.isFinite(epoch)||vals.some(v=>!finite(v))||!finite(volume))continue;
        const ms=epoch*1000,{date,hm}=jstParts(ms);if(date!==sessionDate||hm<'09:00'||hm>'15:30')continue;
        const [open,high,low,close]=vals.map(Number),v=Number(volume);
        if(Math.min(open,high,low,close)<=0||high<low||high<Math.max(open,close)||low>Math.min(open,close)||v<0)continue;
        bars.push({timestamp:new Date(ms).toISOString(),open,high,low,close,volume:v});
      }
      bars.sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
      if(!bars.length)throw new Error('no valid regular-session 5m bars');
      if(new Set(bars.map(x=>x.timestamp)).size!==bars.length)throw new Error('duplicate 5m timestamp');
      return {symbol:sym(symbol),sessionDate,bars};
    }catch(error){errors.push(String(error?.message??error));}
  }
  throw new Error(`Yahoo 5m sparse fetch failed for ${sym(symbol)}: ${errors.join(' | ')}`);
}
const freeze=JSON.parse(fs.readFileSync(path.join(partialDir,'freeze.json'),'utf8'));
const measurements=fs.readFileSync(path.join(partialDir,'partial-measurements.ndjson'),'utf8').split(/\r?\n/).filter(Boolean).map(line=>JSON.parse(line));
const sessionDate=freeze.sessionDate;
const fixedUnion=uniq(Object.values(freeze.variants??{}).flat());
const dynamicUnion=uniq(measurements.flatMap(x=>(x.selected??[]).map(r=>r.symbol)));
const allSymbols=uniq([...fixedUnion,...dynamicUnion]);
const requestedSymbols=allSymbols.filter((_,i)=>i%shardCount===shardIndex);
const sessionBarsBySymbol={},barAudit=[],failures=[];let cursor=0;
async function worker(){while(cursor<requestedSymbols.length){const symbol=requestedSymbols[cursor++];try{const r=await fetchSparseYahoo5m({symbol,sessionDate});sessionBarsBySymbol[symbol]=r.bars;barAudit.push({symbol,barCount:r.bars.length});}catch(error){failures.push({symbol,reason:String(error?.message??error)});}}}
await Promise.all(Array.from({length:Math.min(4,requestedSymbols.length)},()=>worker()));
barAudit.sort((a,b)=>a.symbol.localeCompare(b.symbol));failures.sort((a,b)=>a.symbol.localeCompare(b.symbol));
const payload={schemaVersion:1,phase:'57.p25.incomplete-abcd-bar-shard',status:'P25_INCOMPLETE_ABCD_BAR_SHARD_READY',sessionDate,shardIndex,shardCount,requestedSymbols,sessionBarsBySymbol,barAudit,failures,methodology:{sameYahoo5mSource:true,requestTimeoutMs:12000,partitionByStableSortedSymbolIndexModuloShardCount:true,noBackfillInterpolationOrReplacement:true},safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false}};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,shardIndex,requested:requestedSymbols.length,usable:Object.keys(sessionBarsBySymbol).length,failures:failures.length},null,2));
