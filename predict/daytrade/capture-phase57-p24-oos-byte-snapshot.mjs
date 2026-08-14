import fs from 'node:fs';
import crypto from 'node:crypto';

const dataEndIso=process.env.PHASE57_DATA_END||'2026-08-12T06:30:00.000Z';
const dataEndUnix=Math.floor(Date.parse(dataEndIso)/1000);
if(!Number.isFinite(dataEndUnix))throw Error('invalid PHASE57_DATA_END');
const symbols=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const responses={};
for(const symbol of symbols){
  const d=86400;
  for(const [p1,p2] of [[dataEndUnix-58*d,dataEndUnix-29*d],[dataEndUnix-29*d,dataEndUnix]]){
    const qs=`period1=${p1}&period2=${p2}&interval=5m&includePrePost=false&events=div%2Csplits`;
    let windowHasSuccess=false;
    for(const host of [1,2]){
      const url=`https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${qs}`;
      let captured=null,last=null;
      for(let a=1;a<=4;a++){
        try{
          const c=new AbortController(),t=setTimeout(()=>c.abort(),30000);
          const res=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0',Accept:'application/json'},signal:c.signal});
          clearTimeout(t);
          captured={status:res.status,statusText:res.statusText,headers:Object.fromEntries(res.headers.entries()),body:await res.text()};
          last=null;
          break;
        }catch(e){last=e;if(a<4)await sleep(a*1000);}
      }
      if(last||!captured)throw last||Error(`${symbol} provider capture failed`);
      responses[url]=captured;
      if(captured.status>=200&&captured.status<300)windowHasSuccess=true;
      await sleep(180);
    }
    if(!windowHasSuccess)throw Error(`${symbol} Yahoo window unavailable from both query hosts`);
  }
}
const snapshot={phase:'57.p24.9-oos-byte-snapshot',purpose:'pre-performance canonical OOS provider capture; no model or trade metrics computed during capture',dataEndIso,symbols,responseCount:Object.keys(responses).length,responses,methodology:{performanceObservedBeforeFreeze:false,providerFallbackBytesPreserved:true,parameterSweep:false,postHocSymbolFiltering:false,entryRetuning:false,freshHoldoutConsumed:false},safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false}};
const body=JSON.stringify(snapshot);
fs.mkdirSync('artifacts',{recursive:true});
const output=process.env.P24_9_SNAPSHOT_PATH||'artifacts/phase57-p24-9-oos-byte-snapshot.json';
fs.writeFileSync(output,body);
console.log(JSON.stringify({phase:snapshot.phase,dataEndIso,symbols,responseCount:snapshot.responseCount,snapshotSha256:crypto.createHash('sha256').update(body).digest('hex'),performanceMetricsComputed:false,methodology:snapshot.methodology,safety:snapshot.safety},null,2));