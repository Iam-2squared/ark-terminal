import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fetchJquantsPages} from '../predict/long-only/phase57-long-only-jquants-client.js';

const arg=name=>{const index=process.argv.indexOf(name);return index<0?null:process.argv[index+1];};
const cacheRoot=path.resolve(arg('--cache-root')??'');
const maximumRequests=Number(arg('--maximum-requests')??150);
const shardIndex=Number(arg('--shard-index'));
const shardCount=Number(arg('--shard-count'));
const summaryPath=path.resolve(arg('--summary')??path.join(cacheRoot,'l2-minute-acquisition-summary.json'));
if(!cacheRoot||!Number.isInteger(maximumRequests)||maximumRequests<1)throw new Error('L2 acquisition requires --cache-root and a positive request ceiling');
if(!Number.isInteger(shardIndex)||!Number.isInteger(shardCount)||shardCount!==4||shardIndex<0||shardIndex>=shardCount)throw new Error('L2 acquisition requires one of four fixed ten-session shards');
const apiKey=process.env.JQUANTS_API_KEY;if(!apiKey)throw new Error('JQUANTS_API_KEY is unavailable');
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const contract=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-l2-development-sessions.json',import.meta.url),'utf8'));
const expected=[...allocation.partitions.DEVELOPMENT_C,...allocation.partitions.DEVELOPMENT_D];
const hash=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
if(contract.selectionRule!=='FROZEN_DEVELOPMENT_C_THEN_DEVELOPMENT_D_FROM_ALLOCATION_V3'||contract.selectionUsedMinuteOutcomes!==false)throw new Error('L2 session selection is not frozen');
if(expected.length!==40||JSON.stringify(contract.sessions)!==JSON.stringify(expected)||hash(expected)!==contract.sessionListSha256)throw new Error('L2 session list differs from operator approval');
if(hash(allocation.partitions.DEVELOPMENT_C)!==contract.developmentCSessionListSha256||hash(allocation.partitions.DEVELOPMENT_D)!==contract.developmentDSessionListSha256)throw new Error('L2 partition hash mismatch');
const selected=expected.slice(shardIndex*10,(shardIndex+1)*10);
if(selected.length!==10)throw new Error('L2 shard must contain exactly ten sessions');
const partitionFor=sessionDate=>allocation.partitions.DEVELOPMENT_C.includes(sessionDate)?'DEVELOPMENT_C':'DEVELOPMENT_D';
const sessions=[...selected].reverse().map(sessionDate=>({sessionDate,partition:partitionFor(sessionDate)}));
const requestBudget={remaining:maximumRequests,consumed:0};
const sha=value=>createHash('sha256').update(value).digest('hex');
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2');
const completed=[],unavailable=[];

for(const {partition,sessionDate} of sessions){
  const sessionDir=path.join(base,sessionDate),l0ManifestPath=path.join(sessionDir,'l0-manifest.json');
  if(!fs.existsSync(l0ManifestPath))throw new Error(`approved Daily/Master cache is missing: ${sessionDate}`);
  const l0Manifest=JSON.parse(fs.readFileSync(l0ManifestPath,'utf8'));
  if(l0Manifest.sessionDate!==sessionDate||l0Manifest.partition!==partition)throw new Error(`Daily/Master cache identity mismatch: ${sessionDate}`);
  const pagesPath=path.join(sessionDir,'minute-pages.json'),manifestPath=path.join(sessionDir,'l2-minute-manifest.json');
  if(fs.existsSync(manifestPath)){
    const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8')),pages=JSON.parse(fs.readFileSync(pagesPath,'utf8'));
    if(manifest.sessionDate!==sessionDate||manifest.partition!==partition||manifest.sessionListSha256!==contract.sessionListSha256)throw new Error(`immutable L2 Minute identity mismatch: ${sessionDate}`);
    if(pages.length!==manifest.pageCount||pages.some(page=>sha(page.responseText)!==page.responseSha256))throw new Error(`immutable L2 Minute page verification failed: ${sessionDate}`);
    completed.push({sessionDate,partition,pageCount:pages.length,rowCount:manifest.rowCount,reused:true});
    continue;
  }
  if(fs.existsSync(pagesPath))throw new Error(`incomplete Minute cache requires quarantine: ${sessionDate}`);
  let result;
  try{result=await fetchJquantsPages({endpoint:'/equities/bars/minute',query:{date:sessionDate},apiKey,requestBudget,maxPages:100});}
  catch(error){
    if(/HTTP 400/.test(String(error?.message))){unavailable.push({sessionDate,partition,reason:'HTTP_400_SOURCE_UNAVAILABLE',requestConsumedInThisRun:true});continue;}
    throw error;
  }
  fs.writeFileSync(pagesPath,`${JSON.stringify(result.pages)}\n`,{flag:'wx',mode:0o600});
  const rowCount=result.pages.reduce((sum,page)=>sum+(JSON.parse(page.responseText).data?.length??0),0);
  const manifest={schemaVersion:1,mode:'L2_DEVELOPMENT_C_D_40_FULL_CROSS_SECTION',partition,sessionDate,sessionListSha256:contract.sessionListSha256,endpoint:result.endpoint,query:result.normalizedQuery,pageCount:result.pageCount,rowCount,aggregateSha256:result.aggregateSha256,minuteOnly:true,fetchedAt:new Date().toISOString()};
  manifest.manifestSha256=sha(JSON.stringify(manifest));
  fs.writeFileSync(manifestPath,`${JSON.stringify(manifest,null,2)}\n`,{flag:'wx',mode:0o600});
  completed.push({sessionDate,partition,pageCount:result.pageCount,rowCount,reused:false});
  console.log(JSON.stringify({sessionDate,partition,status:'L2_MINUTE_CACHED',pageCount:result.pageCount,rowCount,requestCount:requestBudget.consumed}));
}
completed.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));unavailable.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));
const summary={status:unavailable.length?'L2_MINUTE_ACQUISITION_PARTIAL':'L2_MINUTE_ACQUISITION_COMPLETE',approvedSessions:40,selectedSessions:selected.length,shardIndex,shardCount:4,completedSessions:completed.length,unavailableSessions:unavailable.length,sessionListSha256:contract.sessionListSha256,providerRequestsConsumedThisRun:requestBudget.consumed,providerRequestHardCeiling:maximumRequests,providerRequestsUnused:requestBudget.remaining,totalPages:completed.reduce((sum,x)=>sum+x.pageCount,0),totalRows:completed.reduce((sum,x)=>sum+x.rowCount,0),completed,unavailable,validationOpened:false,oosOpened:false};
fs.writeFileSync(summaryPath,`${JSON.stringify(summary,null,2)}\n`,{flag:'wx',mode:0o600});
console.log(JSON.stringify({...summary,completed:undefined}));
if(unavailable.length)process.exitCode=2;
