import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {buildStoragePurgeDryRun} from '../predict/long-only/phase57-long-only-storage-lifecycle.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const cacheRootArg=arg('--cache-root'),manifestOutput=arg('--manifest-output'),dryRunOutput=arg('--dry-run-output');
if(!cacheRootArg||!manifestOutput||!dryRunOutput)throw new Error('usage: --cache-root <private-root> --manifest-output <json> --dry-run-output <json>');
const cacheRoot=path.resolve(cacheRootArg),repoRoot=path.resolve(process.cwd());
if(cacheRoot===repoRoot||cacheRoot.startsWith(`${repoRoot}${path.sep}`)||cacheRoot===path.parse(cacheRoot).root)throw new Error('cache root must be an explicit private non-repository directory');
const rawRoot=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2'),objects=[];
if(fs.existsSync(rawRoot))for(const sessionDate of fs.readdirSync(rawRoot).sort()){
  const lifecyclePath=path.join(rawRoot,sessionDate,'storage-lifecycle.json');
  if(!fs.existsSync(lifecyclePath))throw new Error(`storage lifecycle manifest missing: ${sessionDate}`);
  const lifecycle=JSON.parse(fs.readFileSync(lifecyclePath,'utf8'));
  if(lifecycle.privateUserOnly!==true||lifecycle.publiclyAccessible!==false)throw new Error(`storage privacy identity invalid: ${sessionDate}`);
  for(const object of lifecycle.objects??[]){
    const target=path.resolve(cacheRoot,object.relativePath);
    if(!target.startsWith(`${cacheRoot}${path.sep}`))throw new Error(`storage object escaped cache root: ${object.objectId}`);
    const actual=createHash('sha256').update(fs.readFileSync(target)).digest('hex');
    if(actual!==object.sha256)throw new Error(`storage object hash mismatch: ${object.objectId}`);
    objects.push(object);
  }
}
if(new Set(objects.map(x=>x.objectId)).size!==objects.length)throw new Error('duplicate storage lifecycle object identity');
const cacheManifest={schemaVersion:1,privateUserOnly:true,publiclyAccessible:false,cacheRoot,objects};
const dryRun=buildStoragePurgeDryRun({cacheManifest,nowJst:new Date().toISOString()});
fs.writeFileSync(manifestOutput,`${JSON.stringify(cacheManifest,null,2)}\n`,{flag:'wx',mode:0o600});
fs.writeFileSync(dryRunOutput,`${JSON.stringify(dryRun,null,2)}\n`,{flag:'wx',mode:0o600});
console.log(JSON.stringify({status:'PURGE_DRY_RUN_COMPLETE_NO_DELETE',objectCount:objects.length,dryRunSha256:dryRun.dryRunSha256}));
