// Read-only authority audit for the 24 frozen H2/H3/H5 Capital V5 model files.
// Runs at startup when local private model files are available, NOT for every tick.
// Does not execute a model, infer native No.1.1 signals, reset Safety or submit orders.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

export const NO11_MODEL_MANIFEST_BLOB='1cf7c59b55890ba51b570a28210fbec715d27f5e';
export const NO11_MODEL_AUTHORITY='research/capital-v5-sharp-drop-exit-reset20-20261007/FROZEN_NATIVE_INPUT_LINEAGE.json';
const frozenFreeze='10c94c92c4bd2a59a22744667fd0210252602df4';
const modelName=/^H([235])_BLOCK_(0[1-8])\.json$/;
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const fail=message=>{throw Error(message)};
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const manifestPath=path.join(root,NO11_MODEL_AUTHORITY);
function gitBlobHash(bytes) {
  return createHash('sha1').update(Buffer.from('blob '+bytes.length+'\0')).update(bytes).digest('hex');
}
export function loadNo11PinnedModelManifest(){
  const raw=fs.readFileSync(manifestPath);
  // Windows Git may checkout text as CRLF; this is only a memory normalization
  // to check the original exact Git blob. Never rewrite the authoritative file.
  const bytes=Buffer.from(raw.toString('utf8').replace(/\r\n/g,'\n'));
  if(gitBlobHash(bytes)!==NO11_MODEL_MANIFEST_BLOB)fail('NATIVE_MODEL_MANIFEST_BLOB_MISMATCH');
  const m=JSON.parse(bytes.toString('utf8'));
  validateNo11ModelManifest(m);
  return m;
}
export function validateNo11ModelManifest(m){
  if(m?.original_model_member_N!==24||m.models?.length!==24||
     m.status!=='EXACT_MEMBER_HASH_PASS'||m.new_fit!==0||
     m.new_inference!==0||m.new_rank!==0||
     m.model_payloads_verified_without_inference_or_fitting!==true) {
    fail('NATIVE_FROZEN_MODEL_MANIFEST_CONTRACT_INVALID');
  }
  const actual=new Set();
  for(const x of m.models){
    const name=path.posix.basename(x.local_member??'');
    if(typeof x.local_member!=='string'||
       x.local_member!=='inputs/frozen_models/'+name||
       !modelName.test(name)||
       !Number.isInteger(x.bytes)||x.bytes<1||
       !/^[a-f0-9]{64}$/.test(x.sha256??'')||
       !/^[a-f0-9]{40}$/.test(x.git_blob??'')||
       actual.has(name))fail('NATIVE_MODEL_MEMBER_IDENTITY_INVALID');
    actual.add(name);
  }
  for(const h of [2,3,5])for(let b=1;b<=8;b++){
    const name='H'+h+'_BLOCK_'+String(b).padStart(2,'0')+'.json';
    if(!actual.has(name))fail('NATIVE_MODEL_MEMBER_SET_INCOMPLETE');
  }
  return true;
}
function fileSafe(filename,base){
  try{
    const stat=fs.lstatSync(filename);
    if(!stat.isFile()||stat.isSymbolicLink())return false;
    const real=fs.realpathSync(filename);
    if(!real.startsWith(base+path.sep))return false;
    const parent=path.dirname(filename);
    const parentReal=fs.realpathSync(parent);
    if(!parentReal.startsWith(base+path.sep))return false;
    return true;
  }catch{return false;}
}
export function inspectNo11LocalModelFiles({manifest,modelRoot}={}){
  if(typeof modelRoot!=='string'||!path.isAbsolute(modelRoot))fail('NATIVE_MODEL_PRIVATE_ROOT_ABSOLUTE_REQUIRED');
  validateNo11ModelManifest(manifest);
  let safeRoot='';
  try{
    const stat=fs.lstatSync(modelRoot);
    if(!stat.isDirectory()||stat.isSymbolicLink())fail('NATIVE_MODEL_ROOT_UNSAFE');
    safeRoot=fs.realpathSync(modelRoot);
  }catch(error){
    if(error?.code!=='ENOENT')throw error;
  }
  const actual={verified:0,missing:0,changed:0,unsafe:0};
  for(const x of manifest.models){
    const name=path.posix.basename(x.local_member);
    const filename=path.join(modelRoot,'inputs','frozen_models',name);
    if(!safeRoot){actual.missing++;continue;}
    if(!fs.existsSync(filename)){actual.missing++;continue;}
    if(!fileSafe(filename,safeRoot)){actual.unsafe++;continue;}
    try{
      const bytes=fs.readFileSync(filename);
      if(bytes.length!==x.bytes||digest(bytes)!==x.sha256||gitBlobHash(bytes)!==x.git_blob){
        actual.changed++;
      }else actual.verified++;
    }catch{actual.unsafe++;}
  }
  const status=actual.verified===24&&actual.missing===0&&actual.changed===0&&actual.unsafe===0
    ? 'FROZEN_NATIVE_MODEL_BYTES_VERIFIED_READ_ONLY'
    : 'FROZEN_NATIVE_MODEL_SOURCE_UNAVAILABLE';
  return Object.freeze({
    schemaId:'ARK_NO11_FROZEN_NATIVE_MODEL_AUDIT_V1',status,
    sourceManifestBlob:NO11_MODEL_MANIFEST_BLOB,
    strategyFreezeCommit:frozenFreeze,
    expectedModels:24,verifiedModels:actual.verified,
    missingModels:actual.missing,changedModels:actual.changed,unsafeModels:actual.unsafe,
    nativeSelectorConnected:false,nativeEntryConnected:false,nativeExitConnected:false,
    nativeDecisionEmitted:false,brokerFeedArrivalCertified:false,
    productionReady:false,orderTransmission:false
  });
}
export function auditNo11FrozenModelSource({modelRoot}={}){
  return inspectNo11LocalModelFiles({manifest:loadNo11PinnedModelManifest(),modelRoot});
}
