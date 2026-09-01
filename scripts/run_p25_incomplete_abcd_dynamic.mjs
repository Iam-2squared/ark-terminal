import fs from 'node:fs';
import path from 'node:path';
import {spawn,spawnSync} from 'node:child_process';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const partialDir=arg('--partial-dir'),historyPath=arg('--history-pack'),barsPath=arg('--bars'),output=arg('--output');
if(!partialDir||!historyPath||!barsPath||!output)throw new Error('usage: --partial-dir <dir> --history-pack <json> --bars <json> --output <json>');
const safety={executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false};
const outDir=path.dirname(output),shardDir=path.join(outDir,'dynamic-point-shards');fs.mkdirSync(shardDir,{recursive:true});
const shardCount=10;
function runShard(shardIndex){return new Promise((resolve,reject)=>{
  const shardOutput=path.join(shardDir,`dynamic-shard-${shardIndex}.json`);
  const child=spawn(process.execPath,['scripts/run_p25_incomplete_abcd_dynamic_point_shard.mjs','--partial-dir',partialDir,'--history-pack',historyPath,'--bars',barsPath,'--output',shardOutput,'--shard-index',String(shardIndex),'--shard-count',String(shardCount)],{stdio:['ignore','pipe','pipe']});
  let stdout='',stderr='';
  child.stdout.on('data',d=>{stdout+=String(d);process.stdout.write(d);});
  child.stderr.on('data',d=>{stderr+=String(d);process.stderr.write(d);});
  const timer=setTimeout(()=>{child.kill('SIGKILL');reject(new Error(`dynamic point shard ${shardIndex} timed out after 11m`));},11*60*1000);
  child.on('error',error=>{clearTimeout(timer);reject(error);});
  child.on('close',code=>{clearTimeout(timer);if(code===0)resolve();else reject(new Error(`dynamic point shard ${shardIndex} failed code=${code}: ${stderr||stdout}`));});
});}
await Promise.all(Array.from({length:shardCount},(_,i)=>runShard(i)));
const combine=spawnSync(process.execPath,['scripts/combine_p25_incomplete_abcd_dynamic_point_shards.mjs','--partial-dir',partialDir,'--bars',barsPath,'--shard-dir',shardDir,'--output',output],{encoding:'utf8',stdio:['ignore','pipe','pipe'],timeout:2*60*1000,killSignal:'SIGKILL'});
process.stdout.write(combine.stdout??'');process.stderr.write(combine.stderr??'');
if(combine.error)throw combine.error;if(combine.status!==0)throw new Error(`dynamic shard recombine failed: ${combine.stderr||combine.stdout}`);
const payload=JSON.parse(fs.readFileSync(output,'utf8'));
for(const k of Object.keys(safety))if(payload.safety?.[k]!==false)throw new Error(`unsafe ${k}`);
console.log(JSON.stringify({status:payload.status,pointShardCount:shardCount,B:payload.B?.summary,D:Object.fromEntries(Object.entries(payload.D?.profiles??{}).map(([k,v])=>[k,{totalReturnPct:v.return?.totalReturnPct,maxDrawdownPct:v.risk?.maxDrawdownPct}]))},null,2));
