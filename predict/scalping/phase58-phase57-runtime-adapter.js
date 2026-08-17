import {buildSynchronizedPhase57MicrostructureRecord,PHASE58_PHASE57_SNAPSHOT_SAFETY} from './phase58-phase57-snapshot-contract.js';

export const PHASE58_PHASE57_RUNTIME_ADAPTER_SAFETY=Object.freeze({
  ...PHASE58_PHASE57_SNAPSHOT_SAFETY,
  phase:'58.p8.phase57-runtime-adapter',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

const finite=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x));
const FORBIDDEN_OUTCOME_KEYS=Object.freeze([
  'futureBars','outcome','outcomes','grossReturnPct','netReturnPct','mfePct','maePct',
  'exitTimestamp','exitReason','barsHeld','hit','realizedReturn','label','target',
]);

function directionOf(x){
  const v=x?.direction??x?.signalDirection??x?.phase57Direction;
  if(v===1||v==='UP'||v==='LONG')return 1;
  if(v===-1||v==='DOWN'||v==='SHORT')return -1;
  if(v===0||v==='WAIT'||v==='ABSTAIN'||v==='NONE')return 0;
  return null;
}

function hasForbiddenOutcomeFields(x={}){
  return FORBIDDEN_OUTCOME_KEYS.filter(k=>Object.prototype.hasOwnProperty.call(x,k));
}

/**
 * Build the canonical Phase57 snapshot only from an already-frozen, point-in-time
 * Phase57 decision. This adapter deliberately does not reconstruct old decisions
 * from realized trade rows or later outcomes.
 */
export function buildFrozenPhase57SnapshotFromRuntimeDecision({decision,modelId,artifactSha256}={}){
  const blockers=[];
  const x=decision??{};
  const forbidden=hasForbiddenOutcomeFields(x);
  if(!decision||typeof decision!=='object')blockers.push('MISSING_PHASE57_RUNTIME_DECISION');
  if(forbidden.length)blockers.push('OUTCOME_FIELDS_PRESENT_IN_PHASE57_RUNTIME_DECISION');
  if(x.frozenByPhase57!==true)blockers.push('RUNTIME_DECISION_NOT_EXPLICITLY_FROZEN_BY_PHASE57');
  if(x.pointInTimeOnly!==true)blockers.push('PHASE57_POINT_IN_TIME_GUARD_MISSING');
  if(x.futureOutcomeUsed!==false)blockers.push('PHASE57_FUTURE_OUTCOME_GUARD_MISSING');
  if(x.thresholdSearchAfterCapture!==false)blockers.push('PHASE57_POST_CAPTURE_SEARCH_GUARD_MISSING');
  if(x.entryRetunedAfterCapture!==false)blockers.push('PHASE57_ENTRY_RETUNE_GUARD_MISSING');
  const direction=directionOf(x);
  if(direction===null)blockers.push('INVALID_PHASE57_RUNTIME_DIRECTION');
  const asOf=x.asOf??x.sourceTimestamp??x.timestamp??null;
  if(!asOf||!Number.isFinite(Date.parse(asOf)))blockers.push('INVALID_PHASE57_RUNTIME_ASOF');
  if(typeof modelId!=='string'||!modelId.trim())blockers.push('MISSING_PHASE57_MODEL_ID');
  if(typeof artifactSha256!=='string'||!/^[a-f0-9]{64}$/i.test(artifactSha256))blockers.push('INVALID_PHASE57_ARTIFACT_SHA256');
  const confidence=x.confidence==null?null:Number(x.confidence);
  if(confidence!==null&&(!finite(confidence)||confidence<0||confidence>1))blockers.push('INVALID_PHASE57_CONFIDENCE');

  if(blockers.length){
    return Object.freeze({
      phase:'58.p8.phase57-runtime-adapter',
      status:'BLOCKED_PHASE57_RUNTIME_SNAPSHOT',
      complete:false,
      blockers:Object.freeze(blockers),
      forbiddenOutcomeFields:Object.freeze(forbidden),
      safety:PHASE58_PHASE57_RUNTIME_ADAPTER_SAFETY,
    });
  }

  const snapshot=Object.freeze({
    direction,
    confidence,
    setup:x.setup??null,
    context:x.context??null,
    asOf,
    modelId:modelId.trim(),
    artifactSha256:artifactSha256.toLowerCase(),
    frozen:true,
    futureOutcomeUsed:false,
    thresholdSearchAfterCapture:false,
    entryRetunedAfterCapture:false,
  });
  return Object.freeze({
    phase:'58.p8.phase57-runtime-adapter',
    status:'FROZEN_PHASE57_RUNTIME_SNAPSHOT_BUILT',
    complete:true,
    snapshot,
    methodology:Object.freeze({
      reconstructedFromHistoricalOutcome:false,
      pointInTimeOnly:true,
      phase57DecisionFrozenBeforePhase58:true,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE58_PHASE57_RUNTIME_ADAPTER_SAFETY,
  });
}

export function buildProspectivePhase57Phase58Record({decision,modelId,artifactSha256,capturedAt,microstructure}={}){
  const built=buildFrozenPhase57SnapshotFromRuntimeDecision({decision,modelId,artifactSha256});
  if(!built.complete)return Object.freeze({
    phase:'58.p8.prospective-sync',status:'BLOCKED_PHASE57_RUNTIME_SNAPSHOT',complete:false,
    snapshotBuild:built,safety:PHASE58_PHASE57_RUNTIME_ADAPTER_SAFETY,
  });
  const synchronized=buildSynchronizedPhase57MicrostructureRecord({phase57Snapshot:built.snapshot,capturedAt,microstructure});
  return Object.freeze({
    phase:'58.p8.prospective-sync',
    status:synchronized.complete?'PROSPECTIVE_PHASE57_PHASE58_RECORD_READY':'BLOCKED_SYNCHRONIZATION',
    complete:synchronized.complete,
    snapshotBuild:built,
    synchronized,
    safety:PHASE58_PHASE57_RUNTIME_ADAPTER_SAFETY,
  });
}

export default {buildFrozenPhase57SnapshotFromRuntimeDecision,buildProspectivePhase57Phase58Record,PHASE58_PHASE57_RUNTIME_ADAPTER_SAFETY};
