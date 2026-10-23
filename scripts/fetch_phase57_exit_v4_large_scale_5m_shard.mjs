import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fetchP252Yahoo5mSession} from '../predict/daytrade/phase57-p25-2j-routine-nonrss-5m-source.js';
import {PHASE57_EXIT_V4_LARGE_SCALE_SAFETY} from '../predict/daytrade/phase57-exit-v4-large-scale.js';

const arg=(name,fallback)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const manifestPath=arg('--manifest','tmp/phase57-exit-v4-large-scale-universe.json');
const tier=arg('--tier','pilot');
const dates=arg('--dates','2026-09-01,2026-09-02,2026-09-03,2026-09-04').split(',').map(x=>x.trim()).filter(Boolean);
const shardIndex=Number(arg('--shard-index','0'));
const shardCount=Number(arg('--shard-count','10'));
const concurrency=Math.max(1,Math.min(8,Number(arg('--concurrency','4'))));
const output=arg('--output',`tmp/phase57-exit-v4-${tier}-shard-${shardIndex}.json`);
if(!Number.isInteger(shardIndex)||!Number.isInteger(shardCount)||shardIndex<0||shardCount<1||shardIndex>=shardCount)throw new Error('invalid shard index/count');
if(!dates.length||dates.some(x=>!/^\d{4}-\d{2}-\d{2}$/.test(x)))throw new Error('dates must be comma-separated YYYY-MM-DD values');
const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
const selected=manifest?.[tier];
if(!Array.isArray(selected))throw new Error(`manifest tier missing: ${tier}`);
const symbols=selected.filter((_,index)=>index%shardCount===shardIndex);
const tasks=symbols.flatMap(meta=>dates.map(sessionDate=>({meta,sessionDate})));
const sessions=[],failures=[];
let cursor=0;
async function worker(){
  while(cursor<tasks.length){
    const task=tasks[cursor++];
    try{
      const result=await fetchP252Yahoo5mSession({symbol:task.meta.symbol,sessionDate:task.sessionDate});
      sessions.push({symbol:task.meta.symbol,sessionDate:task.sessionDate,market:task.meta.market,sector:task.meta.sector,provider:result.provider,bars:result.bars,sourceQuality:result.sourceQuality,requestHost:result.requestHost,sourcePayloadSha256:result.sourcePayloadSha256});
    }catch(error){failures.push({symbol:task.meta.symbol,sessionDate:task.sessionDate,status:'BLOCKED_SOURCE_SESSION',reason:String(error?.message??error)});}
  }
}
await Promise.all(Array.from({length:Math.min(concurrency,tasks.length||1)},()=>worker()));
sessions.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.symbol.localeCompare(b.symbol));
failures.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.symbol.localeCompare(b.symbol));
const sha=value=>crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
const payload={schemaVersion:1,phase:'57.exit-v4.large-scale.source-shard',status:failures.length?'SOURCE_SHARD_PARTIAL':'SOURCE_SHARD_READY',tier,manifestSha256:manifest.manifestSha256,shardIndex,shardCount,dates,symbolCount:symbols.length,expectedSessionCount:tasks.length,sessionCount:sessions.length,failureCount:failures.length,sessions,failures,methodology:{provider:'YAHOO_FINANCE_CHART_5M',readOnly:true,failedSessionsNeverFabricated:true,fullSessionFetchedAfterClose:true,historicalReconstruction:true,formalOosEvidence:false},safety:PHASE57_EXIT_V4_LARGE_SCALE_SAFETY};
payload.payloadSha256=sha(payload);
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,`${JSON.stringify(payload,null,2)}\n`);
console.log(JSON.stringify({status:payload.status,output,shardIndex,shardCount,symbolCount:payload.symbolCount,sessionCount:payload.sessionCount,failureCount:payload.failureCount,payloadSha256:payload.payloadSha256,safety:payload.safety},null,2));
