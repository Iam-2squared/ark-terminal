import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fetchJquantsPages} from '../predict/long-only/phase57-long-only-jquants-client.js';

const arg=name=>{const index=process.argv.indexOf(name);return index<0?null:process.argv[index+1];};
const cacheRoot=path.resolve(arg('--cache-root')??'');
const maximumRequests=Number(arg('--maximum-requests')??550);
const shardIndex=arg('--shard-index')===null?null:Number(arg('--shard-index'));
const shardCount=arg('--shard-count')===null?null:Number(arg('--shard-count'));
const summaryPath=path.resolve(arg('--summary')??path.join(cacheRoot,'l1-minute-acquisition-summary.json'));
if(!cacheRoot||!Number.isInteger(maximumRequests)||maximumRequests<1)throw new Error('L1 acquisition requires --cache-root and a positive request ceiling');
const apiKey=process.env.JQUANTS_API_KEY;if(!apiKey)throw new Error('JQUANTS_API_KEY is unavailable');
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const partitions=['DEVELOPMENT_A','DEVELOPMENT_B'];
const approvedSessions=partitions.flatMap(partition=>allocation.partitions[partition].map(sessionDate=>({partition,sessionDate})));
const approvedSessionHash='6bc10cf3f55eb4cfcf0e5ffec65d2ccb50a633ca19c88c94a2f78c981945c2cd';
const actualSessionHash=createHash('sha256').update(JSON.stringify(approvedSessions.map(x=>x.sessionDate))).digest('hex');
if(approvedSessions.length!==40||actualSessionHash!==approvedSessionHash)throw new Error('Development A+B session list differs from operator approval');
const sharded=shardIndex!==null||shardCount!==null;
if(sharded&&(!Number.isInteger(shardIndex)||!Number.isInteger(shardCount)||shardCount!==4||shardIndex<0||shardIndex>=shardCount))throw new Error('checkpointed retry requires one of four fixed shards');
if(!sharded&&maximumRequests!==550)throw new Error('unsharded approved L1 acquisition requires --maximum-requests 550');
// Newest-first prevents an expired rolling-window boundary from blocking dates
// that remain available. 2024-09-10 already returned HTTP 400 in run
// 34920375454 and is not requested twice.
const selectedSessions=sharded?approvedSessions.filter((_,index)=>Math.floor(index/10)===shardIndex):approvedSessions;
if(sharded&&selectedSessions.length!==10)throw new Error('fixed retry shard must contain exactly ten approved sessions');
const sessions=[...selectedSessions].reverse();
const priorUnavailable=new Map([['2024-09-10','HTTP_400_RUN_34920375454']]);
const requestBudget={remaining:maximumRequests,consumed:0};
const sha=value=>createHash('sha256').update(value).digest('hex');
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2');

const completed=[],unavailable=[];
for(const {partition,sessionDate} of sessions){
  const sessionDir=path.join(base,sessionDate),l0ManifestPath=path.join(sessionDir,'l0-manifest.json');
  if(!fs.existsSync(l0ManifestPath))throw new Error(`approved Daily/Master cache is missing: ${sessionDate}`);
  const l0Manifest=JSON.parse(fs.readFileSync(l0ManifestPath,'utf8'));
  if(l0Manifest.sessionDate!==sessionDate||l0Manifest.partition!==partition)throw new Error(`Daily/Master cache identity mismatch: ${sessionDate}`);
  const pagesPath=path.join(sessionDir,'minute-pages.json'),manifestPath=path.join(sessionDir,'l1-minute-manifest.json');
  if(fs.existsSync(manifestPath)){
    const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8')),pages=JSON.parse(fs.readFileSync(pagesPath,'utf8'));
    if(manifest.sessionDate!==sessionDate||manifest.partition!==partition||manifest.sessionListSha256!==approvedSessionHash)throw new Error(`immutable Minute identity mismatch: ${sessionDate}`);
    if(pages.length!==manifest.pageCount||pages.some(page=>sha(page.responseText)!==page.responseSha256))throw new Error(`immutable Minute page verification failed: ${sessionDate}`);
    console.log(JSON.stringify({sessionDate,partition,status:'IMMUTABLE_MINUTE_REUSED',pageCount:pages.length}));
    completed.push({sessionDate,partition,pageCount:pages.length,rowCount:manifest.rowCount,reused:true});continue;
  }
  if(priorUnavailable.has(sessionDate)){unavailable.push({sessionDate,partition,reason:priorUnavailable.get(sessionDate),requestConsumedInPriorRun:true});continue;}
  if(fs.existsSync(pagesPath))throw new Error(`incomplete Minute cache requires quarantine: ${sessionDate}`);
  let result;
  try{result=await fetchJquantsPages({endpoint:'/equities/bars/minute',query:{date:sessionDate},apiKey,requestBudget,maxPages:100});}
  catch(error){
    if(/HTTP 400/.test(String(error?.message))){unavailable.push({sessionDate,partition,reason:'HTTP_400_SOURCE_UNAVAILABLE',requestConsumedInThisRun:true});continue;}
    throw error;
  }
  fs.writeFileSync(pagesPath,`${JSON.stringify(result.pages)}\n`,{flag:'wx',mode:0o600});
  const rowCount=result.pages.reduce((sum,page)=>sum+(JSON.parse(page.responseText).data?.length??0),0);
  const manifest={schemaVersion:1,mode:'L1_DEVELOPMENT_A_B_FULL_CROSS_SECTION',partition,sessionDate,sessionListSha256:approvedSessionHash,endpoint:result.endpoint,query:result.normalizedQuery,pageCount:result.pageCount,rowCount,aggregateSha256:result.aggregateSha256,minuteOnly:true,fetchedAt:new Date().toISOString()};
  manifest.manifestSha256=sha(JSON.stringify(manifest));
  fs.writeFileSync(manifestPath,`${JSON.stringify(manifest,null,2)}\n`,{flag:'wx',mode:0o600});
  completed.push({sessionDate,partition,pageCount:result.pageCount,rowCount,reused:false});
  console.log(JSON.stringify({sessionDate,partition,status:'L1_MINUTE_CACHED',pageCount:result.pageCount,rowCount,requestCount:requestBudget.consumed}));
}
completed.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));unavailable.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));
const summary={status:unavailable.length?'L1_MINUTE_ACQUISITION_PARTIAL':'L1_MINUTE_ACQUISITION_COMPLETE',approvedSessions:40,selectedSessions:selectedSessions.length,shardIndex,shardCount:sharded?shardCount:1,completedSessions:completed.length,unavailableSessions:unavailable.length,sessionListSha256:approvedSessionHash,providerRequestsConsumedThisRun:requestBudget.consumed,providerRequestHardCeiling:maximumRequests,providerRequestsUnused:requestBudget.remaining,totalPages:completed.reduce((sum,x)=>sum+x.pageCount,0),totalRows:completed.reduce((sum,x)=>sum+x.rowCount,0),completed,unavailable,validationOpened:false,oosOpened:false};
fs.writeFileSync(summaryPath,`${JSON.stringify(summary,null,2)}\n`,{flag:'wx',mode:0o600});
console.log(JSON.stringify({...summary,completed:undefined}));
if(unavailable.length)process.exitCode=2;
