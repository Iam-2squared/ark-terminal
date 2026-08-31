import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {PHASE57_US_CROSS_MARKET_SAFETY,assertPhase57UsCrossMarketSafety} from '../predict/daytrade/phase57-us-cross-market-policy.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const universePath=arg('--universe');
const output=arg('--output','tmp/us-free-5m.json');
const sessionDate=arg('--session-date');
const sampleSize=Math.max(100,Math.min(600,Number(arg('--sample-size','300'))));
const concurrency=Math.max(1,Math.min(24,Number(arg('--concurrency','12'))));
if(!universePath||!sessionDate)throw new Error('usage: --universe file --session-date YYYY-MM-DD [--output file]');
assertPhase57UsCrossMarketSafety();
const u=JSON.parse(fs.readFileSync(universePath,'utf8'));
if(!['US_FREE_COLLECTION_UNIVERSE','US_UNIVERSE_FROZEN'].includes(u.status))throw new Error(`unsupported US collection universe ${u.status}`);
const symbols=(u.universe??[]).map(x=>String(x.symbol??'').trim().toUpperCase()).filter(Boolean);
if(symbols.length<500)throw new Error(`US free 5m universe too small ${symbols.length}`);
const digest=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const median=a=>{const b=[...a].sort((x,y)=>x-y);if(!b.length)return 0;const m=Math.floor(b.length/2);return b.length%2?b[m]:(b[m-1]+b[m])/2;};
function etParts(ts){const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(ts*1000));const o=Object.fromEntries(parts.map(x=>[x.type,x.value]));return {date:`${o.year}-${o.month}-${o.day}`,hm:`${o.hour}:${o.minute}`};}
function regular(ts){const p=etParts(ts);return p.date===sessionDate&&p.hm>='09:30'&&p.hm<'16:00';}
function stableSample(all,n){return all.map(symbol=>({symbol,h:digest(`${sessionDate}|${symbol}`)})).sort((a,b)=>a.h.localeCompare(b.h)).slice(0,Math.min(n,all.length)).map(x=>x.symbol);}
async function fetchChart(symbol,attempt=0){
  const url=`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=1d&interval=5m&includePrePost=false&events=div%2Csplits`;
  const r=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0','Accept':'application/json'}});
  if((r.status===429||r.status>=500)&&attempt<2){await sleep(500*(attempt+1));return fetchChart(symbol,attempt+1);}
  if(!r.ok)throw new Error(`${symbol} Yahoo chart HTTP ${r.status}`);
  const j=await r.json();const result=j?.chart?.result?.[0];if(!result)throw new Error(`${symbol} Yahoo chart no result`);
  const ts=result.timestamp??[],q=result.indicators?.quote?.[0]??{},bars=[];
  for(let i=0;i<ts.length;i++){const t=Number(ts[i]),c=Number(q.close?.[i]),v=Number(q.volume?.[i]??0);if(Number.isFinite(t)&&Number.isFinite(c)&&c>0&&Number.isFinite(v)&&v>=0&&regular(t))bars.push({t,c,v});}
  if(bars.length<2)return null;bars.sort((a,b)=>a.t-b.t);const latest=bars.at(-1),prev=bars.at(-2);const history=bars.slice(-7,-1).map(x=>x.v).filter(Number.isFinite);const med=median(history);
  return {symbol,currentPrice:latest.c,volume:latest.v,dollarVolume:latest.c*latest.v,changePct:prev.c>0?((latest.c/prev.c)-1)*100:0,volumeRatio:med>0?latest.v/med:1,barTimestamp:latest.t*1000,provider:'YAHOO_PUBLIC_CHART_5M'};
}
const sampledSymbols=stableSample(symbols,sampleSize),rows=[],errors=[];let next=0;
async function worker(){while(true){const i=next++;if(i>=sampledSymbols.length)return;const symbol=sampledSymbols[i];try{const row=await fetchChart(symbol);if(row)rows.push(row);}catch(e){errors.push({symbol,error:String(e?.message??e)});}await sleep(30);}}
await Promise.all(Array.from({length:concurrency},()=>worker()));
const bySymbol=new Map();for(const x of rows){const old=bySymbol.get(x.symbol);if(!old||Number(x.barTimestamp)>Number(old.barTimestamp))bySymbol.set(x.symbol,x);}
const dedup=[...bySymbol.values()].sort((a,b)=>a.symbol.localeCompare(b.symbol));
const sampleCoveragePct=sampledSymbols.length?100*dedup.length/sampledSymbols.length:0;
if(dedup.length<120||sampleCoveragePct<40)throw new Error(`US free 5m sample coverage fail-closed ${dedup.length}/${sampledSymbols.length} (${sampleCoveragePct.toFixed(2)}%); errors=${errors.slice(0,5).map(x=>x.error).join('; ')}`);
const ages=dedup.map(x=>(Date.now()-Number(x.barTimestamp))/1000).filter(Number.isFinite);const medianAgeSeconds=median(ages);
const envelope={
  schemaVersion:2,provider:'YAHOO',plan:'FREE',costUsd:0,sessionDate,mode:'intraday5m',observedAt:new Date().toISOString(),
  freshRealtime:false,researchIntraday5m:true,formalFreshEligible:false,feedClassification:'FREE_INTRADAY_5M_DIAGNOSTIC',
  sourceContract:'UNVERIFIED_PUBLIC_CHART_ENDPOINT_RUNTIME_VALIDATED',universeStatus:u.status,universeSymbols:symbols.length,sampleDiagnostic:true,marketwide:false,
  sampleMethod:'SESSION_DATE_STABLE_SHA256',sampleSize:sampledSymbols.length,sampledSymbols,rows:dedup,sampleCoveragePct,medianAgeSeconds,
  errors,rawDigest:digest(dedup),noPaidFallback:true,noBrokerDependency:true,
  classification:{partialAllowed:true,fullFresh:false,jpxOosSubstitute:false,formalOos:false,promotionEligible:false},
  safety:PHASE57_US_CROSS_MARKET_SAFETY,
};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(envelope,null,2)+'\n');
console.log(JSON.stringify({provider:envelope.provider,mode:envelope.mode,universeSymbols:symbols.length,sampleSize:sampledSymbols.length,rows:dedup.length,sampleCoveragePct:Number(sampleCoveragePct.toFixed(2)),medianAgeSeconds:Number(medianAgeSeconds.toFixed(1)),errors:errors.length,output},null,2));
