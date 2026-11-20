import {createHash} from 'node:crypto';

export const JQUANTS_STORAGE_LIFECYCLE=Object.freeze({
  policyId:'PHASE57_LONG_ONLY_JQUANTS_STORAGE_LIFECYCLE_V1',
  privateUserOnly:true,
  publicRepositoryAllowed:false,
  rawAndCopiesDeleteRequired:true,
  reverseEngineerableDerivedDeleteRequired:true,
  privateNonReversibleResultsMayRemain:true,
  deadlinesJst:Object.freeze({DAILY:'2026-10-06T19:02:00+09:00',MASTER:'2026-10-06T19:02:00+09:00',MINUTE:'2026-10-06T19:07:00+09:00',CAUSAL_5M:'2026-10-06T19:07:00+09:00'}),
  officialSources:Object.freeze(['https://jpx-jquants.com/ja/termsofservice','https://jpx-jquants.com/ja/help/usage']),
});

const sha=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');

export function buildStoragePurgeDryRun({cacheManifest,nowJst='2026-09-15T00:00:00+09:00'}={}){
  if(!cacheManifest?.privateUserOnly||cacheManifest?.publiclyAccessible)throw new Error('cache is not confirmed private user-only storage');
  const objects=(cacheManifest.objects??[]).map((object,index)=>{
    const dataClass=String(object?.dataClass??'');
    const deadlineJst=JQUANTS_STORAGE_LIFECYCLE.deadlinesJst[dataClass];
    if(!deadlineJst)throw new Error(`unknown purge data class at object ${index}`);
    const relativePath=String(object?.relativePath??'');
    if(!String(object?.objectId??'')||!String(object?.sha256??'').match(/^[a-f0-9]{64}$/)||!relativePath||relativePath.startsWith('/')||relativePath.split(/[\\/]/).includes('..'))throw new Error(`object ${index} lacks safe immutable identity`);
    return Object.freeze({objectId:String(object.objectId),relativePath,dataClass,sha256:String(object.sha256),deadlineJst,action:'DELETE_AND_RECORD_TOMBSTONE'});
  });
  const output={mode:'PURGE_DRY_RUN_NO_DELETE',nowJst,objectCount:objects.length,objects:Object.freeze(objects),rawRetainedAfterDeadlineAllowed:false,automaticDeletionPerformed:false};
  return Object.freeze({...output,dryRunSha256:sha(output)});
}

export function assertPurgeCompletion({dryRun,completion}={}){
  if(completion?.dryRunSha256!==dryRun?.dryRunSha256)throw new Error('purge completion does not match frozen dry-run');
  const expected=new Set((dryRun.objects??[]).map(x=>x.objectId)),tombstones=completion?.tombstones??[];
  if(tombstones.length!==expected.size||tombstones.some(x=>!expected.delete(x.objectId)||!String(x.deletedEvidenceSha256??'').match(/^[a-f0-9]{64}$/)))throw new Error('purge tombstones are incomplete or invalid');
  return Object.freeze({status:'PURGE_EVIDENCE_COMPLETE',deletedObjects:tombstones.length,rawOrReversibleDataRetained:0});
}

export default {JQUANTS_STORAGE_LIFECYCLE,buildStoragePurgeDryRun,assertPurgeCompletion};
