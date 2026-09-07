import fs from 'node:fs';

const specUrl=new URL('../research/phase57-selector-capacity-v2-phase-a.json',import.meta.url);

function deepFreeze(value){
  if(value&&typeof value==='object'&&!Object.isFrozen(value)){
    for(const child of Object.values(value))deepFreeze(child);
    Object.freeze(value);
  }
  return value;
}

export const PHASE57_SELECTOR_CAPACITY_V2_PHASE_A=deepFreeze(JSON.parse(fs.readFileSync(specUrl,'utf8')));

const FORBIDDEN_INPUT_KEYS=Object.freeze([
  'outcome','label','target','futureReturn','realizedReturn','entry','exit','positionSize','capitalAllocation',
]);
const ALLOWED_CAPACITIES=Object.freeze(new Set([0,5,10,15,20]));
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const clamp=(value,min=0,max=1)=>Math.min(max,Math.max(min,Number(value)));
const round8=value=>Number(Number(value).toFixed(8));

function assertFrozenIdentity(hybridResult){
  if(hybridResult?.modelDigest!==PHASE57_SELECTOR_CAPACITY_V2_PHASE_A.baseline.modelDigest)throw new Error('Capacity v2 requires the Frozen Hybrid v1 model digest');
  for(const key of FORBIDDEN_INPUT_KEYS)if(Object.prototype.hasOwnProperty.call(hybridResult,key))throw new Error(`Capacity v2 input contains forbidden ${key}`);
  if(!Array.isArray(hybridResult?.ranked)||!Array.isArray(hybridResult?.selected))throw new TypeError('Capacity v2 requires Frozen Hybrid ranked and selected rows');
  for(let index=0;index<hybridResult.ranked.length;index+=1){
    const row=hybridResult.ranked[index];
    if(row.hybridRank!==index+1)throw new Error('Frozen Hybrid ranking is not a contiguous prefix source');
    for(const key of FORBIDDEN_INPUT_KEYS)if(Object.prototype.hasOwnProperty.call(row??{},key))throw new Error(`Capacity v2 ranked row contains forbidden ${key}`);
  }
}

export function extractPhase57CapacityV2Inputs({hybridResult,decisionTime}={}){
  assertFrozenIdentity(hybridResult);
  const decisionMs=Date.parse(String(decisionTime??hybridResult.featureCutoff??''));
  if(!Number.isFinite(decisionMs))throw new TypeError('Capacity v2 requires a valid decisionTime');
  const ranked=hybridResult.ranked;
  const first=ranked[0],fifth=ranked[4];
  const qualityReady=finite(first?.hybridScore)&&finite(fifth?.hybridScore)&&Number(first.hybridScore)>0;
  const hybridQualityDecayRank5To1=qualityReady?round8(clamp(1-Number(fifth.hybridScore)/Math.max(Number(first.hybridScore),1e-8))):null;
  const qualifiedCandidateCount=ranked.filter(row=>finite(row?.stage2?.remainingOpportunityScore)&&Number(row.stage2.remainingOpportunityScore)>=0.65).length;
  const breadthValues=ranked.map(row=>row?.features?.marketBreadth).filter(finite).map(Number);
  const marketBreadth=breadthValues.length&&breadthValues.every(value=>value===breadthValues[0])?breadthValues[0]:null;
  const inspected=ranked.slice(0,20);
  const valid=inspected.filter(row=>finite(row.hybridScore)&&finite(row?.stage2?.remainingOpportunityScore)&&finite(row?.features?.marketBreadth)).length;
  const dataQualityConfidence=inspected.length?valid/inspected.length:0;
  return deepFreeze({
    status:'CAPACITY_V2_CAUSAL_INPUTS_READY',decisionTime:new Date(decisionMs).toISOString(),
    features:{hybridQualityDecayRank5To1,qualifiedCandidateCount,marketBreadth,dataQualityConfidence},
    featureAvailability:{hybridQualityDecayRank5To1:qualityReady,qualifiedCandidateCount:true,marketBreadth:marketBreadth!==null,dataQualityConfidence:true},
    sourceModelDigest:hybridResult.modelDigest,futureInformationUsed:false,entryExitAllocationUsed:false,
  });
}

export function applyPhase57CapacityV2Prefix({hybridResult,capacity}={}){
  assertFrozenIdentity(hybridResult);
  if(!ALLOWED_CAPACITIES.has(capacity))throw new Error('Capacity v2 decision must be one of 0, 5, 10, 15 or 20');
  if(hybridResult.selected.length===0&&capacity!==0)throw new Error('Capacity v2 Phase A preserves Frozen Hybrid v1 ABSTAIN');
  const selected=hybridResult.ranked.slice(0,capacity);
  const prefixIdentity=selected.every((row,index)=>row.symbol===hybridResult.ranked[index].symbol&&row.hybridRank===index+1);
  if(!prefixIdentity)throw new Error('Capacity v2 violated Frozen Hybrid prefix identity');
  return deepFreeze({status:'CAPACITY_V2_PREFIX_READY',capacity,selected,prefixIdentity,reranked:false,sourceModelDigest:hybridResult.modelDigest});
}

export function planPhase57CapacityV2OrdinalAllocation({reserveSessionCount=282}={}){
  if(reserveSessionCount!==282)throw new Error('Capacity v2 Phase A is frozen to the existing 282-session reserve identity');
  return deepFreeze({
    developmentOrdinals:[1,60],purgeDevelopmentValidationOrdinal:61,validationOrdinals:[62,90],
    purgeValidationOosOrdinal:91,untouchedOosOrdinals:[92,120],remainingReserveOrdinals:[121,282],
    developmentSessions:60,validationSessions:29,untouchedOosSessions:29,purgeSessions:2,
    totalAllocatedIncludingPurges:120,reserveRemainingSessions:162,sessionDatesMaterialized:false,
  });
}
