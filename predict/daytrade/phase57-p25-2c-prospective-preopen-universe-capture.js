import {buildP252PointInTimeUniverseAtDecision} from './phase57-p25-2b-point-in-time-oos-substrate.js';

export const PHASE57_P25_2C_SAFETY=Object.freeze({
  phase:'57.p25.2c.prospective-preopen-universe-capture',
  mode:'READ_ONLY_PROSPECTIVE_UNIVERSE_CAPTURE',
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

export const PHASE57_P25_2C_POLICY=Object.freeze({
  captureTimeZone:'Asia/Tokyo',
  preOpenCutoffHm:'08:50',
  scheduledBatchSize:620,
  scheduledBatchesPerCycle:6,
  maxRowAgeMs:12*60*60*1000,
  minimumEligibleCrossSection:3000,
  maxPerSector:4,
  requiresCompletedScreenerCycle:true,
  oneFrozenUniversePerSession:true,
  performanceSelectionAllowed:false,
  entryThresholdRelaxationAllowed:false,
});

const JST=new Intl.DateTimeFormat('en-CA',{
  timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23',
});

function jstParts(timestamp){
  const ms=Date.parse(String(timestamp??''));
  if(!Number.isFinite(ms))throw new TypeError('snapshot generatedAt must be a valid timestamp');
  const parts=Object.fromEntries(JST.formatToParts(new Date(ms)).map(x=>[x.type,x.value]));
  return {sessionDate:`${parts.year}-${parts.month}-${parts.day}`,hm:`${parts.hour}:${parts.minute}`};
}

function blocked({snapshot,reason,detail=null}){
  const generatedAt=snapshot?.meta?.generatedAt??snapshot?.generatedAt??null;
  let sessionDate=null,hm=null;
  try{({sessionDate,hm}=jstParts(generatedAt));}catch{}
  return Object.freeze({
    phase:'57.p25.2c.prospective-preopen-universe-capture',
    status:'BLOCKED_PROSPECTIVE_PREOPEN_UNIVERSE',
    ready:false,
    reason,
    detail,
    sessionDate,
    captureHmJst:hm,
    sourceSnapshotGeneratedAt:generatedAt,
    methodology:Object.freeze({
      prospectiveOnly:true,
      historicalBackfill:false,
      currentOuterOosPerformanceUsed:false,
      entryThresholdRelaxed:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_2C_SAFETY,
  });
}

export function buildP252ProspectivePreopenUniverseRecord({snapshot}={}){
  const generatedAt=snapshot?.meta?.generatedAt??snapshot?.generatedAt??null;
  const {sessionDate,hm}=jstParts(generatedAt);
  if(hm>=PHASE57_P25_2C_POLICY.preOpenCutoffHm){
    return blocked({snapshot,reason:'CAPTURE_AFTER_PREOPEN_CUTOFF',detail:{cutoffHmJst:PHASE57_P25_2C_POLICY.preOpenCutoffHm}});
  }
  if(snapshot?.meta?.refreshProgress?.cycleComplete!==true){
    return blocked({snapshot,reason:'SCREENER_CYCLE_INCOMPLETE',detail:{refreshProgress:snapshot?.meta?.refreshProgress??null}});
  }

  const pointInTime=buildP252PointInTimeUniverseAtDecision({
    sessionDate,
    decisionTimestamp:generatedAt,
    snapshots:[snapshot],
    minimumEligibleCrossSection:PHASE57_P25_2C_POLICY.minimumEligibleCrossSection,
    maxPerSector:PHASE57_P25_2C_POLICY.maxPerSector,
    maxSnapshotAgeMs:0,
    maxRowAgeMs:PHASE57_P25_2C_POLICY.maxRowAgeMs,
  });
  if(!pointInTime.ready){
    return blocked({snapshot,reason:`PIT_${pointInTime.reason}`,detail:{eligibleCount:pointInTime.eligibleCount,inputCount:pointInTime.inputCount,sourceSnapshotFingerprint:pointInTime.sourceSnapshotFingerprint}});
  }

  return Object.freeze({
    phase:'57.p25.2c.prospective-preopen-universe-capture',
    status:'PROSPECTIVE_PREOPEN_UNIVERSE_FROZEN',
    ready:true,
    sessionDate,
    captureHmJst:hm,
    sourceSnapshotGeneratedAt:generatedAt,
    sourceSnapshotFingerprint:pointInTime.sourceSnapshotFingerprint,
    inputCount:pointInTime.inputCount,
    eligibleCount:pointInTime.eligibleCount,
    variants:pointInTime.variants,
    rankAudit:pointInTime.rankAudit,
    methodology:Object.freeze({
      prospectiveOnly:true,
      historicalBackfill:false,
      completedScreenerCycleRequired:true,
      oneFrozenRankForDynamic30_40_50:true,
      currentOuterOosPerformanceUsed:false,
      entryThresholdRelaxed:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_2C_SAFETY,
  });
}

export default {buildP252ProspectivePreopenUniverseRecord,PHASE57_P25_2C_POLICY,PHASE57_P25_2C_SAFETY};
