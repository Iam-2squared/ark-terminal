import fs from 'node:fs';
import crypto from 'node:crypto';

const snapshotPath=process.env.P24_9_SNAPSHOT_PATH;
const target=process.env.P24_9_TARGET;
if(!snapshotPath||!target)throw Error('P24_9_SNAPSHOT_PATH and P24_9_TARGET required');
const bytes=fs.readFileSync(snapshotPath);
const snapshot=JSON.parse(bytes);
if(!snapshot.responses||typeof snapshot.responses!=='object')throw Error('invalid P24.9 snapshot');
let replayRequests=0;
globalThis.fetch=async(url)=>{
  replayRequests++;
  const r=snapshot.responses[String(url)];
  if(!r)throw Error(`P24.9 snapshot miss: ${url}`);
  return new Response(r.body,{status:r.status,statusText:r.statusText,headers:r.headers});
};
await import(new URL(target,import.meta.url));
console.log(JSON.stringify({phase:'57.p24.9-replay',snapshotPath,snapshotSha256:crypto.createHash('sha256').update(bytes).digest('hex'),responseCount:Object.keys(snapshot.responses).length,replayRequests,networkAccessAllowed:false,freshHoldoutConsumed:false,safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false}},null,2));
