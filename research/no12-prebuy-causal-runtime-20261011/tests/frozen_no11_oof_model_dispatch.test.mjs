import test from 'node:test';
import assert from 'node:assert/strict';
import {inspectFrozenNo11OofModelDispatch as inspect,
 NO11_OOF_DISPATCH_SCHEMA as SCHEMA} from '../runtime/frozen_no11_oof_model_dispatch.mjs';
function fixture(){
 const models=[];
 for(let block=1;block<=8;block++){
  const d=String(block).padStart(2,'0');
  for(const slot of ['H2','H3','H5'])
   models.push({block,slot,originalHead:slot==='H5'?'CORE_P':slot,
    sha256:'a'.repeat(64),trainThrough:'2025-06-30',
    testDates:['2025-07-'+d]});
 }
 return {mode:'SYNTHETIC_OFFLINE_ONLY',
  index:{schemaId:SCHEMA,metadataSource:'PRIVATE_SAVED_FROZEN_OOF_MODELS',models},
  requestedSession:'2026-10-13'};
}
test('2026-10-13 is not automatically assigned to the last historical OOF block',()=>{
 const r=inspect(fixture());
 assert.equal(r.savedMetadataRows,24);
 assert.equal(r.historicalOofBlock,null);
 assert.equal(r.status,'FUTURE_OR_UNASSIGNED_DATE_NO_FROZEN_MODEL_DISPATCH');
 assert.equal(r.automaticallyChooseLatestBlock,false);
 assert.equal(r.automaticallyAverageAllBlocks,false);
 assert.equal(r.productionReady,false);
});
test('historical OOF block assignment is reference-only, never live authorization',()=>{
 const f=fixture();f.requestedSession='2025-07-05';
 const r=inspect(f);
 assert.equal(r.historicalOofBlock,5);
 assert.equal(r.status,'HISTORICAL_OOF_BLOCK_ONLY_NOT_LIVE_DISPATCH');
 assert.equal(r.futureLiveModelSelectionCertified,false);
});
test('H5 head must retain original CORE_P lineage',()=>{
 const f=fixture();f.index.models[2].originalHead='H5';
 assert.throws(()=>inspect(f),/NO11_OOF_MODEL_IDENTITY_INVALID/);
});
test('missing or duplicated frozen model metadata fails closed',()=>{
 const a=fixture();a.index.models.pop();
 assert.throws(()=>inspect(a),/NO11_OOF_24_MODEL_METADATA_REQUIRED/);
 const b=fixture();b.index.models[1]={...b.index.models[0]};
 assert.throws(()=>inspect(b),/NO11_OOF_DUPLICATE_MODEL/);
});
test('chronological leakage and different H2/H3/H5 block dates fail',()=>{
 const a=fixture();a.index.models[0].trainThrough='2025-07-01';
 assert.throws(()=>inspect(a),/NO11_OOF_LEAK_OR_DUPLICATE_TEST_DATE/);
 const b=fixture();b.index.models[2].testDates=['2025-07-09'];
 assert.throws(()=>inspect(b),/NO11_OOF_HEAD_DATE_LINEAGE_MISMATCH/);
});
test('source identity and model hashes must be explicit',()=>{
 const a=fixture();a.index.metadataSource='RETRAINED_LIVE_MODEL';
 assert.throws(()=>inspect(a),/NO11_OOF_24_MODEL_METADATA_REQUIRED/);
 const b=fixture();b.index.models[1].sha256='not-sha';
 assert.throws(()=>inspect(b),/NO11_OOF_MODEL_HASH_INVALID/);
});
test('no future live inference or trade can be enabled by this module',()=>{
 const a=fixture();a.mode='LIVE_TRADING';
 assert.throws(()=>inspect(a),/NO11_OOF_LIVE_MODEL_SELECTION_FORBIDDEN/);
});
