import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fetchJquantsPages} from '../predict/long-only/phase57-long-only-jquants-client.js';
import {assertV2PreFitContract,V2_DEVELOPMENT} from '../predict/long-only/phase57-long-only-v2-contract.js';

const arg=name=>{const index=process.argv.indexOf(name);return index<0?null:process.argv[index+1];};
const cacheRoot=path.resolve(arg('--cache-root')??'');
const maximumRequests=Number(arg('--maximum-requests')??150);
const shardIndex=Number(arg('--shard-index'));
const shardCount=Number(arg('--shard-count'));
const summaryPath=path.resolve(arg('--summary')??path.join(cacheRoot,'v2-minute-acquisition-summary.json'));
if(!cacheRoot||!Number.isInteger(maximumRequests)||maximumRequests<1||maximumRequests>150)throw new Error('v2 acquisition requires --cache-root and per-shard ceiling <=150');
if(!Number.isInteger(shardIndex)||shardCount!==2||shardIndex<0||shardIndex>=2)throw new Error('v2 acquisition requires one of two fixed ten-session shards');
const apiKey=process.env.JQUANTS_API_KEY;if(!apiKey)throw new Error('JQUANTS_API_KEY is unavailable');
const read=url=>JSON.parse(fs.readFileSync(url,'utf8'));
const allocation=read(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url));
const l1=read(new URL('../predict/long-only/phase57-long-only-l1-discovery-sessions.json',import.meta.url));
const l2=read(new URL('../predict/long-only/phase57-long-only-l2-development-sessions.json',import.meta.url));
assertV2PreFitContract({allocation,l1Contract:l1,l2Contract:l2});
const selected=V2_DEVELOPMENT.sessions.slice(shardIndex*10,(shardIndex+1)*10);
if(selected.length!==10)throw new Error('v2 shard must contain exactly ten sessions');
const partitionFor=sessionDate=>allocation.partitions.DEVELOPMENT_A.includes(sessionDate)?'DEVELOPMENT_A':'DEVELOPMENT_B';
const requestBudget={remaining:maximumRequests,consumed:0};
const sha=value=>createHash('sha256').update(value).digest('hex');
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2');
const completed=[],unavailable=[];

for(const sessionDate of [...selected].reverse()){
  const partition=partitionFor(sessionDate),sessionDir=path.join(base,sessionDate),l0ManifestPath=path.join(sessionDir,'l0-manifest.json');
  if(!fs.existsSync(l0ManifestPath))throw new Error(`approved Daily/Master cache is missing: ${sessionDate}`);
  const l0Manifest=JSON.parse(fs.readFileSync(l0ManifestPath,'utf8'));
  if(l0Manifest.sessionDate!==sessionDate||l0Manifest.partition!==partition)throw new Error(`Daily/Master cache identity mismatch: ${sessionDate}`);
  const pagesPath=path.join(sessionDir,'minute-pages.json'),manifestPath=path.join(sessionDir,'v2-minute-manifest.json');
  if(fs.existsSync(pagesPath)||fs.existsSync(manifestPath))throw new Error(`pre-existing Minute cache violates unseen v2 contract: ${sessionDate}`);
  let result;
  try{result=await fetchJquantsPages({endpoint:'/equities/bars/minute',query:{date:sessionDate},apiKey,requestBudget,maxPages:100});}
  catch(error){
    if(/HTTP 400/.test(String(error?.message))){unavailable.push({sessionDate,partition,reason:'HTTP_400_SOURCE_UNAVAILABLE',requestConsumedInThisRun:true});continue;}
    throw error;
  }
  fs.writeFileSync(pagesPath,`${JSON.stringify(result.pages)}\n`,{flag:'wx',mode:0o600});
  const rowCount=result.pages.reduce((sum,page)=>sum+(JSON.parse(page.responseText).data?.length??0),0);
  const manifest={schemaVersion:1,mode:'CANDIDATE_V2_FIXED_20_FULL_CROSS_SECTION',partition,sessionDate,sessionListSha256:V2_DEVELOPMENT.sessionListSha256,endpoint:result.endpoint,query:result.normalizedQuery,pageCount:result.pageCount,rowCount,aggregateSha256:result.aggregateSha256,minuteOnly:true,fetchedAt:new Date().toISOString()};
  manifest.manifestSha256=sha(JSON.stringify(manifest));
  fs.writeFileSync(manifestPath,`${JSON.stringify(manifest,null,2)}\n`,{flag:'wx',mode:0o600});
  completed.push({sessionDate,partition,pageCount:result.pageCount,rowCount,reused:false});
  console.log(JSON.stringify({sessionDate,partition,status:'V2_MINUTE_CACHED',pageCount:result.pageCount,rowCount,requestCount:requestBudget.consumed}));
}
completed.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));unavailable.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));
const summary={status:unavailable.length?'V2_MINUTE_ACQUISITION_PARTIAL':'V2_MINUTE_ACQUISITION_COMPLETE',approvedSessions:20,selectedSessions:selected.length,shardIndex,shardCount:2,completedSessions:completed.length,unavailableSessions:unavailable.length,sessionListSha256:V2_DEVELOPMENT.sessionListSha256,providerRequestsConsumedThisRun:requestBudget.consumed,providerRequestHardCeiling:maximumRequests,providerRequestsUnused:requestBudget.remaining,totalPages:completed.reduce((sum,x)=>sum+x.pageCount,0),totalRows:completed.reduce((sum,x)=>sum+x.rowCount,0),completed,unavailable,validationOpened:false,oosOpened:false};
fs.writeFileSync(summaryPath,`${JSON.stringify(summary,null,2)}\n`,{flag:'wx',mode:0o600});
console.log(JSON.stringify({...summary,completed:undefined}));
if(unavailable.length)process.exitCode=2;
