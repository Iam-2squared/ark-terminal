import fs from 'node:fs';
import crypto from 'node:crypto';

const mode=process.env.P23_46_MODE??'capture';
const snapshotPath=process.env.P23_46_SNAPSHOT_PATH??'artifacts/phase57-p23-46-byte-snapshot.json';
const resultCopy=process.env.P23_46_RESULT_COPY??`artifacts/phase57-p23-46-${mode}-result.json`;
const benchmarkPath='artifacts/phase57-p23-42-frozen-development-benchmark.json';
fs.mkdirSync('artifacts',{recursive:true});
const records={};
let replayRequests=0;
if(mode==='capture'){
  const nativeFetch=globalThis.fetch;
  globalThis.fetch=async(url,opts)=>{
    const res=await nativeFetch(url,opts);
    const clone=res.clone();
    records[String(url)]={status:res.status,statusText:res.statusText,headers:Object.fromEntries(clone.headers.entries()),body:await clone.text()};
    return res;
  };
}else if(mode==='replay'){
  const snap=JSON.parse(fs.readFileSync(snapshotPath,'utf8'));
  if(snap.phase!=='57.p23.46-byte-snapshot'||!snap.responses)throw Error('invalid P23.46 snapshot');
  globalThis.fetch=async(url)=>{
    replayRequests++;
    const r=snap.responses[String(url)];
    if(!r)throw Error(`snapshot miss: ${url}`);
    return new Response(r.body,{status:r.status,statusText:r.statusText,headers:r.headers});
  };
}else throw Error(`unsupported P23_46_MODE=${mode}`);

await import(`./run-phase57-p23-42-frozen-development-benchmark.mjs?mode=${mode}&t=${Date.now()}`);
if(!fs.existsSync(benchmarkPath))throw Error('benchmark output missing');
const resultBytes=fs.readFileSync(benchmarkPath);
fs.copyFileSync(benchmarkPath,resultCopy);
if(mode==='capture'){
  const snapshot={phase:'57.p23.46-byte-snapshot',source:'Yahoo Finance chart 5m responses captured before replay',responses:records,responseCount:Object.keys(records).length,freshUntouchedHoldoutConsumed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false};
  const body=JSON.stringify(snapshot);
  fs.writeFileSync(snapshotPath,body);
  console.log(JSON.stringify({phase:'57.p23.46',mode,snapshotSha256:crypto.createHash('sha256').update(body).digest('hex'),resultSha256:crypto.createHash('sha256').update(resultBytes).digest('hex'),responseCount:snapshot.responseCount},null,2));
}else{
  console.log(JSON.stringify({phase:'57.p23.46',mode,snapshotSha256:crypto.createHash('sha256').update(fs.readFileSync(snapshotPath)).digest('hex'),resultSha256:crypto.createHash('sha256').update(resultBytes).digest('hex'),replayRequests,networkAccessAllowed:false},null,2));
}
