import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {PHASE57_US_CROSS_MARKET_SAFETY,assertPhase57UsCrossMarketSafety} from '../predict/daytrade/phase57-us-cross-market-policy.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const universePath=arg('--universe');
const output=arg('--output','tmp/us-free-5m.json');
const sessionDate=arg('--session-date');
const batchSize=Math.max(10,Math.min(100,Number(arg('--batch-size','80'))));
const concurrency=Math.max(1,Math.min(8,Number(arg('--concurrency','4'))));
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
async function getBatch(batch,attempt=0){
  const url=new URL('https://query1.finance.yahoo.com/v7/finance/spark');
  url.searchParams.set('symbols',batch.join(','));url.searchParams.set('range','1d');url.searchParams.set('interval','5m');url.searchParams.set('includePrePost','false');
  const r=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ark-terminal-phase57-research','Accept':'application/json'}});
  if((r.status===429||r.status>=500)&&attempt<2){await sleep(800*(attempt+1));return getBatch(batch,attempt+1);}
  if(!r.ok)throw new Error(`Yahoo batch HTTP ${r.status}`);
  return r.json();
}
function parseSpark(j){
  const result=j?.spark?.result??j?.finance?.result??[];const out=[];
  for(const item of result){
    const symbol=String(item?.symbol??'').toUpperCase();const resp=item?.response?.[0]??item;
    const ts=resp?.timestamp??[];const q=resp?.indicators?.quote?.[0]??{};const closes=q.close??[];const volumes=q.volume??[];
    const bars=[];for(let i=0;i<ts.length;i++){const t=Number(ts[i]),c=Number(closes[i]),v=Number(volumes[i]??0);if(Number.isFinite(t)&&Number.isFinite(c)&&c>0&&Number.isFinite(v)&&v>=0&&regular(t))bars.push({t,c,v});}
    if(bars.length<2)continue;bars.sort((a,b)=>a.t-b.t);
    const latest=bars.at(-1),prev=bars.at(-2);const history=bars.slice(-7,-1).map(x=>x.v).filter(Number.isFinite);const med=median(history);
    out.push({symbol,currentPrice:latest.c,volume:latest.v,dollarVolume:latest.c*latest.v,changePct:prev.c>0?((latest.c/prev.c)-1)*100:0,volumeRatio:med>0?latest.v/med:1,barTimestamp:latest.t*1000,provider:'YAHOO_PUBLIC_SPARK_5M'});
  }
  return out;
}
const batches=[];for(let i=0;i<symbols.length;i+=batchSize)batches.push(symbols.slice(i,i+batchSize));
const rows=[];let next=0;const errors=[];
async function worker(){while(true){const i=next++;if(i>=batches.length)return;try{const j=await getBatch(batches[i]);rows.push(...parseSpark(j));}catch(e){errors.push({batch:i,error:String(e?.message??e)});}await sleep(120);}}
await Promise.all(Array.from({length:concurrency},()=>worker()));
const bySymbol=new Map();for(const x of rows){const old=bySymbol.get(x.symbol);if(!old||Number(x.barTimestamp)>Number(old.barTimestamp))bySymbol.set(x.symbol,x);}
const dedup=[...bySymbol.values()].sort((a,b)=>a.symbol.localeCompare(b.symbol));
const coveragePct=symbols.length?100*dedup.length/symbols.length:0;
if(dedup.length<500||coveragePct<60)throw new Error(`US free 5m coverage fail-closed ${dedup.length}/${symbols.length} (${coveragePct.toFixed(2)}%)`);
const ages=dedup.map(x=>(Date.now()-Number(x.barTimestamp))/1000).filter(Number.isFinite);const medianAgeSeconds=median(ages);
const envelope={
  schemaVersion:1,provider:'YAHOO',plan:'FREE',costUsd:0,sessionDate,mode:'intraday5m',observedAt:new Date().toISOString(),
  freshRealtime:false,researchIntraday5m:true,formalFreshEligible:false,feedClassification:'FREE_INTRADAY_5M_DIAGNOSTIC',
  sourceContract:'UNVERIFIED_PUBLIC_BATCH_ENDPOINT_RUNTIME_VALIDATED',universeStatus:u.status,inputSymbols:symbols.length,rows:dedup,coveragePct,medianAgeSeconds,
  errors,rawDigest:digest(dedup),noPaidFallback:true,noBrokerDependency:true,
  classification:{partialAllowed:true,fullFresh:false,jpxOosSubstitute:false,formalOos:false,promotionEligible:false},
  safety:PHASE57_US_CROSS_MARKET_SAFETY,
};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(envelope,null,2)+'\n');
console.log(JSON.stringify({provider:envelope.provider,mode:envelope.mode,inputSymbols:symbols.length,rows:dedup.length,coveragePct:Number(coveragePct.toFixed(2)),medianAgeSeconds:Number(medianAgeSeconds.toFixed(1)),errors:errors.length,output},null,2));
