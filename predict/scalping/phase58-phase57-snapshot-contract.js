export const PHASE58_PHASE57_SNAPSHOT_SAFETY=Object.freeze({
  phase:'58.p8.phase57-snapshot',
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

const finite=x=>Number.isFinite(Number(x));
const parseMs=x=>{const t=Date.parse(x??'');return Number.isFinite(t)?t:null;};

function normalizeDirection(x){
  if(x===1||x==='UP'||x==='LONG')return 1;
  if(x===-1||x==='DOWN'||x==='SHORT')return -1;
  if(x===0||x==='WAIT'||x==='ABSTAIN'||x==='NONE'||x==null)return 0;
  throw new Error('phase57 direction must be LONG/SHORT/UP/DOWN/+1/-1 or WAIT/ABSTAIN/0');
}

function freshnessBoundary(x,asOfMs,captureMs,blockers){
  const context=x?.context&&typeof x.context==='object'?x.context:{};
  const closeRaw=context.sourceBarCloseAt;
  if(closeRaw===null||closeRaw===undefined||closeRaw==='')return asOfMs;
  const closeMs=parseMs(closeRaw);
  const duration=Number(context.sourceBarDurationMinutes);
  if(closeMs===null){
    blockers.push('INVALID_PHASE57_SOURCE_BAR_CLOSE_AT');
    return asOfMs;
  }
  if(!Number.isFinite(duration)||duration<=0){
    blockers.push('INVALID_PHASE57_SOURCE_BAR_DURATION');
    return asOfMs;
  }
  if(asOfMs!==null&&closeMs-asOfMs!==duration*60_000)blockers.push('PHASE57_SOURCE_BAR_CLOSE_MISMATCH');
  if(captureMs!==null&&closeMs>captureMs)blockers.push('PHASE57_SOURCE_BAR_CLOSE_IN_FUTURE');
  return closeMs;
}

export function validateFrozenPhase57Snapshot(snapshot,{captureAsOf,maxAgeMs=300000}={}){
  const blockers=[];
  if(!snapshot||typeof snapshot!=='object')blockers.push('MISSING_PHASE57_SNAPSHOT');
  const x=snapshot??{};
  const direction=(()=>{try{return normalizeDirection(x.direction)}catch{blockers.push('INVALID_PHASE57_DIRECTION');return 0;}})();
  const asOfMs=parseMs(x.asOf);
  const captureMs=parseMs(captureAsOf);
  if(asOfMs===null)blockers.push('INVALID_PHASE57_ASOF');
  if(captureMs===null)blockers.push('INVALID_CAPTURE_ASOF');
  if(asOfMs!==null&&captureMs!==null&&asOfMs>captureMs)blockers.push('PHASE57_FUTURE_TIMESTAMP');
  const freshnessMs=freshnessBoundary(x,asOfMs,captureMs,blockers);
  if(freshnessMs!==null&&captureMs!==null&&captureMs-freshnessMs>maxAgeMs)blockers.push('STALE_PHASE57_SNAPSHOT');
  if(x.frozen!==true)blockers.push('PHASE57_NOT_FROZEN');
  if(typeof x.modelId!=='string'||!x.modelId.trim())blockers.push('MISSING_PHASE57_MODEL_ID');
  if(typeof x.artifactSha256!=='string'||!/^[a-f0-9]{64}$/i.test(x.artifactSha256))blockers.push('INVALID_PHASE57_ARTIFACT_SHA256');
  if(x.futureOutcomeUsed!==false)blockers.push('PHASE57_FUTURE_OUTCOME_GUARD_MISSING');
  if(x.thresholdSearchAfterCapture!==false)blockers.push('PHASE57_POST_CAPTURE_SEARCH_GUARD_MISSING');
  if(x.entryRetunedAfterCapture!==false)blockers.push('PHASE57_ENTRY_RETUNE_GUARD_MISSING');
  const confidence=x.confidence==null?null:Number(x.confidence);
  if(confidence!==null&&(!finite(confidence)||confidence<0||confidence>1))blockers.push('INVALID_PHASE57_CONFIDENCE');
  return Object.freeze({
    phase:'58.p8.phase57-snapshot',
    status:blockers.length?'BLOCKED':'FROZEN_PHASE57_SNAPSHOT_READY',
    complete:blockers.length===0,
    blockers:Object.freeze(blockers),
    freshness:Object.freeze({
      featureCutoffAsOf:x.asOf??null,
      freshnessAsOf:freshnessMs===null?null:new Date(freshnessMs).toISOString(),
      sourceBarCloseMetadataUsed:freshnessMs!==null&&asOfMs!==null&&freshnessMs!==asOfMs,
      maxAgeMs,
    }),
    normalized:Object.freeze({
      direction,
      confidence:confidence===null?null:confidence,
      setup:x.setup??null,
      context:x.context??null,
      asOf:x.asOf??null,
      modelId:x.modelId??null,
      artifactSha256:x.artifactSha256??null,
      frozen:x.frozen===true,
      futureOutcomeUsed:false,
      thresholdSearchAfterCapture:false,
      entryRetunedAfterCapture:false,
    }),
    safety:PHASE58_PHASE57_SNAPSHOT_SAFETY,
  });
}

export function buildSynchronizedPhase57MicrostructureRecord({phase57Snapshot,capturedAt,microstructure}={}){
  const validation=validateFrozenPhase57Snapshot(phase57Snapshot,{captureAsOf:capturedAt});
  if(!validation.complete)return Object.freeze({phase:'58.p8.sync',status:'BLOCKED_PHASE57_SNAPSHOT',complete:false,validation,safety:PHASE58_PHASE57_SNAPSHOT_SAFETY});
  return Object.freeze({
    phase:'58.p8.sync',
    status:'SYNCHRONIZED_PHASE57_MICROSTRUCTURE_READY',
    complete:true,
    capturedAt,
    phase57:validation.normalized,
    microstructure,
    methodology:Object.freeze({
      phase57DirectionIsFrozenBase:true,
      phase58MayConfirmDeferOrAbstainOnly:true,
      phase58MayReverseDirection:false,
      pointInTimeOnly:true,
      futureOutcomeUsed:false,
      sameTimestampRequired:true,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE58_PHASE57_SNAPSHOT_SAFETY,
  });
}

export default {validateFrozenPhase57Snapshot,buildSynchronizedPhase57MicrostructureRecord,PHASE58_PHASE57_SNAPSHOT_SAFETY};
