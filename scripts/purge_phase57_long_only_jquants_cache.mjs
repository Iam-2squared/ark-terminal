import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {assertPurgeCompletion} from '../predict/long-only/phase57-long-only-storage-lifecycle.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const dryRunPath=arg('--dry-run'),cacheRootArg=arg('--cache-root'),confirmation=arg('--confirm-sha'),output=arg('--tombstones-output');
if(!dryRunPath||!cacheRootArg||!confirmation||!output)throw new Error('usage: --dry-run <json> --cache-root <private-root> --confirm-sha <dryRunSha256> --tombstones-output <json>');
const dryRun=JSON.parse(fs.readFileSync(dryRunPath,'utf8'));
if(dryRun.mode!=='PURGE_DRY_RUN_NO_DELETE'||confirmation!==dryRun.dryRunSha256)throw new Error('exact purge dry-run confirmation SHA-256 is required');
const cacheRoot=path.resolve(cacheRootArg),repoRoot=path.resolve(process.cwd());
if(cacheRoot===repoRoot||cacheRoot.startsWith(`${repoRoot}${path.sep}`)||cacheRoot===path.parse(cacheRoot).root)throw new Error('cache root must be an explicit private non-repository directory');
const tombstones=[];
for(const object of dryRun.objects??[]){
  const target=path.resolve(cacheRoot,object.relativePath);
  if(!target.startsWith(`${cacheRoot}${path.sep}`))throw new Error('purge target escaped private cache root');
  const bytes=fs.readFileSync(target),actual=createHash('sha256').update(bytes).digest('hex');
  if(actual!==object.sha256)throw new Error(`purge target hash mismatch: ${object.objectId}`);
  fs.unlinkSync(target);
  tombstones.push({objectId:object.objectId,deletedEvidenceSha256:createHash('sha256').update(`${object.objectId}|${object.sha256}|DELETED`).digest('hex')});
}
const completion={dryRunSha256:dryRun.dryRunSha256,completedAt:new Date().toISOString(),tombstones};
assertPurgeCompletion({dryRun,completion});
fs.writeFileSync(output,`${JSON.stringify(completion,null,2)}\n`,{flag:'wx',mode:0o600});
console.log(JSON.stringify({status:'PURGE_COMPLETE',deletedObjects:tombstones.length,rawOrReversibleDataRetained:0,tombstonesOutput:output}));
