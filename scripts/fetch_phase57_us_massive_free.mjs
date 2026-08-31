import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const mode=arg('--mode');
const output=arg('--output',mode==='listings'?'tmp/us-listings.json':'tmp/us-snapshot.json');
const universePath=arg('--universe');
const sessionDate=arg('--session-date');
const apiKey=process.env.MASSIVE_API_KEY;
if(!apiKey)throw new Error('MASSIVE_API_KEY missing: fail-closed; no fallback provider');
if(!['listings','snapshot'].includes(mode))throw new Error('usage: --mode listings|snapshot [--universe file] --session-date YYYY-MM-DD');
if(!sessionDate)throw new Error('--session-date required');
const base='https://api.polygon.io';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const digest=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');
let lastRequestAt=0;
async function get(url){
  const wait=Math.max(0,12500-(Date.now()-lastRequestAt)); if(wait)await sleep(wait);
  lastRequestAt=Date.now();
  const u=new URL(url);u.searchParams.set('apiKey',apiKey);
  const r=await fetch(u,{headers:{'User-Agent':'ark-terminal-phase57-research'}});
  if(!r.ok)throw new Error(`Massive HTTP ${r.status}: fail-closed`);
  const j=await r.json();if(j.status==='ERROR')throw new Error(`Massive error ${j.error??j.message??'unknown'}`);return j;
}
async function listings(){
  // Free plan friendly: reference pagination is intentionally throttled below 5 req/min.
  let url=`${base}/v3/reference/tickers?market=stocks&active=true&limit=1000&sort=ticker&order=asc`;
  const out=[];
  while(url){const j=await get(url);for(const x of j.results??[]){
    const type=String(x.type??'').toUpperCase();
    if(!['CS','COMMON_STOCK'].includes(type))continue;
    out.push({symbol:x.ticker,exchange:x.primary_exchange,currency:String(x.currency_name??'USD').toUpperCase(),securityType:'COMMON_STOCK',active:x.active===true,provider:'MASSIVE_FREE_REFERENCE'});
  } url=j.next_url??null;}
  if(out.length<500)throw new Error(`Massive listings incomplete ${out.length}`);
  return out;
}
async function snapshot(){
  if(!universePath)throw new Error('--universe required for snapshot');
  const u=JSON.parse(fs.readFileSync(universePath,'utf8'));
  if(u.status!=='US_UNIVERSE_FROZEN')throw new Error('universe not frozen');
  // Massive Free is EOD, not real-time. We only use completed aggregate bars and label them FREE_DELAYED_RESEARCH.
  // Five calls/min cannot support one request per ticker, so batch by ticker list only if the endpoint accepts it;
  // otherwise fail closed rather than silently degrade to a partial market.
  const symbols=u.universe.map(x=>x.symbol);
  const rows=[];
  for(let i=0;i<symbols.length;i+=50){
    const batch=symbols.slice(i,i+50);
    const url=`${base}/v2/aggs/grouped/locale/us/market/stocks/${sessionDate}?adjusted=false`;
    if(i>0)break; // grouped daily endpoint is a single market-wide call; never repeat it per batch.
    const j=await get(url);
    const wanted=new Set(symbols);
    for(const x of j.results??[]){if(!wanted.has(x.T))continue;rows.push({symbol:x.T,currentPrice:Number(x.c),volume:Number(x.v??0),dollarVolume:Number(x.c)*Number(x.v??0),changePct:0,volumeRatio:1,barTimestamp:x.t,provider:'MASSIVE_FREE_GROUPED_EOD'});}
  }
  if(rows.length<Math.min(500,Math.floor(symbols.length*0.8)))throw new Error(`Massive Free cannot provide required marketwide coverage for ${sessionDate}: ${rows.length}/${symbols.length}`);
  return rows;
}
const data=mode==='listings'?await listings():await snapshot();
const envelope={provider:'MASSIVE',plan:'FREE',costUsd:0,sessionDate,mode,observedAt:new Date().toISOString(),freshRealtime:false,feedClassification:mode==='snapshot'?'EOD_ONLY':'REFERENCE',noPaidFallback:true,noIexSubstitution:true,rawDigest:digest(data),rows:data};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(envelope,null,2)+'\n');
console.log(JSON.stringify({provider:envelope.provider,plan:'FREE',mode,count:data.length,freshRealtime:false,output},null,2));
