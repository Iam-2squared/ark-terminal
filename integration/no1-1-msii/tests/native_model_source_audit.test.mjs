import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {
 loadNo11PinnedModelManifest,validateNo11ModelManifest,
 inspectNo11LocalModelFiles
} from '../runtime/native_model_source_audit.mjs';
const sha=v=>createHash('sha256').update(v).digest('hex');
const gitBlob=v=>createHash('sha1').update('blob '+v.length+'\0').update(v).digest('hex');
function synthetic(){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'no11-native-model-'));
  fs.mkdirSync(path.join(root,'inputs','frozen_models'),{recursive:true});
  const rows=[];
  for(const h of [2,3,5])for(let n=1;n<=8;n++){
    const name='H'+h+'_BLOCK_'+String(n).padStart(2,'0')+'.json';
    const b=Buffer.from(JSON.stringify({fixture:true,horizon:h,block:n}));
    const member='inputs/frozen_models/'+name;
    fs.writeFileSync(path.join(root,member),b);
    rows.push({local_member:member,bytes:b.length,sha256:sha(b),git_blob:gitBlob(b)});
  }
  const manifest={original_model_member_N:24,status:'EXACT_MEMBER_HASH_PASS',
    models:rows,new_fit:0,new_inference:0,new_rank:0,
    model_payloads_verified_without_inference_or_fitting:true};
  return {root,manifest,cleanup:()=>fs.rmSync(root,{recursive:true,force:true})};
}
test('original external frozen model manifest matches pinned Git blob and 24 distinct H2/H3/H5 block files',()=>{
 const m=loadNo11PinnedModelManifest();
 assert.equal(validateNo11ModelManifest(m),true);
 assert.equal(m.models.length,24);
 assert.equal(new Set(m.models.map(x=>x.sha256)).size,24);
});
test('startup-only model audit verifies byte-exact 24 original-shape synthetic model members',()=>{
 const f=synthetic();
 try{
  const x=inspectNo11LocalModelFiles({manifest:f.manifest,modelRoot:f.root});
  assert.equal(x.status,'FROZEN_NATIVE_MODEL_BYTES_VERIFIED_READ_ONLY');
  assert.equal(x.verifiedModels,24);
  assert.equal(x.nativeDecisionEmitted,false);
  assert.equal(x.nativeSelectorConnected,false);
  assert.equal(x.productionReady,false);
  assert.equal(x.orderTransmission,false);
 }finally{f.cleanup()}
});
test('one missing and one modified model each fail closed, never retrain or invent a score',()=>{
 const f=synthetic();
 try{
  const file=x=>path.join(f.root,'inputs','frozen_models',x);
  fs.rmSync(file('H2_BLOCK_01.json'));
  fs.writeFileSync(file('H3_BLOCK_02.json'),'{"tampered":true}');
  const x=inspectNo11LocalModelFiles({manifest:f.manifest,modelRoot:f.root});
  assert.equal(x.status,'FROZEN_NATIVE_MODEL_SOURCE_UNAVAILABLE');
  assert.equal(x.missingModels,1);assert.equal(x.changedModels,1);
  assert.equal(x.nativeDecisionEmitted,false);
 }finally{f.cleanup()}
});
test('absent private source is incomplete, never a permission blocker to keep developing',()=>{
 const f=synthetic();
 try{
  const x=inspectNo11LocalModelFiles({manifest:f.manifest,modelRoot:path.join(f.root,'unavailable')});
  assert.equal(x.verifiedModels,0);assert.equal(x.missingModels,24);
  assert.equal(x.productionReady,false);
 }finally{f.cleanup()}
});
test('model path traversal, duplicate model, future fit and illegitimate source are rejected',()=>{
 const f=synthetic();
 try{
  assert.throws(()=>validateNo11ModelManifest({...f.manifest,new_fit:1}));
  assert.throws(()=>validateNo11ModelManifest({...f.manifest,models:[
    {...f.manifest.models[0],local_member:'../../secrets.json'},...f.manifest.models.slice(1)
  ]}));
  assert.throws(()=>validateNo11ModelManifest({...f.manifest,models:[
    {...f.manifest.models[0]},...f.manifest.models.slice(0,23)
  ]}));
  assert.throws(()=>inspectNo11LocalModelFiles({manifest:f.manifest,modelRoot:'relative/path'}),/NATIVE_MODEL_PRIVATE_ROOT_ABSOLUTE_REQUIRED/);
 }finally{f.cleanup()}
});
test('symlink model source never allowed to appear authenticated',()=>{
 const f=synthetic();
 try{
  const filename=path.join(f.root,'inputs','frozen_models','H5_BLOCK_01.json');
  fs.renameSync(filename,filename+'.orig');
  fs.symlinkSync(filename+'.orig',filename);
  const x=inspectNo11LocalModelFiles({manifest:f.manifest,modelRoot:f.root});
  assert.equal(x.unsafeModels,1);assert.equal(x.productionReady,false);
 }finally{f.cleanup()}
});
