/**
 * Frozen H2/H3/H5 saved OOF model metadata gate. Metadata ONLY; never
 * promotes an OOF fold to an unobserved future live date.
 * H5 is the reused CORE_P original head, NOT a new fitted H5 model.
 */
export const NO11_OOF_DISPATCH_SCHEMA='ARK_NO11_SAVED_24_OOF_MODEL_INDEX_V1';
const fail=x=>{throw Error(x)};
const date=x=>{
  if(typeof x!=='string'||!/^20\d\d-\d\d-\d\d$/.test(x))fail('NO11_OOF_DATE_INVALID');
  const n=Date.parse(x+'T00:00:00Z');
  if(!Number.isFinite(n)||new Date(n).toISOString().slice(0,10)!==x)
    fail('NO11_OOF_DATE_INVALID');
  return x;
};
const sha=x=>{
  if(typeof x!=='string'||!/^[a-f0-9]{64}$/.test(x))fail('NO11_OOF_MODEL_HASH_INVALID');
  return x;
};
export function inspectFrozenNo11OofModelDispatch({
 mode,index,requestedSession
}={}){
  if(mode!=='SYNTHETIC_OFFLINE_ONLY')fail('NO11_OOF_LIVE_MODEL_SELECTION_FORBIDDEN');
  const session=date(requestedSession);
  if(index?.schemaId!==NO11_OOF_DISPATCH_SCHEMA||
    index.metadataSource!=='PRIVATE_SAVED_FROZEN_OOF_MODELS'||
    !Array.isArray(index.models)||index.models.length!==24)
    fail('NO11_OOF_24_MODEL_METADATA_REQUIRED');
  const blocks=new Map(),seen=new Set(),allDates=new Set();
  for(const m of index.models){
    if(!m||typeof m!=='object'||!Number.isInteger(m.block)||
      m.block<1||m.block>8||!['H2','H3','H5'].includes(m.slot)||
      m.originalHead!==(m.slot==='H5'?'CORE_P':m.slot))
      fail('NO11_OOF_MODEL_IDENTITY_INVALID');
    const key=m.block+'|'+m.slot;
    if(seen.has(key))fail('NO11_OOF_DUPLICATE_MODEL');
    seen.add(key);
    sha(m.sha256);
    const through=date(m.trainThrough);
    if(!Array.isArray(m.testDates)||m.testDates.length<1||m.testDates.length>15)
      fail('NO11_OOF_TEST_DATES_INVALID');
    const days=m.testDates.map(date);
    if(new Set(days).size!==days.length||days.some(d=>d<=through))
      fail('NO11_OOF_LEAK_OR_DUPLICATE_TEST_DATE');
    if(blocks.has(m.block)){
      const b=blocks.get(m.block);
      if(b.trainThrough!==through||JSON.stringify(b.testDates)!==JSON.stringify(days))
        fail('NO11_OOF_HEAD_DATE_LINEAGE_MISMATCH');
      b.slots.add(m.slot);
    }else blocks.set(m.block,{trainThrough:through,testDates:days,slots:new Set([m.slot])});
  }
  if(blocks.size!==8)fail('NO11_OOF_EIGHT_BLOCKS_REQUIRED');
  let prevLast=null,selected=null;
  for(let block=1;block<=8;block++){
    const b=blocks.get(block);
    if(!b||b.slots.size!==3)fail('NO11_OOF_MISSING_HEAD_OR_BLOCK');
    if(prevLast!==null&&b.testDates[0]<=prevLast)
      fail('NO11_OOF_BLOCK_OVERLAP_OR_OUT_OF_ORDER');
    if(b.testDates.some(d=>allDates.has(d)))
      fail('NO11_OOF_TEST_DATE_DUPLICATE_ACROSS_BLOCKS');
    for(const d of b.testDates)allDates.add(d);
    prevLast=b.testDates.at(-1);
    if(b.testDates.includes(session))selected=block;
  }
  return Object.freeze({
    schemaId:'ARK_NO11_OOF_DISPATCH_AUDIT_RESULT_V1',
    requestedSession:session,savedMetadataRows:24,
    historicalOofBlock:selected,
    status:selected===null?'FUTURE_OR_UNASSIGNED_DATE_NO_FROZEN_MODEL_DISPATCH':
      'HISTORICAL_OOF_BLOCK_ONLY_NOT_LIVE_DISPATCH',
    futureLiveModelSelectionCertified:false,
    originalFrozenModelArtifactsShaVerifiedByThisGate:false,
    originalModelWeightsChanged:false,
    automaticallyChooseLatestBlock:false,
    automaticallyAverageAllBlocks:false,
    originalFrozenSelectorCertified:false,
    productionReady:false,orderTransmission:false
  });
}
