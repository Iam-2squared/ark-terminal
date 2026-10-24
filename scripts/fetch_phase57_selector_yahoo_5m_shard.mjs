import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fetchYahooChart5m,PHASE57_SELECTOR_YAHOO_SAFETY} from './lib/phase57-selector-yahoo-5m.mjs';

function arg(name,fallback=null){
  const index=process.argv.indexOf(name);
  return index>=0&&index+1<process.argv.length?process.argv[index+1]:fallback;
}
const universePath=arg('--universe','data/screener-universe.json');
const output=arg('--output','artifacts/phase57-selector-yahoo-5m-shard.json');
const start=Number(arg('--start','0'));
const count=Number(arg('--count','50'));
const range=arg('--range','60d');
const concurrency=Number(arg('--concurrency','2'));
const delayMs=Number(arg('--delay-ms','250'));
const sampleSeed=arg('--sample-seed','PHASE57_SELECTOR_V3_0_20260905');
if(!Number.isInteger(start)||start<0||!Number.isInteger(count)||count<1||!Number.isInteger(concurrency)||concurrency<1){
  throw new Error('start/count/concurrency arguments are invalid');
}
const universePayload=JSON.parse(fs.readFileSync(universePath,'utf8'));
const universe=(Array.isArray(universePayload)?universePayload:universePayload.entries??[])
  .map(item=>({symbol:String(item.symbol??'').trim().toUpperCase(),sector:item.sector??'UNKNOWN',market:item.market??null}))
  .filter(item=>item.symbol);
const sampleKey=symbol=>createHash('sha256').update(`${sampleSeed}|${symbol}`).digest('hex');
const sampledUniverse=[...universe].sort((a,b)=>sampleKey(a.symbol).localeCompare(sampleKey(b.symbol))||a.symbol.localeCompare(b.symbol));
const requested=sampledUniverse.slice(start,start+count);
if(!requested.length)throw new Error(`empty universe shard at start=${start} count=${count}`);
const results=new Array(requested.length);
let cursor=0;
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function worker(){
  while(true){
    const index=cursor++;
    if(index>=requested.length)return;
    const item=requested[index];
    try{
      const value=await fetchYahooChart5m({...item,range});
      results[index]={status:'READY',...value};
    }catch(error){
      results[index]={status:'FAILED',symbol:item.symbol,sector:item.sector,market:item.market,error:String(error?.message??error)};
    }
    if(delayMs>0)await sleep(delayMs);
  }
}
await Promise.all(Array.from({length:Math.min(concurrency,requested.length)},()=>worker()));
const ready=results.filter(item=>item.status==='READY');
const failed=results.filter(item=>item.status==='FAILED');
const minimumReady=Math.max(1,Math.floor(requested.length*0.6));
const payload={
  schemaVersion:1,phase:'57.selector-v3.yahoo-5m-shard',
  status:ready.length>=minimumReady?'SELECTOR_YAHOO_5M_SHARD_READY':'SELECTOR_YAHOO_5M_SHARD_INCOMPLETE',
  provider:'YAHOO_FINANCE_CHART',fetchedAt:new Date().toISOString(),range,interval:'5m',
  universe:{
    path:universePath,sourceDate:universePayload?.meta?.sourceDate??null,start,count,requested:requested.length,
    totalSymbols:universe.length,sampling:'DETERMINISTIC_SHA256_WITHOUT_REPLACEMENT',sampleSeed,
  },
  readyCount:ready.length,failedCount:failed.length,symbols:ready,failures:failed,
  methodology:{
    laterFetchedHistoricalReconstruction:true,exactTradingViewReplay:false,
    historicalUniversePointInTime:false,survivorshipLimited:true,
    barTimestampMeaning:'BAR_OPEN',availableAtDerivedByAddingFiveMinutes:true,
    providerTermsMustBeVerifiedByOperatorBeforeScale:true,
    deterministicMarketwideSampling:true,
  },
  safety:PHASE57_SELECTOR_YAHOO_SAFETY,
};
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,output,requested:requested.length,ready:ready.length,failed:failed.length},null,2));
if(payload.status!=='SELECTOR_YAHOO_5M_SHARD_READY')process.exitCode=1;
