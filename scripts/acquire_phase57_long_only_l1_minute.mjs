import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fetchJquantsPages} from '../predict/long-only/phase57-long-only-jquants-client.js';

const arg=name=>{const index=process.argv.indexOf(name);return index<0?null:process.argv[index+1];};
const cacheRoot=path.resolve(arg('--cache-root')??'');
const maximumRequests=Number(arg('--maximum-requests')??550);
if(!cacheRoot||!Number.isInteger(maximumRequests)||maximumRequests!==550)throw new Error('approved L1 acquisition requires --cache-root and --maximum-requests 550');
const apiKey=process.env.JQUANTS_API_KEY;if(!apiKey)throw new Error('JQUANTS_API_KEY is unavailable');
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const partitions=['DEVELOPMENT_A','DEVELOPMENT_B'];
const sessions=partitions.flatMap(partition=>allocation.partitions[partition].map(sessionDate=>({partition,sessionDate})));
const approvedSessionHash='6bc10cf3f55eb4cfcf0e5ffec65d2ccb50a633ca19c88c94a2f78c981945c2cd';
const actualSessionHash=createHash('sha256').update(JSON.stringify(sessions.map(x=>x.sessionDate))).digest('hex');
if(sessions.length!==40||actualSessionHash!==approvedSessionHash)throw new Error('Development A+B session list differs from operator approval');
const requestBudget={remaining:maximumRequests,consumed:0};
const sha=value=>createHash('sha256').update(value).digest('hex');
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2');

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
    continue;
  }
  if(fs.existsSync(pagesPath))throw new Error(`incomplete Minute cache requires quarantine: ${sessionDate}`);
  const result=await fetchJquantsPages({endpoint:'/equities/bars/minute',query:{date:sessionDate},apiKey,requestBudget,maxPages:100});
  fs.writeFileSync(pagesPath,`${JSON.stringify(result.pages)}\n`,{flag:'wx',mode:0o600});
  const rowCount=result.pages.reduce((sum,page)=>sum+(JSON.parse(page.responseText).data?.length??0),0);
  const manifest={schemaVersion:1,mode:'L1_DEVELOPMENT_A_B_FULL_CROSS_SECTION',partition,sessionDate,sessionListSha256:approvedSessionHash,endpoint:result.endpoint,query:result.normalizedQuery,pageCount:result.pageCount,rowCount,aggregateSha256:result.aggregateSha256,minuteOnly:true,fetchedAt:new Date().toISOString()};
  manifest.manifestSha256=sha(JSON.stringify(manifest));
  fs.writeFileSync(manifestPath,`${JSON.stringify(manifest,null,2)}\n`,{flag:'wx',mode:0o600});
  console.log(JSON.stringify({sessionDate,partition,status:'L1_MINUTE_CACHED',pageCount:result.pageCount,rowCount,requestCount:requestBudget.consumed}));
}
console.log(JSON.stringify({status:'L1_MINUTE_ACQUISITION_COMPLETE',sessions:40,sessionListSha256:approvedSessionHash,providerRequestsConsumed:requestBudget.consumed,providerRequestHardCeiling:maximumRequests,providerRequestsUnused:requestBudget.remaining,validationOpened:false,oosOpened:false}));
