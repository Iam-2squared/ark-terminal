import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {acquireFormalL0Session} from '../predict/long-only/phase57-long-only-jquants-client.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const authorizationPath=arg('--authorization'),requestedPartition=arg('--partition')??'DEVELOPMENT_A';
if(!authorizationPath)throw new Error('usage: --authorization <private-runtime-authorization.json> --partition DEVELOPMENT_A');
const root=path.resolve(process.cwd()),plan=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const authorization=JSON.parse(fs.readFileSync(authorizationPath,'utf8')),cacheRoot=path.resolve(authorization.privateCacheRoot??'');
if(cacheRoot===root||cacheRoot.startsWith(`${root}${path.sep}`))throw new Error('raw cache must be private non-Git storage outside the repository');
const partitions=requestedPartition==='ALL_HISTORICAL'?Object.keys(allocation.partitions):[requestedPartition];
for(const partition of partitions)if(!Array.isArray(allocation.partitions?.[partition]))throw new Error('partition is not in frozen session allocation');
const apiKey=process.env.JQUANTS_API_KEY;if(!apiKey)throw new Error('JQUANTS_API_KEY is unavailable');

for(const partition of partitions)for(const sessionDate of allocation.partitions[partition]){
  const sessionDir=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2',sessionDate),manifestPath=path.join(sessionDir,'l0-manifest.json');
  if(fs.existsSync(manifestPath)){
    const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
    if(manifest.sessionDate!==sessionDate||manifest.partition!==partition||manifest.planSha256!==authorization.planSha256)throw new Error(`immutable cache identity mismatch: ${sessionDate}`);
    for(const [kind,expected] of [['daily',manifest.daily],['master',manifest.master]]){
      const pages=JSON.parse(fs.readFileSync(path.join(sessionDir,`${kind}-pages.json`),'utf8'));
      for(const page of pages)if(createHash('sha256').update(page.responseText).digest('hex')!==page.responseSha256)throw new Error(`immutable cache page hash mismatch: ${sessionDate} ${kind}`);
      if(pages.length!==expected.pageCount)throw new Error(`immutable cache page count mismatch: ${sessionDate} ${kind}`);
    }
    console.log(JSON.stringify({sessionDate,status:'IMMUTABLE_CACHE_REUSED_AND_HASH_VERIFIED'}));continue;
  }
  const result=await acquireFormalL0Session({plan,authorization,partition,sessionDate,apiKey});
  fs.mkdirSync(sessionDir,{recursive:true});
  fs.writeFileSync(path.join(sessionDir,'daily-pages.json'),`${JSON.stringify(result.daily.pages)}\n`,{flag:'wx',mode:0o600});
  fs.writeFileSync(path.join(sessionDir,'master-pages.json'),`${JSON.stringify(result.master.pages)}\n`,{flag:'wx',mode:0o600});
  const manifest={...result,daily:{...result.daily,pages:undefined},master:{...result.master,pages:undefined},fetchedAt:new Date().toISOString()};
  fs.writeFileSync(manifestPath,`${JSON.stringify(manifest,null,2)}\n`,{flag:'wx',mode:0o600});
  console.log(JSON.stringify({sessionDate,status:'FORMAL_L0_SESSION_CACHED',minuteRequests:0,manifestSha256:result.manifestSha256}));
}
